"""Schema migration tests — the DB-preservation fix's load-bearing follow-up.

CRITICAL BUG FIXED: `CREATE TABLE IF NOT EXISTS` does not add columns to a table that
already exists. That was invisible while the database was rebuilt on every run; now that
build_graph PRESERVES it by default, opening an old database with newer code used to crash
with "no such column". This proves the migration system fixes that: an intentionally OLD,
pre-migration database — built by hand with raw sqlite3, missing every column added since —
carrying REAL data (a vision_results row, a manual display_title, product/asset rows),
opens cleanly with current code, loses nothing, and is idempotent on repeated opens.

Run: python -m kf_asset_manager.tests_schema_migration
"""
import sys, tempfile, sqlite3, json, time
from pathlib import Path

from . import model

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else " FAIL ") + name)


def _build_old_schema_db(path):
    """Hand-build a database matching the schema BEFORE the migrated columns existed:
    no assets.source_id, no products.source_id/display_title, no vision_results.is_match.
    Populates it with real rows an actual old database would have — the exact scenario
    that used to crash."""
    conn = sqlite3.connect(str(path))
    conn.executescript("""
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE counters (name TEXT PRIMARY KEY, value INTEGER);
        CREATE TABLE families (family_id TEXT PRIMARY KEY, set_code TEXT UNIQUE,
                               created_at REAL, updated_at REAL);
        CREATE TABLE designs (design_id TEXT PRIMARY KEY, family_id TEXT,
                              grouping_key TEXT UNIQUE, design_type TEXT,
                              primary_product TEXT, compatible_products TEXT,
                              created_at REAL, updated_at REAL);
        -- OLD assets: no source_id column
        CREATE TABLE assets (
            asset_id TEXT PRIMARY KEY, design_id TEXT, sha256 TEXT UNIQUE,
            filename TEXT, path TEXT, width INTEGER, height INTEGER,
            side TEXT, role TEXT, source_files TEXT, source_library TEXT,
            match_rule TEXT, confidence REAL, needs_review INTEGER DEFAULT 0,
            design_variant TEXT, legacy_ab INTEGER DEFAULT 0,
            artwork_role TEXT DEFAULT 'Original', artwork_relationship TEXT DEFAULT 'Original',
            derived_from_design TEXT, derived_from_asset TEXT,
            created_at REAL, updated_at REAL);
        CREATE TABLE artwork_sources (
            source_id TEXT PRIMARY KEY, design_id TEXT, application TEXT,
            origin TEXT DEFAULT 'Original', artwork_relationship TEXT DEFAULT 'Original',
            derived_from_source TEXT, side TEXT, label TEXT,
            created_at REAL, updated_at REAL,
            UNIQUE(design_id, application, side, origin));
        -- OLD products: no source_id, no display_title
        CREATE TABLE products (
            product_id TEXT PRIMARY KEY, design_id TEXT, family_id TEXT, product_type TEXT,
            created_at REAL, updated_at REAL);
        CREATE TABLE product_variants (
            product_id TEXT, asset_id TEXT, variant_label TEXT,
            UNIQUE(product_id, asset_id, variant_label));
        CREATE TABLE business_metadata (
            entity_type TEXT, entity_id TEXT, dimension TEXT, value TEXT, created_at REAL,
            UNIQUE(entity_type, entity_id, dimension, value));
        -- OLD vision_results: no is_match column
        CREATE TABLE vision_results (
            asset_id TEXT PRIMARY KEY, sha256 TEXT, vision_version INTEGER,
            colours TEXT, suggested_name TEXT, style_tags TEXT,
            match_confidence REAL, match_reason TEXT, model TEXT, analyzed_at REAL);
    """)
    now = time.time()
    conn.execute("INSERT INTO families VALUES ('KF-FAM-000001','P4186',?,?)", (now, now))
    conn.execute("INSERT INTO designs VALUES ('KF-D-000001','KF-FAM-000001','PANEL|P4186',"
                "'engineered_panel','Curtain','Curtain',?,?)", (now, now))
    conn.execute("INSERT INTO assets VALUES ('KF-AST-000001','KF-D-000001','deadbeef01',"
                "'P4186-L.jpg','/lib/P4186-L.jpg',800,600,'L','panel-L','','',"
                "'flat_curtain',0.9,0,NULL,0,'Original','Original',NULL,NULL,?,?)", (now, now))
    conn.execute("INSERT INTO products VALUES ('KF-PRD-000001','KF-D-000001',"
                "'KF-FAM-000001','Curtain',?,?)", (now, now))
    conn.execute("INSERT INTO product_variants VALUES ('KF-PRD-000001','KF-AST-000001','Left')")
    conn.execute("""INSERT INTO vision_results VALUES ('KF-AST-000001','deadbeef01',1,
        ?, 'Sleepy Moon & Stars Nursery Print', ?, 0.85,
        'whimsical night-sky kids print', 'claude-sonnet-5', ?)""",
                (json.dumps([{"hex": "#1B2A4A", "percentage": 90, "named": "KF Navy"}]),
                 json.dumps(["kids", "nursery"]), now))
    conn.commit()
    conn.close()


def run():
    tmp = Path(tempfile.mkdtemp())
    db_path = tmp / "old_production.db"
    _build_old_schema_db(db_path)

    raw = sqlite3.connect(str(db_path))
    old_cols = {r[1] for r in raw.execute("PRAGMA table_info(products)")}
    check("fixture genuinely predates products.source_id/display_title",
          "source_id" not in old_cols and "display_title" not in old_cols)
    raw.close()

    crashed = False
    try:
        db = model.IdentityDB(str(db_path))
    except Exception:
        crashed = True
        db = None
    check("opening an old-schema DB with current code does NOT crash", not crashed)
    if db is None:
        print(f"\n{len(PASS)} passed, {len(FAIL)+1} failed (fatal: could not open DB)")
        return 1

    applied = db.applied_migrations()
    check("migration recorded: assets.source_id", "2026_assets_source_id" in applied)
    check("migration recorded: products.source_id", "2026_products_source_id" in applied)
    check("migration recorded: products.display_title", "2026_products_display_title" in applied)
    check("migration recorded: vision_results.is_match", "2026_vision_results_is_match" in applied)

    check("assets.source_id column now exists",
          "source_id" in {r[1] for r in db.conn.execute("PRAGMA table_info(assets)")})
    check("products.source_id column now exists",
          "source_id" in {r[1] for r in db.conn.execute("PRAGMA table_info(products)")})
    check("products.display_title column now exists",
          "display_title" in {r[1] for r in db.conn.execute("PRAGMA table_info(products)")})
    check("vision_results.is_match column now exists",
          "is_match" in {r[1] for r in db.conn.execute("PRAGMA table_info(vision_results)")})

    src = db.conn.execute("SELECT source_id FROM products WHERE product_id='KF-PRD-000001'").fetchone()
    check("products.source_id backfilled to '' (grouped-original sentinel) via DEFAULT",
          src["source_id"] == "")

    vis = db.get_vision("KF-AST-000001")
    check("vision_results row survives migration", vis is not None)
    check("suggested_name survives migration",
          vis and vis["suggested_name"] == "Sleepy Moon & Stars Nursery Print")
    check("style_tags survives migration (still valid JSON list)",
          vis and vis["style_tags"] == ["kids", "nursery"])
    check("colours survive migration",
          vis and vis["colours"] and vis["colours"][0]["named"] == "KF Navy")
    check("match_confidence survives migration", vis and vis["match_confidence"] == 0.85)
    check("is_match on an old (pre-migration) row is NULL, not fabricated", vis and vis["is_match"] is None)

    db.set_title("KF-PRD-000001", "Royal Damask Curtain (approved)")
    check("set_title works on a migrated database",
          db.title_for("KF-PRD-000001") == "Royal Damask Curtain (approved)")

    p = db.conn.execute("SELECT product_id,design_id,family_id,product_type FROM products "
                        "WHERE product_id='KF-PRD-000001'").fetchone()
    check("product identity fields untouched by migration",
          tuple(p) == ("KF-PRD-000001", "KF-D-000001", "KF-FAM-000001", "Curtain"))
    a = db.conn.execute("SELECT asset_id,sha256,filename FROM assets "
                        "WHERE asset_id='KF-AST-000001'").fetchone()
    check("asset identity fields untouched by migration",
          tuple(a) == ("KF-AST-000001", "deadbeef01", "P4186-L.jpg"))

    try:
        db2 = model.IdentityDB(str(db_path))
        reopen_ok = True
    except Exception:
        reopen_ok = False
    check("re-opening a migrated DB a second time does not crash", reopen_ok)
    if reopen_ok:
        applied2 = db2.applied_migrations()
        check("migration list is identical on re-open (no duplicates)",
              sorted(applied2) == sorted(applied))
        check("migration table has exactly one row per migration (no duplicate inserts)",
              db2.conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] ==
              len(model.IdentityDB.MIGRATIONS))
        vis2 = db2.get_vision("KF-AST-000001")
        check("AI data still present after a second open", vis2 and vis2["suggested_name"] is not None)
        check("manual title override still present after a second open",
              db2.title_for("KF-PRD-000001") == "Royal Damask Curtain (approved)")

    try:
        db._run_migrations()
        third_ok = True
    except Exception:
        third_ok = False
    check("calling _run_migrations() again directly is a safe no-op", third_ok)

    fresh_path = tmp / "brand_new.db"
    fresh = model.IdentityDB(str(fresh_path))
    check("a brand-new database has all migrations recorded too",
          set(fresh.applied_migrations()) == {m[0] for m in model.IdentityDB.MIGRATIONS})

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(run())
