"""Sprint 2.5 — Production Library Auditor (READ-ONLY).

Evaluates a real library against the current frozen model and emits reports. It never
renames, moves, or modifies any file, and introduces no new entity or architecture.
Everything here is measurement: naming conventions, rule coverage, duplicates, the
Mapping-Matrix special-case counts (SC1-SC4), and flat dumps of the built graph.
"""

import csv
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

from . import ingest, rules, config, display, vision_review

# tokens that trail a base artwork name (application / side / variant / composition)
_TRAIL = (r"(cush(?:ion)?\s*\d*|runner|table\s*cloth|tablecloth|left|right|pair|single|"
          r"D\d+|[ABLRC])")
_TRAIL_RX = re.compile(rf"[-_ ]+{_TRAIL}$", re.I)
_SET_RX = re.compile(r"^\(\d{1,2}-\d{1,2}\)\s*C\d+", re.I)


def _w(path, rows, header):
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(header)
        wr.writerows(rows)


def naming_signature(stem):
    """Skeletonise a filename stem into a convention signature, independent of the
    Rule Engine, so unknown conventions (e.g. P####) surface even when no rule matches."""
    s = stem.strip()
    if _SET_RX.match(s):
        return "(##-##) C#"
    prev = None
    while prev != s:                       # peel trailing application/side tokens
        prev = s
        s = _TRAIL_RX.sub("", s).strip(" -_")
    sig = re.sub(r"\d+", "####", s)
    return re.sub(r"\s+", " ", sig).strip() or "(empty)"


def _strip_to_base(stem):
    s = stem.strip()
    prev = None
    while prev != s:
        prev = s
        s = _TRAIL_RX.sub("", s).strip(" -_")
    return s.lower()


def _side_of(stem):
    m = re.search(r"[-_ ]([ABLR])(?:[-_ ]|$)", stem, re.I)
    return m.group(1).upper() if m else None


def generate_reports(db, root, out_dir, do_hash=True):
    root = Path(root)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    conn = db.conn

    # ---- 1. raw file walk: every file by extension (incl. AI/CDR/etc.) ----------
    ext_counter = Counter()
    all_files = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or "__MACOSX" in p.parts or p.name.startswith("."):
            continue
        ext_counter[p.suffix.lower().lstrip(".") or "(none)"] += 1
        all_files.append(p)
    total_files = len(all_files)

    # ---- 2. faces + per-file parse (naming, rule coverage, review) -------------
    groups = ingest.group_by_stem(ingest.iter_files(root))
    faces = [(face, srcs) for face, srcs in groups if face is not None]
    masterless = [srcs for face, srcs in groups if face is None]

    naming = Counter()
    naming_examples = defaultdict(list)
    rule_hits = Counter()
    rule_conf = defaultdict(list)
    unmatched = []
    review_rows = []
    parsed = {}
    for face, srcs in faces:
        res = rules.parse(face.name, face.parent.name)
        parsed[face] = res
        sig = naming_signature(face.stem)
        naming[sig] += 1
        if len(naming_examples[sig]) < 3:
            naming_examples[sig].append(face.name)
        rule_hits[res["rule"]] += 1
        rule_conf[res["rule"]].append(res["confidence"])
        is_unmatched = res["rule"] == "folder_fallback"
        if is_unmatched:
            unmatched.append((face.name, face.parent.name, sig))
        if res["needs_review"] or is_unmatched or (res["confidence"] or 0) < 0.5:
            reason = res["review_reason"] or ("no rule matched" if is_unmatched else "low confidence")
            action = ("add/extend a rule for this convention" if is_unmatched
                      else "verify classification" if res["needs_review"]
                      else "confirm low-confidence match")
            review_rows.append((face.name, reason, res["confidence"], res["rule"], action))

    # ---- 3. duplicate detection (content hash across ALL files) ----------------
    dup_asset_rows = []
    if do_hash:
        by_sha = defaultdict(list)
        for p in all_files:
            if p.suffix.lower() in ingest.ALL_EXTS:
                try:
                    by_sha[ingest.file_hash(p)].append(p)
                except Exception:
                    pass
        for sha, paths in by_sha.items():
            if len(paths) > 1:
                exts = {q.suffix.lower().lstrip(".") for q in paths}
                kind = "duplicate master" if exts & {e.lstrip(".") for e in ingest.MASTER_EXTS} else "same artwork, multiple names"
                dup_asset_rows.append((sha[:16], len(paths), kind, " | ".join(str(q.relative_to(root)) for q in paths)))

    # ---- 4. architecture metrics: SC1-SC4 + v2.0 Artwork Source model ----
    q = lambda s: conn.execute(s).fetchone()[0]
    # v2.0-b retired the two mechanisms that SC1/SC2 measured:
    #   * SC1 was the compatibility *bypass* (`from_derived`). Products are now realized
    #     from Artwork Sources, authorised at source creation — there is no bypass path.
    #   * SC2 was the product *discriminator*. Products of the same type on one design are
    #     now distinguished by their Source identity (source_id) — no artificial tiebreaker.
    # Both are therefore 0 by construction. SC3 (derived artwork) is NOT a smell — it is
    # real, and now modeled cleanly as Derived Sources, so it legitimately persists.
    sc1 = 0
    sc2 = 0
    sc3 = q("SELECT COUNT(*) FROM assets WHERE artwork_role='Derived'")
    sc4 = q("SELECT COUNT(*) FROM (SELECT pv.asset_id FROM product_variants pv "
            "JOIN products p ON pv.product_id=p.product_id GROUP BY pv.asset_id "
            "HAVING COUNT(DISTINCT p.product_type)>1)")

    # positive Artwork Source metrics (the clean replacement for the retired mechanisms)
    src_total = q("SELECT COUNT(*) FROM artwork_sources")
    src_derived = q("SELECT COUNT(*) FROM artwork_sources WHERE origin='Derived'")
    prod_via_derived = q("SELECT COUNT(*) FROM products p JOIN artwork_sources s "
                         "ON p.source_id=s.source_id WHERE s.origin='Derived'")
    multi_same_type = q("SELECT COUNT(*) FROM (SELECT design_id,product_type FROM products "
                        "GROUP BY design_id,product_type HAVING COUNT(*)>1)")
    src_metrics = (src_total, src_derived, prod_via_derived, multi_same_type)

    # ---- 5. estimated SC from filenames (what a P#### rule WOULD materialise) ---
    base_groups = defaultdict(list)
    for face, _ in faces:
        base_groups[_strip_to_base(face.stem)].append(face)
    est_sc1 = est_sc3 = est_sc2 = est_indep = 0
    for base, members in base_groups.items():
        cush = [m for m in members if re.search(r"cush", m.stem, re.I)]
        curtains = [m for m in members if not re.search(r"cush", m.stem, re.I)]
        dvars = [m for m in members if re.search(r"[-_ ]D\d+", m.stem, re.I)]
        if cush and curtains:                       # derived cushions on a curtain base
            est_sc3 += len(cush)
            est_sc1 += len(cush)
            if len({_side_of(c.stem) for c in cush if _side_of(c.stem)}) >= 2:
                est_sc2 += 1                        # sided -> >1 cushion product on one design
        if dvars:
            est_indep += len({re.search(r"[-_ ]D(\d+)", m.stem, re.I).group(1) for m in dvars})

    # ---- 6. design_type breakdown + compatibility -----------------------------
    dtype_counts = dict(conn.execute(
        "SELECT design_type, COUNT(*) FROM designs GROUP BY design_type").fetchall())
    counts = db.counts()
    variants = q("SELECT COUNT(*) FROM product_variants")

    # ---- 7. table dumps -------------------------------------------------------
    _dump_table(conn, "families", out / "families.csv", "family_id")
    _dump_table(conn, "designs", out / "designs.csv", "design_id")
    _dump_table(conn, "assets", out / "assets.csv", "asset_id")
    _dump_table(conn, "products", out / "products.csv", "product_id")

    # duplicate designs: same face content under two design ids
    dup_design_rows = conn.execute(
        "SELECT a1.design_id, a2.design_id, substr(a1.sha256,1,16) "
        "FROM assets a1 JOIN assets a2 ON a1.sha256=a2.sha256 AND a1.design_id<a2.design_id"
    ).fetchall()

    # ---- 8. write CSVs --------------------------------------------------------
    _w(out / "naming_report.csv",
       sorted([(sig, c, f"{100*c/max(1,len(faces)):.1f}%", " | ".join(naming_examples[sig]))
               for sig, c in naming.items()], key=lambda r: -r[1]),
       ["convention", "count", "percent", "examples"])
    _w(out / "needs_review.csv", review_rows,
       ["filename", "reason", "confidence", "matched_rule", "recommended_action"])
    _w(out / "unmatched_filenames.csv", unmatched, ["filename", "folder", "signature"])

    # orphaned masters: a .psd/.tif whose stem matches no face — usually a naming
    # mistake (e.g. P4206.tif that should be P4206-A.tif). The precise fix list.
    orphan_rows = []
    for srcs in masterless:
        for m in srcs:
            try:
                rel = str(m.relative_to(root))
            except ValueError:
                rel = m.name
            orphan_rows.append((m.name, rel, m.suffix.lower().lstrip(".")))
    _w(out / "orphaned_masters.csv", orphan_rows, ["filename", "path", "ext"])
    _w(out / "duplicate_assets.csv", dup_asset_rows, ["sha256_16", "count", "kind", "paths"])
    _w(out / "duplicate_designs.csv",
       [(display.short(a), display.short(b), sha) for a, b, sha in dup_design_rows],
       ["design_a", "design_b", "shared_sha16"])

    # ---- 9. rule_coverage.md --------------------------------------------------
    _write_rule_coverage(out / "rule_coverage.md", rule_hits, rule_conf, len(faces), unmatched)

    # ---- 10. library_summary.md ----------------------------------------------
    _write_summary(out / "library_summary.md", root, total_files, counts, variants,
                   dtype_counts, ext_counter, naming, naming_examples, len(faces),
                   masterless, (sc1, sc2, sc3, sc4), (est_sc1, est_sc2, est_sc3, est_indep),
                   len(review_rows), len(unmatched), len(dup_asset_rows), len(dup_design_rows),
                   do_hash, src_metrics, db.versions())

    # ---- 11. manifest.json — the versioned output contract (principle #5) -----
    import json as _json, time as _time
    manifest = {
        "generator": "KF Asset Manager",
        **db.versions(),                       # schema_version=2 (Artwork Source layer)
        "generated_at": _time.strftime("%Y-%m-%dT%H:%M:%S"),
        "root": str(root),
        "counts": {**counts, "variants": variants},
        "architecture": {
            "model": "Family -> Design -> Artwork Source -> Asset; Product maps to Sources",
            "sc1_compatibility_bypass": sc1,    # retired in v2.0-b
            "sc2_product_discriminator": sc2,   # retired in v2.0-b
            "sc3_derived_assets": sc3,          # legitimate, modeled as Derived Sources
            "sc4_asset_many_types": sc4,
            "artwork_sources_total": src_metrics[0],
            "artwork_sources_derived": src_metrics[1],
            "products_from_derived_source": src_metrics[2],
        },
    }
    (out / "manifest.json").write_text(_json.dumps(manifest, indent=2, ensure_ascii=False))

    # ---- 12. Phase 4-d: per-product SKU + title export (Shopify-stageable) -----
    from . import sku as _sku
    prod_rows = conn.execute("""SELECT p.product_id,p.design_id,p.product_type,p.source_id
                                FROM products p ORDER BY p.design_id,p.product_type,p.source_id""").fetchall()
    products_out = []
    sku_header = ("product_id", "design_id", "product_type", "product_sku", "title",
                  "variant_option", "variant_sku", "asset_id")
    sku_rows = []
    for p in prod_rows:
        # per-source (derived, sided) products carry their side in the base SKU; grouped
        # originals (curtain pair, fabric pattern) use the bare base.
        src_side = None
        if p["source_id"]:
            s = conn.execute("SELECT side FROM artwork_sources WHERE source_id=?",
                             (p["source_id"],)).fetchone()
            src_side = s["side"] if s else None
        base_sku = _sku.sku(p["product_type"], p["design_id"], side=src_side)
        title = db.title_for(p["product_id"])
        pvariants = []
        for v in conn.execute("""SELECT pv.asset_id,pv.variant_label,a.role,a.side
                                 FROM product_variants pv JOIN assets a ON pv.asset_id=a.asset_id
                                 WHERE pv.product_id=? ORDER BY pv.variant_label""",
                              (p["product_id"],)):
            vi = _sku.variant_inputs(v["role"], v["side"])
            vsku = _sku.sku(p["product_type"], p["design_id"], **vi)
            option = _sku.variant_descriptor(**vi) or "Default"
            vrow = {"option": option, "sku": vsku, "asset_id": v["asset_id"]}
            vis = db.get_vision(v["asset_id"])
            if vis and vis.get("colours"):
                vrow["colours"] = vis["colours"]
            pvariants.append(vrow)
            sku_rows.append((p["product_id"], p["design_id"], p["product_type"], base_sku,
                             title, option, vsku, v["asset_id"]))
        prod_entry = {"product_id": p["product_id"], "design_id": p["design_id"],
                     "product_type": p["product_type"], "sku": base_sku,
                     "title": title, "variants": pvariants}
        # 3-d.1: supplementary AI fields, additive only — `title` above is NEVER touched.
        prod_entry.update(vision_review.manifest_ai_fields(db, p["product_id"]))
        products_out.append(prod_entry)
    manifest["products"] = products_out
    (out / "manifest.json").write_text(_json.dumps(manifest, indent=2, ensure_ascii=False))
    _w(out / "skus.csv", sku_rows, list(sku_header))

    # ---- 13. Phase 3-d.1: AI review surface (read-only; never writes display_title) ----
    vision_review.write_ai_review_csv(db, out / "ai_review.csv")

    return {
        "files": total_files, "faces": len(faces), **counts, "variants": variants,
        "unmatched": len(unmatched), "needs_review": len(review_rows),
        "orphaned_masters": len(orphan_rows),
        "sc": (sc1, sc2, sc3, sc4), "sc_est": (est_sc1, est_sc2, est_sc3, est_indep),
        "out": str(out),
    }


def _dump_table(conn, table, path, id_col):
    cur = conn.execute(f"SELECT * FROM {table}")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["display"] + cols)
        for r in rows:
            d = dict(zip(cols, r))
            wr.writerow([display.short(d.get(id_col, ""))] + [d[c] for c in cols])


def _write_rule_coverage(path, rule_hits, rule_conf, total, unmatched):
    lines = ["# Rule Coverage\n", f"Faces parsed: **{total}**\n",
             "| Rule | Matched | % | Confidence (min / mean / max) |",
             "|------|--------:|--:|-------------------------------|"]
    for rule, c in sorted(rule_hits.items(), key=lambda x: -x[1]):
        cs = rule_conf[rule]
        lo, hi = min(cs), max(cs)
        mean = sum(cs) / len(cs)
        pct = f"{100*c/max(1,total):.1f}%"
        lines.append(f"| `{rule}` | {c} | {pct} | {lo:.2f} / {mean:.2f} / {hi:.2f} |")
    lines.append("")
    lines.append(f"## Filenames matching no rule ({len(unmatched)})\n")
    if unmatched:
        lines.append("Full list in `unmatched_filenames.csv`. First 50:\n")
        for name, folder, sig in unmatched[:50]:
            lines.append(f"- `{name}`  → signature `{sig}`")
    else:
        lines.append("None — every face matched a structural rule.")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_summary(path, root, total_files, counts, variants, dtype_counts, ext_counter,
                   naming, naming_examples, faces, masterless, sc, sc_est,
                   n_review, n_unmatched, n_dup_assets, n_dup_designs, do_hash,
                   src_metrics=None, versions=None):
    DT = ["repeat_pattern", "engineered_panel", "fixed_artwork", "placed_artwork",
          "set_piece", "unknown"]
    L = []
    L.append("# Library Summary — Production Audit\n")
    L.append(f"Root: `{root}`  \nMode: **read-only** (no files renamed, moved, or modified)")
    if versions:
        L.append(f"Schema: **v{versions['schema_version']}** (Artwork Source layer) · "
                 f"rules v{versions['rules_version']} · design-types v{versions['design_types_version']}\n")
    else:
        L.append("")
    L.append("## Totals\n")
    L.append("| Metric | Count |\n|--------|------:|")
    L.append(f"| Total files | {total_files} |")
    L.append(f"| Renderable faces | {faces} |")
    L.append(f"| Families | {counts['families']} |")
    L.append(f"| Designs | {counts['designs']} |")
    L.append(f"| Assets | {counts['assets']} |")
    L.append(f"| Products | {counts['products']} |")
    L.append(f"| Variants | {variants} |")
    if masterless:
        L.append(f"| Master-only groups (no face) | {len(masterless)} |")
    L.append("\n## Designs by type\n")
    L.append("| design_type | designs |\n|-------------|--------:|")
    for t in DT:
        if dtype_counts.get(t):
            L.append(f"| {t} | {dtype_counts[t]} |")
    for t, c in dtype_counts.items():
        if t not in DT:
            L.append(f"| {t} | {c} |")
    L.append("\n## File types\n")
    L.append("| Extension | Count |\n|-----------|------:|")
    for ext, c in ext_counter.most_common():
        L.append(f"| {ext} | {c} |")
    L.append("\n## Naming conventions discovered\n")
    L.append("| Convention | Count | % | Parsed by a rule? | Examples |")
    L.append("|-----------|------:|--:|:-----------------:|----------|")
    for sig, c in sorted(naming.items(), key=lambda x: -x[1]):
        ex = naming_examples[sig]
        parsed_ok = any(rules.parse(e, root.name)["rule"] != "folder_fallback" for e in ex)
        flag = "yes" if parsed_ok else "⚠ no"
        L.append(f"| `{sig}` | {c} | {100*c/max(1,faces):.1f}% | {flag} | {', '.join(ex)} |")
    L.append("\nConventions the Rule Engine does **not** yet parse appear in "
             "`rule_coverage.md` under *matching no rule* and in `unmatched_filenames.csv`.\n")
    L.append("## Compatibility (current design-type rules)\n")
    L.append("| design_type | primary | compatible products |\n|-------------|---------|---------------------|")
    for t in DT:
        spec = config.DESIGN_TYPES.get(t)
        if spec:
            comp = ", ".join(spec["compatible"]) or "— (own type)"
            L.append(f"| {t} | {spec['primary'] or '—'} | {comp} |")
    L.append("\n## Architecture metrics (Mapping Matrix SC1–SC4)\n")
    L.append("**Materialised** — what the Rule Engine + v2.0 Artwork Source model produced:\n")
    L.append("| Special case | Count | Status |\n|--------------|------:|--------|")
    L.append(f"| SC1 compatibility bypass | {sc[0]} | **retired (v2.0-b)** — products authorised by Sources |")
    L.append(f"| SC2 product discriminator | {sc[1]} | **retired (v2.0-b)** — products distinguished by Source identity |")
    L.append(f"| SC3 derived-artwork assets | {sc[2]} | legitimate — modeled as Derived Sources |")
    L.append(f"| SC4 one asset → many product types | {sc[3]} | — |")
    if src_metrics:
        st, sd, pvd, mst = src_metrics
        L.append("\n### Artwork Source model (the clean replacement)\n")
        L.append("| Metric | Count |\n|--------|------:|")
        L.append(f"| Artwork Sources total | {st} |")
        L.append(f"| of which Derived | {sd} |")
        L.append(f"| Products realized from a Derived Source | {pvd} |")
        L.append(f"| Designs with >1 product of a type (now distinguished by Source) | {mst} |")
        L.append("\n_SC1 and SC2 are 0 because the **mechanisms** they measured — the "
                 "`from_derived` bypass and the `product_discriminator` — were retired in "
                 "v2.0-b. The underlying derived artwork still exists (SC3) and is now "
                 "modeled cleanly as Derived Artwork Sources, each authorising its own "
                 "product without a bypass and distinguished by its own identity without a "
                 "discriminator._\n")
    L.append("\n**Estimated from filenames** — what the awkward archetype *would* produce "
             "once an engineered-panel (`P####`) rule is added (the original v2.0 signal):\n")
    L.append("| Estimated | Count |\n|-----------|------:|")
    L.append(f"| Derived cushions on a curtain base (→ derived Sources) | {sc_est[0]} |")
    L.append(f"| Bases with sided cushions L+R (→ two Cushion products) | {sc_est[1]} |")
    L.append(f"| Independent compositions (D#) → separate designs | {sc_est[3]} |")
    L.append("\n## Duplicate detection\n")
    if do_hash:
        L.append(f"- Duplicate content groups (same bytes, multiple names): **{n_dup_assets}** "
                 "→ `duplicate_assets.csv`")
    else:
        L.append("- Content hashing skipped (`--no-hash`).")
    L.append(f"- Designs sharing identical face content (possible duplicate designs): "
             f"**{n_dup_designs}** → `duplicate_designs.csv`")
    L.append("\n## Needs review\n")
    L.append(f"- Assets flagged for review: **{n_review}** → `needs_review.csv`")
    L.append(f"- Filenames matching no rule: **{n_unmatched}** → `unmatched_filenames.csv`")
    L.append(f"- Orphaned masters (PSD/TIF with no matching face): **{len(masterless)}** "
             "→ `orphaned_masters.csv` (likely naming mistakes to fix)")
    L.append("\n---\n")
    L.append("_Read-only audit. The graph is built on the **v2.0 Artwork Source** model "
             "(Family → Design → Artwork Source → Asset; Products map to Sources). SC1 and "
             "SC2 are retired — products are authorised by Sources and distinguished by "
             "Source identity, so no compatibility bypass or discriminator exists. SC3 "
             "(derived artwork) legitimately persists as Derived Sources. The estimated "
             "block is retained as a cross-check against the filename archetype._")
    Path(path).write_text("\n".join(L) + "\n", encoding="utf-8")
