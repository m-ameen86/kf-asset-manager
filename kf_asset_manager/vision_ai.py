"""Phase 3-b — vision AI planning + dry-run (NO real calls, no key required).

Builds the execution plan for a future Phase 3-c run: selects a scoped slice of assets,
applies the sha256 + vision_version cache to count how many would actually be analysed,
estimates the call count and cost, and shows a sample structured prompt — but sends
nothing. The real analysis is Phase 3-c.

CLI:
  python -m kf_asset_manager.vision_ai --db audit.db --dry-run
         [--types Curtain Fabric] [--limit N] [--provider anthropic|mock]
         [--cost-per-call 0.01]
"""
import argparse
import sys
from pathlib import Path

from . import model as _model
from . import vision_provider as vp


def select_assets(db, product_types=None, limit=None):
    conn = db.conn
    if product_types:
        q = ("SELECT DISTINCT a.asset_id,a.path,a.sha256,a.filename,d.design_id,p.product_type "
             "FROM assets a JOIN product_variants pv ON pv.asset_id=a.asset_id "
             "JOIN products p ON p.product_id=pv.product_id "
             "JOIN designs d ON d.design_id=a.design_id "
             "WHERE p.product_type IN (%s) ORDER BY a.asset_id"
             % ",".join("?" * len(product_types)))
        rows = conn.execute(q, list(product_types)).fetchall()
    else:
        rows = conn.execute("SELECT a.asset_id,a.path,a.sha256,a.filename,a.design_id,"
                            "NULL as product_type FROM assets a ORDER BY a.asset_id").fetchall()
    if limit:
        rows = rows[:int(limit)]
    return rows


def needs_ai_analysis(db, asset_id, sha256, version=None):
    """True if no cached AI result (suggested_name) exists for this content + version.
    Mirrors the colour cache strategy, keyed on the AI fields."""
    v = _model.VISION_VERSION if version is None else version
    r = db.conn.execute(
        "SELECT 1 FROM vision_results WHERE asset_id=? AND sha256=? AND vision_version=? "
        "AND suggested_name IS NOT NULL", (asset_id, sha256, v)).fetchone()
    return r is None


def plan(db, product_types=None, limit=None, cost_per_call=vp.PER_CALL_USD_DEFAULT,
         version=None):
    """Compute the dry-run plan. Pure read-only; performs NO provider calls."""
    rows = select_assets(db, product_types, limit)
    to_call = [r for r in rows if needs_ai_analysis(db, r["asset_id"], r["sha256"], version)]
    cached = len(rows) - len(to_call)
    sample = None
    if rows:
        r0 = rows[0]
        from . import sku as _sku
        sample = vp.build_analysis_prompt(
            product_type=(r0["product_type"] or "Textile"),
            design_number=_sku.design_number(r0["design_id"]),
            filename=r0["filename"])
    return {
        "selected": len(rows),
        "cached": cached,
        "to_call": len(to_call),
        "estimated_calls": len(to_call),
        "cost_per_call": cost_per_call,
        "estimated_cost_usd": round(len(to_call) * cost_per_call, 2),
        "sample_prompt": sample,
    }


def dry_run(db, provider, product_types=None, limit=None,
            cost_per_call=vp.PER_CALL_USD_DEFAULT, out=sys.stdout):
    """Print the plan + a sample prompt. NEVER calls provider.analyze."""
    info = plan(db, product_types, limit, cost_per_call)
    print("── Phase 3-c DRY RUN (no API calls made) ──", file=out)
    print(f"provider           : {provider.name} (available={provider.available()})", file=out)
    print(f"scope              : types={product_types or 'ALL'} limit={limit or '-'}", file=out)
    print(f"images selected    : {info['selected']}", file=out)
    print(f"already cached     : {info['cached']}", file=out)
    print(f"would analyse      : {info['to_call']}", file=out)
    print(f"estimated calls    : {info['estimated_calls']} (one structured call per image)", file=out)
    print(f"cost per call (est): ${info['cost_per_call']:.4f}", file=out)
    print(f"estimated cost     : ${info['estimated_cost_usd']:.2f}", file=out)
    print("\n── sample structured prompt ──", file=out)
    print(info["sample_prompt"] or "(no images in scope)", file=out)
    if not provider.available():
        print("\nNOTE: no API key detected — a real Phase 3-c run would need one. "
              "Dry-run spends nothing.", file=out)
    return info


def preflight(db, provider, rows):
    """Phase 3-c gate. Returns (ok, errors). No spend on failure."""
    errs = []
    if not provider.available():
        errs.append("ANTHROPIC_API_KEY not set (provider unavailable)")
    if not getattr(provider, "model", None):
        errs.append("no model configured")
    if not rows:
        errs.append("no asset selected")
    else:
        r = rows[0]
        if not r["sha256"]:
            errs.append(f"asset {r['asset_id']} has no sha256 (rebuild the library)")
        from pathlib import Path as _P
        if not _P(r["path"]).exists():
            errs.append(f"image file not found: {r['path']}")
    return (not errs), errs


_REVIEW_HEADER = ["asset_id", "filename", "design_id", "product_type", "status",
                  "is_match", "confidence", "reason", "suggested_name", "style_tags",
                  "model", "input_tokens", "output_tokens", "analyzed_at"]


def _write_review_row(path, row):
    import csv as _csv
    from pathlib import Path as _P
    exists = _P(path).exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        wr = _csv.writer(f)
        if not exists:
            wr.writerow(_REVIEW_HEADER)
        wr.writerow([row.get(k, "") for k in _REVIEW_HEADER])


def execute_one(db, provider, row, *, prompt, version=None, out=sys.stdout):
    """Run ONE image: call (retry once on invalid JSON), validate, commit, return a result
    dict. Writes only vision_results + the returned review row. Never raises on a bad model
    reply — marks the asset failed cleanly so a re-run retries it."""
    import time as _t
    from . import sku as _sku
    v = _model.VISION_VERSION if version is None else version
    base = {"asset_id": row["asset_id"], "filename": row["filename"],
            "design_id": row["design_id"],
            "product_type": (row["product_type"] or ""), "model": provider.model}

    resp, err = None, None
    for attempt in (1, 2):                    # one retry on invalid/contract failure
        try:
            r = provider.analyze(row["path"], prompt)
        except vp.InvalidVisionResponse:
            err = "invalid JSON"; continue
        except vp.VisionAuthError as e:
            err = f"auth error: {e}"; break    # do not retry/spend on auth
        except vp.VisionTransportError as e:
            err = f"transport error: {e}"; break
        ok, errs = vp.validate_response(r)
        if ok:
            resp, err = r, None; break
        err = "contract: " + "; ".join(errs)

    usage = getattr(provider, "last_usage", {}) or {}
    if resp is None:                          # clean failure: store nothing as success
        base.update({"status": "failed", "reason": err,
                     "input_tokens": usage.get("input_tokens", ""),
                     "output_tokens": usage.get("output_tokens", ""),
                     "analyzed_at": _t.strftime("%Y-%m-%dT%H:%M:%S")})
        return base

    m = resp["match"]
    db.record_vision_ai(row["asset_id"], row["sha256"],
                        suggested_name=resp["suggested_name"], style_tags=resp["style_tags"],
                        is_match=bool(m["is_match"]),
                        match_confidence=float(m["confidence"]), match_reason=m["reason"],
                        model=getattr(provider, "last_model", provider.model), version=v)
    base.update({"status": "ok", "is_match": m["is_match"], "confidence": m["confidence"],
                 "reason": m["reason"], "suggested_name": resp["suggested_name"],
                 "style_tags": ", ".join(resp["style_tags"]),
                 "model": getattr(provider, "last_model", provider.model),
                 "input_tokens": usage.get("input_tokens", ""),
                 "output_tokens": usage.get("output_tokens", ""),
                 "analyzed_at": _t.strftime("%Y-%m-%dT%H:%M:%S")})
    return base


def smoke_execute(db, provider, *, product_types=None, review_csv=None,
                  cost_per_call=vp.PER_CALL_USD_DEFAULT, confirm=None, out=sys.stdout):
    """Phase 3-c.1: process exactly ONE uncached image, with pre-flight + confirmation.
    Returns a summary dict. Makes at most one real API call."""
    rows = select_assets(db, product_types, limit=1)
    # only consider images that still need AI analysis (cache-aware)
    rows = [r for r in rows if needs_ai_analysis(db, r["asset_id"], r["sha256"])]
    if not rows:
        print("nothing to do — selected image already analysed (cached).", file=out)
        return {"ran": False, "reason": "all cached", "calls": 0}
    ok, errs = preflight(db, provider, rows)
    if not ok:
        for e in errs:
            print(f"PRE-FLIGHT FAIL: {e}", file=out)
        return {"ran": False, "reason": "preflight", "errors": errs, "calls": 0}

    row = rows[0]
    from . import sku as _sku
    prompt = vp.build_analysis_prompt(product_type=(row["product_type"] or "Textile"),
                                      design_number=_sku.design_number(row["design_id"]),
                                      filename=row["filename"])
    print("── Phase 3-c.1 SMOKE (one real call) ──", file=out)
    print(f"image      : {row['filename']}", file=out)
    print(f"model      : {provider.model}", file=out)
    print(f"selected   : 1   estimated calls: 1   estimated cost: ${cost_per_call:.4f}", file=out)
    if confirm is None:
        confirm = lambda: input("Proceed with ONE real API call? [y/N] ").strip().lower() == "y"
    if not confirm():
        print("aborted — no call made.", file=out)
        return {"ran": False, "reason": "declined", "calls": 0}

    result = execute_one(db, provider, row, prompt=prompt, out=out)
    if review_csv:
        _write_review_row(review_csv, result)
    print(f"result     : {result['status']}", file=out)
    if result["status"] == "ok":
        print(f"name       : {result['suggested_name']}", file=out)
        print(f"match      : {result['is_match']} ({result['confidence']})", file=out)
        print(f"tags       : {result['style_tags']}", file=out)
        print(f"tokens     : in={result['input_tokens']} out={result['output_tokens']}", file=out)
    else:
        print(f"failed     : {result.get('reason')}", file=out)
    return {"ran": True, "calls": 1, "status": result["status"], "result": result}


# --- Phase 3-c.2: batch execution (2..30 images, hard-capped, no override flag) ---
BATCH_MIN = 2
BATCH_MAX = 30


def batch_execute(db, provider, *, limit, product_types=None, review_csv=None,
                  cost_per_call=vp.PER_CALL_USD_DEFAULT, delay=0.0, confirm=None,
                  out=sys.stdout):
    """Phase 3-c.2: process up to `limit` (2..30) uncached images. Reuses select_assets /
    needs_ai_analysis / preflight / execute_one exactly as in 3-c.1 — only the loop, the
    real-count confirmation, the courtesy delay, and the end-of-batch summary are new.
    Commits each image immediately (via execute_one/record_vision_ai), so an interrupted
    run resumes cleanly: already-committed images are skipped as cached on re-run, and no
    duplicate provider calls are made for them."""
    if not (BATCH_MIN <= limit <= BATCH_MAX):
        raise ValueError(f"batch limit must be between {BATCH_MIN} and {BATCH_MAX}")

    selected = select_assets(db, product_types, limit=limit)
    to_call = [r for r in selected if needs_ai_analysis(db, r["asset_id"], r["sha256"])]
    cached = len(selected) - len(to_call)

    summary = {"ran": False, "selected": len(selected), "cached": cached,
              "would_call": len(to_call), "calls": 0, "ok": 0, "failed": 0,
              "skipped": cached, "estimated_cost_usd": round(len(to_call) * cost_per_call, 2),
              "actual_cost_input_tokens": 0, "actual_cost_output_tokens": 0, "results": []}

    if not to_call:
        print("nothing to do — all selected images already analysed (cached).", file=out)
        return summary

    ok0, errs = preflight(db, provider, to_call)
    if not ok0:
        for e in errs:
            print(f"PRE-FLIGHT FAIL: {e}", file=out)
        summary["reason"] = "preflight"
        summary["errors"] = errs
        return summary

    print("── Phase 3-c.2 BATCH (real calls) ──", file=out)
    print(f"provider           : {provider.name} (model={provider.model})", file=out)
    print(f"selected           : {len(selected)}", file=out)
    print(f"already cached     : {cached}", file=out)
    print(f"would call         : {len(to_call)}", file=out)
    print(f"estimated cost     : ${summary['estimated_cost_usd']:.2f}", file=out)

    if confirm is None:
        confirm = lambda: input(f"Proceed with {len(to_call)} real API call(s)? [y/N] "
                                ).strip().lower() == "y"
    if not confirm():
        print("aborted — no calls made.", file=out)
        summary["reason"] = "declined"
        return summary

    from . import sku as _sku
    import time as _t
    for i, row in enumerate(to_call):
        prompt = vp.build_analysis_prompt(product_type=(row["product_type"] or "Textile"),
                                          design_number=_sku.design_number(row["design_id"]),
                                          filename=row["filename"])
        result = execute_one(db, provider, row, prompt=prompt, out=out)     # commits immediately
        if review_csv:
            _write_review_row(review_csv, result)                          # append-only
        summary["calls"] += 1
        summary["results"].append(result)
        if result["status"] == "ok":
            summary["ok"] += 1
            usage = getattr(provider, "last_usage", {}) or {}
            summary["actual_cost_input_tokens"] += int(usage.get("input_tokens", 0) or 0)
            summary["actual_cost_output_tokens"] += int(usage.get("output_tokens", 0) or 0)
            print(f"[{i+1}/{len(to_call)}] ok     : {row['filename']} -> {result['suggested_name']}", file=out)
        else:
            summary["failed"] += 1
            print(f"[{i+1}/{len(to_call)}] failed : {row['filename']} -> {result.get('reason')}", file=out)
        if delay and i < len(to_call) - 1:
            _t.sleep(delay)

    summary["ran"] = True
    print("── batch summary ──", file=out)
    print(f"ok={summary['ok']}  failed={summary['failed']}  skipped(cached)={summary['skipped']}  "
         f"calls={summary['calls']}", file=out)
    print(f"actual tokens: in={summary['actual_cost_input_tokens']} "
         f"out={summary['actual_cost_output_tokens']}", file=out)
    return summary


def _main(argv=None):
    ap = argparse.ArgumentParser(description="Phase 3-b/3-c vision (dry-run + smoke + batch).")
    ap.add_argument("--db", required=True)
    ap.add_argument("--dry-run", action="store_true", help="show the plan; make no API calls")
    ap.add_argument("--execute", action="store_true",
                    help="--limit 1: 3-c.1 single call. --limit 2..30: 3-c.2 batch.")
    ap.add_argument("--types", nargs="*", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--provider", default="anthropic", choices=["anthropic", "mock"])
    ap.add_argument("--model", default=None, help="override the vision model string")
    ap.add_argument("--cost-per-call", type=float, default=vp.PER_CALL_USD_DEFAULT)
    ap.add_argument("--review-csv", default=None)
    ap.add_argument("--delay", type=float, default=0.0, help="courtesy delay (seconds) between batch calls")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    a = ap.parse_args(argv)

    db = _model.IdentityDB(a.db)
    provider = vp.get_provider(a.provider, model=a.model or vp.DEFAULT_MODEL)

    if a.execute:
        if a.limit is None:
            print("Phase 3-c requires --limit. Pass --limit 1 for a single-image smoke, "
                 f"or --limit N ({BATCH_MIN}..{BATCH_MAX}) for a batch.")
            return 2
        out = a.review_csv or str(Path(a.db).parent / "vision_review.csv")
        if a.limit == 1:
            smoke_execute(db, provider, product_types=a.types, review_csv=out,
                         cost_per_call=a.cost_per_call,
                         confirm=(lambda: True) if a.yes else None)
            return 0
        if BATCH_MIN <= a.limit <= BATCH_MAX:
            batch_execute(db, provider, limit=a.limit, product_types=a.types, review_csv=out,
                         cost_per_call=a.cost_per_call, delay=a.delay,
                         confirm=(lambda: True) if a.yes else None)
            return 0
        print(f"--execute --limit must be 1 (smoke) or between {BATCH_MIN} and {BATCH_MAX} "
             f"(batch). Got --limit {a.limit}.")
        return 2
    if a.dry_run:
        dry_run(db, provider, product_types=a.types, limit=a.limit, cost_per_call=a.cost_per_call)
        return 0
    print(f"Pass --dry-run (preview) or --execute --limit 1|{BATCH_MIN}-{BATCH_MAX}.")
    return 2


if __name__ == "__main__":
    sys.exit(_main())
