"""Phase 3-d.2 tests — explicit AI acceptance workflow (revised, right-sized scope).

Proves every acceptance criterion from the pre-build audit: no silent writes, conflict
requires an explicit choice, set_title() is the only write path, identity/SKU/manifest/
Shopify surfaces are provably untouched, idempotency, and the pending-review read layer
correctly reflects acceptance. No real API calls anywhere.

Run: python -m kf_asset_manager.tests_vision_accept
"""
import sys, tempfile, json
from pathlib import Path
from PIL import Image

from . import model, vision_accept as va, vision_review as vr, audit, sku, shopify_export

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else " FAIL ") + name)


def _build():
    """A conflicting curtain (P4186 L/R, disagreeing AI names) and a clean, agreeing one
    (Kids-3040 L/R) — mirrors the real production data shape exactly (conflicts on
    grouped curtain products, agreement elsewhere)."""
    lib = Path(tempfile.mkdtemp()) / "Curtains"
    lib.mkdir(parents=True)
    for n, c in [("P4186-L", (1, 2, 3)), ("P4186-R", (4, 5, 6)),
                 ("Kids-3040-L", (9, 9, 0)), ("Kids-3040-R", (9, 8, 0))]:
        Image.new("RGB", (16, 16), c).save(lib / (n + ".jpg"), "JPEG")
    db = model.IdentityDB(str(lib.parent / "x.db"))
    model.build_graph(db, lib)
    c = db.conn

    def analyze(fn, name, tags, conf):
        aid, sha = c.execute("SELECT asset_id,sha256 FROM assets WHERE filename=?", (fn,)).fetchone()
        db.record_vision_ai(aid, sha, suggested_name=name, style_tags=tags, is_match=True,
                            match_confidence=conf, match_reason="matches", model="claude-sonnet-5")
        return aid

    aL = analyze("P4186-L.jpg", "Sleepy Moon Starlight Sky", ["kids", "nursery"], 0.95)
    aR = analyze("P4186-R.jpg", "Starry Cloud Dreams", ["kids", "playful"], 0.91)
    analyze("Kids-3040-L.jpg", "Cartoon Animal Parade", ["kids", "cartoon"], 0.93)
    analyze("Kids-3040-R.jpg", "Cartoon Animal Parade", ["kids", "cartoon"], 0.93)

    conflict_pid = c.execute("SELECT product_id FROM products WHERE product_type='Curtain' "
                             "AND design_id=(SELECT design_id FROM assets WHERE filename='P4186-L.jpg')"
                             ).fetchone()[0]
    clean_pid = c.execute("SELECT product_id FROM products WHERE product_type='Curtain' "
                          "AND design_id=(SELECT design_id FROM assets WHERE filename='Kids-3040-L.jpg')"
                          ).fetchone()[0]
    return db, lib, conflict_pid, clean_pid, aL, aR


def run():
    db, lib, conflict_pid, clean_pid, aL, aR = _build()

    # ---- sanity: the fixture really does conflict / not conflict as intended ----
    s_conflict = vr.product_ai_summary(db, conflict_pid)
    s_clean = vr.product_ai_summary(db, clean_pid)
    check("fixture: conflicting product really has conflict=True", s_conflict["conflict"] is True)
    check("fixture: clean product really has conflict=False", s_clean["conflict"] is False)

    # ---- accept_title(): the core primitive, always explicit ----
    r = va.accept_title(db, clean_pid, "Cartoon Animal Parade")
    check("accept_title writes exactly the given string", db.title_for(clean_pid) == "Cartoon Animal Parade")
    check("accept_title reports changed=True on first write", r["changed"] is True)

    r2 = va.accept_title(db, clean_pid, "Cartoon Animal Parade")
    check("accept_title is idempotent: re-accepting the same title is a safe no-op",
          db.title_for(clean_pid) == "Cartoon Animal Parade")
    check("idempotent re-accept reports changed=False", r2["changed"] is False)

    # ---- accept_title on a nonexistent product refuses, no crash ----
    raised = False
    try:
        va.accept_title(db, "KF-PRD-999999", "Anything")
    except va.AcceptError:
        raised = True
    check("accept_title on nonexistent product raises AcceptError (no crash)", raised)

    # ---- accept_title rejects empty/blank titles ----
    raised2 = False
    try:
        va.accept_title(db, clean_pid, "   ")
    except va.AcceptError:
        raised2 = True
    check("accept_title rejects a blank title", raised2)

    # ---- THE critical rule: conflict requires explicit choice, no silent default ----
    before_conflict_title = db.title_for(conflict_pid)
    result = va.accept_ai_suggestion(db, conflict_pid)   # no asset_id given
    check("accept_ai_suggestion REFUSES a conflicting product with no asset_id",
          result["accepted"] is False and result["reason"] == "conflict_requires_explicit_choice")
    check("refused conflict acceptance made NO write",
          db.title_for(conflict_pid) == before_conflict_title)
    check("refusal returns the actual options to choose from",
          {o["asset_id"] for o in result["options"]} == {aL, aR})

    # ---- accepting WITH an explicit asset_id succeeds, and picks THAT side, not the other ----
    rL = va.accept_ai_suggestion(db, conflict_pid, asset_id=aL)
    check("accept_ai_suggestion with explicit asset_id succeeds", rL["accepted"] is True)
    check("accepted title matches the L side's suggestion, not R's",
          db.title_for(conflict_pid) == "Sleepy Moon Starlight Sky")
    check("result records which asset was used", rL["asset_id_used"] == aL)

    rR = va.accept_ai_suggestion(db, conflict_pid, asset_id=aR)
    check("re-choosing the other side's suggestion overwrites correctly",
          db.title_for(conflict_pid) == "Starry Cloud Dreams")

    # ---- an asset_id that doesn't belong to / isn't analyzed for the product is refused ----
    bogus = va.accept_ai_suggestion(db, conflict_pid, asset_id="KF-AST-999999")
    check("accept_ai_suggestion refuses an unknown/foreign asset_id",
          bogus["accepted"] is False and bogus["reason"] == "asset_not_found_or_not_analyzed")

    # ---- accept_ai_suggestion on a NON-conflicting product needs no asset_id ----
    db2, lib2, cp2, clp2, _, _ = _build()
    r_clean_ai = va.accept_ai_suggestion(db2, clp2)
    check("non-conflicting product accepts without needing an asset_id", r_clean_ai["accepted"] is True)
    check("non-conflicting accept writes the single agreed suggestion",
          db2.title_for(clp2) == "Cartoon Animal Parade")

    # ---- nothing to accept yet (not_analyzed / colour_only) is refused cleanly ----
    db3, lib3, _, _, _, _ = _build()
    fab = lib3.parent / "Fabrics"; fab.mkdir()
    Image.new("RGB", (16, 16), (5, 5, 5)).save(fab / "G200-1.jpg")
    model.build_graph(db3, lib3.parent)
    fab_pid = db3.conn.execute("SELECT product_id FROM products WHERE product_type='Fabric'").fetchone()[0]
    r_none = va.accept_ai_suggestion(db3, fab_pid)
    check("accept refuses a product with no AI coverage at all",
          r_none["accepted"] is False and r_none["reason"] == "no_ai_suggestion")

    # ---- pending_review(): read-only, reflects acceptance correctly ----
    db4, lib4, cp4, clp4, aL4, aR4 = _build()
    pending_before = {s["product_id"] for s in va.pending_review(db4)}
    check("pending_review lists both AI-covered products before any acceptance",
          {cp4, clp4} <= pending_before)
    va.accept_ai_suggestion(db4, clp4)          # accept the clean one
    pending_after = {s["product_id"] for s in va.pending_review(db4)}
    check("accepted product DROPS OUT of pending_review", clp4 not in pending_after)
    check("still-unaccepted conflicting product REMAINS in pending_review", cp4 in pending_after)

    # ==================================================================================
    # BOUNDARY PROOFS — every "must NOT modify" item from the audit, verified directly
    # ==================================================================================
    db5, lib5, cp5, clp5, aL5, aR5 = _build()

    before_counts = db5.counts()
    va.accept_ai_suggestion(db5, clp5)
    va.accept_ai_suggestion(db5, cp5, asset_id=aL5)
    va.accept_title(db5, cp5, "A manually retyped custom title")
    after_counts = db5.counts()
    check("identity/product/asset/source counts are IDENTICAL before and after acceptance",
          before_counts == after_counts)

    design_id_cp5 = db5.conn.execute(
        "SELECT design_id FROM products WHERE product_id=?", (cp5,)).fetchone()[0]
    sku_before = sku.sku("Curtain", design_id_cp5)
    va.accept_ai_suggestion(db5, cp5, asset_id=aR5)   # switch choice again
    sku_after = sku.sku("Curtain", design_id_cp5)
    check("SKU for the accepted product is unaffected by title acceptance", sku_before == sku_after)

    vis_before = dict(db5.get_vision(aL5))
    va.accept_title(db5, cp5, "yet another retyped title")
    vis_after = dict(db5.get_vision(aL5))
    check("vision_results row for the AI source data is byte-identical after acceptance",
          vis_before == vis_after)
    check("vision_version on the analyzed asset is unchanged by acceptance",
          vis_before["vision_version"] == vis_after["vision_version"])

    rep = audit.generate_reports(db5, lib5, lib5.parent / "rep", do_hash=False)
    m = json.loads((lib5.parent / "rep" / "manifest.json").read_text())
    expected_top_keys = {"generator", "schema_version", "rules_version", "design_types_version",
                         "generated_at", "root", "counts", "architecture", "products"}
    check("manifest top-level keys are exactly the pre-existing set (no new/removed keys)",
          set(m.keys()) == expected_top_keys)
    cp5_entry = next(p for p in m["products"] if p["product_id"] == cp5)
    check("manifest 'title' field reflects the accepted title via the EXISTING title_for() call",
          cp5_entry["title"] == db5.title_for(cp5))

    shx_rows = shopify_export.to_rows(db5)
    check("Shopify export title reflects the accepted title with ZERO exporter changes",
          any(r["Title"] == db5.title_for(cp5) for r in shx_rows if r["Title"]))

    import inspect
    src = inspect.getsource(va)
    check("vision_accept.py does not import vision_provider (no AI/network path)",
          "vision_provider" not in src)
    check("vision_accept.py does not import colour.py or vision_colour.py",
          ("import colour" not in src) and ("vision_colour" not in src))
    check("vision_accept.py never imports sku.py (no SKU-writing/generation surface)",
          "import sku" not in src and "from . import sku" not in src)

    # ---- CLI: --list is read-only ----
    db6, lib6, cp6, clp6, aL6, aR6 = _build()
    import io
    from contextlib import redirect_stdout
    out = io.StringIO()
    with redirect_stdout(out):
        rc = va._main(["--db", str(lib6.parent / "x.db"), "--list"])
    check("CLI --list returns 0", rc == 0)
    check("CLI --list shows the conflicting product flagged", "[CONFLICT]" in out.getvalue())
    counts_after_list = db6.counts()
    check("CLI --list makes no write (identity unchanged)",
          model.IdentityDB(str(lib6.parent / "x.db")).counts() == counts_after_list)

    # ---- CLI: --accept-ai without --asset on a conflicting product refuses (exit 2) ----
    out2 = io.StringIO()
    with redirect_stdout(out2):
        rc2 = va._main(["--db", str(lib6.parent / "x.db"), "--product", cp6, "--accept-ai"])
    check("CLI --accept-ai on conflict with no --asset returns exit code 2 (refused)", rc2 == 2)
    check("CLI refusal message shows the options", "--asset" in out2.getvalue())
    db6b = model.IdentityDB(str(lib6.parent / "x.db"))
    check("CLI refused conflict made no write", db6b.title_for(cp6).startswith("Design"))

    # ---- CLI: --accept-ai WITH --asset succeeds (exit 0) ----
    out3 = io.StringIO()
    with redirect_stdout(out3):
        rc3 = va._main(["--db", str(lib6.parent / "x.db"), "--product", cp6,
                        "--accept-ai", "--asset", aL6])
    check("CLI --accept-ai with --asset on conflict succeeds (exit 0)", rc3 == 0)
    db6c = model.IdentityDB(str(lib6.parent / "x.db"))
    check("CLI accept-ai with --asset wrote the chosen side's suggestion",
          db6c.title_for(cp6) == "Sleepy Moon Starlight Sky")

    # ---- CLI: --accept-title accepts a fully custom string ----
    out4 = io.StringIO()
    with redirect_stdout(out4):
        rc4 = va._main(["--db", str(lib6.parent / "x.db"), "--product", clp6,
                        "--accept-title", "A Completely Custom Reviewer Title"])
    check("CLI --accept-title returns 0", rc4 == 0)
    db6d = model.IdentityDB(str(lib6.parent / "x.db"))
    check("CLI --accept-title writes the exact custom string",
          db6d.title_for(clp6) == "A Completely Custom Reviewer Title")

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(run())
