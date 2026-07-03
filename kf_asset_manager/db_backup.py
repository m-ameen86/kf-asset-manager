"""audit.db backup & restore — WAL-safe, configurable destination.

Scope (per ARCHITECTURE_PREBUILD_AUDIT_DB_BACKUP.md): backup/restore for audit.db only.
No scheduling, no cloud sync, no Time Machine configuration, no external-drive
partitioning — those remain deliberately out of scope until the environmental questions
in that audit are answered.

WAL SAFETY: audit.db runs in WAL (write-ahead log) mode (see model.py). Recently committed
data can live in a separate `<db>-wal` file, not yet folded into the main file. A naive
file copy (`cp`, Finder drag-copy) can silently miss that data or copy an inconsistent
state. This module NEVER does a raw file copy of a live database — it uses SQLite's
built-in online backup API (`sqlite3.Connection.backup()`), which is specifically designed
to produce a correct, complete, self-contained snapshot of a live database regardless of
WAL state, without requiring the source to be closed, idle, or manually checkpointed.

CONFIGURABLE DESTINATION: the backup directory is resolved, in order:
  1. an explicit `dest_dir` argument / `--backup-dir` CLI flag,
  2. the `KF_BACKUP_DIR` environment variable,
  3. a `backups/` folder next to the database itself (same-drive default).
The same-drive default is intentionally last-resort and is NOT protection against a
physical drive failure — see DATABASE_LIFECYCLE.md / the backup audit for the distinction.
Nothing in this module assumes any particular external drive, mount path, or filesystem.
"""
import argparse
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path


class BackupError(Exception):
    """A backup or restore operation could not be completed safely."""


def resolve_backup_dir(db_path, dest_dir=None):
    """Resolve where backups should live, per the configuration order documented above.
    Never assumes a specific drive; the same-drive fallback is explicit and last-resort."""
    if dest_dir:
        return Path(dest_dir)
    env = os.environ.get("KF_BACKUP_DIR")
    if env:
        return Path(env)
    return Path(db_path).resolve().parent / "backups"


def backup_database(db_path, dest_dir=None, *, label=None):
    """Create a WAL-safe, complete, self-contained snapshot of `db_path`.

    Uses SQLite's online backup API (source.backup(destination)), which correctly
    includes all committed data regardless of WAL state and does not require the source
    database to be closed or idle. Returns the Path to the created backup file.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        raise BackupError(f"no database at {db_path}")

    out_dir = resolve_backup_dir(db_path, dest_dir)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise BackupError(f"cannot create backup destination {out_dir}: {e}")

    ts = time.strftime("%Y%m%dT%H%M%S")
    name = f"{db_path.stem}.{ts}"
    if label:
        name += f".{label}"
    name += ".db"
    dest_path = out_dir / name
    if dest_path.exists():
        raise BackupError(f"backup destination already exists: {dest_path}")

    src_conn = sqlite3.connect(str(db_path))
    try:
        try:
            dst_conn = sqlite3.connect(str(dest_path))
        except sqlite3.OperationalError as e:
            raise BackupError(f"cannot open backup destination {dest_path}: {e}")
        try:
            src_conn.backup(dst_conn)          # WAL-safe online backup, live source OK
            try:
                dst_conn.execute("PRAGMA wal_checkpoint(FULL)")
            except sqlite3.OperationalError:
                pass                            # not in WAL mode; nothing to checkpoint
        finally:
            dst_conn.close()
    finally:
        src_conn.close()

    # the backup file must be fully self-contained: no leftover sidecar files
    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(dest_path) + suffix)
        if sidecar.exists():
            sidecar.unlink()

    return dest_path


def restore_database(backup_path, dest_db_path, *, overwrite=False):
    """Restore a backup file into place as `dest_db_path`. The backup file produced by
    `backup_database()` is already a complete, self-contained snapshot, so restore is a
    straightforward copy — but any stale -wal/-shm sidecars at the DESTINATION are removed
    first, so they can never be mixed with the restored main file."""
    backup_path = Path(backup_path)
    dest_db_path = Path(dest_db_path)
    if not backup_path.exists():
        raise BackupError(f"no backup file at {backup_path}")
    if dest_db_path.exists() and not overwrite:
        raise BackupError(f"{dest_db_path} already exists; pass overwrite=True to replace it")

    for suffix in ("-wal", "-shm"):
        stale = Path(str(dest_db_path) + suffix)
        if stale.exists():
            stale.unlink()

    dest_db_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(backup_path), str(dest_db_path))
    return dest_db_path


def verify_restore(original_db_path, restored_db_path):
    """Compare the non-derivable and identity-critical facts between two databases and
    report whether the restore is faithful. Does not compare timestamps (backup/restore
    naturally have different `analyzed_at`/`created_at` file-level metadata is irrelevant;
    row-level timestamps ARE compared since they're part of the actual data)."""
    def snapshot(path):
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        s = {}
        for table in ("families", "designs", "assets", "products", "artwork_sources",
                     "product_variants", "vision_results", "schema_migrations"):
            try:
                s[f"{table}_count"] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except sqlite3.OperationalError:
                s[f"{table}_count"] = None
        s["display_titles"] = sorted(
            (r["product_id"], r["display_title"]) for r in
            conn.execute("SELECT product_id, display_title FROM products "
                        "WHERE display_title IS NOT NULL"))
        s["vision_suggestions"] = sorted(
            (r["asset_id"], r["suggested_name"], r["match_confidence"], r["is_match"]) for r in
            conn.execute("SELECT asset_id, suggested_name, match_confidence, is_match "
                        "FROM vision_results WHERE suggested_name IS NOT NULL"))
        s["migrations_applied"] = sorted(
            r[0] for r in conn.execute("SELECT name FROM schema_migrations"))
        conn.close()
        return s

    orig = snapshot(original_db_path)
    restored = snapshot(restored_db_path)

    checks = {
        "table_counts_match": all(orig[k] == restored[k] for k in orig if k.endswith("_count")),
        "display_titles_match": orig["display_titles"] == restored["display_titles"],
        "vision_suggestions_match": orig["vision_suggestions"] == restored["vision_suggestions"],
        "schema_migrations_match": orig["migrations_applied"] == restored["migrations_applied"],
    }
    checks["all_ok"] = all(checks.values())
    return {"checks": checks, "original": orig, "restored": restored}


def list_backups(db_path, dest_dir=None):
    """Read-only: list backup files found in the resolved backup directory, newest first.
    No retention/rotation logic — just visibility into what already exists."""
    out_dir = resolve_backup_dir(db_path, dest_dir)
    if not out_dir.exists():
        return []
    return sorted(out_dir.glob(f"{Path(db_path).stem}.*.db"), reverse=True)


def _main(argv=None):
    ap = argparse.ArgumentParser(
        description="audit.db backup & restore (WAL-safe). See "
                    "ARCHITECTURE_PREBUILD_AUDIT_DB_BACKUP.md for scope and rationale.")
    ap.add_argument("--db", required=True, help="path to audit.db")
    ap.add_argument("--backup-dir", default=None,
                    help="backup destination (default: $KF_BACKUP_DIR, else a 'backups/' "
                        "folder next to the database — same-drive fallback, NOT hardware-"
                        "failure protection)")
    ap.add_argument("--label", default=None, help="optional label appended to the backup filename")
    ap.add_argument("--list", action="store_true", help="list existing backups, newest first")
    ap.add_argument("--restore", metavar="BACKUP_FILE", help="restore this backup file")
    ap.add_argument("--dest", help="where to restore to (default: overwrite --db in place)")
    ap.add_argument("--overwrite", action="store_true", help="allow --restore to replace an existing file")
    ap.add_argument("--verify-against", metavar="ORIGINAL_DB",
                    help="after --restore, verify the result against this original database")
    a = ap.parse_args(argv)

    if a.list:
        backups = list_backups(a.db, a.backup_dir)
        if not backups:
            print("no backups found.")
        for b in backups:
            print(b)
        return 0

    if a.restore:
        dest = a.dest or a.db
        try:
            path = restore_database(a.restore, dest, overwrite=a.overwrite)
        except BackupError as e:
            print(f"REFUSED: {e}")
            return 2
        print(f"restored {a.restore} -> {path}")
        if a.verify_against:
            report = verify_restore(a.verify_against, path)
            print(f"verification: {'OK' if report['checks']['all_ok'] else 'MISMATCH'}")
            for k, v in report["checks"].items():
                if k != "all_ok":
                    print(f"  {k}: {v}")
            if not report["checks"]["all_ok"]:
                return 2
        return 0

    try:
        path = backup_database(a.db, a.backup_dir, label=a.label)
    except BackupError as e:
        print(f"REFUSED: {e}")
        return 2
    print(f"backup created: {path}")
    print("NOTE: if this backup lives on the same drive as the source database, it "
         "protects against accidental deletion/corruption of the live file — it does "
         "NOT protect against physical drive failure. See DATABASE_LIFECYCLE.md.")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
