"""CLI: import a library folder into the KF database, optionally emitting an audit.

This is the **Import / Refresh Library** operation (idempotent re-import preserves IDs).

    python -m kf_asset_manager.build_graph --root "/path/to/02_Engineered_Panels" --report

The audit is READ-ONLY: it scans into a throwaway database and writes report files to a
`/reports/` folder. It never renames, moves, or modifies anything in the library.
"""

import argparse
import sys
from pathlib import Path

from . import model, audit


def main(argv=None):
    ap = argparse.ArgumentParser(prog="kf_asset_manager.build_graph",
                                 description="Import a library into the KF database (and optional read-only audit).")
    ap.add_argument("--root", required=True, help="library folder to scan")
    ap.add_argument("--db", help="database path (default: <reports>/audit.db, PRESERVED "
                    "across runs; schema migrations run automatically on open)")
    ap.add_argument("--report", action="store_true", help="produce the read-only audit reports")
    ap.add_argument("--out", help="reports output folder (default: ./reports)")
    ap.add_argument("--no-hash", action="store_true", help="skip content hashing for duplicate detection")
    ap.add_argument("--fresh", action="store_true",
                    help="wipe the database and rebuild from scratch. DESTRUCTIVE: this "
                         "erases non-derivable data — AI vision results (vision_results, "
                         "paid analysis), local colour extraction, and any manual "
                         "display_title overrides — none of which can be recovered from "
                         "the image library alone. Only use this when you deliberately "
                         "want a clean throwaway database. A safety snapshot is taken "
                         "automatically before the wipe (see --backup-dir).")
    ap.add_argument("--backup-dir", default=None,
                    help="where the automatic pre-fresh safety snapshot is written "
                        "(default: $KF_BACKUP_DIR, else a 'backups/' folder next to the "
                        "database). Configurable — never assumes a specific drive.")
    args = ap.parse_args(argv)

    root = Path(args.root)
    if not root.is_dir():
        ap.error(f"--root is not a directory: {root}")

    out = Path(args.out) if args.out else Path("reports")
    out.mkdir(parents=True, exist_ok=True)
    db_path = args.db or str(out / "audit.db")
    if args.fresh and Path(db_path).exists():
        from . import db_backup
        try:
            snap = db_backup.backup_database(db_path, args.backup_dir, label="pre-fresh")
            print(f"--fresh: safety snapshot written to {snap} before wiping", file=sys.stderr)
        except db_backup.BackupError as e:
            print(f"--fresh REFUSED: safety snapshot could not be created ({e}). "
                 f"Not proceeding with a destructive wipe without one — fix the backup "
                 f"destination (see --backup-dir / $KF_BACKUP_DIR) and try again.",
                 file=sys.stderr)
            return 2
        print(f"--fresh: wiping {db_path} (vision results, colours, and manual title "
             f"overrides will be lost)", file=sys.stderr)
        Path(db_path).unlink()
    # Default: PRESERVE the existing database across runs. Re-importing is idempotent for
    # identity (re-scan adds no rows, asset/design/product IDs never change — proven since
    # Phase 1), so it safely updates/extends identity data while keeping vision_results,
    # colour extraction, and display_title overrides intact. Use --fresh for a deliberate
    # clean rebuild.

    db = model.IdentityDB(db_path)

    def progress(i, n, name):
        if i == 1 or i == n or i % 50 == 0:
            print(f"  scanning {i}/{n}: {name}", file=sys.stderr)

    print(f"Importing library {root} …", file=sys.stderr)
    summary = model.build_graph(db, root, progress=progress)
    counts = db.counts()
    print(f"Built: {counts['families']} families · {counts['designs']} designs · "
          f"{counts['assets']} assets · {counts['products']} products "
          f"({len(summary.get('errors', []))} review/skip notes)", file=sys.stderr)

    if args.report:
        print("Generating audit reports …", file=sys.stderr)
        r = audit.generate_reports(db, root, out, do_hash=not args.no_hash)
        print(f"\nReports written to {r['out']}/", file=sys.stderr)
        print(f"  files={r['files']} faces={r['faces']} designs={r['designs']} "
              f"products={r['products']} variants={r['variants']}", file=sys.stderr)
        print(f"  unmatched={r['unmatched']} needs_review={r['needs_review']} "
              f"SC(mat)={r['sc']} SC(est)={r['sc_est']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
