"""Phase 3-a tests — local colour extraction (no AI), caching, manifest surfacing.

Run: python -m kf_asset_manager.tests_vision_colour
"""
import sys, tempfile, json
from pathlib import Path
from PIL import Image

from . import model, colour, vision_colour as vc, audit

PASS, FAIL = [], []


def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("  ok  " if cond else " FAIL ") + name)


def run():
    # ---- named-colour mapping ----
    check("pure red -> Red", colour.nearest_name(255, 0, 0) == "Red")
    check("near-black -> Black", colour.nearest_name(8, 8, 8) == "Black")
    check("KF navy maps to KF Navy", colour.nearest_name(0x1B, 0x2A, 0x4A) == "KF Navy")
    check("KF gold maps to KF Gold", colour.nearest_name(0xB8, 0x94, 0x3F) == "KF Gold")

    # ---- palette extraction on synthetic images ----
    d = Path(tempfile.mkdtemp())
    solid = d / "solid.png"
    Image.new("RGB", (64, 64), (200, 30, 30)).save(solid)
    pal = colour.extract_palette(str(solid))
    check("solid image -> dominant ~100%", pal[0]["percentage"] >= 95.0)
    check("solid red named Red", pal[0]["named"] == "Red")

    half = d / "half.png"
    im = Image.new("RGB", (64, 64), (200, 30, 30))
    for y in range(32):
        for x in range(64):
            im.putpixel((x, y), (40, 70, 180))     # top half blue
    half_path = d / "half.png"; im.save(half_path)
    pal2 = colour.extract_palette(str(half_path))
    names = colour.dominant_names(pal2)
    check("two-colour image yields two dominant names", len([n for n in names]) >= 2)
    check("blue + red both detected", "Blue" in names and "Red" in names)

    # ---- build a tiny library, run the colour pass, check caching ----
    lib = Path(tempfile.mkdtemp()) / "Curtains"; lib.mkdir(parents=True)
    Image.new("RGB", (32, 32), (0x1B, 0x2A, 0x4A)).save(lib / "P4186-L.jpg")
    Image.new("RGB", (32, 32), (0xB8, 0x94, 0x3F)).save(lib / "P4186-R.jpg")
    db = model.IdentityDB(str(lib.parent / "x.db"))
    model.build_graph(db, lib)

    proc, skip, err = vc.run_colours(db)
    check("colour pass processed both assets", proc == 2 and err == 0)
    proc2, skip2, err2 = vc.run_colours(db)
    check("re-run is fully cached (0 processed)", proc2 == 0 and skip2 == 2)
    proc3, _, _ = vc.run_colours(db, force=True)
    check("--force re-extracts", proc3 == 2)

    # stored + retrievable
    aid = db.conn.execute("SELECT asset_id FROM assets WHERE filename='P4186-L.jpg'").fetchone()[0]
    vis = db.get_vision(aid)
    check("vision row stored with colours", vis is not None and isinstance(vis["colours"], list))
    check("navy curtain reads as KF Navy", vis["colours"][0]["named"] == "KF Navy")

    # colours.csv
    out = lib.parent / "colours.csv"
    n = vc.write_colours_csv(db, out)
    check("colours.csv written for all assets", n == 2 and out.exists())

    # ---- manifest surfaces colours when present ----
    rep = audit.generate_reports(db, lib, lib.parent / "rep", do_hash=False)
    m = json.loads((lib.parent / "rep" / "manifest.json").read_text())
    has_col = any(v.get("colours") for p in m["products"] for v in p["variants"])
    check("manifest variants carry colours after a colour pass", has_col)

    # ---- vision metadata is NOT identity ----
    check("vision_results is separate from identity tables",
          "vision_results" in {r[0] for r in db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")})
    cnt_before = db.counts()["designs"]
    vc.run_colours(db, force=True)
    check("running vision does not change identity counts", db.counts()["designs"] == cnt_before)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(run())
