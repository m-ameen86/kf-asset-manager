"""Phase 1 — Internal Identity + Relationships.

Implements the frozen v1.0 identity layer: four entities (Family, Design, Asset,
Product) with **opaque, immutable** IDs drawn from independent counters, wired by
foreign keys. No business meaning lives in any ID. SKU generation, the rule engine,
confidence scoring and the review UI are explicitly LATER phases — this module is
identity only.

Natural keys used purely for idempotent re-scans (NOT identities, never exported):
  * Asset      -> content hash (sha256). Same bytes => same asset, forever.
  * Design     -> a grouping key derived from the current parser.
  * Family     -> the set code.
Re-scanning never mints a new ID for content already known.
"""

import argparse
import json
import sqlite3
import time
from pathlib import Path

from PIL import Image

from . import config, ingest, rules

SCHEMA_VERSION = 2          # identity layer schema (v2 = Artwork Source layer)
VISION_VERSION = 2          # Phase 3 vision/colour analysis version (v2 = 3-c.3 prompt/vocab tuning)


class IncompatibleProductError(Exception):
    """Raised when a product type is not compatible with a design's design_type."""


class IdentityDB:
    def __init__(self, db_path):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()
        self._run_migrations()

    def _init_schema(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS counters (name TEXT PRIMARY KEY, value INTEGER);

        CREATE TABLE IF NOT EXISTS families (
            family_id TEXT PRIMARY KEY,
            set_code  TEXT UNIQUE,
            created_at REAL, updated_at REAL);

        CREATE TABLE IF NOT EXISTS designs (
            design_id   TEXT PRIMARY KEY,
            family_id   TEXT REFERENCES families(family_id),
            grouping_key TEXT UNIQUE,
            design_type TEXT,
            primary_product TEXT,
            compatible_products TEXT,
            created_at REAL, updated_at REAL);

        CREATE TABLE IF NOT EXISTS assets (
            asset_id TEXT PRIMARY KEY,
            design_id TEXT REFERENCES designs(design_id),
            sha256 TEXT UNIQUE,
            filename TEXT, path TEXT, width INTEGER, height INTEGER,
            side TEXT, role TEXT, source_files TEXT, source_library TEXT,
            match_rule TEXT, confidence REAL, needs_review INTEGER DEFAULT 0,
            design_variant TEXT, legacy_ab INTEGER DEFAULT 0,
            artwork_role TEXT DEFAULT 'Original',
            artwork_relationship TEXT DEFAULT 'Original',
            derived_from_design TEXT REFERENCES designs(design_id),
            derived_from_asset TEXT REFERENCES assets(asset_id),
            source_id TEXT REFERENCES artwork_sources(source_id),
            created_at REAL, updated_at REAL);

        -- v2.0-a: Artwork Source — a specific APPLICATION of a design's artwork to a
        -- surface (Curtain Left, Cushion Right, Runner…). Sits between Design and Asset.
        -- Additive in v2.0-a: created alongside the existing structure, identity-
        -- preserving. Products are mapped to Sources in v2.0-b.
        CREATE TABLE IF NOT EXISTS artwork_sources (
            source_id TEXT PRIMARY KEY,
            design_id TEXT REFERENCES designs(design_id),
            application TEXT,                 -- Curtain / Cushion / Runner / …
            origin TEXT DEFAULT 'Original',   -- Original | Derived
            artwork_relationship TEXT DEFAULT 'Original',
            derived_from_source TEXT REFERENCES artwork_sources(source_id),
            side TEXT,                        -- L | R | C | null
            label TEXT,
            created_at REAL, updated_at REAL,
            UNIQUE(design_id, application, side, origin));

        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            design_id  TEXT REFERENCES designs(design_id),
            family_id  TEXT REFERENCES families(family_id),
            product_type TEXT,
            source_id TEXT DEFAULT '',         -- realizing Artwork Source ('' = grouped originals)
            display_title TEXT,                -- Phase 4-c: manual override; NULL = use generated default
            created_at REAL, updated_at REAL,
            UNIQUE(design_id, product_type, source_id));

        CREATE TABLE IF NOT EXISTS product_variants (
            product_id TEXT REFERENCES products(product_id),
            asset_id   TEXT REFERENCES assets(asset_id),
            variant_label TEXT,
            UNIQUE(product_id, asset_id, variant_label));

        -- Business metadata: ONE generic key/value store, deliberately NOT a set of
        -- per-dimension tables. It tags any entity (usually a Design) with business
        -- dimensions (business_line, market, room, collection, theme, …). It is
        -- metadata ONLY — it never participates in IDs, SKUs, design identity, or
        -- compatibility. It exists purely to power search, filtering, Shopify
        -- collections, AI, SEO, and merchandising.
        CREATE TABLE IF NOT EXISTS business_metadata (
            entity_type TEXT,           -- 'design' | 'product' | 'family' | 'asset'
            entity_id   TEXT,           -- the opaque internal id (loose ref, not a FK)
            dimension   TEXT,           -- e.g. 'business_line', 'market', 'theme'
            value       TEXT,
            created_at  REAL,
            UNIQUE(entity_type, entity_id, dimension, value));
        CREATE INDEX IF NOT EXISTS ix_bizmeta_dim ON business_metadata(dimension, value);
        CREATE INDEX IF NOT EXISTS ix_bizmeta_entity ON business_metadata(entity_type, entity_id);

        -- Phase 3 Vision: DERIVED suggestions + metadata, never identity. Keyed by asset,
        -- cached by sha256 + vision_version so re-runs never re-spend. Colours come from a
        -- local pass (3-a, no AI); name/tags/match come from an AI pass (3-c).
        CREATE TABLE IF NOT EXISTS vision_results (
            asset_id TEXT PRIMARY KEY REFERENCES assets(asset_id),
            sha256 TEXT,
            vision_version INTEGER,
            colours TEXT,             -- JSON: [{hex,percentage,named}] (local, 3-a)
            suggested_name TEXT,      -- AI suggestion (3-c)
            style_tags TEXT,          -- JSON list (3-c)
            is_match INTEGER,         -- 0/1, the model's actual match verdict (3-d.1 fix: was
                                      -- computed in 3-c.1 but never persisted, only confidence was)
            match_confidence REAL,    -- 3-c
            match_reason TEXT,        -- 3-c
            model TEXT,               -- provider/model used (3-c)
            analyzed_at REAL);
        """)
        self.conn.execute("INSERT OR IGNORE INTO meta(key,value) VALUES('schema_version',?)",
                          (str(SCHEMA_VERSION),))
        self.conn.execute("INSERT OR IGNORE INTO meta(key,value) VALUES('design_types_version',?)",
                          (str(config.DESIGN_TYPES_VERSION),))
        self.conn.execute("INSERT OR IGNORE INTO meta(key,value) VALUES('rules_version',?)",
                          (str(rules.RULES_VERSION),))
        for c in ("family", "design", "asset", "product", "source"):
            self.conn.execute("INSERT OR IGNORE INTO counters(name,value) VALUES(?,0)", (c,))
        self.conn.commit()

    # --- schema migrations ----------------------------------------------------
    # Every table is created above with `CREATE TABLE IF NOT EXISTS`, which is a no-op
    # against a table that already exists — it does NOT add new columns. That was
    # invisible for the whole project because the database used to be rebuilt from
    # scratch on every run. Now that build_graph PRESERVES the database by default (the
    # correct behaviour, since vision_results/colours/display_title overrides are
    # non-derivable), any additive column change made in code after a database was first
    # created would otherwise crash that database with "no such column" on open.
    #
    # This registry lists every column that was added to an ALREADY-EXISTING table after
    # that table's initial creation, across the project's history. Each entry is applied
    # idempotently: check whether the column exists, add it if not (SQLite ALTER TABLE
    # ADD COLUMN, which correctly backfills existing rows when a DEFAULT is given, and
    # leaves them NULL otherwise — which is already the correct "not set" sentinel used
    # throughout this codebase, so no further data massaging is needed). Applying a
    # migration a second time against a database that already has the column is a no-op.
    #
    # Format: (unique_name, table, column, column_def_sql, human note)
    MIGRATIONS = [
        ("2026_assets_source_id", "assets", "source_id",
         "TEXT REFERENCES artwork_sources(source_id)",
         "v2.0-a: link assets to their realizing Artwork Source"),
        ("2026_products_source_id", "products", "source_id", "TEXT DEFAULT ''",
         "v2.0-b: products realized from Artwork Sources ('' = grouped originals)"),
        ("2026_products_display_title", "products", "display_title", "TEXT",
         "Phase 4-c: manual title override (NULL = use the generated default)"),
        ("2026_vision_results_is_match", "vision_results", "is_match", "INTEGER",
         "Phase 3-d.1 fix: persist the AI match verdict (was computed but not stored)"),
    ]

    def _run_migrations(self):
        """Apply every pending migration exactly once, tracked in `schema_migrations`.
        Safe to call on every open — brand-new databases already have every column (via
        `_init_schema`'s CREATE TABLE) and simply get each migration recorded as applied
        without attempting a redundant ALTER. Never touches data beyond adding a column."""
        self.conn.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
            name TEXT PRIMARY KEY, applied_at REAL, detail TEXT)""")
        table_names = {r[0] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        for name, table, column, coldef, note in self.MIGRATIONS:
            if table not in table_names:
                continue    # defensive: every table above already exists by this point
            already = self.conn.execute(
                "SELECT 1 FROM schema_migrations WHERE name=?", (name,)).fetchone()
            cols = {r[1] for r in self.conn.execute(f"PRAGMA table_info({table})")}
            if column not in cols:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coldef}")
            if not already:
                self.conn.execute(
                    "INSERT OR IGNORE INTO schema_migrations(name,applied_at,detail) VALUES(?,?,?)",
                    (name, time.time(), note))
        self.conn.commit()

    def applied_migrations(self):
        """Read-only: names of migrations recorded as applied against this database."""
        return [r[0] for r in self.conn.execute(
            "SELECT name FROM schema_migrations ORDER BY name")]

    # --- opaque ID minting (independent counters) ---------------------------
    def _mint(self, name, prefix):
        self.conn.execute("UPDATE counters SET value=value+1 WHERE name=?", (name,))
        n = self.conn.execute("SELECT value FROM counters WHERE name=?", (name,)).fetchone()[0]
        self.conn.commit()
        return f"{prefix}-{n:06d}"

    def ensure_family(self, set_code):
        if not set_code:
            return None
        r = self.conn.execute("SELECT family_id FROM families WHERE set_code=?", (set_code,)).fetchone()
        if r:
            return r["family_id"]
        fid = self._mint("family", "KF-FAM")
        now = time.time()
        self.conn.execute("INSERT INTO families(family_id,set_code,created_at,updated_at) VALUES(?,?,?,?)",
                          (fid, set_code, now, now))
        self.conn.commit()
        return fid

    def assign_family(self, design_id, family_id):
        """Attach an existing design (and its products) to a family. Used by the
        engineered-panel post-pass, where a family exists only once >=2 sibling
        designs share a code. Identity-preserving: no IDs change."""
        self.conn.execute("UPDATE designs SET family_id=? WHERE design_id=?", (family_id, design_id))
        self.conn.execute("UPDATE products SET family_id=? WHERE design_id=?", (family_id, design_id))
        self.conn.commit()

    def ensure_design(self, grouping_key, family_id, design_type, primary_product, compatible_products):
        r = self.conn.execute("SELECT design_id FROM designs WHERE grouping_key=?", (grouping_key,)).fetchone()
        if r:
            return r["design_id"]
        did = self._mint("design", "KF-D")
        now = time.time()
        self.conn.execute("""INSERT INTO designs(design_id,family_id,grouping_key,design_type,
                             primary_product,compatible_products,created_at,updated_at)
                             VALUES(?,?,?,?,?,?,?,?)""",
                          (did, family_id, grouping_key, design_type, primary_product,
                           json.dumps(compatible_products), now, now))
        self.conn.commit()
        return did

    def compatible_products(self, design_id):
        r = self.conn.execute("SELECT compatible_products FROM designs WHERE design_id=?", (design_id,)).fetchone()
        return json.loads(r["compatible_products"] or "[]") if r else []

    def can_make_product(self, design_id, product_type):
        return product_type in self.compatible_products(design_id)

    def ensure_asset(self, sha, design_id, *, filename, path, width, height, side, role,
                     source_files, source_library=None, match_rule=None, confidence=None,
                     needs_review=False, design_variant=None, legacy_ab=False,
                     artwork_role="Original", artwork_relationship="Original",
                     derived_from_design=None, derived_from_asset=None, source_id=None):
        """Create/refresh an asset. `artwork_role` is Original or Derived; a Derived
        asset (a cushion cropped/adapted from a curtain, etc.) stays in its PARENT
        design and records what it was derived from. Derivation never mints a new
        Design — only independently created artwork does."""
        r = self.conn.execute("SELECT asset_id FROM assets WHERE sha256=?", (sha,)).fetchone()
        now = time.time()
        nr = 1 if needs_review else 0
        lab = 1 if legacy_ab else 0
        if r:
            # re-scan: refresh mutable file facts, never the identity or design link
            self.conn.execute("""UPDATE assets SET filename=?,path=?,width=?,height=?,side=?,role=?,
                                 source_files=?,source_library=COALESCE(?,source_library),
                                 match_rule=?,confidence=?,needs_review=?,design_variant=?,legacy_ab=?,
                                 artwork_role=?,artwork_relationship=?,derived_from_design=?,derived_from_asset=?,
                                 source_id=COALESCE(?,source_id),
                                 updated_at=? WHERE sha256=?""",
                              (filename, path, width, height, side, role, source_files,
                               source_library, match_rule, confidence, nr, design_variant, lab,
                               artwork_role, artwork_relationship, derived_from_design, derived_from_asset,
                               source_id, now, sha))
            self.conn.commit()
            return r["asset_id"]
        aid = self._mint("asset", "KF-AST")
        self.conn.execute("""INSERT INTO assets(asset_id,design_id,sha256,filename,path,width,height,
                             side,role,source_files,source_library,match_rule,confidence,needs_review,
                             design_variant,legacy_ab,artwork_role,artwork_relationship,
                             derived_from_design,derived_from_asset,source_id,created_at,updated_at)
                             VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                          (aid, design_id, sha, filename, path, width, height, side, role,
                           source_files, source_library, match_rule, confidence, nr,
                           design_variant, lab, artwork_role, artwork_relationship,
                           derived_from_design, derived_from_asset, source_id, now, now))
        self.conn.commit()
        return aid

    def ensure_product(self, design_id, family_id, product_type, *,
                       source_id="", derived=False):
        """v2.0-b: a Product is realized from an Artwork Source. A design backs MANY
        products (curtain, cushion, tote…) — 1:N.

        Authorization is now Source-based:
          * ORIGINAL product: created without a specific source (`source_id=''`), so all
            original applications of a type GROUP into one product (a curtain's Left/Right
            panels are variants of one Curtain product). Still gated by the design-type
            compatibility rules.
          * DERIVED product: authorized by its derived Artwork Source, which already
            passed the source-creation gate. No compatibility *bypass* is needed — the
            Source justifies it. Distinct derived sources -> distinct products, so no
            artificial *discriminator* is needed either.

        Uniqueness is (design, product_type, source_id): '' for grouped originals, the
        KF-SRC id for each derived application."""
        if not derived and not self.can_make_product(design_id, product_type):
            raise IncompatibleProductError(
                f"{product_type!r} not compatible with design {design_id} "
                f"(allowed: {self.compatible_products(design_id)})")
        key_src = source_id if derived else ""
        r = self.conn.execute(
            "SELECT product_id FROM products WHERE design_id=? AND product_type=? AND source_id=?",
            (design_id, product_type, key_src)).fetchone()
        if r:
            return r["product_id"]
        pid = self._mint("product", "KF-PRD")
        now = time.time()
        self.conn.execute("""INSERT INTO products(product_id,design_id,family_id,product_type,
                             source_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?)""",
                          (pid, design_id, family_id, product_type, key_src, now, now))
        self.conn.commit()
        return pid

    def link_variant(self, product_id, asset_id, label):
        self.conn.execute("INSERT OR IGNORE INTO product_variants(product_id,asset_id,variant_label) VALUES(?,?,?)",
                          (product_id, asset_id, label))
        self.conn.commit()

    def ensure_source(self, design_id, application, *, origin="Original",
                      artwork_relationship="Original", side=None, label=None,
                      derived_from_source=None):
        """v2.0-a: get-or-create an Artwork Source (an application of a design's
        artwork). Idempotent on (design, application, side, origin). Opaque KF-SRC id.
        Additive — does not alter Design/Asset/Product identity."""
        r = self.conn.execute(
            "SELECT source_id FROM artwork_sources WHERE design_id=? AND application=? "
            "AND COALESCE(side,'')=COALESCE(?,'') AND origin=?",
            (design_id, application, side, origin)).fetchone()
        if r:
            return r["source_id"]
        sid = self._mint("source", "KF-SRC")
        now = time.time()
        self.conn.execute("""INSERT INTO artwork_sources(source_id,design_id,application,origin,
                             artwork_relationship,derived_from_source,side,label,created_at,updated_at)
                             VALUES(?,?,?,?,?,?,?,?,?,?)""",
                          (sid, design_id, application, origin, artwork_relationship,
                           derived_from_source, side, label, now, now))
        self.conn.commit()
        return sid

    # --- read helpers -------------------------------------------------------
    def counts(self):
        q = lambda t: self.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        return {t: q(t) for t in ("families", "designs", "artwork_sources",
                                  "assets", "products", "product_variants")}

    # --- business metadata (metadata ONLY; never touches identity/SKU/compat) ---
    def set_metadata(self, entity_type, entity_id, dimension, value):
        """Tag an entity with a business dimension/value. Purely additive metadata
        for search, filtering, Shopify collections, AI, SEO, merchandising. Has no
        effect on IDs, SKUs, design identity, or compatibility."""
        self.conn.execute("""INSERT OR IGNORE INTO business_metadata
                             (entity_type,entity_id,dimension,value,created_at)
                             VALUES(?,?,?,?,?)""",
                          (entity_type, entity_id, dimension, value, time.time()))
        self.conn.commit()

    def get_metadata(self, entity_type, entity_id):
        rows = self.conn.execute(
            "SELECT dimension,value FROM business_metadata WHERE entity_type=? AND entity_id=?",
            (entity_type, entity_id)).fetchall()
        out = {}
        for d, v in rows:
            out.setdefault(d, []).append(v)
        return out

    def record_vision_colours(self, asset_id, sha256, colours, version=None):
        """Phase 3-a: upsert local colour results (JSON). Derived metadata, never identity."""
        import json as _json
        v = VISION_VERSION if version is None else version
        now = time.time()
        self.conn.execute("""INSERT INTO vision_results(asset_id,sha256,vision_version,colours,analyzed_at)
                             VALUES(?,?,?,?,?)
                             ON CONFLICT(asset_id) DO UPDATE SET
                               sha256=excluded.sha256, vision_version=excluded.vision_version,
                               colours=excluded.colours, analyzed_at=excluded.analyzed_at""",
                          (asset_id, sha256, v, _json.dumps(colours), now))
        self.conn.commit()

    def record_vision_ai(self, asset_id, sha256, *, suggested_name, style_tags,
                         match_confidence, match_reason, model, is_match=None, version=None):
        """Phase 3-c: upsert AI suggestion fields. Preserves any existing colours. Derived
        metadata, never identity. A manual value elsewhere always wins downstream.
        `is_match` added in 3-d.1 (was computed by 3-c.1 but never persisted before)."""
        import json as _json
        v = VISION_VERSION if version is None else version
        now = time.time()
        self.conn.execute("""INSERT INTO vision_results(asset_id,sha256,vision_version,
                               suggested_name,style_tags,is_match,match_confidence,match_reason,model,analyzed_at)
                             VALUES(?,?,?,?,?,?,?,?,?,?)
                             ON CONFLICT(asset_id) DO UPDATE SET
                               sha256=excluded.sha256, vision_version=excluded.vision_version,
                               suggested_name=excluded.suggested_name, style_tags=excluded.style_tags,
                               is_match=excluded.is_match,
                               match_confidence=excluded.match_confidence, match_reason=excluded.match_reason,
                               model=excluded.model, analyzed_at=excluded.analyzed_at""",
                          (asset_id, sha256, v, suggested_name, _json.dumps(style_tags),
                           (None if is_match is None else (1 if is_match else 0)),
                           match_confidence, match_reason, model, now))
        self.conn.commit()

    def get_vision(self, asset_id):
        """Return the vision row for an asset as a dict (colours/style_tags parsed), or None."""
        import json as _json
        r = self.conn.execute("SELECT * FROM vision_results WHERE asset_id=?", (asset_id,)).fetchone()
        if not r:
            return None
        d = dict(r)
        for f in ("colours", "style_tags"):
            if d.get(f):
                try:
                    d[f] = _json.loads(d[f])
                except Exception:
                    pass
        if "is_match" in d and d["is_match"] is not None:
            d["is_match"] = bool(d["is_match"])
        return d

    def has_vision_colours(self, asset_id, sha256, version=None):
        """True if a cached colour result already exists for this content + version."""
        v = VISION_VERSION if version is None else version
        r = self.conn.execute(
            "SELECT 1 FROM vision_results WHERE asset_id=? AND sha256=? AND vision_version=? "
            "AND colours IS NOT NULL", (asset_id, sha256, v)).fetchone()
        return r is not None

    def versions(self):
        """Versioned contract recorded in the DB: schema (identity layer), rule engine,
        and design-type taxonomy. schema_version=2 introduced the Artwork Source layer."""
        rows = dict(self.conn.execute("SELECT key,value FROM meta").fetchall())
        return {
            "schema_version": int(rows.get("schema_version", SCHEMA_VERSION)),
            "rules_version": int(rows.get("rules_version", rules.RULES_VERSION)),
            "design_types_version": int(rows.get("design_types_version", config.DESIGN_TYPES_VERSION)),
        }

    def resolve(self, query):
        """Phase 4-b: padding-insensitive lookup. Accepts a short number ('19'), a Display
        ID ('D19'), a zero-padded number ('000019'), an internal design ID
        ('KF-D-000019'), or a full business SKU ('KF-CUR-000019-L'). Returns a dict:
        {query, design_id, design_number, exists, product_type, product_id, variant}
        with whatever the query and the data support, or design_id None if no such design."""
        from . import sku as _sku
        parts = _sku.parse_query(query)
        n = parts["design_number"]
        out = {"query": str(query), "design_id": None, "design_number": n,
               "exists": False, "product_type": parts["product_type"],
               "product_id": None, "variant": parts["variant"]}
        if n is None:
            return out
        did = f"KF-D-{n:0{_sku.DESIGN_WIDTH}d}"
        row = self.conn.execute("SELECT design_id FROM designs WHERE design_id=?", (did,)).fetchone()
        if not row:
            return out
        out["design_id"], out["exists"] = did, True
        if parts["product_type"]:
            pr = self.conn.execute(
                "SELECT product_id FROM products WHERE design_id=? AND product_type=? LIMIT 1",
                (did, parts["product_type"])).fetchone()
            if pr:
                out["product_id"] = pr["product_id"]
        return out

    # --- Phase 4-c: display titles (generated default + permanent manual override) ---
    def generated_title(self, product_id):
        """Deterministic default title, e.g. 'Design 19 Curtain', or 'Design 19 Cushion
        (Left)' for a per-source (derived, sided) product. No AI, no storage."""
        from . import sku as _sku
        r = self.conn.execute("SELECT design_id,product_type,source_id FROM products WHERE product_id=?",
                              (product_id,)).fetchone()
        if not r:
            return None
        base = f"Design {_sku.design_number(r['design_id'])} {r['product_type']}"
        if r["source_id"]:
            s = self.conn.execute("SELECT side FROM artwork_sources WHERE source_id=?",
                                  (r["source_id"],)).fetchone()
            desc = _sku.variant_descriptor(side=(s["side"] if s else None))
            if desc:
                base = f"{base} ({desc})"
        return base

    def title_for(self, product_id):
        """The product's effective title: the manual override if set, else the default.
        A manual title NEVER affects identity or SKU."""
        r = self.conn.execute("SELECT display_title FROM products WHERE product_id=?",
                              (product_id,)).fetchone()
        if r and r["display_title"]:
            return r["display_title"]
        return self.generated_title(product_id)

    def set_title(self, product_id, title):
        """Set (or clear, with None/'') the manual title. Clearing falls back to default."""
        self.conn.execute("UPDATE products SET display_title=?, updated_at=? WHERE product_id=?",
                          ((title or None), time.time(), product_id))
        self.conn.commit()
        return self.title_for(product_id)

    def variant_title(self, product_id, variant_label):
        """Display title for a specific variant, e.g. 'Design 19 Curtain — Left'. The pair
        (or a sole 'Fabric'/base variant) shows the product title with no suffix."""
        base = self.title_for(product_id)
        if not variant_label or variant_label in ("Pair", "Fabric"):
            return base
        return f"{base} — {variant_label}"

    def find_by_metadata(self, dimension, value, entity_type="design"):
        return [r[0] for r in self.conn.execute(
            "SELECT entity_id FROM business_metadata WHERE dimension=? AND value=? AND entity_type=?",
            (dimension, value, entity_type)).fetchall()]


# --- classification via the versioned Rule Engine (Phase 2) -------------------

def _classify(f: Path):
    res = rules.parse(f.name, f.parent.name)
    atype = res["asset_type"]
    side = res["side"]
    is_merged = res["is_merged"]
    piece, cidx, side_raw = res["piece"], res["cushion_index"], res["side_raw"]

    # role + provisional variant label (commerce-variant labels finalised in Phase 4)
    disc = ""
    if atype == "Cushion":
        if cidx:
            role, label, disc = f"cushion-{cidx}", f"Cushion {cidx}", str(cidx)
        elif side_raw in ("A", "B", "L", "R"):
            side_word = {"A": "Left", "B": "Right", "L": "Left", "R": "Right"}[side_raw]
            role, label, disc = f"cushion-{side_raw}", f"Cushion ({side_word})", side_raw
        else:
            role, label = "cushion", "Cushion"
    elif atype == "Curtain Panel Set":
        if is_merged:
            role, label = "single-merged", "Merged Single"
        elif side == "L":
            role, label = "panel-L", "Left"
        elif side == "R":
            role, label = "panel-R", "Right"
        else:
            role, label = "panel", "Single"
    elif atype == "Pattern":
        # repeat-pattern fabric: colourways are variants of one pattern design
        cw = res.get("colorway")
        if cw:
            role, label = f"fabric-c{cw}", f"Colour {cw}"
        else:
            role, label = "fabric", "Fabric"
    else:
        role, label = (piece or atype or "item"), (piece or atype or "Item").title()
    if res["design_variant"]:
        label = f"{label} ({res['design_variant']})"

    return dict(atype=atype, set_code=res["set_code"], gkey=res["design_key"],
                side=side, role=role, label=label, discriminator=disc,
                design_type=res["design_type"], design_variant=res["design_variant"],
                match_rule=res["rule"], confidence=res["confidence"],
                needs_review=res["needs_review"], review_reason=res["review_reason"],
                legacy_ab=res["legacy_ab"],
                family_code=res["family_code"], is_derived=res["is_derived"],
                artwork_role=res["artwork_role"], artwork_relationship=res["artwork_relationship"])


def _design_compatibility(design_type, own_product_type):
    """Resolve (primary_product, compatible_products) for a design_type. For
    set_piece/unknown the design is bound to its own product type."""
    spec = config.DESIGN_TYPES.get(design_type, config.DESIGN_TYPES["unknown"])
    primary = spec["primary"]
    compatible = list(spec["compatible"])
    if not primary:                       # set_piece / unknown -> own type only
        primary = own_product_type if own_product_type != "Unknown" else None
        compatible = [own_product_type] if own_product_type != "Unknown" else []
    return primary, compatible


def build_graph(db: IdentityDB, root, progress=None):
    """Walk a folder and build Family/Design/Asset/Product with opaque IDs."""
    root = Path(root)
    groups = ingest.group_by_stem(ingest.iter_files(root))
    errors = []
    panel_family = {}          # family_code -> set(design_id) for post-pass families
    for i, (face, sources) in enumerate(groups):
        if progress:
            progress(i + 1, len(groups), face.name if face else "")
        if face is None:
            for m in sources:
                errors.append({"file": m.name, "error": "master with no JPG/PNG face (Phase 3 review)"})
            continue
        try:
            g = _classify(face)
            own_type = config.canon_product_type(g["atype"])
            design_type = g["design_type"]
            primary, compatible = _design_compatibility(design_type, own_type)
            # engineered-panel families are decided in a post-pass (>=2 sibling designs);
            # set-based families are still created eagerly from the set code.
            family_id = None if g["family_code"] else db.ensure_family(g["set_code"])
            # a derived cushion lives in its parent curtain design (same design_key)
            design_id = db.ensure_design(g["gkey"], family_id, design_type, primary, compatible)
            if g["family_code"]:
                panel_family.setdefault(g["family_code"], set()).add(design_id)

            # v2.0-a: create the Artwork Source (the application of this artwork). A
            # derived application records what it was derived from (the same-side
            # Original source of this design). Additive — products are unchanged here.
            application = own_type
            derived_from_source = None
            if g["is_derived"]:
                derived_from_source = db.ensure_source(
                    design_id, "Curtain", origin="Original", side=g["side"])
            source_id = db.ensure_source(
                design_id, application,
                origin=g["artwork_role"], artwork_relationship=g["artwork_relationship"],
                side=g["side"], label=g["label"], derived_from_source=derived_from_source)

            sha = ingest.file_hash(face)
            try:
                with Image.open(face) as im:
                    w, h = im.size
            except Exception:
                w = h = None
            src = json.dumps([{"filename": s.name, "path": str(s.resolve()),
                               "ext": s.suffix.lower().lstrip(".")} for s in sources])
            asset_id = db.ensure_asset(
                sha, design_id, filename=face.name, path=str(face.resolve()),
                width=w, height=h, side=g["side"], role=g["role"], source_files=src,
                match_rule=g["match_rule"], confidence=g["confidence"],
                needs_review=g["needs_review"], design_variant=g["design_variant"],
                legacy_ab=g["legacy_ab"], artwork_role=g["artwork_role"],
                artwork_relationship=g["artwork_relationship"],
                derived_from_design=(design_id if g["is_derived"] else None),
                source_id=source_id)
            if g["needs_review"]:
                errors.append({"file": face.name, "reason": g["review_reason"] or "needs review"})

            if g["is_derived"]:
                # derived artwork (e.g. cushion cropped from the curtain) is realized from
                # its own derived Artwork Source, which authorises this product. Distinct
                # derived sources -> distinct products (no discriminator, no bypass flag).
                product_id = db.ensure_product(design_id, family_id, own_type,
                                               source_id=source_id, derived=True)
                db.link_variant(product_id, asset_id, g["label"])
            elif primary:
                # the design's PRIMARY product (compatibility-enforced). Original sources of
                # one type GROUP into a single product (curtain Left/Right are variants).
                product_id = db.ensure_product(design_id, family_id, primary)
                db.link_variant(product_id, asset_id, g["label"])
            else:
                errors.append({"file": face.name, "reason": "no primary product (Phase 3 review)"})
        except Exception as e:
            errors.append({"file": str(face), "error": f"{type(e).__name__}: {e}"})

    # post-pass: an engineered-panel family exists only when >=2 sibling designs share
    # the code (e.g. P4204 + P4204-V2). A lone design stays family-less.
    for code, design_ids in panel_family.items():
        if len(design_ids) >= 2:
            fam = db.ensure_family(code)
            for did in design_ids:
                db.assign_family(did, fam)

    summary = db.counts()
    summary["errors"] = errors
    return summary


def main():
    ap = argparse.ArgumentParser(description="KF Asset Manager — Phase 1 identity builder")
    ap.add_argument("--root", required=True, help="folder to scan")
    ap.add_argument("--db", required=True, help="identity database path")
    args = ap.parse_args()
    db = IdentityDB(args.db)
    s = build_graph(db, args.root)
    print("schema_version:", SCHEMA_VERSION)
    print("counts:", {k: v for k, v in s.items() if k != "errors"})
    print("errors:", len(s["errors"]))
    print()
    # show the entity graph
    rows = db.conn.execute("""
        SELECT d.design_id, d.family_id, p.product_id, p.product_type,
               a.asset_id, a.side, a.role, a.filename
        FROM designs d
        LEFT JOIN products p ON p.design_id = d.design_id
        LEFT JOIN assets a ON a.design_id = d.design_id
        ORDER BY d.design_id, a.asset_id""").fetchall()
    for r in rows:
        fam = r["family_id"] or "-"
        print(f"{r['design_id']}  fam={fam:<12} {r['product_id']}  {str(r['product_type']):<18} "
              f"{r['asset_id']}  {str(r['side'] or ''):<3} {r['filename']}")


if __name__ == "__main__":
    main()
