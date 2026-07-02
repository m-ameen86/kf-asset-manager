"""Exporters. The DB is the source of truth; these produce *views* of it.

  * manifest.json — the master asset record (effective values resolved), grouped
    into bundles, ready for any downstream consumer.
  * crosswalk.csv — legacy filename -> new Design ID + Product SKU + status, the
    safety net for recoding without breaking the live site.
"""

import csv
import json
from pathlib import Path

from . import classify, config

TYPE_LABEL = {
    "Curtain Panel Set": "Curtain Pair", "Cushion": "Cushion",
    "Table Runner": "Table Runner", "Table Cloth": "Table Cloth",
    "Tapestry Artwork": "Tapestry", "Apparel Artwork": "Apparel",
    "Flag": "Flag", "Painting": "Painting", "Pattern": "Pattern", "Unknown": "Item",
}


def _effective_asset(db, row):
    eff = {f: db.effective(row, f) for f in config.OVERRIDABLE}
    pal = json.loads(row.get("color_palette") or "[]")
    # colour label for titles: top two distinct named colours
    seen, names = set(), []
    for p in pal:
        if p["name"] not in seen:
            seen.add(p["name"]); names.append(p["name"])
    eff["color"] = " & ".join(n.replace("KF ", "") for n in names[:2])
    return eff, pal


def build_manifest(db) -> dict:
    assets = db.all_assets()
    sets = {s["set_code"]: s for s in db.all_sets()}
    out_assets, bundles = [], {}

    for row in assets:
        eff, pal = _effective_asset(db, row)
        atype = eff["asset_type"] or row.get("ai_asset_type") or "Unknown"
        type_label = TYPE_LABEL.get(atype, "Item")
        if atype == "Cushion" and row.get("role", "").startswith("cushion-"):
            type_label = f"Cushion {row['role'].split('-')[1]}"

        # inherit the set's selling name if the asset has none of its own
        if row.get("set_code") and row["set_code"] in sets:
            s = sets[row["set_code"]]
            set_name = db.effective_set(s, "selling_name")
            if not eff.get("selling_name") and set_name:
                eff["selling_name"] = set_name

        title = eff["title"] or classify.build_title(eff, type_label)

        rec = {
            "asset_uid": row["design_uid"],
            "product_sku": row.get("product_sku"),
            "sha256": row["sha256"][:16],
            "path": row["path"],
            "asset_type": atype,
            "set_code": row.get("set_code"),
            "role": row.get("role"), "side": row.get("side"),
            "status": row.get("status"),
            "style": eff["style"], "theme": eff["theme"],
            "primary_motif": eff["primary_motif"], "occasion": eff["occasion"],
            "region": eff["region"],
            "color_palette": pal, "color_label": eff["color"],
            "selling_name": eff["selling_name"],
            "title": title,
            "description": eff["description"],
            "source_files": json.loads(row.get("source_files") or "[]"),
            "tags": json.loads(row.get("manual_tags") or row.get("ai_tags") or "[]"),
        }
        out_assets.append(rec)
        if row.get("set_code"):
            bundles.setdefault(row["set_code"], []).append(row["product_sku"])

    bundle_list = []
    for code, skus in bundles.items():
        s = sets.get(code, {})
        name = db.effective_set(s, "selling_name") if s else ""
        bundle_list.append({
            "set_code": code,
            "set_uid": s.get("set_uid"),
            "selling_name": name,
            "title": db.effective_set(s, "title") if s else "",
            "status": s.get("status", "draft"),
            "components": sorted(set(x for x in skus if x)),
        })

    return {
        "generator": config.APP_NAME,
        "asset_count": len(out_assets),
        "bundle_count": len(bundle_list),
        "bundles": bundle_list,
        "assets": out_assets,
    }


def write_manifest(db, out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.write_text(json.dumps(build_manifest(db), indent=2, ensure_ascii=False))
    return out_path


def write_crosswalk(db, out_path: Path) -> Path:
    out_path = Path(out_path)
    rows = []
    for row in db.all_assets():
        eff_type = db.effective(row, "asset_type") or row.get("ai_asset_type")
        rows.append({
            "legacy_filename": row["filename"],
            "legacy_path": row["path"],
            "design_uid": row["design_uid"],
            "product_sku": row.get("product_sku"),
            "side": row.get("side") or "",
            "set_code": row.get("set_code") or "",
            "asset_type": eff_type,
            "status": row.get("status"),
        })
    with open(out_path, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else
                            ["legacy_filename"])
        wr.writeheader(); wr.writerows(rows)
    return out_path
