"""Phase 3-d.2 (revised, right-sized) — Explicit AI Acceptance Workflow.

Per the pre-build audit: a single, explicit "accept this one product's chosen title"
primitive — not a bulk-accept or confidence-threshold workflow. That is deliberately
deferred until real catalogue-wide volume justifies it; at ten reviewed products, a
one-at-a-time action is the right size.

HARD RULES (from the audit's acceptance criteria):
  * `accept_title()` is the ONLY function in this module that ever writes
    `display_title`, and it does so exclusively via the existing `db.set_title()` — no
    new write path is introduced.
  * Acceptance always requires an EXPLICIT, SPECIFIC title string from the caller. There
    is no "just accept the AI's guess" shortcut that infers a string silently.
  * When a product's AI suggestions CONFLICT (its assets disagree), `accept_ai_suggestion`
    refuses to proceed without an explicit `asset_id` naming which side's suggestion is
    being accepted. It never silently falls back to a "representative" choice.
  * Nothing here touches identity, Artwork Sources, SKU generation, vision prompts, the
    vision cache, colour extraction, or Shopify export. Those are read, never written, and
    only via already-existing functions (`vision_review.product_ai_summary`,
    `vision_review.product_ai_options`, `db.set_title`, `db.title_for`).
  * No confirmation prompt is added here (unlike the paid vision-execution CLIs) — this is
    a free, local, fully reversible metadata write (re-running it, or calling
    `db.set_title(product_id, None)`, undoes it), and the CLI invocation itself — naming a
    specific product and a specific title or asset — already IS the explicit human action.
"""
import argparse
import sys

from . import model as _model
from . import vision_review as vr


class AcceptError(Exception):
    """Raised when an accept action cannot proceed safely — e.g. no AI data exists yet,
    or a conflicting product was asked to accept without naming which side. Never raised
    AFTER a write; these are all pre-write refusals."""


def accept_title(db, product_id, title):
    """THE single write primitive. Writes `title` into display_title for `product_id`,
    verbatim, via the existing `set_title()`. No inference, no default derivation — the
    caller supplies the exact text. Idempotent: accepting the same title twice is a safe
    no-op (set_title is an UPDATE, not an INSERT)."""
    row = db.conn.execute("SELECT product_id FROM products WHERE product_id=?",
                          (product_id,)).fetchone()
    if not row:
        raise AcceptError(f"no such product: {product_id!r}")
    if not title or not str(title).strip():
        raise AcceptError("title must be a non-empty string")
    previous = db.title_for(product_id)
    new_title = db.set_title(product_id, title)
    return {"product_id": product_id, "previous_title": previous,
           "new_title": new_title, "changed": previous != new_title}


def accept_ai_suggestion(db, product_id, *, asset_id=None):
    """Convenience wrapper over accept_title() for the common case: accept what the AI
    already suggested, without retyping it. Enforces the conflict rule: if the product's
    AI suggestions disagree across its assets, this REFUSES (no write) unless `asset_id`
    explicitly names which side's suggestion to use. Returns either a success dict (same
    shape as accept_title's) or, on refusal, a dict describing why and — for conflicts —
    the exact options to choose from."""
    summary = vr.product_ai_summary(db, product_id)
    if summary is None:
        raise AcceptError(f"no such product: {product_id!r}")
    if summary["coverage_status"] not in ("analyzed", "partial"):
        return {"accepted": False, "reason": "no_ai_suggestion",
               "detail": f"coverage_status={summary['coverage_status']!r} — nothing to accept yet"}

    options = vr.product_ai_options(db, product_id)
    if summary["conflict"] and asset_id is None:
        return {"accepted": False, "reason": "conflict_requires_explicit_choice",
               "detail": "this product's assets disagree on a name — re-call with an "
                         "explicit asset_id naming which suggestion to accept",
               "options": options}

    if asset_id is not None:
        match = next((o for o in options if o["asset_id"] == asset_id), None)
        if match is None:
            return {"accepted": False, "reason": "asset_not_found_or_not_analyzed",
                   "detail": f"{asset_id!r} is not an analyzed asset of this product",
                   "options": options}
        chosen_title = match["suggested_name"]
        chosen_asset = asset_id
    else:
        chosen_title = summary["ai_suggested_name"]
        chosen_asset = summary["representative_asset_id"]

    result = accept_title(db, product_id, chosen_title)
    result.update({"accepted": True, "source": "ai", "asset_id_used": chosen_asset})
    return result


def pending_review(db, *, only_unset=True):
    """Read-only: products with real AI coverage (analyzed or partial) worth a human
    look. If `only_unset` (default), excludes products that already have a manual
    display_title set — i.e. shows what's still waiting for a decision. Never writes."""
    out = []
    for s in vr.all_product_summaries(db):
        if s["coverage_status"] not in ("analyzed", "partial"):
            continue
        if only_unset:
            row = db.conn.execute("SELECT display_title FROM products WHERE product_id=?",
                                  (s["product_id"],)).fetchone()
            if row and row["display_title"]:
                continue
        out.append(s)
    return out


def _main(argv=None):
    ap = argparse.ArgumentParser(
        description="Phase 3-d.2 — explicit, one-product-at-a-time AI title acceptance. "
                    "No bulk accept, no thresholds: every write names a specific product "
                    "and a specific title.")
    ap.add_argument("--db", required=True)
    ap.add_argument("--list", action="store_true",
                    help="read-only: list products with AI coverage still awaiting review")
    ap.add_argument("--product", help="the product_id to inspect or act on")
    ap.add_argument("--show", action="store_true",
                    help="read-only: show a product's AI summary and per-asset options")
    ap.add_argument("--accept-ai", action="store_true",
                    help="accept the AI's suggestion for --product (requires --asset if "
                        "the product's suggestions conflict)")
    ap.add_argument("--asset", help="asset_id naming which side's suggestion to accept "
                                    "(required when --accept-ai hits a conflict)")
    ap.add_argument("--accept-title", help="accept this exact, caller-supplied title "
                                           "text for --product (bypasses AI entirely)")
    a = ap.parse_args(argv)
    db = _model.IdentityDB(a.db)

    if a.list:
        rows = pending_review(db)
        print(f"{len(rows)} product(s) with AI coverage awaiting review:\n")
        for s in rows:
            flag = " [CONFLICT]" if s["conflict"] else ""
            print(f"  {s['product_id']}  {s['product_type']:8}  "
                 f"{s['coverage_status']:12}{flag}  -> {s['ai_suggested_name']}")
        return 0

    if not a.product:
        ap.error("--product is required unless using --list")

    if a.show:
        s = vr.product_ai_summary(db, a.product)
        if s is None:
            print(f"no such product: {a.product}")
            return 2
        print(f"product     : {s['product_id']} ({s['product_type']})")
        print(f"current title: {s['current_title']}")
        print(f"coverage    : {s['coverage_status']}  conflict={s['conflict']}")
        print(f"suggestion  : {s['ai_suggested_name']} (confidence={s['ai_match_confidence']})")
        print(f"tags        : {', '.join(s['ai_style_tags'])}")
        if s["conflict"]:
            print("\nPer-side options (use --accept-ai --asset <id> to pick one):")
            for o in vr.product_ai_options(db, a.product):
                print(f"  {o['asset_id']}: {o['suggested_name']} (confidence={o['match_confidence']})")
        return 0

    if a.accept_title:
        try:
            r = accept_title(db, a.product, a.accept_title)
        except AcceptError as e:
            print(f"REFUSED: {e}")
            return 2
        print(f"accepted custom title for {a.product}: {r['previous_title']!r} -> {r['new_title']!r}")
        return 0

    if a.accept_ai:
        try:
            r = accept_ai_suggestion(db, a.product, asset_id=a.asset)
        except AcceptError as e:
            print(f"REFUSED: {e}")
            return 2
        if not r["accepted"]:
            print(f"REFUSED: {r['reason']} — {r['detail']}")
            if r.get("options"):
                print("\nOptions:")
                for o in r["options"]:
                    print(f"  --asset {o['asset_id']}: {o['suggested_name']} "
                         f"(confidence={o['match_confidence']})")
            return 2
        print(f"accepted AI suggestion for {a.product}: "
             f"{r['previous_title']!r} -> {r['new_title']!r} (asset {r['asset_id_used']})")
        return 0

    ap.error("choose one of --list, --show, --accept-ai, or --accept-title")


if __name__ == "__main__":
    sys.exit(_main())
