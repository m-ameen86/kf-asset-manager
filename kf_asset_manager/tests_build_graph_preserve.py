"""Regression test — build_graph DB preservation fix.

CRITICAL BUG FIXED: build_graph used to silently delete audit.db on every run without
--db, erasing NON-DERIVABLE paid AI vision results, local colour analysis, and manual
display_title overrides. This proves: (1) the default (no --fresh) PRESERVES all of that
across a re-run of the exact same command a user would routinely run, and (2) --fresh
still gives a genuine clean wipe when explicitly requested.

Run: python -m kf_asset_manager.tests_build_graph_preserve
"""
import sys, tempfile, io
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from PIL import Image

from . import model, build_graph

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else " FAIL ") + name)


def _silent_main(argv):
    """Run build_graph.main() with stdout/stderr swallowed (it prints progress)."""
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        build_graph.main(argv)


def run():
    lib = Path(tempfile.mkdtemp()) / "Curtains"
    lib.mkdir(parents=True)
    for n, c in [("P4186-L", (1, 2, 3)), ("P4186-R", (4, 5, 6))]:
        Image.new("RGB", (16, 16), c).save(lib / (n + ".jpg"), "JPEG")
    out_dir = lib.parent / "reports"

    # ---- run 1: the routine command a user actually runs (no --db, no --fresh) ----
    _silent_main(["--root", str(lib), "--report", "--out", str(out_dir), "--no-hash"])
    db_path = out_dir / "audit.db"
    check("first run creates audit.db", db_path.exists())

    db = model.IdentityDB(str(db_path))
    asset = db.conn.execute("SELECT asset_id, sha256 FROM assets LIMIT 1").fetchone()
    product = db.conn.execute("SELECT product_id FROM products LIMIT 1").fetchone()
    aid, sha, pid = asset["asset_id"], asset["sha256"], product["product_id"]
    design_ids_before = sorted(r[0] for r in db.conn.execute("SELECT design_id FROM designs"))
    product_count_before = db.conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]

    # simulate REAL paid AI work + a manual title override — the exact scenario that was lost
    db.record_vision_colours(aid, sha, [{"hex": "#1B2A4A", "percentage": 90, "named": "KF Navy"}])
    db.record_vision_ai(aid, sha, suggested_name="Sleepy Moon & Stars Nursery Print",
                        style_tags=["kids", "nursery"], is_match=True, match_confidence=0.85,
                        match_reason="whimsical night-sky kids print", model="claude-sonnet-5")
    db.set_title(pid, "Royal Damask Curtain (manually approved)")
    db.conn.close()

    # ---- run 2: the SAME routine command again (the real-world trigger of the bug) ----
    _silent_main(["--root", str(lib), "--report", "--out", str(out_dir), "--no-hash"])

    db2 = model.IdentityDB(str(db_path))
    vis = db2.get_vision(aid)
    check("re-run (no --fresh) PRESERVES vision_results",
          vis is not None and vis.get("suggested_name") == "Sleepy Moon & Stars Nursery Print")
    check("re-run PRESERVES colour extraction",
          vis is not None and vis.get("colours") and vis["colours"][0]["named"] == "KF Navy")
    check("re-run PRESERVES is_match", vis is not None and vis.get("is_match") is True)
    check("re-run PRESERVES the manual display_title override",
          db2.title_for(pid) == "Royal Damask Curtain (manually approved)")
    design_ids_after = sorted(r[0] for r in db2.conn.execute("SELECT design_id FROM designs"))
    check("re-run keeps identity idempotent (same design IDs, no duplicates)",
          design_ids_before == design_ids_after)
    check("re-run does not duplicate products (same count, not doubled)",
          db2.conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == product_count_before)
    db2.conn.close()

    # ---- run 3: explicit --fresh WIPES everything, including the paid AI data ----
    _silent_main(["--root", str(lib), "--report", "--out", str(out_dir), "--no-hash", "--fresh"])
    db3 = model.IdentityDB(str(db_path))
    # asset IDs are re-minted fresh (new DB), so re-check by filename instead of the old id
    new_asset = db3.conn.execute("SELECT asset_id FROM assets WHERE filename LIKE 'P4186-L%'").fetchone()
    vis3 = db3.get_vision(new_asset["asset_id"]) if new_asset else None
    check("--fresh actually wipes vision_results (no leftover AI data)",
          vis3 is None or vis3.get("suggested_name") is None)
    new_product = db3.conn.execute("SELECT product_id FROM products LIMIT 1").fetchone()
    check("--fresh wipes manual display_title overrides too",
          db3.title_for(new_product["product_id"]) != "Royal Damask Curtain (manually approved)")
    db3.conn.close()

    # ---- --fresh is documented clearly in --help ----
    help_buf = io.StringIO()
    with redirect_stdout(help_buf):
        try:
            build_graph.main(["--help"])
        except SystemExit:
            pass
    helptext = help_buf.getvalue()
    check("--fresh is documented as destructive in --help",
          "--fresh" in helptext and ("DESTRUCTIVE" in helptext or "wipe" in helptext.lower()))
    check("--db default is documented as preserved, not rebuilt",
          "PRESERVED" in helptext or "preserved" in helptext.lower())

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(run())
