"""Phase 4-c / 4-d tests — display titles + manifest SKU/title export.

Run: python -m kf_asset_manager.tests_phase4
"""
import sys, tempfile, json
from pathlib import Path
from PIL import Image

from . import model, audit, sku

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else " FAIL ") + name)


def run():
    # ---- descriptors (4-c/4-d shared) ----
    check("descriptor Left", sku.variant_descriptor(side="L") == "Left")
    check("descriptor Right", sku.variant_descriptor(side="R") == "Right")
    check("descriptor Single", sku.variant_descriptor(merged=True) == "Single")
    check("descriptor Colour 02", sku.variant_descriptor(colorway="2") == "Colour 02")
    check("descriptor pair/base is None", sku.variant_descriptor() is None)
    check("inputs from fabric role", sku.variant_inputs("fabric-c03", None)["colorway"] == "03")
    check("inputs from merged role", sku.variant_inputs("single-merged", None)["merged"] is True)

    # ---- build a mixed library ----
    lib = Path(tempfile.mkdtemp())
    cur = lib / "Curtains"; cur.mkdir(parents=True)
    for n, c in [("P4186-L", (1, 2, 3)), ("P4186-R", (4, 5, 6)),
                 ("P4186-L-cush", (7, 8, 9)), ("P4186-R-cush", (10, 11, 12)),
                 ("P4190-C", (5, 5, 5))]:
        Image.new("RGB", (16, 16), c).save(cur / (n + ".jpg"), "JPEG")
    fab = lib / "Fabrics"; fab.mkdir()
    for n, c in [("G122-1", (20, 20, 20)), ("G122-2", (30, 30, 30))]:
        Image.new("RGB", (16, 16), c).save(fab / (n + ".jpg"), "JPEG")
    db = model.IdentityDB(str(lib / "x.db"))
    model.build_graph(db, lib)
    c = db.conn

    # ---- 4-c: titles ----
    cur_prod = c.execute("SELECT product_id FROM products WHERE product_type='Curtain' AND source_id='' LIMIT 1").fetchone()[0]
    check("curtain generated title", db.title_for(cur_prod).endswith("Curtain"))
    cushL = c.execute("""SELECT p.product_id FROM products p JOIN artwork_sources s ON p.source_id=s.source_id
                         WHERE p.product_type='Cushion' AND s.side='L' LIMIT 1""").fetchone()[0]
    check("cushion-left title carries (Left)", db.title_for(cushL).endswith("Cushion (Left)"))

    before_sku = sku.sku("Curtain", c.execute("SELECT design_id FROM products WHERE product_id=?", (cur_prod,)).fetchone()[0])
    db.set_title(cur_prod, "Royal Damask")
    check("manual title overrides default", db.title_for(cur_prod) == "Royal Damask")
    check("override did NOT change SKU", sku.sku("Curtain", c.execute("SELECT design_id FROM products WHERE product_id=?", (cur_prod,)).fetchone()[0]) == before_sku)
    db.set_title(cur_prod, None)
    check("clearing title falls back to default", db.title_for(cur_prod).endswith("Curtain"))

    # display_title is not identity
    check("display_title column exists on products",
          "display_title" in {r[1] for r in c.execute("PRAGMA table_info(products)")})

    # ---- 4-d: manifest export ----
    rep = audit.generate_reports(db, lib, lib / "rep", do_hash=False)
    m = json.loads((lib / "rep" / "manifest.json").read_text())
    check("manifest has products array", "products" in m and len(m["products"]) >= 5)
    check("skus.csv emitted", (lib / "rep" / "skus.csv").exists())

    allskus = {v["sku"] for p in m["products"] for v in p["variants"]}
    check("curtain L/R variant SKUs present",
          any(s.endswith("-L") and s.startswith("KF-CUR-") for s in allskus) and
          any(s.endswith("-R") and s.startswith("KF-CUR-") for s in allskus))
    check("merged single SKU present", any(s.endswith("-SINGLE") for s in allskus))
    check("fabric colourway SKUs present",
          any(s.endswith("-C01") and s.startswith("KF-FAB-") for s in allskus) and
          any(s.endswith("-C02") for s in allskus))
    # two distinct cushion products, side-specific base SKUs
    cush_bases = sorted(p["sku"] for p in m["products"] if p["product_type"] == "Cushion")
    check("two cushion products with -L/-R base SKUs",
          len(cush_bases) == 2 and cush_bases[0].endswith("-L") and cush_bases[1].endswith("-R"))
    # every variant has a unique SKU
    flat = [v["sku"] for p in m["products"] for v in p["variants"]]
    check("all variant SKUs unique", len(flat) == len(set(flat)))

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(run())
