"""Phase 1 automated tests — Internal Identity + Relationships.

Run: python -m kf_asset_manager.tests_phase1
Exits non-zero on any failure.
"""
import json
import re
import sys
import tempfile
from pathlib import Path

from PIL import Image

from . import model

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else " FAIL ") + name)


def make_sample(root):
    def jpg(p, c):
        p.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (40, 40), c).save(p, "JPEG")

    def tif(p, c):
        Image.new("RGB", (40, 40), c).save(p, "TIFF")

    cur = root / "Curtains"
    # flat curtain pair + a linked TIF master + a merged single
    jpg(cur / "Kids-3141-L.jpg", (180, 40, 40))
    tif(cur / "Kids-3141-L.tif", (180, 40, 40))      # master, same name -> no own id
    jpg(cur / "Kids-3141-R.jpg", (40, 180, 40))
    jpg(cur / "Kids-3061-C.jpg", (90, 60, 140))       # merged single
    sets = root / "Sets"
    # a coordinated family: curtain pair + two distinct cushions
    jpg(sets / "(18-11) C3-A.jpg", (10, 10, 10))
    jpg(sets / "(18-11) C3-B.jpg", (20, 20, 20))
    jpg(sets / "(18-11) C3-A-cushion.jpg", (30, 30, 30))
    jpg(sets / "(18-11) C3-B-cushion.jpg", (40, 40, 40))
    # a repeat pattern (multi-product capable) and a fixed tapestry (single-product)
    jpg(root / "Fabrics" / "floral_repeat_2201.jpg", (120, 160, 90))
    jpg(root / "Tapestry" / "ayah_composition.jpg", (160, 120, 90))


def run():
    tmp = Path(tempfile.mkdtemp())
    root = tmp / "lib"
    make_sample(root)
    dbpath = tmp / "id.db"
    db = model.IdentityDB(dbpath)
    model.build_graph(db, root)

    conn = db.conn
    A = {r["filename"]: dict(r) for r in conn.execute("SELECT * FROM assets")}

    # 1. ID formats are opaque (entity prefix + 6 digits, nothing else)
    pat = {"families": r"^KF-FAM-\d{6}$", "designs": r"^KF-D-\d{6}$",
           "assets": r"^KF-AST-\d{6}$", "products": r"^KF-PRD-\d{6}$"}
    idcol = {"families": "family_id", "designs": "design_id",
             "assets": "asset_id", "products": "product_id"}
    opaque = True
    for t, rx in pat.items():
        for r in conn.execute(f"SELECT {idcol[t]} AS id FROM {t}"):
            if not re.match(rx, r["id"]):
                opaque = False
    check("IDs are opaque (no type/side/family meaning encoded)", opaque)

    # 2. L and R share one design, but are different assets
    L, R = A["Kids-3141-L.jpg"], A["Kids-3141-R.jpg"]
    check("curtain L/R share one design", L["design_id"] == R["design_id"])
    check("curtain L/R are distinct assets", L["asset_id"] != R["asset_id"])

    # 3. Design -> Products is 1:N, but only for COMPATIBLE product types
    A.update({r["filename"]: dict(r) for r in conn.execute("SELECT * FROM assets")})
    pat_design = A["floral_repeat_2201.jpg"]["design_id"]
    dt = conn.execute("SELECT design_type, primary_product, compatible_products FROM designs WHERE design_id=?",
                      (pat_design,)).fetchone()
    check("repeat pattern classified as repeat_pattern", dt["design_type"] == "repeat_pattern")
    famp = conn.execute("SELECT family_id FROM designs WHERE design_id=?", (pat_design,)).fetchone()["family_id"]
    # repeat pattern can back many products
    db.ensure_product(pat_design, famp, "Cushion")
    db.ensure_product(pat_design, famp, "Tapestry")
    np = conn.execute("SELECT COUNT(*) FROM products WHERE design_id=?", (pat_design,)).fetchone()[0]
    check("repeat pattern backs multiple products (1:N)", np >= 3)
    p_again = db.ensure_product(pat_design, famp, "Cushion")
    p_first = conn.execute("SELECT product_id FROM products WHERE design_id=? AND product_type='Cushion'",
                           (pat_design,)).fetchone()["product_id"]
    check("ensure_product idempotent per (design, type)", p_again == p_first)

    # 3b. Compatibility is ENFORCED: an engineered curtain panel cannot become a tote
    eng_design = L["design_id"]
    edt = conn.execute("SELECT design_type, compatible_products FROM designs WHERE design_id=?",
                       (eng_design,)).fetchone()
    check("flat curtain classified as engineered_panel", edt["design_type"] == "engineered_panel")
    check("engineered panel compatible with Curtain only",
          json.loads(edt["compatible_products"]) == ["Curtain"])
    refused = False
    try:
        db.ensure_product(eng_design, None, "Tote")
    except model.IncompatibleProductError:
        refused = True
    check("incompatible product (Tote on engineered panel) is REFUSED", refused)

    # 4. set: cushions A and B are different designs; curtain A/B one design; all share family
    cA, cB = A["(18-11) C3-A-cushion.jpg"], A["(18-11) C3-B-cushion.jpg"]
    curA, curB = A["(18-11) C3-A.jpg"], A["(18-11) C3-B.jpg"]
    check("set cushions A/B are separate designs", cA["design_id"] != cB["design_id"])
    check("set curtain A/B are one design", curA["design_id"] == curB["design_id"])
    fam_ids = set()
    for fn in ["(18-11) C3-A.jpg", "(18-11) C3-A-cushion.jpg", "(18-11) C3-B-cushion.jpg"]:
        d = conn.execute("SELECT family_id FROM designs WHERE design_id=?", (A[fn]["design_id"],)).fetchone()
        fam_ids.add(d["family_id"])
    check("all C3 pieces share one family", len(fam_ids) == 1 and None not in fam_ids)

    # 5. TIF master attached under the face, with NO asset row of its own
    check("TIF master has no asset row", "Kids-3141-L.tif" not in A)
    srcs = json.loads(L["source_files"])
    check("TIF master linked under its JPG face", any(s["filename"] == "Kids-3141-L.tif" for s in srcs))

    # 6. relationships resolve (no orphan FKs)
    orphans = conn.execute("""SELECT COUNT(*) n FROM assets a
                              LEFT JOIN designs d ON d.design_id=a.design_id WHERE d.design_id IS NULL""").fetchone()["n"]
    check("no orphan asset->design links", orphans == 0)

    # 7. idempotent re-scan: same IDs, no new rows
    before = db.counts()
    ids_before = [r["asset_id"] for r in conn.execute("SELECT asset_id FROM assets ORDER BY sha256")]
    model.build_graph(db, root)
    after = db.counts()
    ids_after = [r["asset_id"] for r in conn.execute("SELECT asset_id FROM assets ORDER BY sha256")]
    check("re-scan adds no rows (idempotent)", before == after)
    check("re-scan preserves asset IDs (immutable)", ids_before == ids_after)

    # 8. v1.4 refinements: taxonomy + source library metadata
    from . import config as _cfg
    check("placed_artwork in design-type taxonomy", "placed_artwork" in _cfg.DESIGN_TYPES)
    # source_library is optional metadata, settable, and does not affect identity
    aid = L["asset_id"]
    conn.execute("UPDATE assets SET source_library=? WHERE asset_id=?", ("Legacy", aid))
    conn.commit()
    sl = conn.execute("SELECT source_library FROM assets WHERE asset_id=?", (aid,)).fetchone()["source_library"]
    check("source_library metadata settable", sl == "Legacy")
    id_after_meta = conn.execute("SELECT asset_id FROM assets WHERE asset_id=?", (aid,)).fetchone()
    check("setting source_library does not change identity", id_after_meta is not None)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(run())
