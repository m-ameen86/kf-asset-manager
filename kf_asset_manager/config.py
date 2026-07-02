"""KF Asset Manager — configuration: taxonomies, type rules, brand tokens.

Everything here is a *default*. Controlled vocabularies are copied into the DB on
first run so they can be edited in the UI without touching code.
"""

APP_NAME = "KF Asset Manager"
TAGLINE = "Where Ideas Become Fabric"

# --- KF brand tokens (UI) ---
BRAND = {
    "navy": "#1B2A4A",
    "gold": "#B8943F",
    "ivory": "#F5EDD6",
    "charcoal": "#2A2A2A",
    "paper": "#FBF8F0",
}

# --- Controlled vocabularies (each field is independent; the UI can extend) ---
VOCAB = {
    "asset_type": [
        "Pattern", "Curtain Panel Set", "Cushion", "Table Runner", "Table Cloth",
        "Tapestry Artwork", "Apparel Artwork", "Flag", "Painting", "Unknown",
    ],
    "style": [
        "geometric", "floral", "paisley", "stripe", "calligraphy", "abstract",
        "damask", "arabesque", "medallion", "zellige-tile", "ikat", "novelty",
        "texture-solid", "border-trim",
    ],
    "theme": [
        "traditional", "modern", "oriental", "folk", "royal", "kids",
        "bohemian", "romantic", "minimalist", "festive",
    ],
    "primary_motif": [
        "ramadan-kareem-calligraphy", "lantern", "crescent-moon", "arabesque",
        "star-tessellation", "rosette", "mandala", "octagon-tile", "botanical",
        "stripe-band", "none",
    ],
    "occasion": [
        "ramadan", "eid", "wedding", "everyday", "summer", "winter",
        "baby-kids", "national-day",
    ],
    "region": ["egypt", "gulf", "uk", "us", "global"],
    "status": ["draft", "approved", "archived"],
}

# Fields that have an ai_/manual_ pair (effective = manual ?? ai).
OVERRIDABLE = [
    "asset_type", "style", "theme", "primary_motif", "occasion", "region",
    "selling_name", "title", "description",
]

# --- Asset-type detection rules (folder name -> type, component, side hints) ---
# Matched case-insensitively against the *containing folder* name first.
FOLDER_TYPE_RULES = [
    (r"curtain",                "Curtain Panel Set", None),
    (r"cushion\s*(\d+)",        "Cushion",           "cushion"),
    (r"cushion",                "Cushion",           "cushion"),
    (r"coffee.*runner|runner\s*1", "Table Runner",   "coffee"),
    (r"dining.*runner|runner\s*2", "Table Runner",   "dining"),
    (r"runner",                 "Table Runner",      "runner"),
    (r"table\s*cloth|tablecloth", "Table Cloth",     None),
    (r"tapestr",                "Tapestry Artwork",  None),
    (r"apparel|women|dress|wear", "Apparel Artwork", None),
    (r"flag",                   "Flag",              None),
    (r"painting",               "Painting",          None),
    (r"pattern",                "Pattern",           None),
]

# Title template. {selling_name} {headline} {type_label} {color}. headline =
# effective primary_motif (humanised) if present, else effective style.
TITLE_TEMPLATE = "{selling_name} — {headline} {type_label} — {color}"

# Category codes used in product SKUs (KF-{CODE}-NNNNNN).
TYPE_SKU_CODE = {
    "Curtain Panel Set": "CUR",
    "Cushion": "CSH",
    "Table Runner": "RUN",
    "Table Cloth": "TBL",
    "Tapestry Artwork": "TAP",
    "Apparel Artwork": "WMN",
    "Flag": "FLG",
    "Painting": "PNT",
    "Pattern": "PAT",
    "Unknown": "UNK",
}

# --- Product-type vocabulary (canonical names used by the identity layer) -------
# Detected asset types map to a clean canonical product type.
PRODUCT_TYPE_CANON = {
    "Curtain Panel Set": "Curtain",
    "Cushion": "Cushion",
    "Table Runner": "Runner",
    "Table Cloth": "Tablecloth",
    "Tapestry Artwork": "Tapestry",
    "Tapestry": "Tapestry",
    "Apparel Artwork": "Apparel",
    "Pattern": "Fabric",
    "Fabric": "Fabric",
    "Flag": "Flag",
    "Painting": "Painting",
}

def canon_product_type(asset_type):
    return PRODUCT_TYPE_CANON.get(asset_type, asset_type or "Unknown")

# --- Phase 4: canonical product_type -> SKU type code -------------------------
# NOTE: TYPE_SKU_CODE above is keyed by *asset_type*; products store the canonical
# *product_type*, so SKU generation uses this map. Fabric -> FAB (self-describing).
PRODUCT_TYPE_SKU_CODE = {
    "Curtain": "CUR",
    "Cushion": "CSH",
    "Runner": "RUN",
    "Tablecloth": "TBL",
    "Tapestry": "TAP",
    "Apparel": "WMN",
    "Fabric": "FAB",
    "Flag": "FLG",
    "Painting": "PNT",
    "Unknown": "UNK",
}

def product_type_sku_code(product_type):
    return PRODUCT_TYPE_SKU_CODE.get(product_type, "UNK")

# --- Design type -> which products it may back (compatibility) ------------------
# Not every design can generate every product. A repeat pattern tiles onto anything;
# an engineered panel or fixed artwork is bound to its own type. The Asset Manager
# enforces this so downstream only ever generates VALID products. Versioned config.
DESIGN_TYPES_VERSION = 2
DESIGN_TYPES = {
    "repeat_pattern": {
        "primary": "Fabric",
        "compatible": ["Fabric", "Curtain", "Cushion", "Tapestry",
                       "Runner", "Tablecloth", "Tote", "Scarf"],
    },
    "engineered_panel": {"primary": "Curtain", "compatible": ["Curtain"]},
    "fixed_artwork":    {"primary": "Tapestry", "compatible": ["Tapestry"]},
    # single-placement prints: t-shirt fronts, posters, canvas — neither a repeat
    # pattern nor a fixed tapestry composition.
    "placed_artwork":   {"primary": "Poster",
                         "compatible": ["Poster", "Canvas", "Apparel", "Tote", "Cushion", "Scarf"]},
    # set_piece / unknown are resolved to the piece's own type at assignment time
    "set_piece": {"primary": None, "compatible": []},
    "unknown":   {"primary": None, "compatible": []},
}

# --- Curtain panel naming convention -------------------------------------------
# Files look like  "Kids-3141-R"  /  "Paintings 4111-L"  /  "Kids-3061-C".
#   {Line}-{Number}-{Side}   (space or dash before the number is fine)
# Side letters and what they mean (confirmed with Ameen — different designers used
# different letters for the same thing):
#   A = L = left      B = R = right      C = a single MERGED panel, sold alone.
SIDE_ALIASES = {"A": "L", "B": "R", "L": "L", "R": "R"}
MERGED_SIDE = "C"          # a standalone single panel that merges both designs
# Curtains: one design = one product, sold as a PAIR (hero), with single-Left and
# single-Right offered as variants. L and R of the same (Line, Number) are ONE
# design / ONE product. A "-C" file is its own standalone product in the same
# design family, linked back to the pair.

# --- Folders the scanner must NEVER treat as products --------------------------
# Matched (case-insensitive) against EACH folder name in a file's path. Anything
# under a matching folder is skipped. This keeps the working archive's process
# cruft out of the source of truth.
IGNORE_DIR_PATTERNS = [
    r"^_",                      # _WIP, _Templates, _anything
    r"^\.",                     # dotfolders
    r"^new folder",             # New folder, New folder (2), New folder3 ...
    r"^new\s",                  # "New designs" working dumps -> promote manually
    r"untitled folder",
    r"\bpantone\b", r"\bpms\b", r"palette", r"color charts", r"cmyk",
    r"packaging",
    r"\b3d\b", r"mockup", r"render",
    r"original", r"\bold\b", r"^old ", r"\bwip\b", r"\bundone\b",
    r"\btest\b", r"changed", r"trial", r"z options", r"other trials",
    r"drive-download", r"wetransfer", r"-\d{8}t\d{6}z",   # google/wetransfer dumps
    r"\beps\b", r"\bpsd\b", r"\btiff\b", r"\btts_test\b", r"dgi",
    r"subjet", r"\bnames\b", r"\bideas\b",
]
IGNORE_FILENAMES = {".ds_store", "thumbs.db"}

PALETTE_SIZE = 5
THUMB_MAX = 1024
DB_FILENAME = "kf_assets.db"


# --- Business metadata dimensions (metadata ONLY; never affects identity) ----
# A controlled-but-extensible vocabulary. Values are examples, not enforced — the
# importer/UI may add values. These dimensions NEVER enter IDs, SKUs, or design type.
BUSINESS_METADATA_DIMENSIONS = {
    "business_line": ["Kids", "Paintings", "Ramadan", "Luxury", "Hotels", "Outdoor"],
    "market":        ["Egypt", "GCC", "Europe", "USA"],
    "room":          ["Kids Room", "Living Room", "Bedroom", "Dining"],
    "collection":    ["Summer 2027", "Ramadan 2027", "Classic Collection"],
    "theme":         ["Floral", "Islamic", "Modern", "Vintage"],
}
