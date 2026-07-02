"""Phase 2 — Versioned Rule Engine.

Filename parsing as an ordered list of named, data-driven rules carried with a
`RULES_VERSION`. The engine core never changes when a convention is added — you add a
rule entry. Implements the locked naming policy (v1.3/v1.4):

  * Legacy curtain A/B -> Left/Right (frozen).
  * Legacy non-curtain A/B -> distinct-design suffix, BACKWARD-COMPATIBLE only
    (flagged `legacy_ab=True`; never generated for new assets).
  * New design compositions -> D1/D2/D3 (distinct designs; the canonical token).
  * `Variant` (size/material/colour/side) is a commerce concept, never `D`.

Each rule is pure data: name, priority, a regex with named groups, the kind of thing
it matches, and a base confidence. Normalisation turns raw groups into a canonical
ParseResult. A folder name is used only as a low-confidence fallback.
"""

import re

from . import config

RULES_VERSION = 3   # v3: fabric pattern/colourway rule (pattern=design, colour=variant)

# Ordered, data-driven rules. Lower priority number = tried first.
RULES = [
    dict(name="batched_set", priority=10, kind="set", base_confidence=0.95,
         regex=r"^\((?P<batch>\d{1,2}-\d{1,2})\)\s*"
               r"C(?P<set>\d+)"
               r"(?:-(?P<side>[ABLR]))?"
               r"(?:-D(?P<dvar>\d+))?"
               r"(?:[-\s]*(?P<piece>cushion|runner|table\s*cloth|tablecloth)(?:\s*(?P<pidx>\d+))?)?$"),
    # Engineered panels: P#### (canonical, no space) or 'P ####' (legacy, space).
    # Tokens, in order: -V#/-D# version, -L/-R/-C side, -cush derived cushion.
    dict(name="engineered_panel", priority=15, kind="panel", base_confidence=0.92,
         regex=r"^P\s*(?P<num>\d{3,4})"
               r"(?:[-\s]+(?P<pver>V\d+|D\d+|\d{1,2}|[ABD-KM-QS-Z]))?"
               r"(?:-(?P<pside>[LRC])(?=-|$))?"
               r"(?:-(?P<papp>cush(?:ion)?))?$"),
    dict(name="flat_curtain", priority=20, kind="curtain", base_confidence=0.90,
         regex=r"^(?P<line>[A-Za-z][A-Za-z ]*?)[\s-]+(?P<number>\d{2,})"
               r"(?:-D(?P<dvar>\d+))?"
               r"(?:-(?P<side>[A-Za-z]))?$"),
    # Fabric / repeat-pattern codes. The PATTERN is the design identity; an optional
    # trailing -<number> is a COLOURWAY (a commerce variant, NOT a new design), per the
    # locked Design-vs-Variant policy. Accepts the real library forms:
    #   bare number  15, 16            -> pattern 15        (single colourway)
    #   G-prefixed    G122-2, G122-3   -> pattern G122, colourway 2
    #   numeric       1003-01, 1003-02 -> pattern 1003, colourway 01
    #   legacy named  4011_Floral      -> pattern 4011, line "Floral"
    dict(name="fabric_code", priority=30, kind="fabric", base_confidence=0.82,
         regex=r"^(?P<pattern>[A-Za-z]{0,3}\d{1,4})"
               r"(?:[-_](?P<colour>\d{1,3}))?"
               r"(?:[-_](?P<name>[A-Za-z][\w ]*?))?$"),
]

_COMPILED = [(r, re.compile(r["regex"], re.I)) for r in sorted(RULES, key=lambda x: x["priority"])]

PIECE_TYPE = {
    "cushion": "Cushion", "runner": "Table Runner",
    "tablecloth": "Table Cloth", "table cloth": "Table Cloth",
}


def _norm_side_curtain(raw):
    """Curtain side normalisation: A/L -> L, B/R -> R, C -> merged single."""
    if not raw:
        return None, False
    raw = raw.upper()
    if raw == config.MERGED_SIDE:           # 'C'
        return None, True
    return config.SIDE_ALIASES.get(raw), False


def parse(filename, folder_name=None):
    """Parse a filename into a canonical ParseResult dict."""
    stem = re.sub(r"\.[^.]+$", "", filename).strip()
    matched = None
    for rule, rx in _COMPILED:
        m = rx.match(stem)
        if m:
            matched = (rule, m.groupdict())
            break

    res = {
        "filename": filename, "stem": stem, "rules_version": RULES_VERSION,
        "rule": None, "confidence": 0.0,
        "asset_type": None, "design_type": None,
        "set_code": None, "batch": None, "set_num": None,
        "line": None, "number": None,
        "side": None, "side_raw": None, "piece": None, "cushion_index": None,
        "design_variant": None, "is_merged": False, "colorway": None,
        "legacy_ab": False, "needs_review": False, "review_reason": None,
        "design_key": None,
        "family_code": None, "is_derived": False,
        "artwork_role": "Original", "artwork_relationship": "Original",
    }

    if not matched:
        # fall back to folder hint only (low confidence) -> needs review
        atype = _folder_type(folder_name)
        res.update(rule="folder_fallback", confidence=0.40,
                   asset_type=atype, design_type=_design_type_for(atype, None, folder_name),
                   needs_review=True, review_reason="no filename rule matched",
                   design_key=f"STEM|{folder_name or ''}|{stem.lower()}")
        return res

    rule, g = matched
    res["rule"] = rule["name"]
    res["confidence"] = rule["base_confidence"]
    dvar = g.get("dvar")
    res["design_variant"] = f"D{int(dvar)}" if dvar else None

    if rule["kind"] == "set":
        res["batch"] = _norm_batch(g["batch"])
        res["set_num"] = g["set"]
        res["set_code"] = f"{res['batch']}/C{int(g['set'])}"
        piece = (g.get("piece") or "").lower().replace("  ", " ").strip() or None
        res["piece"] = "tablecloth" if piece in ("table cloth", "tablecloth") else piece
        res["cushion_index"] = int(g["pidx"]) if g.get("pidx") else None
        if res["piece"]:                       # a named piece (cushion/runner/…)
            res["asset_type"] = PIECE_TYPE.get(res["piece"], "Unknown")
            # legacy A/B on a non-curtain piece = legacy distinct-design suffix
            if g.get("side") and g["side"].upper() in ("A", "B"):
                res["side_raw"] = g["side"].upper()
                res["legacy_ab"] = True
            elif g.get("side") and g["side"].upper() in ("L", "R"):
                res["side_raw"] = g["side"].upper()
        else:                                   # no piece word -> the curtain
            res["asset_type"] = "Curtain Panel Set"
            res["side"], res["is_merged"] = _norm_side_curtain(g.get("side"))
            res["side_raw"] = (g.get("side") or "").upper() or None
            if g.get("side") and g["side"].upper() in ("A", "B"):
                res["legacy_ab"] = True
        res["design_type"] = "set_piece"

    elif rule["kind"] == "panel":
        num = g["num"]
        ver = g.get("pver")
        if ver:
            ver = ver.upper()
            if ver.isdigit():           # '-2' means a version, equivalent to '-V2'
                ver = f"V{int(ver)}"
        res["number"] = num
        res["family_code"] = f"P{num}"          # family grouping code (e.g. P4204)
        res["design_variant"] = ver or None     # 'V2' / 'D2' / 'A' / 'B' …
        res["side"], res["is_merged"] = _norm_side_curtain(g.get("pside"))
        res["side_raw"] = (g.get("pside") or "").upper() or None
        res["design_type"] = "engineered_panel"
        if g.get("papp"):                        # -cush -> derived cushion artwork
            res["asset_type"] = "Cushion"
            res["is_derived"] = True
            res["artwork_role"] = "Derived"
            res["artwork_relationship"] = "Cropped"
        else:                                    # curtain panel (L / R / merged C)
            res["asset_type"] = "Curtain Panel Set"

    elif rule["kind"] == "curtain":
        res["line"] = g["line"].strip().title()
        res["number"] = g["number"]
        res["asset_type"] = "Curtain Panel Set"
        res["side"], res["is_merged"] = _norm_side_curtain(g.get("side"))
        res["side_raw"] = (g.get("side") or "").upper() or None
        if g.get("side") and g["side"].upper() in ("A", "B"):
            res["legacy_ab"] = True
        # unknown trailing letter (not A/B/L/R/C) -> review, don't guess
        if g.get("side") and g["side"].upper() not in ("A", "B", "L", "R", "C"):
            res["needs_review"] = True
            res["review_reason"] = f"unknown side suffix -{g['side'].upper()}"
        res["design_type"] = "engineered_panel"

    elif rule["kind"] == "fabric":
        # PATTERN (incl. any letter prefix, upper-cased) is the design identity.
        res["number"] = g["pattern"].upper()
        res["line"] = (g.get("name") or "").strip().title() or None
        # trailing -<n> is a COLOURWAY: a variant of the same pattern, never a new design.
        cw = g.get("colour")
        res["colorway"] = f"{int(cw):02d}" if cw else None
        res["asset_type"] = "Pattern"
        res["design_type"] = "repeat_pattern"

    # folder may upgrade an unknown asset_type, but never overrides a rule hit's type
    if res["asset_type"] in (None, "Unknown") and folder_name:
        ft = _folder_type(folder_name)
        if ft != "Unknown":
            res["asset_type"] = ft

    res["design_key"] = _design_key(res)
    return res


# --- helpers ----------------------------------------------------------------

def _norm_batch(b):
    a, c = re.split(r"\s*-\s*", b)
    return f"{int(a):02d}-{int(c):02d}"


def _folder_type(folder_name):
    if not folder_name:
        return "Unknown"
    n = re.sub(r"\s+", " ", folder_name.strip().lower())
    for pat, atype, _hint in config.FOLDER_TYPE_RULES:
        if re.search(pat, n):
            return atype
    return "Unknown"


def _design_type_for(atype, set_code, folder_name):
    f = (folder_name or "").lower()
    if set_code:
        return "set_piece"
    if atype in ("Pattern", "Fabric") or "fabric" in f or "pattern" in f:
        return "repeat_pattern"
    if atype in ("Tapestry Artwork", "Tapestry") or "tapestry" in f:
        return "fixed_artwork"
    if any(k in f for k in ("poster", "t-shirt", "tshirt", "canvas", "apparel")):
        return "placed_artwork"
    if atype == "Curtain Panel Set":
        return "engineered_panel"
    return "unknown"


def _design_key(res):
    """Internal dedupe key (NOT an identity). D-variants split designs; legacy A/B
    on non-curtains split designs; curtain A/B/L/R do not (they're one paired design)."""
    dv = res["design_variant"] or ""
    if res["family_code"]:                       # engineered panel (P####)
        # curtain panels (L/R/C) AND their derived cushions of the same code+version
        # are ONE design; a different version (V2/D2) is a sibling design.
        return f"PANEL|{res['family_code']}|{dv}"
    if res["set_code"]:
        if res["asset_type"] == "Curtain Panel Set":
            return f"SET|{res['set_code']}|curtain|{dv}"
        return (f"SET|{res['set_code']}|{res['piece']}|{res['cushion_index'] or ''}|"
                f"{res['side_raw'] or ''}|{dv}")
    if res["asset_type"] == "Curtain Panel Set" and res["line"] and res["number"]:
        head = "CURC" if res["is_merged"] else "CUR"
        return f"{head}|{res['line']}|{res['number']}|{dv}"
    if res["asset_type"] in ("Pattern", "Fabric") and res["number"]:
        return f"FAB|{res['number']}|{dv}"
    return f"STEM|{res['stem'].lower()}|{dv}"
