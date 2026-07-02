"""Phase 3-a colour pass — run local colour extraction over a built library.

Reads asset file paths from a built DB, extracts dominant colours locally (no AI), caches
by sha256+version, and writes colours.csv. Opt-in and scopable; safe to re-run (cached).

CLI:
  python -m kf_asset_manager.vision_colour --db audit.db [--out colours.csv]
         [--types Curtain Fabric] [--limit N] [--force]
"""
import argparse
import csv
import sys
from pathlib import Path

from . import colour as _colour


def run_colours(db, product_types=None, limit=None, force=False, progress=None):
    """Extract+cache colours for assets backing the (optionally filtered) products.
    Returns (processed, skipped, errors)."""
    conn = db.conn
    if product_types:
        q = ("SELECT DISTINCT a.asset_id,a.path,a.sha256 FROM assets a "
             "JOIN product_variants pv ON pv.asset_id=a.asset_id "
             "JOIN products p ON p.product_id=pv.product_id "
             "WHERE p.product_type IN (%s) ORDER BY a.asset_id"
             % ",".join("?" * len(product_types)))
        rows = conn.execute(q, list(product_types)).fetchall()
    else:
        rows = conn.execute("SELECT asset_id,path,sha256 FROM assets ORDER BY asset_id").fetchall()
    if limit:
        rows = rows[:int(limit)]

    processed = skipped = errors = 0
    for i, r in enumerate(rows):
        if progress and i % 50 == 0:
            progress(i, len(rows), r["path"])
        if not force and db.has_vision_colours(r["asset_id"], r["sha256"]):
            skipped += 1
            continue
        try:
            pal = _colour.extract_palette(r["path"])
            db.record_vision_colours(r["asset_id"], r["sha256"], pal)
            processed += 1
        except Exception as e:
            errors += 1
            if progress:
                progress(i, len(rows), f"ERROR {r['path']}: {e}")
    return processed, skipped, errors


def write_colours_csv(db, path, product_types=None):
    import json as _json
    conn = db.conn
    rows = conn.execute("""SELECT v.asset_id,a.filename,v.colours FROM vision_results v
                           JOIN assets a ON a.asset_id=v.asset_id
                           WHERE v.colours IS NOT NULL ORDER BY v.asset_id""").fetchall()
    header = ["asset_id", "filename", "dominant", "hex1", "pct1", "hex2", "pct2", "hex3", "pct3"]
    out = []
    for r in rows:
        pal = _json.loads(r["colours"])
        dom = ", ".join(_colour.dominant_names(pal)) or (pal[0]["named"] if pal else "")
        cells = [r["asset_id"], r["filename"], dom]
        for c in pal[:3]:
            cells += [c["hex"], c["percentage"]]
        cells += [""] * (len(header) - len(cells))
        out.append(cells)
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(header)
        wr.writerows(out)
    return len(out)


def _main(argv=None):
    ap = argparse.ArgumentParser(description="Phase 3-a local colour extraction (no AI).")
    ap.add_argument("--db", required=True)
    ap.add_argument("--out", default=None, help="colours.csv path (default: next to the db)")
    ap.add_argument("--types", nargs="*", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--force", action="store_true", help="re-extract even if cached")
    a = ap.parse_args(argv)

    from . import model
    db = model.IdentityDB(a.db)

    def prog(i, n, msg):
        print(f"  colours {i}/{n}: {Path(str(msg)).name}", file=sys.stderr)

    proc, skip, err = run_colours(db, product_types=a.types, limit=a.limit,
                                  force=a.force, progress=prog)
    out = a.out or str(Path(a.db).parent / "colours.csv")
    n = write_colours_csv(db, out, product_types=a.types)
    print(f"Colours: {proc} extracted, {skip} cached-skip, {err} errors. "
          f"Wrote {n} rows -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
