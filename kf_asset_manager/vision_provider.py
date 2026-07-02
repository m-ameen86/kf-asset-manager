"""Phase 3-b — Vision provider adapter scaffolding (NO real AI calls).

This is the integration boundary for Phase 3-c. It defines:
  * the provider interface (`VisionProvider`) and two implementations — a `MockVisionProvider`
    for tests and an `AnthropicVisionProvider` stub whose real network call is intentionally
    NOT enabled until 3-c;
  * the single structured prompt (`build_analysis_prompt`) that answers all three AI tasks
    — match verification, name suggestion, style tags — in ONE request per image;
  * the strict JSON response contract and a `validate_response` checker;
  * the controlled style vocabulary.

Nothing here calls an external API or requires a key. Cost/scale control and the dry-run
live in `vision_ai.py`.

────────────────────────────────────────────────────────────────────────────
STRICT JSON RESPONSE CONTRACT  (what the model MUST return in Phase 3-c)
────────────────────────────────────────────────────────────────────────────
The model is instructed to return ONLY this JSON object, no prose:

    {
      "match": {
        "is_match":   <bool>,        // image consistent with the catalogued type?
        "confidence": <0.0..1.0>,    // how sure
        "reason":     "<short text>" // ≤ ~120 chars
      },
      "suggested_name": "<short product name>",   // a SUGGESTION only
      "style_tags": ["<tag>", ...]                // 0..MAX_TAGS from STYLE_VOCAB
    }

Phase 3-c will: cache-check (sha256 + vision_version) → call the provider once → run the
response through `validate_response` → store via the existing `vision_results` columns
(`suggested_name`, `style_tags`, `match_confidence`, `match_reason`, `model`). A manual
value always wins and is never overwritten. None of this is identity.
"""
import base64
import io
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

# Controlled style/aesthetic vocabulary (decision D5: small + filterable, not free-form).
# 3-c.3: expanded with kids-safe commercial tags after real-slice review showed nursery/
# kids patterns had no fitting tag (everything fell back to generic ones like "minimal").
STYLE_VOCAB = [
    "floral", "botanical", "geometric", "abstract", "striped", "paisley",
    "damask", "ornate", "minimal", "modern", "traditional", "vintage",
    "oriental", "contemporary", "textured",
    "kids", "nursery", "playful", "cartoon", "novelty",
]
MAX_TAGS = 4

# Default vision model + a documented per-call cost ESTIMATE (real cost varies by model,
# image size and tokens; override at the CLI). Used only for dry-run budgeting.
DEFAULT_MODEL = "claude-sonnet-5"            # current generation vision-capable model
PER_CALL_USD_DEFAULT = 0.01

_MEDIA = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}

# Anthropic recommends a long edge <= 1568px; we downscale before sending (smaller + cheaper).
MAX_EDGE = 1568
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class InvalidVisionResponse(Exception):
    """Model reply could not be parsed into the JSON contract."""


class VisionTransportError(Exception):
    """Network/HTTP failure talking to the provider (after retries)."""


class VisionAuthError(Exception):
    """Authentication failure (bad/missing key) — never retried."""


def strip_fences(text):
    """Remove ```json / ``` fences and surrounding prose, returning the JSON-ish core."""
    t = (text or "").strip()
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", t, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return t


def parse_vision_text(text):
    """Strip fences and parse JSON; on failure, extract the first {...} block; else raise."""
    core = strip_fences(text)
    try:
        return json.loads(core)
    except Exception:
        pass
    m = re.search(r"\{.*\}", core, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    raise InvalidVisionResponse("could not parse JSON from model reply")


def build_analysis_prompt(*, product_type, design_number=None, filename=None):
    """The single structured instruction covering match + name + style tags. Pure text."""
    ctx = f"catalogued as a {product_type}"
    if design_number is not None:
        ctx += f" (design #{design_number})"
    tags = ", ".join(STYLE_VOCAB)
    return (
        "You are assisting a textile catalogue. Analyse the attached product image, which is "
        f"{ctx}.\n"
        "Return ONLY a JSON object (no prose, no markdown) with exactly these keys:\n"
        '  "match": {"is_match": bool, "confidence": number 0..1, "reason": short string},\n'
        '  "suggested_name": a short, customer-facing PRODUCT name for a home-décor catalogue,\n'
        f'  "style_tags": an array of 0 to {MAX_TAGS} tags chosen ONLY from this list: [{tags}].\n'
        "Naming guidance for suggested_name: prefer 3-6 words; describe the actual motif/scene "
        "(e.g. \"Sleeping Fox Meadow\", \"Coastal Palm Breeze\") rather than a generic category "
        "label; avoid ending in a generic word like \"Textile\", \"Print\", or \"Pattern\" unless "
        "no more descriptive name is possible; use warm, customer-facing décor language, not "
        "technical or literal descriptions. If the design visually reads as a children's or "
        "nursery pattern (cartoon characters, playful motifs, baby animals, soft pastel scenes), "
        "prefer kids/nursery-appropriate wording in the name and choose the kids/nursery/playful/"
        "cartoon/novelty tags when they fit, rather than defaulting to generic tags.\n"
        "Judge is_match by whether the image is visually consistent with the catalogued "
        "product type. Do not invent tags outside the list."
    )


def validate_response(obj):
    """Validate a model response against the strict contract. Returns (ok, errors)."""
    errs = []
    if not isinstance(obj, dict):
        return False, ["response is not a JSON object"]
    m = obj.get("match")
    if not isinstance(m, dict):
        errs.append("missing/invalid 'match'")
    else:
        if not isinstance(m.get("is_match"), bool):
            errs.append("match.is_match must be bool")
        c = m.get("confidence")
        if not isinstance(c, (int, float)) or not (0.0 <= float(c) <= 1.0):
            errs.append("match.confidence must be a number in 0..1")
        if not isinstance(m.get("reason"), str):
            errs.append("match.reason must be a string")
    if not isinstance(obj.get("suggested_name"), str) or not obj.get("suggested_name").strip():
        errs.append("suggested_name must be a non-empty string")
    tags = obj.get("style_tags")
    if not isinstance(tags, list):
        errs.append("style_tags must be a list")
    else:
        if len(tags) > MAX_TAGS:
            errs.append(f"style_tags exceeds MAX_TAGS ({MAX_TAGS})")
        for t in tags:
            if t not in STYLE_VOCAB:
                errs.append(f"style_tag '{t}' not in controlled vocabulary")
    return (not errs), errs


def _media_type(path):
    return _MEDIA.get(Path(path).suffix.lower(), "image/jpeg")


class VisionProvider:
    """Adapter interface. 3-c implementations return a dict matching the JSON contract."""
    name = "base"

    def available(self):
        return False

    def analyze(self, image_path, prompt):
        raise NotImplementedError


class MockVisionProvider(VisionProvider):
    """Deterministic, offline provider for tests. Counts calls; never touches the network."""
    name = "mock"

    def __init__(self, response=None):
        self.calls = 0
        self.last_usage = {"input_tokens": 0, "output_tokens": 0}
        self._response = response or {
            "match": {"is_match": True, "confidence": 0.95, "reason": "consistent with type"},
            "suggested_name": "Botanical Damask",
            "style_tags": ["floral", "damask"],
        }

    def available(self):
        return True

    def analyze(self, image_path, prompt):
        self.calls += 1
        return dict(self._response)


class AnthropicVisionProvider(VisionProvider):
    """Anthropic vision adapter. In 3-b the real network call is NOT enabled — `analyze`
    raises. `build_request` is pure and testable so 3-c only has to perform the POST."""
    name = "anthropic"

    def __init__(self, api_key=None, model=DEFAULT_MODEL):
        import os
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.last_usage = {}
        self.last_model = model

    def available(self):
        return bool(self.api_key)

    def build_request(self, image_path, prompt, max_tokens=512):
        """Pure: assemble the Messages API payload (downscaled base64 image + prompt)."""
        from PIL import Image
        media = _media_type(image_path)
        raw = Path(image_path).read_bytes()
        # downscale if the long edge exceeds MAX_EDGE (smaller payload, lower cost)
        try:
            im = Image.open(io.BytesIO(raw))
            if max(im.size) > MAX_EDGE:
                im = im.convert("RGB")
                im.thumbnail((MAX_EDGE, MAX_EDGE))
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=90)
                raw, media = buf.getvalue(), "image/jpeg"
        except Exception:
            pass  # if PIL can't open it, send the original bytes
        data = base64.b64encode(raw).decode("ascii")
        return {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media, "data": data}},
                    {"type": "text", "text": prompt},
                ],
            }],
        }

    def analyze(self, image_path, prompt, timeout=60, retries=2):
        """Phase 3-c: ONE real Messages API call (with simple transport retries). Returns the
        parsed contract dict; raises InvalidVisionResponse / VisionAuthError /
        VisionTransportError. Records token usage in self.last_usage. Never logs the key."""
        if not self.api_key:
            raise VisionAuthError("no API key")
        body = json.dumps(self.build_request(image_path, prompt)).encode("utf-8")
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        last = None
        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(ANTHROPIC_URL, data=body, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    payload = json.loads(r.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:
                code = e.code
                if code in (401, 403):
                    raise VisionAuthError(f"auth failed (HTTP {code})")
                if code == 429 or 500 <= code < 600:
                    last = VisionTransportError(f"HTTP {code}")
                    continue  # retry
                raise VisionTransportError(f"HTTP {code}")
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last = VisionTransportError(str(e))
                continue
        else:
            raise last or VisionTransportError("request failed")

        self.last_usage = payload.get("usage", {}) or {}
        self.last_model = payload.get("model", self.model)
        text = "".join(b.get("text", "") for b in payload.get("content", []) if b.get("type") == "text")
        return parse_vision_text(text)        # raises InvalidVisionResponse on bad JSON


def get_provider(name="anthropic", api_key=None, model=DEFAULT_MODEL):
    if name == "mock":
        return MockVisionProvider()
    return AnthropicVisionProvider(api_key=api_key, model=model)
