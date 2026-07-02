"""Phase 3-b tests — vision provider adapter scaffolding (MOCKED; no real calls, no key).

Run: python -m kf_asset_manager.tests_vision_ai
"""
import sys, tempfile, os
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
    regardless of the developer's real shell environment, and so AnthropicVisionProvider's
    env-fallback can never pick up a real key inside a test (which could otherwise trigger
    an actual network call). Always restores the original value afterward."""
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        yield
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved


def run():
    # ---- structured prompt ----
    p = vp.build_analysis_prompt(product_type="Curtain", design_number=19, filename="P4019.jpg")
    check("prompt mentions the catalogued type", "Curtain" in p)
    check("prompt demands JSON-only", "ONLY a JSON object" in p)
    check("prompt lists the three keys", all(k in p for k in ("match", "suggested_name", "style_tags")))
    check("prompt constrains tags to the vocabulary", "floral" in p and "damask" in p)
    # ---- 3-c.3: naming guidance + expanded kids/nursery vocabulary ----
    check("prompt gives word-count guidance (3-6 words)", "3-6 words" in p)
    check("prompt discourages generic 'Textile'/'Print' endings", "Textile" in p and "generic" in p)
    check("prompt asks for warm customer-facing décor language", "customer-facing" in p)
    check("prompt nudges kids/nursery wording when it fits", "nursery" in p and "kids" in p)
    check("STYLE_VOCAB includes the new kids-safe tags",
          all(t in vp.STYLE_VOCAB for t in ("kids", "nursery", "playful", "cartoon", "novelty")))
    check("expanded vocab still validates a kids-tagged response",
          vp.validate_response({"match": {"is_match": True, "confidence": 0.8, "reason": "ok"},
                                "suggested_name": "Sleepy Moon & Stars Nursery Print",
                                "style_tags": ["kids", "nursery", "playful"]})[0])

    # ---- response contract validation ----
    good = {"match": {"is_match": True, "confidence": 0.9, "reason": "ok"},
            "suggested_name": "Botanical Damask", "style_tags": ["floral", "damask"]}
    ok, errs = vp.validate_response(good)
    check("valid response passes", ok and not errs)
    bad_conf = {**good, "match": {"is_match": True, "confidence": 5, "reason": "x"}}
    check("confidence out of range rejected", not vp.validate_response(bad_conf)[0])
    bad_tag = {**good, "style_tags": ["floral", "sparkly"]}
    check("tag outside vocabulary rejected", not vp.validate_response(bad_tag)[0])
    kids_resp = {**good, "style_tags": ["kids", "nursery", "playful", "cartoon"]}
    check("all 4 new kids tags together validate (within MAX_TAGS)", vp.validate_response(kids_resp)[0])
    novelty_resp = {**good, "style_tags": ["novelty"]}
    check("novelty tag validates alone", vp.validate_response(novelty_resp)[0])
    bad_missing = {"suggested_name": "x", "style_tags": []}
    check("missing match rejected", not vp.validate_response(bad_missing)[0])
    bad_name = {**good, "suggested_name": ""}
    check("empty name rejected", not vp.validate_response(bad_name)[0])
    too_many = {**good, "style_tags": ["floral", "damask", "ornate", "modern", "vintage"]}
    check("too many tags rejected", not vp.validate_response(too_many)[0])

    # ---- mock provider returns a contract-valid response ----
    mock = vp.MockVisionProvider()
    resp = mock.analyze("x.jpg", "prompt")
    check("mock provider available", mock.available())
    check("mock response is contract-valid", vp.validate_response(resp)[0])

    # ---- anthropic stub: pure request build, inert analyze, key-gated availability ----
    d = Path(tempfile.mkdtemp())
    img = d / "p.jpg"
    Image.new("RGB", (8, 8), (10, 20, 30)).save(img)
    with no_api_key_env():
        prov_nokey = vp.AnthropicVisionProvider(api_key=None)
        check("anthropic without key -> unavailable (env-isolated)", prov_nokey.available() is False)
    prov = vp.AnthropicVisionProvider(api_key="sk-test")
    req = prov.build_request(str(img), "hello")
    check("build_request has model + messages", "model" in req and req["messages"])
    check("build_request embeds base64 image", req["messages"][0]["content"][0]["source"]["data"])
    check("build_request includes the prompt text",
          req["messages"][0]["content"][1]["text"] == "hello")
    # analyze() without a key raises immediately — no network call is attempted.
    # CRITICAL: isolated from the real shell environment, since AnthropicVisionProvider
    # falls back to os.environ["ANTHROPIC_API_KEY"] — without this guard, a developer
    # with a real key exported would cause this test to attempt an ACTUAL API call.
    raised = False
    with no_api_key_env():
        try:
            vp.AnthropicVisionProvider(api_key=None).analyze(str(img), "p")
        except vp.VisionAuthError:
            raised = True
    check("analyze without key raises VisionAuthError, env-isolated (no network)", raised)

    # ---- dry-run on a real build makes NO provider call ----
    lib = Path(tempfile.mkdtemp()) / "Curtains"; lib.mkdir(parents=True)
    for n, c in [("P4186-L", (1, 2, 3)), ("P4186-R", (4, 5, 6)), ("Kids-3040-L", (9, 9, 0))]:
        Image.new("RGB", (16, 16), c).save(lib / (n + ".jpg"), "JPEG")
    db = model.IdentityDB(str(lib.parent / "x.db"))
    model.build_graph(db, lib)

    counting = vp.MockVisionProvider()
    import io
    info = vision_ai.dry_run(db, counting, limit=3, out=io.StringIO())
    check("dry-run made ZERO provider calls", counting.calls == 0)
    check("dry-run selected the slice", info["selected"] == 3)
    check("dry-run would-analyse all (nothing cached yet)", info["to_call"] == 3)
    check("dry-run estimates calls = uncached images", info["estimated_calls"] == 3)
    check("dry-run estimates a cost", info["estimated_cost_usd"] == round(3 * vp.PER_CALL_USD_DEFAULT, 2))
    check("dry-run shows a sample prompt", "JSON object" in info["sample_prompt"])
    check("dry-run sample prompt reflects the 3-c.3 naming guidance",
          "3-6 words" in info["sample_prompt"] and "nursery" in info["sample_prompt"])

    # ---- cache awareness: pre-seed an AI result -> it drops out of 'to_call' ----
    aid = db.conn.execute("SELECT asset_id,sha256 FROM assets LIMIT 1").fetchone()
    import time as _t
    db.conn.execute("""INSERT INTO vision_results(asset_id,sha256,vision_version,suggested_name,analyzed_at)
                       VALUES(?,?,?,?,?)
                       ON CONFLICT(asset_id) DO UPDATE SET suggested_name=excluded.suggested_name,
                         sha256=excluded.sha256, vision_version=excluded.vision_version""",
                    (aid["asset_id"], aid["sha256"], model.VISION_VERSION, "Pre-named", _t.time()))
    db.conn.commit()
    info2 = vision_ai.plan(db, limit=3)
    check("cached AI result is skipped in plan", info2["cached"] == 1 and info2["to_call"] == 2)

    # ---- missing key does not break dry-run (env-isolated so the assertion is honest) ----
    with no_api_key_env():
        nokey = vp.get_provider("anthropic")
        info3 = vision_ai.dry_run(db, nokey, limit=3, out=io.StringIO())
    check("dry-run works with no API key (env-isolated)", info3["selected"] == 3)

    # ---- identity untouched ----
    before = db.counts()
    vision_ai.dry_run(db, counting, limit=3, out=io.StringIO())
    check("dry-run changes no identity counts", db.counts() == before)
    check("dry-run still made zero calls", counting.calls == 0)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(run())
