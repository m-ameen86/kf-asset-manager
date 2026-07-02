"""Phase 3-a — Local colour extraction (no AI, no key, no cost).

Dominant colours come straight from the pixels: quantize the image to a small palette,
count coverage, and map each colour to a named vocabulary (KF brand colours first, then a
general set). Deterministic and offline — re-runs are identical, and results cache by the
asset's sha256.
"""
from PIL import Image

# KF brand colours take naming priority, then a general named set.
KF_BRAND = {
    "KF Navy": (0x1B, 0x2A, 0x4A),
    "KF Gold": (0xB8, 0x94, 0x3F),
    "KF Ivory": (0xF5, 0xED, 0xD6),
    "KF Charcoal": (0x2A, 0x2A, 0x2A),
}
GENERAL = {
    "Black": (0, 0, 0), "White": (255, 255, 255), "Grey": (128, 128, 128),
    "Red": (200, 30, 30), "Maroon": (128, 0, 0), "Orange": (230, 140, 40),
    "Yellow": (235, 205, 60), "Olive": (128, 128, 0), "Green": (40, 140, 60),
    "Teal": (0, 128, 128), "Blue": (40, 70, 180), "Navy": (20, 30, 90),
    "Purple": (120, 50, 140), "Pink": (235, 170, 190), "Brown": (120, 72, 40),
    "Beige": (235, 225, 200), "Cream": (245, 240, 220), "Sage": (150, 165, 130),
    "Terracotta": (200, 110, 80),
}
_VOCAB = list(KF_BRAND.items()) + list(GENERAL.items())


def nearest_name(r, g, b):
    """Nearest named colour by squared RGB distance; KF brand names win ties (listed first)."""
    best, bestd = None, None
    for name, (cr, cg, cb) in _VOCAB:
        d = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
        if bestd is None or d < bestd:
            best, bestd = name, d
    return best


def extract_palette(path, k=5, resize=160):
    """Return dominant colours as [{hex, percentage, named}], sorted by coverage desc."""
    im = Image.open(path).convert("RGB")
    im.thumbnail((resize, resize))
    q = im.quantize(colors=max(1, k), method=Image.MEDIANCUT)
    pal = q.getpalette()
    counts = q.getcolors() or []
    total = sum(c for c, _ in counts) or 1
    out = []
    for count, idx in sorted(counts, key=lambda x: x[0], reverse=True):
        r, g, b = pal[idx * 3:idx * 3 + 3]
        out.append({
            "hex": "#%02X%02X%02X" % (r, g, b),
            "percentage": round(100.0 * count / total, 1),
            "named": nearest_name(r, g, b),
        })
    return out


def dominant_names(palette, min_pct=8.0):
    """The distinct named colours that cover at least `min_pct`, in coverage order."""
    seen, names = set(), []
    for c in palette:
        if c["percentage"] >= min_pct and c["named"] not in seen:
            seen.add(c["named"])
            names.append(c["named"])
    return names
