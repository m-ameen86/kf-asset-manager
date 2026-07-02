"""Classification + naming.

Vision classification is a *pluggable, optional* step. If an ANTHROPIC_API_KEY is
configured and the anthropic SDK is installed, classify_asset() asks Claude for
Style / Theme / Primary Motif / Occasion / Region / tags / a selling-name
suggestion. Otherwise it is a no-op and those ai_ fields stay empty for manual
entry. Either way these only ever populate ai_ columns — manual edits win.

Title building uses *effective* values (manual ?? ai), so a title regenerates
correctly the moment you override any field.
"""

import json
import os
import re
import time

from . import config


def _humanise(token):
    if not token or token == "none":
        return ""
    return token.replace("-", " ").title()


def build_title(eff: dict, type_label: str) -> str:
    """eff = effective field values for one asset. Returns a generated title.
    Falls back gracefully when classification is missing."""
    selling = eff.get("selling_name") or "Untitled"
    headline = _humanise(eff.get("primary_motif")) or _humanise(eff.get("style"))
    color = eff.get("color") or ""
    title = config.TITLE_TEMPLATE.format(
        selling_name=selling, headline=headline, type_label=type_label, color=color)
    return re.sub(r"\s+", " ", title.replace("—  ", "— ")).strip(" —")


# ----------------------------------------------------------------- vision
SYSTEM = (
    "You catalogue textile / home-decor artwork for Karen Fabrics (KF), an "
    "Egyptian-Gulf-UK home and fashion brand. Tagline: 'Where Ideas Become Fabric'. "
    "Return ONLY a JSON object, no prose."
)


def _prompt(vocab):
    return (
        "Classify this artwork. Choose values from the given vocabularies where they "
        "fit; you may add one new value only if nothing fits.\n\n"
        f"style: {vocab['style']}\n"
        f"theme: {vocab['theme']}\n"
        f"primary_motif: {vocab['primary_motif']}\n"
        f"occasion: {vocab['occasion']}\n"
        f"region: {vocab['region']}\n\n"
        "Return JSON with keys: style, theme, primary_motif, occasion, region, "
        "tags (4-8 lowercase strings), description (one sentence), "
        "selling_name (an evocative 1-3 word collection name in KF voice; a mood or "
        "place, NOT a literal restatement of the style or colour). "
        "Confidence 0-1 in 'confidence'."
    )


def _parse(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    s, e = text.find("{"), text.rfind("}")
    return json.loads(text[s:e + 1]) if s != -1 else {}


def classify_available():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa
        return True
    except ImportError:
        return False


def classify_asset(thumb_b64, media_type, vocab, model="claude-haiku-4-5-20251001"):
    """Call Claude vision. Returns a dict of ai_ suggestions, or {} on failure."""
    if not classify_available():
        return {}
    from anthropic import Anthropic
    client = Anthropic()
    for attempt in range(3):
        try:
            msg = client.messages.create(
                model=model, max_tokens=600, system=SYSTEM,
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {
                        "type": "base64", "media_type": media_type, "data": thumb_b64}},
                    {"type": "text", "text": _prompt(vocab)},
                ]}],
            )
            text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
            return _parse(text)
        except Exception:
            if attempt == 2:
                return {}
            time.sleep(2 * (attempt + 1))


def suggest_set_name(component_names):
    """Lightweight fallback set selling-name when no per-set vision call is made:
    reuse the most common component selling_name, else blank for manual entry."""
    names = [n for n in component_names if n]
    if not names:
        return ""
    return max(set(names), key=names.count)
