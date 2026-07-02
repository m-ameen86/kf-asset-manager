"""Fabric naming rule tests — pattern is the design, colourway is a variant.

Per the locked policy (mirror of the engineered-panel case): for repeat-pattern fabrics,
the pattern code is ONE design identity and a trailing -<n> colour suffix is a commerce
VARIANT (colourway), never a sibling design. Validates the real library forms.

Run: python -m kf_asset_manager.tests_fabric
"""
import sys, tempfile
from pathlib import Path
from PIL import Image

from . import rules, model

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else " FAIL ") + name)


def run():
    # ---- parser-level ----
    g1 = rules.parse("G122-1.jpg", "Fabrics")
    g2 = rules.parse("G122-2.jpg", "Fabrics")
    g3 = rules.parse("G122-3.jpg", "Fabrics")
    check("G-prefixed fabric matches fabric_code", g1["rule"] == "fabric_code")
    check("pattern is the design identity (G122)", g1["number"] == "G122")
    check("colourway parsed and zero-padded (1 -> 01)", g1["colorway"] == "01")
    check("colourways share ONE design key", g1["design_key"] == g2["design_key"] == g3["design_key"])
    check("colourway is NOT a design_variant (not a sibling design)", g2["design_variant"] is None)
    check("fabric design_type is repeat_pattern", g1["design_type"] == "repeat_pattern")

    n1 = rules.parse("1003-01.jpg", "Fabrics")
    n2 = rules.parse("1003-02.jpg", "Fabrics")
    check("numeric pattern-colour parses (1003-01)", n1["rule"] == "fabric_code" and n1["number"] == "1003")
    check("numeric colourways share one design", n1["design_key"] == n2["design_key"])
    check("different patterns are different designs", g1["design_key"] != n1["design_key"])

    b1 = rules.parse("15.jpg", "Fabrics")
    b2 = rules.parse("16.jpg", "Fabrics")
    check("bare number is a fabric pattern (15)", b1["rule"] == "fabric_code" and b1["number"] == "15")
    check("bare number has no colourway", b1["colorway"] is None)
    check("distinct bare numbers are distinct designs", b1["design_key"] != b2["design_key"])

    leg = rules.parse("4011_Floral.jpg", "Fabrics")
    check("legacy named form still parses (4011_Floral)", leg["rule"] == "fabric_code" and leg["number"] == "4011")

    # junk must NOT be matched as catalogue — it stays flagged for review
    for junk in ("02-topaz-upscale-3.8x.jpg", "flag copy.png",
                 "WhatsApp Image 2026-02-28 at 14.58.01 (1)-topaz-upscale-6x.jpeg"):
        r = rules.parse(junk, "Fabrics")
        check(f"junk flagged for review, not parsed: {junk[:24]}…", r["needs_review"] and r["rule"] != "fabric_code")

    # ---- build-level: colourways collapse to one design + variants ----
    lib = Path(tempfile.mkdtemp()) / "Fabrics"
    lib.mkdir(parents=True)
    def jpg(n, c):
        Image.new("RGB", (16, 16), c).save(lib / n, "JPEG")
    jpg("G122-1.jpg", (10, 20, 30)); jpg("G122-2.jpg", (20, 30, 40)); jpg("G122-3.jpg", (30, 40, 50))
    jpg("1003-01.jpg", (1, 1, 1)); jpg("1003-02.jpg", (2, 2, 2))
    jpg("15.jpg", (99, 0, 0)); jpg("16.jpg", (0, 99, 0))

    db = model.IdentityDB(str(lib.parent / "fab.db"))
    model.build_graph(db, lib)
    c = db.conn

    check("4 fabric designs built (G122,1003,15,16)", db.counts()["designs"] == 4)
    check("7 assets (3+2+1+1)", db.counts()["assets"] == 7)
    check("4 Fabric products (one per pattern)", db.counts()["products"] == 4)

    g122 = c.execute("SELECT design_id FROM assets WHERE filename='G122-2.jpg'").fetchone()[0]
    prods = c.execute("SELECT product_id,product_type FROM products WHERE design_id=?", (g122,)).fetchall()
    check("G122 backs exactly one Fabric product", len(prods) == 1 and prods[0]["product_type"] == "Fabric")
    vlabels = sorted(r[0] for r in c.execute("SELECT variant_label FROM product_variants WHERE product_id=?", (prods[0]["product_id"],)))
    check("G122 product has 3 colour variants", vlabels == ["Colour 01", "Colour 02", "Colour 03"])
    srcs = c.execute("SELECT COUNT(*),MAX(origin) FROM artwork_sources WHERE design_id=?", (g122,)).fetchone()
    check("G122 has ONE Fabric Source, Original", srcs[0] == 1 and srcs[1] == "Original")

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(run())
