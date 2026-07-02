"""Shopify export tests — Shopify-format product CSV from the built graph.

Run: python -m kf_asset_manager.tests_shopify
"""
import sys, tempfile, csv
from pathlib import Path
from PIL import Image

from . import model, shopify_export as shx

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else " FAIL ") + name)


def run():
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

    out = lib / "shopify.csv"
    info = shx.write_csv(db, out)
    with open(out, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    check("CSV written with rows", len(rows) > 0)
    check("header has Handle/Title/Variant SKU",
          all(c in rows[0] for c in ("Handle", "Title", "Variant SKU", "Option1 Name", "Status")))

    # curtain: one product (handle), two variant rows (Left/Right), title only on first
    cur_rows = [r for r in rows if r["Handle"] == "kf-cur-000001"]
    check("curtain product present by handle", len(cur_rows) == 2)
    check("curtain title only on first row", cur_rows[0]["Title"] and cur_rows[1]["Title"] == "")
    check("curtain option name is Side", cur_rows[0]["Option1 Name"] == "Side")
    check("curtain variant values Left/Right",
          sorted(r["Option1 Value"] for r in cur_rows) == ["Left", "Right"])
    check("curtain variant SKUs L/R",
          sorted(r["Variant SKU"] for r in cur_rows) == ["KF-CUR-000001-L", "KF-CUR-000001-R"])

    # merged single curtain -> one row, value Single
    single = [r for r in rows if r["Variant SKU"].endswith("-SINGLE")]
    check("merged single exported", len(single) == 1 and single[0]["Option1 Value"] == "Single")

    # two sided cushions -> two distinct handles, each one row
    cush_handles = sorted({r["Handle"] for r in rows if r["Handle"].startswith("kf-csh-")})
    check("two cushion products by handle (-l/-r)",
          cush_handles == ["kf-csh-000001-l", "kf-csh-000001-r"])

    # fabric -> Colour option, values 01/02
    fab_rows = [r for r in rows if r["Handle"].startswith("kf-fab-")]
    check("fabric option name is Colour", all(r["Option1 Name"] == "Colour" for r in fab_rows))
    check("fabric colour values 01/02",
          sorted(r["Option1 Value"] for r in fab_rows) == ["01", "02"])

    # staging safety: everything draft / unpublished
    check("all products draft", all(r["Status"] in ("draft", "") for r in rows))
    check("nothing published", all(r["Published"] in ("FALSE", "") for r in rows))

    # every variant row carries a SKU; handles unique per product count
    check("every row has a Variant SKU", all(r["Variant SKU"] for r in rows))
    check("summary product count matches handles",
          info["products"] == len({r["Handle"] for r in rows}))

    # scope filter: curtains only
    out2 = lib / "shopify_cur.csv"
    info2 = shx.write_csv(db, out2, product_types=["Curtain"])
    with open(out2, encoding="utf-8") as f:
        rows2 = list(csv.DictReader(f))
    check("type filter keeps only curtains",
          all(r["Handle"].startswith("kf-cur-") for r in rows2) and len(rows2) > 0)

    # limit filter
    info3 = shx.write_csv(db, lib / "shopify_lim.csv", limit_products=2)
    check("limit caps product count", info3["products"] == 2)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(run())
