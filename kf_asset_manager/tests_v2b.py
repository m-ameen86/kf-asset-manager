"""v2.0-b tests — products realized from Artwork Sources; bypass + discriminator retired.

Proves the two special cases the production data flagged as routine are dissolved:
  * SC1 (compatibility bypass / `from_derived`) → gone: products are authorised by Sources.
  * SC2 (product discriminator) → gone: products are distinguished by Source identity.
…while every design still produces the same products and identity is preserved.

Run: python -m kf_asset_manager.tests_v2b
"""
import sys, tempfile
from pathlib import Path
from PIL import Image

from . import model, audit

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else " FAIL ") + name)


def run():
    lib = Path(tempfile.mkdtemp()) / "Curtains"
    lib.mkdir(parents=True)
    def jpg(n, c):
        Image.new("RGB", (24, 24), c).save(lib / n, "JPEG")
    # sided panels + sided derived cushions (the SC1/SC2 archetype)
    jpg("P4186-L.jpg", (10, 20, 30)); jpg("P4186-R.jpg", (40, 50, 60))
    jpg("P4186-L-cush.jpg", (11, 21, 31)); jpg("P4186-R-cush.jpg", (41, 51, 61))
    # an unsided base + one derived cushion
    jpg("P4190.jpg", (5, 5, 5)); jpg("P4190-cush.jpg", (6, 6, 6))
    # a plain curtain, no derivation
    jpg("Kids-3040-L.jpg", (90, 90, 0)); jpg("Kids-3040-R.jpg", (90, 80, 0))

    db = model.IdentityDB(str(lib.parent / "v2b.db"))
    model.build_graph(db, lib)
    c = db.conn

    # --- the two mechanisms are physically gone from the schema ---
    cols = {r[1] for r in c.execute("PRAGMA table_info(products)")}
    check("products.from_derived column retired", "from_derived" not in cols)
    check("products.product_discriminator column retired", "product_discriminator" not in cols)
    check("products.source_id column present", "source_id" in cols)

    # --- SC1 & SC2 dissolved per the auditor ---
    rep = audit.generate_reports(db, lib, lib.parent / "rep", do_hash=False)
    sc1, sc2, sc3, sc4 = rep["sc"]
    check("SC1 (compatibility bypass) = 0", sc1 == 0)
    check("SC2 (product discriminator) = 0", sc2 == 0)
    check("SC3 (derived artwork) persists legitimately (>0)", sc3 > 0)

    # --- products are correct: P4186 still Curtain + 2 Cushion, now by Source ---
    p4186 = c.execute("SELECT design_id FROM assets WHERE filename='P4186-L.jpg'").fetchone()[0]
    types = sorted(r[0] for r in c.execute("SELECT product_type FROM products WHERE design_id=?", (p4186,)))
    check("P4186 backs Curtain + 2 Cushion products", types == ["Curtain", "Cushion", "Cushion"])

    # the single Curtain product GROUPS both panels (source_id = '')
    cur_prod = c.execute("SELECT product_id,source_id FROM products WHERE design_id=? AND product_type='Curtain'", (p4186,)).fetchall()
    check("one grouped Curtain product (source_id empty)", len(cur_prod) == 1 and cur_prod[0]["source_id"] == "")
    cur_variants = c.execute("SELECT COUNT(*) FROM product_variants WHERE product_id=?", (cur_prod[0]["product_id"],)).fetchone()[0]
    check("Curtain product has both L/R panels as variants", cur_variants == 2)

    # the two Cushion products are distinguished by distinct DERIVED sources (no discriminator)
    cush = c.execute("""SELECT p.source_id, s.origin, s.side FROM products p
                        JOIN artwork_sources s ON p.source_id=s.source_id
                        WHERE p.design_id=? AND p.product_type='Cushion'
                        ORDER BY s.side""", (p4186,)).fetchall()
    check("2 Cushion products map to 2 distinct sources", len({r["source_id"] for r in cush}) == 2)
    check("both Cushion sources are Derived", all(r["origin"] == "Derived" for r in cush))
    check("Cushion products distinguished by side via Source", sorted(r["side"] for r in cush) == ["L", "R"])

    # --- compatibility still HOLDS on the original path (no general widening) ---
    refused = False
    try:
        db.ensure_product(p4186, None, "Tote")           # not derived, not compatible
    except model.IncompatibleProductError:
        refused = True
    check("incompatible ORIGINAL product still refused", refused)

    # --- identity preserved: ids are opaque, every product realized & linked ---
    check("product IDs opaque KF-PRD",
          all(r[0].startswith("KF-PRD-") for r in c.execute("SELECT product_id FROM products")))
    linked = c.execute("SELECT COUNT(*) FROM products p WHERE NOT EXISTS "
                       "(SELECT 1 FROM product_variants v WHERE v.product_id=p.product_id)").fetchone()[0]
    check("every product has at least one variant", linked == 0)

    # plain curtain has exactly one Curtain product, no cushions
    kids = c.execute("SELECT design_id FROM assets WHERE filename='Kids-3040-L.jpg'").fetchone()[0]
    kt = sorted(r[0] for r in c.execute("SELECT product_type FROM products WHERE design_id=?", (kids,)))
    check("plain curtain backs exactly one Curtain product", kt == ["Curtain"])

    # --- v2.0-c: schema_version bumped + manifest emitted ---
    import json
    check("schema_version is 2 (Artwork Source layer)", db.versions()["schema_version"] == 2)
    man_path = lib.parent / "rep" / "manifest.json"
    check("manifest.json emitted", man_path.exists())
    man = json.loads(man_path.read_text())
    check("manifest records schema_version 2", man.get("schema_version") == 2)
    check("manifest records SC1/SC2 retired (0)",
          man["architecture"]["sc1_compatibility_bypass"] == 0 and
          man["architecture"]["sc2_product_discriminator"] == 0)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(run())
