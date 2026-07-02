"""Phase 4-a — Business SKU generation (pure, derived, never identity).

A SKU identifies the exact sellable/printable unit. It is *derived* from identity +
relationships and may be regenerated or rebranded at will — internal `KF-…` IDs never
change. Format:

    KF-<TYPE>-<DESIGN>-<VARIANT>

    KF-CUR-000019            curtain · design 19 · the pair (base)
    KF-CUR-000019-L          curtain · design 19 · left panel
    KF-CSH-000019-R          cushion · design 19 · right (derived) cushion
    KF-FAB-000087-C02        fabric  · design 87 · colourway 02

Variant suffixes derive from the v2.0 Artwork Source model (curtain side / merged,
cushion Source side, fabric colourway). Market is NOT in the SKU (Shopify markets handle
region), so one SKU is stable worldwide.

These are pure functions — no DB. The DB wiring (per product/variant) lands in Phase 4-d.
"""
import re

from . import config

DESIGN_WIDTH = 6           # matches the internal KF-…-NNNNNN width


def design_number(design):
    """Accept an int, a Display ID ('D19'), or an internal ID ('KF-D-000019') -> 19."""
    if isinstance(design, int):
        return design
    s = str(design).strip().upper()
    m = re.search(r"(\d+)\s*$", s)        # trailing digits
    if not m:
        raise ValueError(f"cannot read a design number from {design!r}")
    return int(m.group(1))


def type_code(product_type):
    """Canonical product_type -> SKU type code ('Curtain' -> 'CUR', 'Fabric' -> 'FAB')."""
    return config.product_type_sku_code(product_type)


def variant_suffix(product_type, *, side=None, colorway=None, merged=False):
    """Derive the variant segment from the v2.0 model.

    Curtain: pair is the base (no suffix); L/R single panels; merged -> SINGLE.
    Cushion: sided L/R from its Source; unsided -> base.
    Fabric:  colourway -> C01/C02…; single-colour -> base.
    Other types: no sub-variant.
    """
    t = product_type
    side = (side or "").upper() or None
    if t == "Curtain":
        if merged:
            return "SINGLE"
        if side in ("L", "R"):
            return side
        return ""                       # pair = base unit (decision D1)
    if t == "Cushion":
        return side if side in ("L", "R") else ""
    if t == "Fabric":
        if colorway is not None and str(colorway) != "":
            return f"C{int(colorway):02d}"   # decision D2
        return ""
    return ""                            # Runner/Tablecloth/Tapestry/Apparel/Flag/Painting


def sku_for(product_type, design, variant=""):
    """Compose a full SKU from a product_type, a design (id/number), and a variant suffix."""
    code = type_code(product_type)
    num = design_number(design)
    base = f"KF-{code}-{num:0{DESIGN_WIDTH}d}"
    return f"{base}-{variant}" if variant else base


def sku(product_type, design, *, side=None, colorway=None, merged=False):
    """Convenience: derive the variant suffix and compose the SKU in one call."""
    return sku_for(product_type, design,
                   variant_suffix(product_type, side=side, colorway=colorway, merged=merged))


# --- query parsing (used by the padding-insensitive resolver, Phase 4-b) ---------
_SKU_RE = re.compile(r"^KF-(?P<code>[A-Z]{3})-(?P<num>\d+)(?:-(?P<variant>[A-Z0-9]+))?$")
_CODE_TO_TYPE = {v: k for k, v in config.PRODUCT_TYPE_SKU_CODE.items()}


def variant_descriptor(*, side=None, colorway=None, merged=False):
    """Friendly option label, consistent with the SKU suffix:
    Left / Right / Single / Colour 02 / None (pair or sole base variant)."""
    if merged:
        return "Single"
    side = (side or "").upper() or None
    if side == "L":
        return "Left"
    if side == "R":
        return "Right"
    if colorway is not None and str(colorway) != "":
        return f"Colour {int(colorway):02d}"
    return None


def variant_inputs(role, side):
    """Map a stored asset (role, side) to the SKU variant inputs.
    Roles seen in the model: panel-L/R, cushion-L/R, single-merged, fabric-c0n."""
    role = role or ""
    merged = role == "single-merged"
    colorway = None
    m = re.match(r"fabric-c(\d+)$", role)
    if m:
        colorway = m.group(1)
    return {"side": side, "colorway": colorway, "merged": merged}


def parse_query(query):
    """Normalize any human/SKU input to its parts. Returns a dict with at least
    `design_number`; plus `product_type` / `variant` when the query is a full SKU.

    Accepts: '19', 'd19', '000019', 'KF-D-000019', 'KF-CUR-000019-L', 'KF-FAB-000087-C02'.
    """
    q = str(query).strip().upper()
    out = {"design_number": None, "product_type": None, "variant": None}
    m = _SKU_RE.match(q)
    if m:                                  # full business SKU
        out["design_number"] = int(m.group("num"))
        out["product_type"] = _CODE_TO_TYPE.get(m.group("code"))
        out["variant"] = m.group("variant")
        return out
    m = re.match(r"^KF-D-(\d+)$", q)        # internal design ID
    if m:
        out["design_number"] = int(m.group(1))
        return out
    m = re.match(r"^D?(\d+)$", q)           # 'D19' or bare '19' / '000019'
    if m:
        out["design_number"] = int(m.group(1))
        return out
    return out                              # unrecognised -> design_number None
