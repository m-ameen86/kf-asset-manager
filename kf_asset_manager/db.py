"""SQLite data layer for KF Asset Manager. The DB is the single source of truth.

Identity model:
  * Each file is one row, keyed by its content hash (sha256, UNIQUE). Same bytes =>
    same row, forever, regardless of path. Re-scans never duplicate known content.
  * design_uid is the *artwork* identity (KF-D-xxxxxx). It is shared when several
    files are one design (curtain panels A/B), so it is intentionally NOT unique.
  * product_sku is assigned per design_uid (the curtain pair = one product).
  * Every overridable field stores ai_<f> and manual_<f>; effective = manual ?? ai.
    Re-scan / re-classify only write ai_<f>, so manual edits are permanent.
"""
import json, sqlite3, time
from pathlib import Path
from . import config

def _eff(ai, manual):
    return manual if (manual is not None and str(manual).strip() != "") else ai

class DB:
    def __init__(self, db_path):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self):
        ov = "".join(f"ai_{f} TEXT, manual_{f} TEXT,\n" for f in config.OVERRIDABLE)
        self.conn.executescript(f"""
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY,
            design_uid TEXT,
            sha256 TEXT UNIQUE,
            path TEXT, filename TEXT, width INTEGER, height INTEGER,
            set_code TEXT, role TEXT, side TEXT, product_sku TEXT,
            {ov}
            ai_tags TEXT, manual_tags TEXT,
            color_palette TEXT, dominant_color TEXT, source_files TEXT,
            status TEXT DEFAULT 'draft', created_at REAL, updated_at REAL);
        CREATE TABLE IF NOT EXISTS sets (
            set_code TEXT PRIMARY KEY, set_uid TEXT, set_number INTEGER,
            ai_selling_name TEXT, manual_selling_name TEXT,
            ai_title TEXT, manual_title TEXT, taste TEXT,
            status TEXT DEFAULT 'draft', updated_at REAL);
        CREATE TABLE IF NOT EXISTS relationships (
            a_uid TEXT, b_uid TEXT, kind TEXT, UNIQUE(a_uid,b_uid,kind));
        CREATE TABLE IF NOT EXISTS vocab (field TEXT, value TEXT, UNIQUE(field,value));
        CREATE TABLE IF NOT EXISTS counters (name TEXT PRIMARY KEY, value INTEGER);
        """)
        for field, values in config.VOCAB.items():
            for v in values:
                self.conn.execute("INSERT OR IGNORE INTO vocab(field,value) VALUES(?,?)",(field,v))
        for c in ("design","product","set"):
            self.conn.execute("INSERT OR IGNORE INTO counters(name,value) VALUES(?,0)",(c,))
        self.conn.commit()

    def _next(self, name, fmt):
        self.conn.execute("UPDATE counters SET value=value+1 WHERE name=?", (name,))
        n = self.conn.execute("SELECT value FROM counters WHERE name=?", (name,)).fetchone()[0]
        self.conn.commit()
        return fmt.format(n=n)

    def next_design_uid(self): return self._next("design","KF-D-{n:06d}")
    def next_product_sku(self, code): return self._next("product","KF-"+code+"-{n:06d}")
    def next_set_uid(self): return self._next("set","KF-SET-{n:05d}")

    def get_by_hash(self, sha):
        r = self.conn.execute("SELECT * FROM assets WHERE sha256=?", (sha,)).fetchone()
        return dict(r) if r else None

    def upsert_asset(self, *, sha, path, filename, width, height, set_code, role,
                     side, asset_type_ai, palette, dominant, design_grouping_uid=None,
                     source_files=None):
        now = time.time()
        src = json.dumps(source_files or [])
        existing = self.get_by_hash(sha)
        if existing:
            self.conn.execute("""UPDATE assets SET path=?,filename=?,width=?,height=?,
                set_code=?,role=?,side=?,ai_asset_type=?,color_palette=?,dominant_color=?,
                source_files=?,updated_at=? WHERE sha256=?""",
                (path,filename,width,height,set_code,role,side,asset_type_ai,
                 json.dumps(palette),dominant,src,now,sha))
            self.conn.commit()
            return existing["design_uid"]
        uid = design_grouping_uid or self.next_design_uid()
        self.conn.execute("""INSERT INTO assets(design_uid,sha256,path,filename,width,height,
            set_code,role,side,ai_asset_type,color_palette,dominant_color,source_files,status,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?, 'draft', ?, ?)""",
            (uid,sha,path,filename,width,height,set_code,role,side,asset_type_ai,
             json.dumps(palette),dominant,src,now,now))
        self.conn.commit()
        return uid

    def assign_product_sku(self, design_uid, type_code):
        r = self.conn.execute(
            "SELECT product_sku FROM assets WHERE design_uid=? AND product_sku IS NOT NULL LIMIT 1",
            (design_uid,)).fetchone()
        sku = r["product_sku"] if r else self.next_product_sku(type_code)
        self.conn.execute("UPDATE assets SET product_sku=? WHERE design_uid=?", (sku,design_uid))
        self.conn.commit()
        return sku

    def assign_set_sku(self, design_uid, type_code, set_number, suffix=""):
        """SKU for a piece inside a set: all pieces share the set's number, the
        type prefix says what it is, and the suffix (-A/-B, -1/-2) distinguishes
        multiple pieces of the same type. e.g. KF-CUR-000338, KF-CSH-000338-A."""
        r = self.conn.execute(
            "SELECT product_sku FROM assets WHERE design_uid=? AND product_sku IS NOT NULL LIMIT 1",
            (design_uid,)).fetchone()
        if r:
            sku = r["product_sku"]
        else:
            sku = f"KF-{type_code}-{set_number:06d}" + (f"-{suffix}" if suffix else "")
        self.conn.execute("UPDATE assets SET product_sku=? WHERE design_uid=?", (sku, design_uid))
        self.conn.commit()
        return sku

    def set_field(self, sha, column, value):
        if not (column.startswith(("manual_","ai_")) or column=="status"):
            raise ValueError("protected column "+column)
        self.conn.execute(f"UPDATE assets SET {column}=?,updated_at=? WHERE sha256=?",
                          (value,time.time(),sha))
        self.conn.commit()

    def upsert_set(self, set_code):
        r = self.conn.execute("SELECT set_uid FROM sets WHERE set_code=?", (set_code,)).fetchone()
        if r:
            return r["set_uid"]
        self.conn.execute("UPDATE counters SET value=value+1 WHERE name='set'")
        num = self.conn.execute("SELECT value FROM counters WHERE name='set'").fetchone()[0]
        uid = f"KF-SET-{num:05d}"
        self.conn.execute(
            "INSERT INTO sets(set_code,set_uid,set_number,updated_at) VALUES(?,?,?,?)",
            (set_code, uid, num, time.time()))
        self.conn.commit()
        return uid

    def set_number_for(self, set_code):
        """The shared numeric id for a set (minting the set if needed)."""
        self.upsert_set(set_code)
        r = self.conn.execute("SELECT set_number FROM sets WHERE set_code=?", (set_code,)).fetchone()
        return r["set_number"]

    def set_set_field(self, set_code, column, value):
        self.conn.execute(f"UPDATE sets SET {column}=?,updated_at=? WHERE set_code=?",
                          (value,time.time(),set_code)); self.conn.commit()

    def add_relationship(self, a, b, kind):
        if a==b: return
        self.conn.execute("INSERT OR IGNORE INTO relationships(a_uid,b_uid,kind) VALUES(?,?,?)",
                          (a,b,kind)); self.conn.commit()

    def vocab(self, field):
        return [r["value"] for r in self.conn.execute(
            "SELECT value FROM vocab WHERE field=? ORDER BY value",(field,)).fetchall()]
    def add_vocab(self, field, value):
        self.conn.execute("INSERT OR IGNORE INTO vocab(field,value) VALUES(?,?)",(field,value))
        self.conn.commit()

    def all_assets(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM assets ORDER BY set_code,role,side").fetchall()]
    def all_sets(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM sets ORDER BY set_code").fetchall()]
    def effective(self, row, field): return _eff(row.get(f"ai_{field}"), row.get(f"manual_{field}"))
    def effective_set(self, row, field): return _eff(row.get(f"ai_{field}"), row.get(f"manual_{field}"))
