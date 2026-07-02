"""KF Asset Manager — local web app (desktop-first, runs entirely on your machine).

Flow: pick a root folder -> Scan -> review the grid -> edit anything (manual edits
are permanent overrides) -> Approve -> Export. No data leaves your computer except
the optional vision-classification call to the Anthropic API.
"""

import io
import json
import os
from pathlib import Path

from flask import (Flask, jsonify, render_template, request,
                   send_file, redirect, url_for)

from . import classify, config, exporters, ingest
from .db import DB

app = Flask(__name__)
# The database is the single source of truth and lives in ONE fixed place,
# independent of whichever content folder you scan. Default: alongside the tool
# (current working directory). Override with the KF_DB env var or --db.
DB_PATH = Path(os.environ.get("KF_DB", Path.cwd() / config.DB_FILENAME)).expanduser()
STATE = {"db": None, "root": None}


def set_db_path(path):
    global DB_PATH
    DB_PATH = Path(path).expanduser()


def open_root(root):
    """Point at a content folder to scan. The DB stays at DB_PATH regardless."""
    root = Path(root).expanduser().resolve()
    STATE["root"] = root
    if STATE["db"] is None:
        STATE["db"] = DB(DB_PATH)
    return STATE["db"]


@app.route("/")
def index():
    return render_template("index.html", root=STATE["root"],
                           has_db=STATE["db"] is not None, app_name=config.APP_NAME,
                           tagline=config.TAGLINE)


@app.route("/scan", methods=["POST"])
def scan():
    root = request.form.get("root") or request.json.get("root")
    if not root or not Path(root).expanduser().exists():
        return jsonify(error="Folder not found. Check the path."), 400
    db = open_root(root)
    summary = ingest.scan(db, STATE["root"])
    STATE["last_summary"] = summary
    print(f"[scan] files={summary['files']} assets={summary['assets']} "
          f"pairs={summary['curtain_pairs']} merged={summary['merged_singles']} "
          f"sets={summary['sets']} set_designs={summary.get('set_designs',0)} "
          f"masters={summary.get('linked_masters', 0)} "
          f"skipped={len(summary['skipped'])} review={len(summary['review'])}")
    for e in summary["skipped"][:10]:
        print("   skipped:", e["file"], "->", e["error"])
    for r in summary["review"][:10]:
        print("   review :", r["file"], "->", r["reason"])
    return redirect(url_for("review"))


@app.route("/review")
def review():
    db = STATE["db"]
    if not db:
        return redirect(url_for("index"))
    assets = db.all_assets()
    sets = {s["set_code"]: s for s in db.all_sets()}
    # resolve effective values for display
    for a in assets:
        a["_eff"] = {f: db.effective(a, f) for f in config.OVERRIDABLE}
        a["_palette"] = json.loads(a.get("color_palette") or "[]")
    # group by set
    grouped, loose = {}, []
    for a in assets:
        (grouped.setdefault(a["set_code"], []).append(a)
         if a["set_code"] else loose.append(a))
    vocab = {f: db.vocab(f) for f in
             ("asset_type", "style", "theme", "primary_motif", "occasion",
              "region", "status")}
    return render_template(
        "review.html", grouped=grouped, loose=loose, sets=sets, vocab=vocab,
        overridable=config.OVERRIDABLE, app_name=config.APP_NAME,
        classify_on=classify.classify_available(),
        effset=lambda code, f: db.effective_set(sets.get(code, {}), f))


@app.route("/thumb/<key>")
def thumb(key):
    db = STATE["db"]
    row = next((a for a in db.all_assets() if a["sha256"] == key), None)
    if not row:
        return "", 404
    data = ingest.thumbnail_bytes(Path(row["path"]))
    return send_file(io.BytesIO(data), mimetype="image/jpeg")


@app.route("/asset/<key>", methods=["POST"])
def update_asset(key):
    db = STATE["db"]
    payload = request.json or {}
    for field in config.OVERRIDABLE:
        if field in payload:
            db.set_field(key, f"manual_{field}", payload[field] or None)
    if "status" in payload:
        db.set_field(key, "status", payload["status"])
    if "tags" in payload:
        db.set_field(key, "manual_tags", json.dumps(payload["tags"]))
    # add any new free-text vocab values so dropdowns learn them
    for f in ("style", "theme", "primary_motif", "occasion", "region", "asset_type"):
        if payload.get(f):
            db.add_vocab(f, payload[f])
    return jsonify(ok=True)


@app.route("/set/<set_code>", methods=["POST"])
def update_set(set_code):
    db = STATE["db"]
    payload = request.json or {}
    if "selling_name" in payload:
        db.set_set_field(set_code, "manual_selling_name", payload["selling_name"] or None)
    if "status" in payload:
        db.set_set_field(set_code, "status", payload["status"])
    return jsonify(ok=True)


@app.route("/classify", methods=["POST"])
def classify_all():
    db = STATE["db"]
    if not classify.classify_available():
        return jsonify(error="No ANTHROPIC_API_KEY / anthropic SDK. "
                             "Classification is optional; you can fill fields manually."), 400
    vocab = {f: db.vocab(f) for f in ("style", "theme", "primary_motif", "occasion", "region")}
    done = 0
    seen = set()
    for a in db.all_assets():
        if a.get("ai_style") or a["design_uid"] in seen:   # skip suggested + shared designs
            continue
        seen.add(a["design_uid"])
        import base64
        raw = ingest.thumbnail_bytes(Path(a["path"]), max_side=1024)
        res = classify.classify_asset(base64.standard_b64encode(raw).decode(),
                                      "image/jpeg", vocab)
        for f in ("style", "theme", "primary_motif", "occasion", "region",
                  "selling_name", "description"):
            if res.get(f):
                db.set_field(a["sha256"], f"ai_{f}", res[f])
        if res.get("tags"):
            db.set_field(a["sha256"], "ai_tags", json.dumps(res["tags"]))
        done += 1
    return jsonify(ok=True, classified=done)


@app.route("/export", methods=["POST"])
def export():
    db = STATE["db"]
    out = DB_PATH.parent / "_kfam_export"
    out.mkdir(exist_ok=True)
    m = exporters.write_manifest(db, out / "manifest.json")
    c = exporters.write_crosswalk(db, out / "crosswalk.csv")
    return jsonify(ok=True, manifest=str(m), crosswalk=str(c))
