"""v2.0-a tests — Artwork Source layer (additive, identity-preserving).

Proves Sources are created beneath Designs, derived applications link to their origin
Source, assets re-point to Sources, and the existing Design/Asset/Product structure is
untouched (dual-run).

Run: python -m kf_asset_manager.tests_v2a
"""
import sys, tempfile, os
from pathlib import Path

from PIL import Image

from . import model

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else " FAIL ") + name)


def run():
    lib = Path(tempfile.mkdtemp()) / "Curtains"
    lib.mkdir(parents=True)
    def jpg(n, c=(80, 80, 80)):
        Image.new("RGB", (32, 32), c).save(lib / n, "JPEG")
    # P4186: sided panels + sided derived cushions
    jpg("P4186-L.jpg", (10, 20, 30)); jpg("P4186-R.jpg", (40, 50, 60))
    jpg("P4186-L-cush.jpg", (11, 21, 31)); jpg("P4186-R-cush.jpg", (41, 51, 61))
    # P4204 master + V2 sibling, each with a derived cushion
    jpg("P4204.jpg", (1, 2, 3)); jpg("P4204-cush.jpg", (4, 5, 6))
    jpg("P4204-V2.jpg", (7, 8, 9)); jpg("P4204-V2-cush.jpg", (10, 11, 12))
    # a plain flat curtain (no derivation)
    jpg("Kids-3033-L.jpg", (100, 100, 0)); jpg("Kids-3033-R.jpg", (100, 90, 0))

    db = model.IdentityDB(str(lib.parent / "v2a.db"))
    model.build_graph(db, lib)
    c = db.conn

    check("counts include artwork_sources", "artwork_sources" in db.counts())
    check("sources were created", db.counts()["artwork_sources"] > 0)
    check("source IDs are opaque KF-SRC",
          all(r[0].startswith("KF-SRC-") for r in c.execute("SELECT source_id FROM artwork_sources")))

    # find the P4186 design (engineered_panel, has 2 cushion sources)
    p4186 = c.execute("""SELECT a.design_id FROM assets a WHERE a.filename='P4186-L.jpg'""").fetchone()[0]
    srcs = c.execute("SELECT application,side,origin FROM artwork_sources WHERE design_id=? ORDER BY application,side",
                     (p4186,)).fetchall()
    apps = sorted((s[0], s[1], s[2]) for s in srcs)
    check("P4186 has 4 sources (Curtain L/R + Cushion L/R)", len(srcs) == 4)
    check("P4186 has both Curtain sides", ("Curtain", "L", "Original") in apps and ("Curtain", "R", "Original") in apps)
    check("P4186 cushions are Derived", ("Cushion", "L", "Derived") in apps and ("Cushion", "R", "Derived") in apps)

    # derived cushion source links to its same-side Original Curtain source
    cushL = c.execute("SELECT source_id,derived_from_source FROM artwork_sources "
                      "WHERE design_id=? AND application='Cushion' AND side='L'", (p4186,)).fetchone()
    curL = c.execute("SELECT source_id FROM artwork_sources "
                     "WHERE design_id=? AND application='Curtain' AND side='L'", (p4186,)).fetchone()[0]
    check("derived cushion links to its origin Curtain source", cushL["derived_from_source"] == curL)

    # every asset re-points to a source
    n_assets = c.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
    n_linked = c.execute("SELECT COUNT(*) FROM assets WHERE source_id IS NOT NULL").fetchone()[0]
    check("every asset is linked to a source", n_assets == n_linked and n_assets > 0)

    # identity preserved / dual-run: products still exist exactly as before
    p4186_prods = c.execute("SELECT product_type FROM products WHERE design_id=?", (p4186,)).fetchall()
    types = sorted(p[0] for p in p4186_prods)
    check("P4186 still has Curtain + 2 Cushion products (unchanged)", types == ["Curtain", "Cushion", "Cushion"])

    # P4204 + V2 are two designs sharing one family; each has its own sources
    fam = c.execute("SELECT family_id FROM designs WHERE design_id IN "
                    "(SELECT design_id FROM assets WHERE filename='P4204.jpg') AND family_id IS NOT NULL").fetchone()
    check("P4204 family exists (master + V2 siblings)", fam is not None)

    # flat curtain (no derivation) -> one Curtain source per side, no Derived
    kids = c.execute("SELECT design_id FROM assets WHERE filename='Kids-3033-L.jpg'").fetchone()[0]
    kids_derived = c.execute("SELECT COUNT(*) FROM artwork_sources WHERE design_id=? AND origin='Derived'", (kids,)).fetchone()[0]
    check("flat curtain has no derived sources", kids_derived == 0)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(run())
