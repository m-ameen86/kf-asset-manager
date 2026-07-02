"""Phase 3-c.1 tests — real single-image smoke path (MOCKED; no real API calls).

Run: python -m kf_asset_manager.tests_vision_exec
"""
import sys, tempfile, io, os
from pathlib import Path
from contextlib import contextmanager
from PIL import Image

from . import model, vision_provider as vp, vision_ai

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else " FAIL ") + name)


@contextmanager
def no_api_key_env():
    """Isolation guard: temporarily clear ANTHROPIC_API_KEY so 'no key' tests are true
    regardless of the developer's real shell environment. Always restores it afterward."""
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        yield
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved


class ScriptedProvider(vp.VisionProvider):
    """Returns/raises a scripted sequence; counts calls. Never touches the network."""
    name = "scripted"

    def __init__(self, script, model="mock-model"):
        self.script = list(script)
        self.calls = 0
        self.model = model
        self.last_usage = {"input_tokens": 11, "output_tokens": 7}
        self.last_model = model

    def available(self):
        return True

    def analyze(self, image_path, prompt):
        self.calls += 1
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


GOOD = {"match": {"is_match": True, "confidence": 0.9, "reason": "ok"},
        "suggested_name": "Botanical Damask", "style_tags": ["floral", "damask"]}


def _build():
    lib = Path(tempfile.mkdtemp()) / "Curtains"; lib.mkdir(parents=True)
    for n, c in [("P4186-L", (1, 2, 3)), ("P4186-R", (4, 5, 6))]:
        Image.new("RGB", (16, 16), c).save(lib / (n + ".jpg"), "JPEG")
    db = model.IdentityDB(str(lib.parent / "x.db"))
    model.build_graph(db, lib)
    return db, lib


def run():
    # ---- pure JSON helpers ----
    check("strip fences (```json)", vp.strip_fences('```json\n{"a":1}\n```') == '{"a":1}')
    check("parse fenced JSON", vp.parse_vision_text('```json\n{"a":1}\n```') == {"a": 1})
    check("parse prose-wrapped JSON", vp.parse_vision_text('Here:\n{"a":2} thanks')["a"] == 2)
    raised = False
    try:
        vp.parse_vision_text("not json at all")
    except vp.InvalidVisionResponse:
        raised = True
    check("unparseable -> InvalidVisionResponse", raised)

    # ---- pre-flight: missing key fails with zero spend (env-isolated) ----
    db, lib = _build()
    rows = vision_ai.select_assets(db, limit=1)
    with no_api_key_env():
        nokey = vp.AnthropicVisionProvider(api_key=None)
        ok, errs = vision_ai.preflight(db, nokey, rows)
        check("preflight fails without key (env-isolated)",
              not ok and any("KEY" in e or "key" in e for e in errs))

        out = io.StringIO()
        summ = vision_ai.smoke_execute(db, nokey, review_csv=str(lib.parent / "rev.csv"),
                                       confirm=lambda: True, out=out)
    check("missing key -> no run, zero calls", summ["ran"] is False and summ["calls"] == 0)
    check("no review CSV written on preflight fail", not (lib.parent / "rev.csv").exists())

    # preflight catches missing sha256 and missing file
    fake = [{"asset_id": "KF-AST-x", "path": "/nope.jpg", "sha256": "", "filename": "x.jpg",
             "design_id": "KF-D-000001", "product_type": "Curtain"}]
    prov_key = ScriptedProvider([GOOD])
    ok2, errs2 = vision_ai.preflight(db, prov_key, fake)
    check("preflight flags missing sha256", not ok2 and any("sha256" in e for e in errs2))

    # ---- successful smoke: one call, one row, one CSV line ----
    db, lib = _build()
    csv_path = lib.parent / "vision_review.csv"
    good = ScriptedProvider([GOOD])
    s = vision_ai.smoke_execute(db, good, review_csv=str(csv_path), confirm=lambda: True, out=io.StringIO())
    check("smoke ran exactly one call", good.calls == 1 and s["calls"] == 1)
    check("smoke status ok", s["status"] == "ok")
    aid = vision_ai.select_assets(db, limit=1)[0]["asset_id"]
    vis = db.get_vision(aid)
    check("vision_results row written with suggested_name", vis and vis["suggested_name"] == "Botanical Damask")
    check("style_tags stored as list", isinstance(vis["style_tags"], list) and "floral" in vis["style_tags"])
    check("match confidence stored", abs(vis["match_confidence"] - 0.9) < 1e-6)
    import csv as _csv
    with open(csv_path) as f:
        review = list(_csv.DictReader(f))
    check("one review CSV row written", len(review) == 1 and review[0]["status"] == "ok")
    check("review CSV has no api key text", "sk-" not in open(csv_path).read())

    # ---- re-run skips due to cache ----
    good2 = ScriptedProvider([GOOD])
    s2 = vision_ai.smoke_execute(db, good2, review_csv=str(csv_path), confirm=lambda: True, out=io.StringIO())
    check("re-run skips (cached) with zero calls", s2["ran"] is False and good2.calls == 0)

    # ---- retry once on invalid JSON, then success ----
    db, lib = _build()
    retry = ScriptedProvider([vp.InvalidVisionResponse("bad"), GOOD])
    s3 = vision_ai.smoke_execute(db, retry, review_csv=str(lib.parent / "r.csv"), confirm=lambda: True, out=io.StringIO())
    check("invalid-then-valid retries once and succeeds", retry.calls == 2 and s3["status"] == "ok")

    # ---- retry exhausted -> clean failure, nothing cached ----
    db, lib = _build()
    bad = ScriptedProvider([vp.InvalidVisionResponse("bad"), vp.InvalidVisionResponse("still bad")])
    s4 = vision_ai.smoke_execute(db, bad, review_csv=str(lib.parent / "f.csv"), confirm=lambda: True, out=io.StringIO())
    check("exhausted retries -> status failed", s4["status"] == "failed")
    aid2 = vision_ai.select_assets(db, limit=1)[0]
    check("failure caches nothing (still needs analysis)",
          vision_ai.needs_ai_analysis(db, aid2["asset_id"], aid2["sha256"]))
    with open(lib.parent / "f.csv") as f:
        frow = list(_csv.DictReader(f))
    check("failed review row recorded", frow[0]["status"] == "failed")

    # ---- auth error mid-call: no retry, clean failure ----
    db, lib = _build()
    autherr = ScriptedProvider([vp.VisionAuthError("bad key")])
    s5 = vision_ai.smoke_execute(db, autherr, review_csv=str(lib.parent / "a.csv"), confirm=lambda: True, out=io.StringIO())
    check("auth error -> single attempt, failed", autherr.calls == 1 and s5["status"] == "failed")

    # ---- confirmation decline -> no call ----
    db, lib = _build()
    decl = ScriptedProvider([GOOD])
    s6 = vision_ai.smoke_execute(db, decl, review_csv=str(lib.parent / "d.csv"), confirm=lambda: False, out=io.StringIO())
    check("declining confirmation makes no call", decl.calls == 0 and s6["ran"] is False)

    # ---- CLI guards: --execute requires --limit 1; bare run makes no call ----
    db, lib = _build()
    # NOTE: since 3-c.2, --limit 2 is a VALID batch size (see tests_vision_batch.py).
    # --limit 1 is the smoke path (this file); an out-of-range limit still refuses.
    rc = vision_ai._main(["--db", str(lib.parent / "x.db"), "--execute", "--limit", "31", "--provider", "mock"])
    check("--execute refuses an out-of-range --limit (31)", rc == 2)
    rc2 = vision_ai._main(["--db", str(lib.parent / "x.db")])
    check("no --execute/--dry-run -> guard, returns 2", rc2 == 2)

    # ---- CLI --execute --limit 1 with NO key fails cleanly via pre-flight (regression) ----
    db, lib = _build()
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        crashed = False
        rc3 = None
        try:
            rc3 = vision_ai._main(["--db", str(lib.parent / "x.db"), "--execute", "--limit", "1",
                                   "--provider", "anthropic"])
        except Exception:
            crashed = True
        check("CLI --execute --limit 1 no-key does not crash", not crashed)
        check("CLI --execute --limit 1 no-key returns cleanly (0)", rc3 == 0)
        check("no review CSV created on no-key preflight fail",
              not (lib.parent / "vision_review.csv").exists())
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved

    # ---- identity untouched ----
    db, lib = _build()
    before = db.counts()
    vision_ai.smoke_execute(db, ScriptedProvider([GOOD]), review_csv=str(lib.parent / "i.csv"),
                            confirm=lambda: True, out=io.StringIO())
    after = db.counts()
    check("identity counts unchanged by smoke (except vision table)",
          {k: after[k] for k in before} == before)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(run())
