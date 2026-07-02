# KF Asset Manager

The local **master asset database** for Karen Fabrics — the single source of truth
that every downstream system (Shopify, Kickflip, mockups, search, future AI) reads
from. Desktop-first, runs entirely on your machine. Nothing leaves your computer
except the *optional* vision-classification call to the Anthropic API.

> Where Ideas Become Fabric

---

## What it does (Phase 1)

- **Recursive ingestion** from any folder layout — sets, patterns, pieces, mixed.
- **Content-hash identity.** Each file is identified by its bytes, not its path.
  Reorganise or rename freely; IDs and metadata stay attached forever.
- **Asset-type detection** (Curtain Panel Set, Cushion, Table Runner, Table Cloth,
  Tapestry/Apparel Artwork, Pattern…) from folder + filename, all overridable.
- **Bundle detection.** Files sharing a set code (e.g. `C13`) become one bundle;
  components stay standalone-sellable and the bundle references them.
- **Design grouping.** Curtain panels A/B are one design / one product, two files.
- **Automatic colour extraction** with KF-aware palette naming.
- **Vision classification** (optional) → Style, Theme, Primary Motif, Occasion,
  Region, tags, and a selling-name suggestion, in KF voice.
- **AI is always a suggestion.** Every field stores an `ai_` value and a `manual_`
  value; the **effective value is `manual ?? ai`**. Re-scanning or re-classifying
  only writes `ai_` — your manual edits are permanent and always win downstream.
- **Status** per asset and per bundle: Draft / Approved / Archived.
- **Exports:** `manifest.json` (master record, effective values resolved) and
  `crosswalk.csv` (legacy filename → Design ID + Product SKU + status).

## Run it

```bash
pip install -r requirements.txt          # Flask + Pillow (anthropic optional)
export ANTHROPIC_API_KEY=sk-...           # optional, only for "Suggest with AI"
python -m kf_asset_manager                # opens http://127.0.0.1:5000
# or jump straight in:
python -m kf_asset_manager --root "/path/to/assets"
```

Then: **Scan** a folder → review the grid → edit anything (overrides are permanent)
→ set bundle selling names → mark Approved → **Export**. The DB lives at
`<root>/kf_assets.db`; exports go to `<root>/_kfam_export/`.

## Architecture

```
ingest ─► SQLite (kf_assets.db)  ◄─► review/edit UI (local Flask)
              │  source of truth
              ├─► manifest.json ─┐
              └─► crosswalk.csv  ├─► downstream (Phase 2+): Shopify, Kickflip, mockups
                                 ┘
```

- `config.py` — taxonomies, type rules, SKU codes, brand tokens.
- `db.py` — schema, stable-ID allocation, override-preserving writes.
- `ingest.py` — scan, hash, detect, colour, bundle + relationship building.
- `classify.py` — optional Anthropic vision + title/name suggestion.
- `exporters.py` — manifest + crosswalk from effective values.
- `app.py` / `templates/` / `static/` — local review & edit web UI.

## Roadmap

- **Phase 1 (this):** asset manager — ingest, classify, override, manifest, crosswalk.
- **Phase 2:** Shopify CSV export, Metaobject seeder, Product seeder.
- **Phase 3:** Kickflip linking, mockup generation, Flow/Imagen integration.

All of these read the manifest; the Asset Manager stays the source of truth.

## Production Library Auditor (read-only)

Evaluate a real library against the current model and emit reports — never modifies files:

```bash
python -m kf_asset_manager.build_graph --root "/path/to/02_Engineered_Panels" --report
```

Options: `--out DIR` (default `./reports`), `--no-hash` (skip duplicate hashing), `--db PATH`.
Writes `library_summary.md`, `naming_report.csv`, `rule_coverage.md`, `needs_review.csv`,
`duplicate_assets.csv`, `duplicate_designs.csv`, `unmatched_filenames.csv`, and flat dumps
`families.csv` / `designs.csv` / `assets.csv` / `products.csv`.
