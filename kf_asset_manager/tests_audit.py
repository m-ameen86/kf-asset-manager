"""Smoke test for the Production Library Auditor (read-only).

Run: python -m kf_asset_manager.tests_audit
"""
import sys, tempfile, os
from pathlib import Path

from PIL import Image

from . import model, audit

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else " FAIL ") + name)


def run():
    lib = Path(tempfile.mkdtemp()) / "Panels"
    lib.mkdir(parents=True)
    def jpg(n, c=(80, 80, 80)):
        Image.new("RGB", (32, 32), c).save(lib / n, "JPEG")
    jpg("Kids-3141-L.jpg"); jpg("Kids-3141-R.jpg")        # matched by flat_curtain
    jpg("P4134-L.jpg", (1, 2, 3)); jpg("P4134-L-cush.jpg", (4, 5, 6))  # matched by engineered_panel
    (lib / "P4134-L.psd").write_bytes(b"M")               # a master
    jpg("weird_name.jpg", (9, 9, 9))                      # genuinely unknown convention

    out = Path(tempfile.mkdtemp()) / "reports"
    db = model.IdentityDB(str(out.parent / "audit.db"))
    model.build_graph(db, lib)
    r = audit.generate_reports(db, lib, out, do_hash=True)

    expected = ["library_summary.md", "naming_report.csv", "rule_coverage.md",
                "needs_review.csv", "duplicate_assets.csv", "duplicate_designs.csv",
                "unmatched_filenames.csv", "families.csv", "designs.csv",
                "assets.csv", "products.csv"]
    for fn in expected:
        check(f"report exists: {fn}", (out / fn).exists())

    check("only the unknown name is unmatched (P#### now parses)", r["unmatched"] == 1)
    check("naming + faces counted", r["faces"] >= 4)
    summary = (out / "library_summary.md").read_text()
    check("summary lists file types", "psd" in summary and "jpg" in summary)
    check("summary has SC metrics block", "SC1" in summary and "Estimated" in summary)
    check("estimated derived cushion detected", r["sc_est"][0] >= 1)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(run())
