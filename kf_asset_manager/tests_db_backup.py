"""db_backup tests — WAL-safe backup, restore, --fresh integration, configurable
destination. No real API calls, no Shopify writes — pure local filesystem/sqlite.

Run: python -m kf_asset_manager.tests_db_backup
"""
import sys, tempfile, os, io
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from PIL import Image

from . import model, db_backup, build_graph

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else " FAIL ") + name)


def _seeded_db(tmp):
    """A database with real identity + non-derivable data: vision_results, is_match,
    and an accepted display_title — the exact things that must survive backup/restore."""
    lib = tmp / "Curtains"; lib.mkdir(parents=True)
    for n, c in [("P4186-L", (1, 2, 3)), ("P4186-R", (4, 5, 6))]:
        Image.new("RGB", (16, 16), c).save(lib / (n + ".jpg"), "JPEG")
    db = model.IdentityDB(str(tmp / "audit.db"))
    model.build_graph(db, lib)
    conn = db.conn
    aid, sha = conn.execute("SELECT asset_id,sha256 FROM assets WHERE filename='P4186-L.jpg'").fetchone()
    db.record_vision_ai(aid, sha, suggested_name="Botanical Damask", style_tags=["floral"],
                        is_match=True, match_confidence=0.91, match_reason="matches",
                        model="claude-sonnet-5")
    pid = conn.execute("SELECT product_id FROM products WHERE product_type='Curtain'").fetchone()[0]
    db.set_title(pid, "Royal Damask Curtain (accepted)")
    return db, tmp / "audit.db", pid, aid


def run():
    tmp = Path(tempfile.mkdtemp())

    # ---- WAL-safety: THE core proof, live connection, no close, no manual checkpoint ----
    db, db_path, pid, aid = _seeded_db(tmp)
    wal_path = Path(str(db_path) + "-wal")
    check("fixture genuinely has unmerged WAL content before backup",
          wal_path.exists() and wal_path.stat().st_size > 0)

    backup1 = db_backup.backup_database(str(db_path), tmp / "backups1")
    check("backup_database succeeds against a live, open, uncheckpointed connection",
          backup1.exists())
    check("backup filename is timestamped under the resolved directory",
          backup1.parent == (tmp / "backups1"))

    # Check self-containment IMMEDIATELY, before anything else opens/uses the backup file.
    # Once something DOES open it (below, via IdentityDB, which itself forces WAL mode on
    # any database it manages), it will legitimately grow its own -wal/-shm — that's
    # normal WAL behaviour for an in-use database, not a defect in the backup itself.
    check("backup file is self-contained immediately after creation (no -wal/-shm yet)",
          not Path(str(backup1) + "-wal").exists() and not Path(str(backup1) + "-shm").exists())

    verify1 = model.IdentityDB(str(backup1))
    check("WAL-only committed data (accepted title) IS present in the backup",
          verify1.title_for(pid) == "Royal Damask Curtain (accepted)")
    vis1 = verify1.get_vision(aid)
    check("WAL-only committed AI data IS present in the backup",
          vis1 and vis1["suggested_name"] == "Botanical Damask" and vis1["is_match"] is True)
    verify1.conn.close()

    # ---- manual backup command ----
    out = io.StringIO()
    with redirect_stdout(out):
        rc = db_backup._main(["--db", str(db_path), "--backup-dir", str(tmp / "manual_backups")])
    check("manual backup CLI returns 0", rc == 0)
    check("manual backup CLI creates a file", any((tmp / "manual_backups").glob("*.db")))
    check("manual backup CLI prints the same-drive caveat (not hardware-failure protection)",
          "NOT protect against physical drive failure" in out.getvalue())

    # ---- configurable destination: explicit dir > env var > same-drive default ----
    explicit_dir = tmp / "explicit_dest"
    b_explicit = db_backup.backup_database(str(db_path), explicit_dir)
    check("explicit dest_dir argument is honoured", b_explicit.parent == explicit_dir)

    os.environ["KF_BACKUP_DIR"] = str(tmp / "env_dest")
    try:
        resolved = db_backup.resolve_backup_dir(str(db_path))
        check("KF_BACKUP_DIR env var is honoured when no explicit dir given",
              resolved == tmp / "env_dest")
    finally:
        del os.environ["KF_BACKUP_DIR"]

    default_resolved = db_backup.resolve_backup_dir(str(db_path))
    check("same-drive default (no config) is a 'backups/' folder next to the db",
          default_resolved == db_path.resolve().parent / "backups")
    check("nothing hard-codes a specific drive name anywhere in the resolution",
          "Work_4TB" not in str(default_resolved))

    # ---- restore + restore verification (the dedicated function) ----
    restore_target = tmp / "restored" / "audit.db"
    restored_path = db_backup.restore_database(backup1, restore_target)
    check("restore_database creates the target file", restored_path.exists())

    report = db_backup.verify_restore(db_path, restored_path)
    check("verify_restore reports all_ok=True for a faithful restore", report["checks"]["all_ok"])
    check("verify_restore checks table counts match", report["checks"]["table_counts_match"])
    check("verify_restore checks display_titles match (non-derivable)",
          report["checks"]["display_titles_match"])
    check("verify_restore checks vision_results/is_match match (non-derivable)",
          report["checks"]["vision_suggestions_match"])
    check("verify_restore checks schema_migrations state matches",
          report["checks"]["schema_migrations_match"])

    restored_db = model.IdentityDB(str(restored_path))
    check("restored database is independently queryable and correct",
          restored_db.title_for(pid) == "Royal Damask Curtain (accepted)")

    # restore refuses to silently clobber an existing file without --overwrite
    raised = False
    try:
        db_backup.restore_database(backup1, restore_target)
    except db_backup.BackupError:
        raised = True
    check("restore_database refuses to overwrite an existing file without overwrite=True", raised)
    ok2 = db_backup.restore_database(backup1, restore_target, overwrite=True)
    check("restore_database with overwrite=True succeeds", ok2.exists())

    # restore correctly clears stale sidecars at the destination first
    stale_wal = Path(str(restore_target) + "-wal")
    stale_wal.write_bytes(b"stale garbage from a previous db at this path")
    db_backup.restore_database(backup1, restore_target, overwrite=True)
    check("restore clears stale -wal sidecars at the destination before copying in",
          not stale_wal.exists())

    # ---- --fresh integration: automatic safety snapshot before the wipe ----
    tmp2 = Path(tempfile.mkdtemp())
    db2, db2_path, pid2, aid2 = _seeded_db(tmp2)
    db2.conn.close()
    lib2 = tmp2 / "Curtains"
    out_dir = tmp2 / "reports"
    backup_dir2 = tmp2 / "fresh_backups"
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        build_graph.main(["--root", str(lib2), "--report", "--out", str(out_dir),
                          "--no-hash", "--fresh", "--db", str(db2_path),
                          "--backup-dir", str(backup_dir2)])
    check("--fresh with configurable --backup-dir does not crash", True)  # would've raised above
    fresh_backups = list(backup_dir2.glob("*pre-fresh*.db"))
    check("--fresh produced an automatic pre-fresh safety snapshot", len(fresh_backups) == 1)

    presnap_db = model.IdentityDB(str(fresh_backups[0]))
    check("the pre-fresh snapshot contains the data that --fresh was about to erase",
          presnap_db.title_for(pid2) == "Royal Damask Curtain (accepted)")

    post_fresh_db = model.IdentityDB(str(db2_path))
    check("--fresh actually wiped the live database (confirms the snapshot was necessary)",
          post_fresh_db.title_for(pid2) != "Royal Damask Curtain (accepted)")

    # ---- --fresh refuses to proceed if the safety snapshot cannot be created ----
    tmp3 = Path(tempfile.mkdtemp())
    db3, db3_path, pid3, aid3 = _seeded_db(tmp3)
    db3.conn.close()
    lib3 = tmp3 / "Curtains"
    unwritable_parent = tmp3 / "not_a_real_dir_because_this_is_a_file"
    unwritable_parent.write_text("occupying this path as a file, not a directory")
    buf2 = io.StringIO()
    with redirect_stdout(buf2), redirect_stderr(buf2):
        rc3 = build_graph.main(["--root", str(lib3), "--report", "--out", str(tmp3 / "reports"),
                                "--no-hash", "--fresh", "--db", str(db3_path),
                                "--backup-dir", str(unwritable_parent / "sub")])
    check("--fresh REFUSES (does not wipe) when the safety snapshot cannot be created",
          rc3 == 2)
    still_there_db = model.IdentityDB(str(db3_path))
    check("original data survives when --fresh refuses due to a failed snapshot",
          still_there_db.title_for(pid3) == "Royal Damask Curtain (accepted)")

    # ---- list_backups: read-only visibility, no rotation logic ----
    backups_listed = db_backup.list_backups(str(db_path), tmp / "backups1")
    check("list_backups finds the backup created earlier", backup1 in backups_listed)

    # ---- CLI restore + verify end-to-end ----
    out3 = io.StringIO()
    with redirect_stdout(out3):
        rc4 = db_backup._main(["--db", str(db_path), "--restore", str(backup1),
                              "--dest", str(tmp / "cli_restored" / "audit.db"),
                              "--verify-against", str(db_path)])
    check("CLI --restore --verify-against returns 0 on a faithful restore", rc4 == 0)
    check("CLI restore reports verification OK", "verification: OK" in out3.getvalue())

    # ---- boundary: nothing here touches identity/SKU/vision/manifest/Shopify code ----
    import inspect
    src = inspect.getsource(db_backup)
    check("db_backup.py never imports vision_provider (no AI/network path)",
          "vision_provider" not in src)
    check("db_backup.py never imports sku.py, shopify_export.py, or vision_review.py",
          all(m not in src for m in ("import sku", "shopify_export", "vision_review")))

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(run())
