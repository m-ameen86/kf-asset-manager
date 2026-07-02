"""Phase 4-a / 4-b tests — SKU generation (pure) + padding-insensitive resolver.

Run: python -m kf_asset_manager.tests_sku
"""
import sys, tempfile
from pathlib import Path
from PIL import Image

from . import sku, model

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else " FAIL ") + name)


def run():
    # ---- type codes ----
    check("Curtain -> CUR", sku.type_code("Curtain") == "CUR")
    check("Cushion -> CSH", sku.type_code("Cushion") == "CSH")
    check("Fabric -> FAB (not PAT)", sku.type_code("Fabric") == "FAB")
    check("Tapestry -> TAP", sku.type_code("Tapestry") == "TAP")
    check("Unknown -> UNK", sku.type_code("Unknown") == "UNK")
    check("unmapped -> UNK", sku.type_code("Nonsense") == "UNK")

    # ---- design number parsing ----
    check("design_number from int", sku.design_number(19) == 19)
    check("design_number from 'D19'", sku.design_number("D19") == 19)
    check("design_number from '000019'", sku.design_number("000019") == 19)
    check("design_number from 'KF-D-000019'", sku.design_number("KF-D-000019") == 19)

    # ---- zero padding to internal width ----
    check("sku zero-pads design to 6", sku.sku_for("Curtain", 19) == "KF-CUR-000019")
    check("sku zero-pads design 87", sku.sku_for("Fabric", 87) == "KF-FAB-000087")

    # ---- curtain variants (D1: pair = base) ----
    check("curtain pair is base (no suffix)", sku.sku("Curtain", 19) == "KF-CUR-000019")
    check("curtain left -> -L", sku.sku("Curtain", 19, side="L") == "KF-CUR-000019-L")
    check("curtain right -> -R", sku.sku("Curtain", 19, side="R") == "KF-CUR-000019-R")
    check("curtain merged -> -SINGLE", sku.sku("Curtain", 19, merged=True) == "KF-CUR-000019-SINGLE")

    # ---- cushion variants (from Source side) ----
    check("cushion right -> -R", sku.sku("Cushion", 19, side="R") == "KF-CSH-000019-R")
    check("cushion left -> -L", sku.sku("Cushion", 19, side="L") == "KF-CSH-000019-L")
    check("unsided cushion -> base", sku.sku("Cushion", 19) == "KF-CSH-000019")

    # ---- fabric colourways (D2: -C0n) ----
    check("fabric colourway 1 -> -C01", sku.sku("Fabric", 87, colorway="01") == "KF-FAB-000087-C01")
    check("fabric colourway 2 -> -C02", sku.sku("Fabric", 87, colorway=2) == "KF-FAB-000087-C02")
    check("single-colour fabric -> base", sku.sku("Fabric", 87) == "KF-FAB-000087")

    # ---- other types: no sub-variant ----
    check("runner -> base", sku.sku("Runner", 5) == "KF-RUN-000005")
    check("tapestry -> base", sku.sku("Tapestry", 5) == "KF-TAP-000005")

    # ---- query parsing ----
    check("parse '19'", sku.parse_query("19")["design_number"] == 19)
    check("parse 'd19' (lower)", sku.parse_query("d19")["design_number"] == 19)
    check("parse '000019'", sku.parse_query("000019")["design_number"] == 19)
    check("parse 'KF-D-000019'", sku.parse_query("KF-D-000019")["design_number"] == 19)
    p = sku.parse_query("KF-CUR-000019-L")
    check("parse full SKU -> number", p["design_number"] == 19)
    check("parse full SKU -> type", p["product_type"] == "Curtain")
    check("parse full SKU -> variant", p["variant"] == "L")
    pf = sku.parse_query("KF-FAB-000087-C02")
    check("parse fabric SKU -> Fabric + C02", pf["product_type"] == "Fabric" and pf["variant"] == "C02")
    check("parse junk -> no number", sku.parse_query("hello")["design_number"] is None)

    # ---- resolver against a real build ----
    lib = Path(tempfile.mkdtemp()) / "Curtains"
    lib.mkdir(parents=True)
    for n, c in [("P4186-L", (1, 2, 3)), ("P4186-R", (4, 5, 6)),
                 ("P4186-L-cush", (7, 8, 9)), ("P4186-R-cush", (10, 11, 12))]:
        Image.new("RGB", (16, 16), c).save(lib / (n + ".jpg"), "JPEG")
    db = model.IdentityDB(str(lib.parent / "sku.db"))
    model.build_graph(db, lib)
    # pick a real design number that exists
    did = db.conn.execute("SELECT design_id FROM designs LIMIT 1").fetchone()[0]
    num = sku.design_number(did)

    for form in (str(num), f"D{num}", f"{num:06d}", did):
        r = db.resolve(form)
        check(f"resolve '{form}' -> design exists", r["exists"] and r["design_id"] == did)

    # resolve a full SKU to the product
    rc = db.resolve(f"KF-CUR-{num:06d}-L")
    check("resolve curtain SKU -> Curtain product found", rc["exists"] and rc["product_id"] is not None)
    rmiss = db.resolve("999999")
    check("resolve non-existent design -> not exists", rmiss["exists"] is False)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(run())
