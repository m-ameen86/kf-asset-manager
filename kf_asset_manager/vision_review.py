"""Phase 3-d.1 — AI review surface (read-only). Turns vision_results into a reviewable
per-product summary: ai_review.csv + supplementary (never-title) manifest fields.

HARD RULE: nothing in this module ever writes to `display_title`. It only READS
vision_results and title_for(). Accepting an AI suggestion into the title is a separate,
explicit action (Phase 3-d.2, not built here).

Coverage, per asset (checked the same way the AI cache does — suggested_name IS NULL means
"not AI-analyzed", even if a colour-only row exists from the free local 3-a pass):
    not_analyzed  — no vision_results row at all
    colour_only   — a row exists (3-a ran) but suggested_name is NULL (3-c never ran)
    analyzed      — suggested_name IS NOT NULL (3-c produced a real suggestion)

Coverage, per PRODUCT (aggregated over every asset backing that product's variants):
    analyzed      — every asset is analyzed
    partial       — some analyzed, some not (mixed)
    colour_only   — none analyzed, at least one colour_only
    not_analyzed  — no asset has any vision data at all

Representative asset (for the single suggested_name/confidence/match/reason shown per
product): the ANALYZED asset with the lowest asset_id, for determinism. If more than one
analyzed asset disagrees on suggested_name, `conflict` is set True — the representative's
value is still shown, but flagged, so a human reviews it rather than the tool silently
picking a "winner" as truth.

NOTE: `is_match` (the model's actual match/no-match verdict) was computed by 3-c.1 at
call time but never persisted to `vision_results` — only confidence and reason were. Since
this module surfaces coverage honestly, that gap was fixed here: `vision_results` gained
an `is_match` column and `execute_one`/`record_vision_ai` now store it. This is a pure
additive fix (existing rows have `is_match=NULL`, correctly distinguishable from a real
True/False) — no other 3-c behavior changed.
"""
import csv as _csv
import json as _json

from . import vision_provider as vp


def _asset_ai_status(vis):
    """Classify one asset's vision_results row (or None) into a coverage bucket."""
    if vis is None:
        return "not_analyzed"
    if vis.get("suggested_name"):
        return "analyzed"
    return "colour_only"


def product_ai_summary(db, product_id):
    """Read-only aggregation across every asset backing a product's variants. Reuses
    db.get_vision() and db.title_for() exactly as they exist — no new write path."""
    conn = db.conn
    prod = conn.execute("SELECT product_id,design_id,product_type FROM products WHERE product_id=?",
                        (product_id,)).fetchone()
    if not prod:
        return None
    asset_ids = [r["asset_id"] for r in conn.execute(
        "SELECT DISTINCT asset_id FROM product_variants WHERE product_id=? ORDER BY asset_id",
        (product_id,))]

    statuses, analyzed = [], []
    for aid in asset_ids:
        vis = db.get_vision(aid)
        st = _asset_ai_status(vis)
        statuses.append(st)
        if st == "analyzed":
            analyzed.append((aid, vis))

    if statuses and all(s == "analyzed" for s in statuses):
        coverage = "analyzed"
    elif analyzed:
        coverage = "partial"
    elif any(s == "colour_only" for s in statuses):
        coverage = "colour_only"
    else:
        coverage = "not_analyzed"

    out = {
        "product_id": product_id, "design_id": prod["design_id"],
        "product_type": prod["product_type"], "current_title": db.title_for(product_id),
        "coverage_status": coverage, "conflict": False,
        "asset_count": len(asset_ids), "analyzed_count": len(analyzed),
        "representative_asset_id": None,
        "ai_suggested_name": None, "ai_match_confidence": None,
        "ai_is_match": None, "ai_match_reason": None, "ai_style_tags": [],
    }
    if not analyzed:
        return out

    analyzed.sort(key=lambda t: t[0])                # lowest asset_id wins as representative
    rep_id, rep = analyzed[0]
    names = {v.get("suggested_name") for _, v in analyzed}
    out["conflict"] = len(names) > 1
    out["representative_asset_id"] = rep_id
    out["ai_suggested_name"] = rep.get("suggested_name")
    out["ai_match_confidence"] = rep.get("match_confidence")
    out["ai_match_reason"] = rep.get("match_reason")
    out["ai_is_match"] = rep.get("is_match")   # the model's actual verdict (fixed in 3-d.1;
                                                # previously computed but not persisted)

    # union of tags across ALL analyzed assets, rechecked against STYLE_VOCAB (defense in
    # depth — validate_response already enforced this at write time, but re-check here in
    # case of any future write path that bypasses it).
    tags = set()
    for _, v in analyzed:
        for t in (v.get("style_tags") or []):
            if t in vp.STYLE_VOCAB:
                tags.add(t)
    out["ai_style_tags"] = sorted(tags)
    return out


def product_ai_options(db, product_id):
    """Read-only: per-asset AI suggestions for a product, for presenting a conflict
    choice to a reviewer. Returns a list of {asset_id, suggested_name, match_confidence,
    is_match} for every ANALYZED asset backing the product, ordered by asset_id. Used by
    Phase 3-d.2's accept workflow to show exactly what a reviewer is choosing between —
    never writes anything."""
    conn = db.conn
    asset_ids = [r["asset_id"] for r in conn.execute(
        "SELECT DISTINCT asset_id FROM product_variants WHERE product_id=? ORDER BY asset_id",
        (product_id,))]
    out = []
    for aid in asset_ids:
        vis = db.get_vision(aid)
        if vis and vis.get("suggested_name"):
            out.append({"asset_id": aid, "suggested_name": vis["suggested_name"],
                       "match_confidence": vis.get("match_confidence"),
                       "is_match": vis.get("is_match")})
    return out


def all_product_summaries(db):
    """Read-only summaries for every product in the DB, in product_id order."""
    ids = [r["product_id"] for r in db.conn.execute("SELECT product_id FROM products ORDER BY product_id")]
    return [product_ai_summary(db, pid) for pid in ids]


_CSV_HEADER = ["product_id", "design_id", "product_type", "current_title",
              "coverage_status", "conflict", "asset_count", "analyzed_count",
              "representative_asset_id", "ai_suggested_name", "ai_match_confidence",
              "ai_is_match", "ai_match_reason", "ai_style_tags"]


def write_ai_review_csv(db, path):
    """Write ai_review.csv. Pure read + format — no writes to display_title or anywhere
    else in the identity/product tables."""
    rows = []
    for s in all_product_summaries(db):
        rows.append([
            s["product_id"], s["design_id"], s["product_type"], s["current_title"],
            s["coverage_status"], "TRUE" if s["conflict"] else "FALSE",
            s["asset_count"], s["analyzed_count"], s["representative_asset_id"] or "",
            s["ai_suggested_name"] or "",
            s["ai_match_confidence"] if s["ai_match_confidence"] is not None else "",
            ("TRUE" if s["ai_is_match"] else "FALSE") if s["ai_is_match"] is not None else "",
            s["ai_match_reason"] or "", ", ".join(s["ai_style_tags"]),
        ])
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = _csv.writer(f)
        wr.writerow(_CSV_HEADER)
        wr.writerows(rows)
    return len(rows)


def manifest_ai_fields(db, product_id):
    """Supplementary (NEVER-title) fields for one product, for manifest.json. Additive
    only — callers merge these into an existing product dict; `title` is never touched."""
    s = product_ai_summary(db, product_id)
    if s is None:
        return {}
    return {
        "ai_suggested_name": s["ai_suggested_name"],
        "ai_style_tags": s["ai_style_tags"],
        "ai_match_confidence": s["ai_match_confidence"],
        "ai_review_status": s["coverage_status"],
    }
