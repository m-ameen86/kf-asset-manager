"""Derived-artwork model tests (v1.5).

Proves the core distinction:
  * Independently created artwork  -> a NEW Design.
  * Derived artwork (cropped/adapted) -> stays in the PARENT Design, linked by an
    explicit relationship, and still yields its own Product.

Run: python -m kf_asset_manager.tests_derive
"""
import sys, tempfile, os, hashlib

from .model import IdentityDB

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else " FAIL ") + name)


def _sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


def run():
    fd, path = tempfile.mkstemp(suffix=".db"); os.close(fd); os.remove(path)
    db = IdentityDB(path)

    # ---- Situation 1: derived artwork (P4134) ----------------------------
    # One engineered curtain design (L/R panels are ORIGINAL artwork).
    fam = None  # single composition -> no family
    cur = db.ensure_design("CUR|P4134", fam, "engineered_panel", "Curtain", ["Curtain"])
    aL = db.ensure_asset(_sha("P4134-L"), cur, filename="P4134-L.jpg", path="/x/P4134-L.jpg",
                         width=4000, height=2000, side="L", role="panel-L",
                         source_files='[{"ext":"psd"}]')   # master .psd attached, no own ID
    aR = db.ensure_asset(_sha("P4134-R"), cur, filename="P4134-R.jpg", path="/x/P4134-R.jpg",
                         width=4000, height=2000, side="R", role="panel-R",
                         source_files='[{"ext":"tif"}]')   # master .tif attached, no own ID

    designs_before = db.counts()["designs"]
    # The two cushions are DERIVED from the curtain panels — NOT new designs.
    cushL = db.ensure_asset(_sha("P4134-L-cush"), cur, filename="P4134-L-cush.jpg",
                            path="/x/P4134-L-cush.jpg", width=1200, height=1200, side="L",
                            role="cushion", source_files="[]",
                            artwork_role="Derived", artwork_relationship="Cropped",
                            derived_from_design=cur, derived_from_asset=aL)
    cushR = db.ensure_asset(_sha("P4134-R-cush"), cur, filename="P4134-R-cush.jpg",
                            path="/x/P4134-R-cush.jpg", width=1200, height=1200, side="R",
                            role="cushion", source_files="[]",
                            artwork_role="Derived", artwork_relationship="Cropped",
                            derived_from_design=cur, derived_from_asset=aR)
    designs_after = db.counts()["designs"]

    check("derived cushions create NO new design", designs_after == designs_before)
    row = db.conn.execute("SELECT artwork_role,artwork_relationship,derived_from_design,derived_from_asset "
                          "FROM assets WHERE asset_id=?", (cushL,)).fetchone()
    check("derived cushion marked artwork_role=Derived", row["artwork_role"] == "Derived")
    check("derived cushion records relationship (Cropped)", row["artwork_relationship"] == "Cropped")
    check("derived cushion links derived_from_design = curtain", row["derived_from_design"] == cur)
    check("derived cushion links derived_from_asset = L panel", row["derived_from_asset"] == aL)

    # Products: one Curtain (from originals) + two Cushion products (from derived).
    curtain_prod = db.ensure_product(cur, fam, "Curtain")
    db.link_variant(curtain_prod, aL, "Left")
    db.link_variant(curtain_prod, aR, "Right")
    # A Cushion product would normally be refused (engineered_panel -> Curtain only)…
    refused = False
    try:
        db.ensure_product(cur, fam, "Cushion")
    except Exception:
        refused = True
    check("Cushion refused via ORIGINAL path (compatibility holds)", refused)
    # …but the DERIVED cushion artwork is realized from its own derived Source, which
    # authorizes its product (no bypass) and distinguishes it by identity (no discriminator).
    srcL = db.ensure_source(cur, "Cushion", origin="Derived", artwork_relationship="Cropped", side="L")
    srcR = db.ensure_source(cur, "Cushion", origin="Derived", artwork_relationship="Cropped", side="R")
    pL = db.ensure_product(cur, fam, "Cushion", source_id=srcL, derived=True)
    pR = db.ensure_product(cur, fam, "Cushion", source_id=srcR, derived=True)
    check("two derived cushions -> two distinct Cushion products", pL != pR)
    prods = db.conn.execute("SELECT product_type,source_id FROM products WHERE design_id=? "
                            "ORDER BY product_type,source_id", (cur,)).fetchall()
    check("design backs Curtain + 2 Cushion products", len(prods) == 3)
    cushion_via_derived = db.conn.execute(
        "SELECT COUNT(*) FROM products p JOIN artwork_sources s ON p.source_id=s.source_id "
        "WHERE p.design_id=? AND p.product_type='Cushion' AND s.origin='Derived'", (cur,)).fetchone()[0]
    check("cushion products realized from a derived Source", cushion_via_derived == 2)

    # ---- Situation 2: independent compositions (P4207) -------------------
    fam2 = db.ensure_family("P4207")
    d1 = db.ensure_design("CUR|P4207|D1", fam2, "engineered_panel", "Curtain", ["Curtain"])
    d2 = db.ensure_design("CUR|P4207|D2", fam2, "engineered_panel", "Curtain", ["Curtain"])
    check("independent compositions D1 and D2 ARE different designs", d1 != d2)
    # each design's cushion is derived from its own curtain
    db.ensure_asset(_sha("P4207"), d1, filename="P4207.jpg", path="/x/P4207.jpg",
                    width=4000, height=2000, side=None, role="panel", source_files='[{"ext":"tif"}]')
    cd1 = db.ensure_asset(_sha("P4207-cush"), d1, filename="P4207-cush.jpg", path="/x/P4207-cush.jpg",
                          width=1200, height=1200, side=None, role="cushion", source_files="[]",
                          artwork_role="Derived", artwork_relationship="Cropped", derived_from_design=d1)
    db.ensure_asset(_sha("P4207-D2"), d2, filename="P4207-D2.jpg", path="/x/P4207-D2.jpg",
                    width=4000, height=2000, side=None, role="panel", source_files='[{"ext":"psd"}]')
    cd2 = db.ensure_asset(_sha("P4207-D2-cush"), d2, filename="P4207-D2-cush.jpg", path="/x/P4207-D2-cush.jpg",
                          width=1200, height=1200, side=None, role="cushion", source_files="[]",
                          artwork_role="Derived", artwork_relationship="Cropped", derived_from_design=d2)
    s_d1 = db.ensure_source(d1, "Cushion", origin="Derived", artwork_relationship="Cropped")
    s_d2 = db.ensure_source(d2, "Cushion", origin="Derived", artwork_relationship="Cropped")
    db.ensure_product(d1, fam2, "Curtain"); db.ensure_product(d1, fam2, "Cushion", source_id=s_d1, derived=True)
    db.ensure_product(d2, fam2, "Curtain"); db.ensure_product(d2, fam2, "Cushion", source_id=s_d2, derived=True)
    check("D1 cushion derived from D1 (not D2)",
          db.conn.execute("SELECT derived_from_design FROM assets WHERE asset_id=?", (cd1,)).fetchone()[0] == d1)
    check("family P4207 groups the two independent designs",
          db.conn.execute("SELECT COUNT(*) FROM designs WHERE family_id=?", (fam2,)).fetchone()[0] == 2)

    os.remove(path)
    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(run())
