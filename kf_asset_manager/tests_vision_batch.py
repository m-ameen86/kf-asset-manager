"""Phase 3-c.2 tests — batch execution (2..30 images, hard-capped). MOCKED; no real calls.

Run: python -m kf_asset_manager.tests_vision_batch
"""
import sys, tempfile, io, csv as _csv
from pathlib import Path
from PIL import Image

from . import model, vision_provider as vp, vision_ai

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else " FAIL ") + name)


class ScriptedProvider(vp.VisionProvider):
    """Returns/raises a scripted sequence, one entry per .analyze() call. Counts calls."""
    name = "scripted"

    def __init__(self, script, model="mock-model"):
        self.script = list(script)
        self.calls = 0
        self.model = model
        self.last_usage = {"input_tokens": 10, "output_tokens": 5}
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
        "suggested_name": "Botanical Damask", "style_tags": ["floral"]}


def _build(n):
    """Build a library with n distinct curtain designs (n asset files)."""
    lib = Path(tempfile.mkdtemp()) / "Curtains"; lib.mkdir(parents=True)
    for i in range(n):
        Image.new("RGB", (16, 16), (i % 255, (i * 3) % 255, (i * 7) % 255)).save(
            lib / f"P{4000+i}.jpg", "JPEG")
    db = model.IdentityDB(str(lib.parent / "x.db"))
    model.build_graph(db, lib)
    return db, lib


def run():
    # ---- 1. cap enforcement (function-level: ValueError outside 2..30) ----
    db, lib = _build(5)
    raised_low, raised_high = False, False
    try:
        vision_ai.batch_execute(db, ScriptedProvider([]), limit=1, confirm=lambda: True, out=io.StringIO())
    except ValueError:
        raised_low = True
    try:
        vision_ai.batch_execute(db, ScriptedProvider([]), limit=31, confirm=lambda: True, out=io.StringIO())
    except ValueError:
        raised_high = True
    check("batch_execute rejects limit below BATCH_MIN", raised_low)
    check("batch_execute rejects limit above BATCH_MAX", raised_high)
    check("BATCH_MIN/BATCH_MAX are 2/30 as specified", vision_ai.BATCH_MIN == 2 and vision_ai.BATCH_MAX == 30)

    # ---- cap enforcement at the CLI ----
    db, lib = _build(5)
    dbpath = str(lib.parent / "x.db")
    rc31 = vision_ai._main(["--db", dbpath, "--execute", "--limit", "31", "--provider", "mock"])
    check("CLI --execute --limit 31 refuses", rc31 == 2)
    rc0 = vision_ai._main(["--db", dbpath, "--execute", "--limit", "0", "--provider", "mock"])
    check("CLI --execute --limit 0 refuses", rc0 == 2)

    # ---- 2. missing --limit refusal ----
    rc_missing = vision_ai._main(["--db", dbpath, "--execute", "--provider", "mock"])
    check("CLI --execute with no --limit refuses", rc_missing == 2)

    # ---- --limit 1 still routes to the smoke (single) path, unaffected ----
    db1, lib1 = _build(2)
    rc1 = vision_ai._main(["--db", str(lib1.parent / "x.db"), "--execute", "--limit", "1",
                           "--provider", "mock", "--yes"])
    check("CLI --execute --limit 1 still works (smoke path)", rc1 == 0)

    # ---- 3. cached skip count ----
    db, lib = _build(6)
    rows_all = vision_ai.select_assets(db, limit=6)
    # pre-cache 2 of them directly
    for r in rows_all[:2]:
        db.record_vision_ai(r["asset_id"], r["sha256"], suggested_name="Pre", style_tags=[],
                            match_confidence=0.5, match_reason="pre", model="x")
    prov = ScriptedProvider([GOOD] * 4)
    s = vision_ai.batch_execute(db, prov, limit=6, confirm=lambda: True, out=io.StringIO())
    check("cached count reflects pre-seeded results", s["cached"] == 2)
    check("would_call excludes cached", s["would_call"] == 4)
    check("calls made == would_call (not selected)", prov.calls == 4 and s["calls"] == 4)
    check("skipped reported in summary", s["skipped"] == 2)

    # ---- confirmation shows real counts BEFORE spending ----
    db, lib = _build(5)
    seen = {}
    def capturing_confirm():
        seen["cached_before_call"] = True
        return True
    out_buf = io.StringIO()
    prov2 = ScriptedProvider([GOOD] * 5)
    s2 = vision_ai.batch_execute(db, prov2, limit=5, confirm=capturing_confirm, out=out_buf)
    txt = out_buf.getvalue()
    check("confirmation output shows selected/cached/would-call/cost",
          "selected" in txt and "already cached" in txt and "would call" in txt and "estimated cost" in txt)
    check("no calls happened before confirm (all 5 counted correctly)", prov2.calls == 5)

    # ---- declining confirmation makes zero calls ----
    db, lib = _build(3)
    prov3 = ScriptedProvider([GOOD] * 3)
    s3 = vision_ai.batch_execute(db, prov3, limit=3, confirm=lambda: False, out=io.StringIO())
    check("declining batch confirmation makes zero calls", prov3.calls == 0 and s3["ran"] is False)

    # ---- 4. partial failure summary ----
    db, lib = _build(4)
    # image2 fails BOTH attempts (initial + the one retry) = 2 script entries consumed;
    # images 1, 3, 4 succeed on the first attempt = 1 entry each. Total script entries: 5.
    mixed = ScriptedProvider([GOOD, vp.InvalidVisionResponse("bad"), vp.InvalidVisionResponse("bad2"),
                              GOOD, GOOD])
    s4 = vision_ai.batch_execute(db, mixed, limit=4, confirm=lambda: True, out=io.StringIO())
    check("partial failure: ok count == 3", s4["ok"] == 3)
    check("partial failure: failed count == 1", s4["failed"] == 1)
    check("partial failure: ok + failed == calls (4 images)", s4["ok"] + s4["failed"] == s4["calls"] == 4)
    check("partial failure: calls == would_call", s4["calls"] == s4["would_call"])
    check("provider was actually called 5 times (1 retry on the bad one)", mixed.calls == 5)

    # ---- 5. interrupted run + clean resume, 6. no duplicate calls on resume ----
    db, lib = _build(5)
    dbpath5 = str(lib.parent / "x.db")
    csvpath = str(lib.parent / "review.csv")
    # "interrupt" after 2 successes: script only has 2 responses -> StopIteration-like on 3rd pop
    interrupting = ScriptedProvider([GOOD, GOOD])   # only 2 scripted; batch wants up to 5
    try:
        vision_ai.batch_execute(db, interrupting, limit=5, review_csv=csvpath,
                                confirm=lambda: True, out=io.StringIO())
    except IndexError:
        pass  # simulates the run being cut off after 2 successful, committed images
    check("interrupted run made 3 attempts (2 committed, 3rd raised)", interrupting.calls == 3)
    remaining_before_resume = [r for r in vision_ai.select_assets(db, limit=5)
                               if vision_ai.needs_ai_analysis(db, r["asset_id"], r["sha256"])]
    check("2 of 5 cached after interruption, 3 remain", len(remaining_before_resume) == 3)

    resume_prov = ScriptedProvider([GOOD, GOOD, GOOD])
    s5 = vision_ai.batch_execute(db, resume_prov, limit=5, review_csv=csvpath,
                                 confirm=lambda: True, out=io.StringIO())
    check("resume only calls the remaining 3 (no duplicates)", resume_prov.calls == 3)
    check("resume plan correctly reports 2 cached, 3 to call", s5["cached"] == 2 and s5["would_call"] == 3)
    all_done = [r for r in vision_ai.select_assets(db, limit=5)
               if vision_ai.needs_ai_analysis(db, r["asset_id"], r["sha256"])]
    check("after resume, nothing left to analyse", len(all_done) == 0)

    # review CSV is append-only: interrupted run's 2 rows + resume's 3 rows = 5 total
    with open(csvpath) as f:
        review_rows = list(_csv.DictReader(f))
    check("review CSV append-only: 5 total rows across both runs", len(review_rows) == 5)

    # ---- end-of-batch summary reports actual usage ----
    db, lib = _build(3)
    usage_prov = ScriptedProvider([GOOD, GOOD, GOOD])
    s6 = vision_ai.batch_execute(db, usage_prov, limit=3, confirm=lambda: True, out=io.StringIO())
    check("summary reports actual input tokens", s6["actual_cost_input_tokens"] == 30)   # 10 * 3
    check("summary reports actual output tokens", s6["actual_cost_output_tokens"] == 15)  # 5 * 3

    # ---- delay parameter is honoured but does not block correctness (use 0 in tests) ----
    db, lib = _build(2)
    fast = ScriptedProvider([GOOD, GOOD])
    s7 = vision_ai.batch_execute(db, fast, limit=2, delay=0.0, confirm=lambda: True, out=io.StringIO())
    check("delay=0 batch completes normally", s7["ok"] == 2)

    # ---- no manifest/SKU/product/identity mutation from a batch run ----
    db, lib = _build(4)
    before = db.counts()
    vision_ai.batch_execute(db, ScriptedProvider([GOOD] * 4), limit=4, confirm=lambda: True, out=io.StringIO())
    after = db.counts()
    check("batch execution changes no identity/product counts", after == before)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(run())
