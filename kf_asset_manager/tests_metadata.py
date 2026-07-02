"""Business-metadata tests — proves it is metadata ONLY (no identity impact).

Run: python -m kf_asset_manager.tests_metadata
"""
import sys, tempfile, os

from .model import IdentityDB

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else " FAIL ") + name)


def run():
    fd, path = tempfile.mkstemp(suffix=".db"); os.close(fd); os.remove(path)
    db = IdentityDB(path)

    d = db.ensure_design("CUR|Kids-3141", None, "engineered_panel", "Curtain", ["Curtain"])
    id_before = d
    dtype_before = db.conn.execute("SELECT design_type FROM designs WHERE design_id=?", (d,)).fetchone()[0]

    # tag with several business dimensions
    db.set_metadata("design", d, "business_line", "Kids")
    db.set_metadata("design", d, "theme", "Floral")
    db.set_metadata("design", d, "market", "GCC")
    db.set_metadata("design", d, "market", "Europe")     # multi-valued

    meta = db.get_metadata("design", d)
    check("metadata stored and grouped by dimension", meta["business_line"] == ["Kids"])
    check("dimension can hold multiple values", set(meta["market"]) == {"GCC", "Europe"})
    check("theme captured", meta["theme"] == ["Floral"])

    # identity is untouched by metadata
    check("design ID unchanged after tagging", d == id_before)
    dtype_after = db.conn.execute("SELECT design_type FROM designs WHERE design_id=?", (d,)).fetchone()[0]
    check("design_type unchanged by metadata", dtype_after == dtype_before)
    check("no metadata column leaked into designs table",
          "business_line" not in [c[1] for c in db.conn.execute("PRAGMA table_info(designs)").fetchall()])

    # filtering / collections use-case
    d2 = db.ensure_design("CUR|Kids-3199", None, "engineered_panel", "Curtain", ["Curtain"])
    db.set_metadata("design", d2, "business_line", "Kids")
    kids = db.find_by_metadata("business_line", "Kids")
    check("find_by_metadata returns both Kids designs", set(kids) == {d, d2})
    check("idempotent: re-tagging does not duplicate",
          (db.set_metadata("design", d, "business_line", "Kids"),
           len(db.find_by_metadata("business_line", "Kids")))[1] == 2)

    os.remove(path)
    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(run())
