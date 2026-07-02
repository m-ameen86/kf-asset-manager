"""Phase 3-d.1 tests — AI review surface (read-only). No real API calls; no writes to
display_title anywhere in this module.

Run: python -m kf_asset_manager.tests_vision_review
"""
import sys, tempfile, json, csv as _csv
from pathlib import Path
from PIL import Image

from . import model, vision_review as vr, audit

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else " FAIL ") + name)


def _build():
    """Sided curtain (P4186 L/R), a plain unsided curtain, and a fabric with 2 colourways."""
    lib = Path(tempfile.mkdtemp())
    cur = lib / "Curtains"; cur.mkdir(parents=True)
    for n, c in [("P4186-L", (1, 2, 3)), ("P4186-R", (4, 5, 6)), ("P4190-C", (5, 5, 5))]:
        Image.new("RGB", (16, 16), c).save(cur / (n + ".jpg"), "JPEG")
    fab = lib / "Fabrics"; fab.mkdir()
    for n, c in [("G122-1", (20, 20, 20)), ("G122-2", (30, 30, 30))]:
        Image.new("RGB", (16, 16), c).save(fab / (n + ".jpg"), "JPEG")
    db = model.IdentityDB(str(lib / "x.db"))
    model.build_graph(db, lib)
    return db, lib


def run():
    db, lib = _build()

    # curtain product (L+R assets) — start with NO vision data at all
    cur_prod = db.conn.execute(
        "SELECT product_id FROM products WHERE product_type='Curtain' AND source_id=''").fetchone()[0]
    s0 = vr.product_ai_summary(db, cur_prod)
    check("no vision data -> coverage not_analyzed", s0["coverage_status"] == "not_analyzed")
    check("not_analyzed has no suggested name", s0["ai_suggested_name"] is None)
    check("not_analyzed has no conflict", s0["conflict"] is False)

    # add COLOUR-ONLY data (3-a) to both assets — must NOT count as analyzed
    assets = [r["asset_id"] for r in db.conn.execute(
        "SELECT DISTINCT asset_id FROM product_variants WHERE product_id=?", (cur_prod,))]
    for aid in assets:
        sha = db.conn.execute("SELECT sha256 FROM assets WHERE asset_id=?", (aid,)).fetchone()[0]
        db.record_vision_colours(aid, sha, [{"hex": "#000000", "percentage": 100, "named": "Black"}])
    s1 = vr.product_ai_summary(db, cur_prod)
    check("colour-only rows -> coverage colour_only (NOT analyzed)", s1["coverage_status"] == "colour_only")
    check("colour_only has suggested_name IS NULL check honoured", s1["ai_suggested_name"] is None)

    # now AI-analyze only ONE of the two assets -> PARTIAL coverage
    a0 = assets[0]
    sha0 = db.conn.execute("SELECT sha256 FROM assets WHERE asset_id=?", (a0,)).fetchone()[0]
    db.record_vision_ai(a0, sha0, suggested_name="Botanical Damask Curtain",
                        style_tags=["floral", "damask"], is_match=True,
                        match_confidence=0.9, match_reason="looks like a curtain panel",
                        model="claude-sonnet-5")
    s2 = vr.product_ai_summary(db, cur_prod)
    check("one of two analyzed -> coverage partial", s2["coverage_status"] == "partial")
    check("partial still surfaces the analyzed suggestion", s2["ai_suggested_name"] == "Botanical Damask Curtain")
    check("partial: no conflict yet (only one analyzed)", s2["conflict"] is False)
    check("ai_is_match reflects the REAL persisted verdict (not a derived guess)", s2["ai_is_match"] is True)
    check("ai_match_confidence surfaced", s2["ai_match_confidence"] == 0.9)

    # analyze the SECOND asset with a DIFFERENT name -> full coverage + CONFLICT
    a1 = assets[1]
    sha1 = db.conn.execute("SELECT sha256 FROM assets WHERE asset_id=?", (a1,)).fetchone()[0]
    db.record_vision_ai(a1, sha1, suggested_name="Coastal Palm Curtain",
                        style_tags=["geometric"], is_match=False,
                        match_confidence=0.4, match_reason="doesn't look like a curtain",
                        model="claude-sonnet-5")
    s3 = vr.product_ai_summary(db, cur_prod)
    check("both analyzed -> coverage analyzed", s3["coverage_status"] == "analyzed")
    check("differing names across L/R -> conflict TRUE", s3["conflict"] is True)
    check("representative is the LOWEST asset_id (deterministic)",
          s3["representative_asset_id"] == min(assets))
    check("style tags are the UNION of both assets, deduped",
          set(s3["ai_style_tags"]) == {"floral", "damask", "geometric"})

    # ---- product_ai_options: per-asset breakdown used by 3-d.2's conflict resolution ----
    opts = vr.product_ai_options(db, cur_prod)
    check("product_ai_options returns one entry per ANALYZED asset", len(opts) == 2)
    check("product_ai_options entries carry asset_id + suggested_name + confidence",
          all({"asset_id", "suggested_name", "match_confidence", "is_match"} <= set(o.keys()) for o in opts))
    check("product_ai_options reflects the actual conflicting names",
          {o["suggested_name"] for o in opts} == {"Botanical Damask Curtain", "Coastal Palm Curtain"})

    # ---- style tag recheck (defense in depth): inject an invalid tag directly, bypassing validate_response ----
    db.conn.execute("UPDATE vision_results SET style_tags=? WHERE asset_id=?",
                    (json.dumps(["floral", "not-a-real-tag"]), a0))
    s4 = vr.product_ai_summary(db, cur_prod)
    check("invalid tag rechecked against STYLE_VOCAB and dropped", "not-a-real-tag" not in s4["ai_style_tags"])
    check("valid tag from same asset survives the recheck", "floral" in s4["ai_style_tags"])

    # ---- current_title uses title_for exactly (no bypass) ----
    check("current_title matches db.title_for exactly", s3["current_title"] == db.title_for(cur_prod))

    # ---- display_title is NEVER written by anything in this module ----
    before_titles = {r["product_id"]: r["display_title"] for r in
                     db.conn.execute("SELECT product_id, display_title FROM products")}
    vr.all_product_summaries(db)
    vr.write_ai_review_csv(db, lib / "ai_review.csv")
    after_titles = {r["product_id"]: r["display_title"] for r in
                    db.conn.execute("SELECT product_id, display_title FROM products")}
    check("display_title column completely unchanged after review surfacing", before_titles == after_titles)
    check("set_title/title_for still behave exactly as before (manual override still wins)",
          db.title_for(cur_prod) != "Manually Renamed" and
          db.set_title(cur_prod, "Manually Renamed") == "Manually Renamed" and
          db.title_for(cur_prod) == "Manually Renamed")
    db.set_title(cur_prod, None)  # restore to default for cleanliness

    # ---- ai_review.csv structure + honesty ----
    n = vr.write_ai_review_csv(db, lib / "ai_review.csv")
    check("csv row count == product count", n == db.counts()["products"])
    with open(lib / "ai_review.csv") as f:
        rows = list(_csv.DictReader(f))
    header = list(rows[0].keys())
    for col in ("product_id", "design_id", "product_type", "current_title", "coverage_status",
               "conflict", "ai_suggested_name", "ai_match_confidence", "ai_is_match",
               "ai_match_reason", "ai_style_tags"):
        check(f"ai_review.csv has column '{col}'", col in header)
    conflict_row = next(r for r in rows if r["product_id"] == cur_prod)
    check("csv shows conflict as TRUE for the conflicting product", conflict_row["conflict"] == "TRUE")
    not_analyzed_rows = [r for r in rows if r["coverage_status"] == "not_analyzed"]
    check("csv distinguishes not_analyzed products (fabric never touched)", len(not_analyzed_rows) >= 1)
    for r in not_analyzed_rows:
        check(f"not_analyzed row '{r['product_id']}' has empty suggested name (honest, not blank-as-rejected)",
              r["ai_suggested_name"] == "")

    # ---- manifest: additive AI fields, never replaces title, existing structure intact ----
    rep = audit.generate_reports(db, lib, lib / "rep", do_hash=False)
    m = json.loads((lib / "rep" / "manifest.json").read_text())
    check("manifest still has schema_version (existing structure intact)", "schema_version" in m)
    check("manifest products array present", "products" in m and len(m["products"]) > 0)
    cur_entry = next(p for p in m["products"] if p["product_id"] == cur_prod)
    check("manifest product has ai_suggested_name (additive)", "ai_suggested_name" in cur_entry)
    check("manifest product has ai_style_tags (additive)", "ai_style_tags" in cur_entry)
    check("manifest product has ai_match_confidence (additive)", "ai_match_confidence" in cur_entry)
    check("manifest product has ai_review_status (additive)", "ai_review_status" in cur_entry)
    check("manifest 'title' field is UNCHANGED by AI fields (never replaced)",
          cur_entry["title"] == db.title_for(cur_prod))
    check("ai_review.csv generated as part of generate_reports", (lib / "rep" / "ai_review.csv").exists())

    # existing manifest consumers (variants/sku structure) still intact
    check("existing variant structure (option/sku/asset_id) still present",
          all({"option", "sku", "asset_id"} <= set(v.keys()) for v in cur_entry["variants"]))

    # No real API calls anywhere in this suite — vision_review.py itself never imports or
    # calls anything network-capable (it only reads existing vision_results via the DB).
    import inspect as _inspect
    src = _inspect.getsource(vr)
    check("vision_review.py source contains no urllib/network call", "urllib" not in src and "requests" not in src)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(run())
