"""Ingest engine: recursive scan -> hashed identity -> type/set detection ->
color extraction -> DB upsert -> bundle + relationship building.

Route-agnostic: walks any folder layout. Asset identity is the content hash, so
reorganising or renaming files never changes an asset's ID or loses its metadata.
"""

import hashlib
import io
import re
from pathlib import Path

from PIL import Image, ImageFile

# Real print-ready files are large and sometimes imperfect exports. Lift PIL's
# decompression-bomb ceiling (these are trusted local files) and tolerate JPEGs
# that are slightly truncated rather than aborting on them.
Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

from . import config

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff", ".bmp"}
# Files that can be the visible catalog "face" (get a thumbnail/colours).
FACE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
# Editable masters that link to a design but never become products themselves.
MASTER_EXTS = {".tif", ".tiff", ".psd", ".eps", ".ai", ".pdf"}
ALL_EXTS = FACE_EXTS | MASTER_EXTS
# When several files share a name, this order decides which is the face.
FACE_PREFERENCE = [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp", ".gif"]

# --- named colours for palette labelling (KF tokens first so house colours snap) ---
NAMED = {
    "KF Navy": (0x1B, 0x2A, 0x4A), "KF Gold": (0xB8, 0x94, 0x3F),
    "KF Ivory": (0xF5, 0xED, 0xD6), "KF Charcoal": (42, 42, 42),
    "black": (16, 16, 16), "white": (250, 250, 250), "grey": (128, 128, 128),
    "red": (192, 48, 48), "terracotta": (196, 106, 75), "amber": (224, 150, 40),
    "mustard": (212, 160, 32), "yellow": (240, 208, 64), "olive": (128, 128, 48),
    "sage": (140, 175, 130), "green": (58, 138, 74), "teal": (42, 138, 138),
    "sky-blue": (106, 168, 216), "blue": (42, 74, 192), "indigo": (48, 48, 128),
    "purple": (128, 64, 160), "pink": (224, 128, 168), "blush": (232, 192, 192),
    "brown": (106, 74, 42), "beige": (216, 200, 168), "cream": (240, 232, 208),
}


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def near_color(hex_color: str) -> str:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    best, bd = "grey", 1e9
    for name, (nr, ng, nb) in NAMED.items():
        d = 2 * (r - nr) ** 2 + 4 * (g - ng) ** 2 + 3 * (b - nb) ** 2
        if d < bd:
            bd, best = d, name
    return best


def extract_palette(img: Image.Image, n=config.PALETTE_SIZE):
    small = img.convert("RGB").copy()
    small.thumbnail((128, 128))
    q = small.quantize(colors=16, method=Image.MEDIANCUT).convert("RGB")
    cols = q.getcolors(maxcolors=small.width * small.height) or []
    total = sum(c for c, _ in cols) or 1
    top = sorted(cols, key=lambda x: x[0], reverse=True)[:n]
    return [{"hex": "#%02X%02X%02X" % rgb, "name": near_color("#%02X%02X%02X" % rgb),
             "ratio": round(c / total, 3)} for c, rgb in top]


def detect_type(folder_name: str):
    """Return (asset_type, component_hint, cushion_index)."""
    n = re.sub(r"\s+", " ", folder_name.strip().lower())
    for pat, atype, hint in config.FOLDER_TYPE_RULES:
        m = re.search(pat, n)
        if m:
            cidx = None
            if hint == "cushion":
                mi = re.search(r"(\d+)", n)
                cidx = int(mi.group(1)) if mi else None
            return atype, hint, cidx
    return "Unknown", None, None


def parse_name(filename: str) -> dict:
    """Parse a filename into grouping hints.

    Two conventions are recognised:

    Flat curtains: ``{Line}-{Number}-{Side}`` e.g. ``Kids-3141-R``,
    ``Paintings 4111-L``, ``Kids-3061-C`` (C = merged single panel).

    Batched sets: ``(DD-MM) C{n}{-side}{-piece}`` e.g. ``(18-11) C4-A``,
    ``(18-11) C4-A-cushion``, ``(18-11) C6-cushion 1``, ``(19-11) C1-A``.
    The set identity is BATCH + number (``18-11/C1`` ≠ ``19-11/C1``). Piece type
    comes from the filename (``-cushion`` etc.); no piece word in a set file
    means the curtain. Side A/B = L/R and is optional.
    """
    stem = re.sub(r"\.[^.]+$", "", filename).strip()
    low = stem.lower()

    # Batch/date tag "(18-11)" -> part of the set identity.
    batch = None
    mb = re.match(r"\(\s*(\d{1,2})\s*-\s*(\d{1,2})\s*\)", stem)
    if mb:
        batch = f"{int(mb.group(1)):02d}-{int(mb.group(2)):02d}"

    # Set number: 'C' + digits (C1, C13).
    set_num = None
    msc = re.search(r"\bC0*(\d+)\b", stem)
    if msc:
        set_num = msc.group(1)
    set_code = (f"{batch}/C{set_num}" if (set_num and batch)
                else (f"C{set_num}" if set_num else None))

    # Piece type from the filename (filename wins for set files).
    piece = cushion_index = None
    mci = re.search(r"cushion\s*(\d+)", low)
    if mci:
        piece, cushion_index = "cushion", int(mci.group(1))
    elif re.search(r"\bcushion\b", low):
        piece = "cushion"
    elif re.search(r"\brunner\b", low):
        piece = "runner"
    elif re.search(r"table\s*cloth|tablecloth", low):
        piece = "tablecloth"
    elif set_num:                       # set file, no piece word -> the curtain
        piece = "curtain"
    asset_type_hint = {
        "curtain": "Curtain Panel Set", "cushion": "Cushion",
        "runner": "Table Runner", "tablecloth": "Table Cloth",
    }.get(piece)

    # Flat curtain line + number (only when this is NOT a set file).
    line = number = None
    if not set_num:
        mc = re.match(r"\s*([A-Za-z][A-Za-z ]*?)[\s-]+(\d{2,})", stem)
        if mc:
            line = mc.group(1).strip().title()
            number = mc.group(2)

    # Side marker: A/B/L/R as a standalone token (handles '-A', '-A-cushion').
    side = side_raw = None
    msd = re.search(r"[-\s]([ABLR])\b(?!\w)", stem)
    if msd:
        side_raw = msd.group(1).upper()
        if side_raw in config.SIDE_ALIASES:
            side = config.SIDE_ALIASES[side_raw]

    # Merged single panel: a flat curtain ending in '-C'.
    is_merged = False
    if not set_num and re.search(r"-\s*C\s*$", stem):
        is_merged = True
        side = None

    if re.search(r"\bA\s*,\s*B\b", stem):
        side = "PAIR"

    alt = bool(re.search(r"option\s*\d|alt\s*\d|\b[AB]2\b", stem, re.I))
    return {"batch": batch, "set_num": set_num, "set_code": set_code,
            "piece": piece, "cushion_index": cushion_index,
            "asset_type_hint": asset_type_hint,
            "line": line, "number": number, "side": side, "side_raw": side_raw,
            "is_merged": is_merged, "alt": alt}


def _ignored(path: Path, root: Path) -> bool:
    """True if a file sits under a junk/process folder or is an OS sidecar file."""
    if path.name.lower() in config.IGNORE_FILENAMES or path.name.startswith("."):
        return True
    for part in path.relative_to(root).parts[:-1]:   # folder names only
        pl = part.lower()
        for pat in config.IGNORE_DIR_PATTERNS:
            if re.search(pat, pl):
                return True
    return False


def iter_files(root: Path):
    for p in sorted(root.rglob("*")):
        if not (p.is_file() and p.suffix.lower() in ALL_EXTS):
            continue
        if "__MACOSX" in p.parts:
            continue
        if _ignored(p, root):
            continue
        yield p


def group_by_stem(files):
    """Group files in the same folder that share a name stem (e.g. a JPG and its
    layered TIF master). Returns list of (face, [source_files]). The face is the
    best renderable file by FACE_PREFERENCE; everything else in the group is a
    linked source. A group with no renderable face yields (None, members)."""
    groups = {}
    for f in files:
        key = (str(f.parent), f.stem.lower())
        groups.setdefault(key, []).append(f)

    def face_rank(p):
        ext = p.suffix.lower()
        return FACE_PREFERENCE.index(ext) if ext in FACE_PREFERENCE else 99

    out = []
    for key, members in groups.items():
        faces = sorted([m for m in members if m.suffix.lower() in FACE_EXTS],
                       key=face_rank)
        face = faces[0] if faces else None
        sources = [m for m in members if m is not face]
        out.append((face, sources))
    return out


def iter_images(root: Path):
    for p in sorted(root.rglob("*")):
        if not (p.is_file() and p.suffix.lower() in IMAGE_EXTS):
            continue
        if "__MACOSX" in p.parts:
            continue
        if _ignored(p, root):
            continue
        yield p


def thumbnail_bytes(path: Path, max_side=480, fmt="JPEG"):
    im = Image.open(path).convert("RGB")
    im.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    im.save(buf, format=fmt, quality=82)
    return buf.getvalue()


def scan(db, root: Path, progress=None):
    """Full ingest pass. Returns a summary dict."""
    root = Path(root)
    groups = group_by_stem(iter_files(root))
    design_map = {}       # design-group key -> design uid (shared by pairs/sets)
    family_parts = {}     # (line, number) -> {"pair": uid, "merged": uid}
    by_set = {}           # set_code -> [uid,...]   (bundle membership)
    alt_groups = {}       # (set_code, role) -> [uid,...]

    errors = []           # files that could not be read at all
    review = []           # files read OK but with ambiguous identity
    linked_masters = 0    # count of TIF/PSD masters attached to a face

    for i, (f, sources) in enumerate(groups):
        if progress:
            progress(i + 1, len(groups), f.name if f else "")
        if f is None:
            # a master (e.g. PSD) with no JPG/PNG to represent it
            for m in sources:
                review.append({"file": m.name, "reason": "master file with no JPG/PNG face"})
            continue
        try:
            source_files = [{"filename": s.name, "path": str(s.resolve()),
                             "ext": s.suffix.lower().lstrip(".")} for s in sources]
            linked_masters += sum(1 for s in sources if s.suffix.lower() in MASTER_EXTS)
            with Image.open(f) as im:
                im.load()
                w, h = im.size
                palette = extract_palette(im)
            dominant = palette[0]["name"] if palette else "grey"
            atype_folder, hint, cidx_folder = detect_type(f.parent.name)
            info = parse_name(f.name)
            set_code = info["set_code"]
            side = info["side"]
            is_merged = info["is_merged"]
            line, number = info["line"], info["number"]
            piece = info["piece"]
            cidx = info["cushion_index"]
            # filename-derived piece type wins for set files; else folder decides
            atype = info["asset_type_hint"] or atype_folder

            # role
            role = hint
            if atype == "Cushion":
                if cidx:
                    role = f"cushion-{cidx}"
                elif side in ("L", "R"):
                    role = f"cushion-{side}"
                else:
                    role = "cushion"
            elif atype == "Curtain Panel Set":
                if is_merged:
                    role = "single-merged"
                elif side in ("L", "R"):
                    role = f"panel-{side}"
                else:
                    role = "panel"
            elif atype == "Table Runner":
                role = piece or hint or "runner"
            elif atype == "Table Cloth":
                role = "tablecloth"

            # review flags (don't guess)
            if atype == "Curtain Panel Set" and not set_code:
                if not (line and number):
                    review.append({"file": f.name, "reason": "no line/number parsed"})
                elif info["side_raw"] and side not in ("L", "R") and not is_merged:
                    review.append({"file": f.name,
                                   "reason": f"unknown side suffix -{info['side_raw']}"})

            sha = file_hash(f)

            # Decide which design this file belongs to.
            #  * set piece: group by (set, piece, cushion#); A/B are the pair.
            #  * flat curtain: group by (line, number); A/B are the pair; -C separate.
            if set_code:
                # A/B pair into one design ONLY for curtains; for cushions and
                # other pieces, A and B are distinct designs (own products).
                if atype == "Curtain Panel Set":
                    key = ("SET", set_code, piece, cidx)
                else:
                    key = ("SET", set_code, piece, cidx, side)
            elif atype == "Curtain Panel Set" and line and number:
                key = ("CURC", line, number) if is_merged else ("CUR", line, number)
            else:
                key = None
            grouping = design_map.get(key) if key else None

            uid = db.upsert_asset(
                sha=sha, path=str(f.resolve()), filename=f.name,
                width=w, height=h, set_code=set_code, role=role,
                side=(None if is_merged else side),
                asset_type_ai=atype, palette=palette, dominant=dominant,
                design_grouping_uid=grouping, source_files=source_files)

            if key:
                design_map.setdefault(key, uid)
            # track flat-curtain family for pair<->merged linking
            if not set_code and line and number:
                slot = "merged" if is_merged else "pair"
                family_parts.setdefault((line, number), {})[slot] = uid

            # SKU assignment
            type_code = config.TYPE_SKU_CODE.get(atype, "UNK")
            if set_code:
                # all pieces of a set share the set's number; suffix tells them apart
                set_number = db.set_number_for(set_code)
                if atype == "Curtain Panel Set":
                    suffix = ""                       # the curtain pair, no suffix
                elif cidx:
                    suffix = str(cidx)                # numbered: -1, -2
                elif info["side_raw"] in ("A", "B"):
                    suffix = info["side_raw"]          # sided cushions: -A, -B
                elif side in ("L", "R"):
                    suffix = side
                else:
                    suffix = ""
                db.assign_set_sku(uid, type_code, set_number, suffix)
            else:
                # flat curtains keep their own global product number (unchanged)
                db.assign_product_sku(uid, type_code)
        except Exception as e:
            errors.append({"file": str(f), "error": f"{type(e).__name__}: {e}"})
            continue

        if set_code:
            by_set.setdefault(set_code, [])
            if uid not in by_set[set_code]:
                by_set[set_code].append(uid)
        if info["alt"] and set_code:
            alt_groups.setdefault((set_code, role), []).append(uid)

    # link a merged single panel to its pair (same design family)
    for parts in family_parts.values():
        if "pair" in parts and "merged" in parts:
            db.add_relationship(parts["pair"], parts["merged"], "same-family")

    # Ramadan-style bundles + alt versions
    for set_code, uids in by_set.items():
        db.upsert_set(set_code)
        for a in uids:
            for b in uids:
                db.add_relationship(a, b, "same-set")
    for uids in alt_groups.values():
        for a in uids:
            for b in uids:
                db.add_relationship(a, b, "alt-version")


    flat_pairs = sum(1 for k in design_map if k[0] == "CUR")
    flat_merged = sum(1 for k in design_map if k[0] == "CURC")
    set_designs = sum(1 for k in design_map if k[0] == "SET")
    return {
        "files": len(groups),
        "assets": len(db.all_assets()),
        "sets": len(by_set),
        "curtain_pairs": flat_pairs,
        "merged_singles": flat_merged,
        "set_designs": set_designs,
        "linked_masters": linked_masters,
        "skipped": errors,
        "review": review,
    }
