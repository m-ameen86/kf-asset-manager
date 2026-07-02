# KF Asset Manager — Backlog (tracked, non-gating)

> **Fixed:** `build_graph` used to silently delete `audit.db` on every routine run,
> erasing paid AI vision results, colours, and manual title overrides. Now preserved by
> default; use `--fresh` for a deliberate clean wipe. See `ARCHITECTURE_AUDIT.md`.
>
> **Fixed:** schema evolution had no migration path — `CREATE TABLE IF NOT EXISTS` cannot
> add columns to an already-existing table, which became load-bearing the moment the
> database started being preserved. A lightweight automatic migration system now runs on
> every database open; proven against a real old-schema database with real AI data intact
> afterward, through both the unit-level and full CLI path. See `DATABASE_LIFECYCLE.md`.

Items surfaced by the production audit that do **not** block the v2.0 Artwork Source
decision. Ordered by priority.

## Architecture
- [x] **v2.0 — Artwork Source layer. COMPLETE.** Spec
  (`ARCHITECTURE_V2_ARTWORK_SOURCE.md`), built phase-gated and proven on production data:
  v2.0-a (table + KF-SRC + Sources into import), v2.0-b (products from Sources;
  `from_derived` bypass + `product_discriminator` retired; SC1/SC2 → 0 on the real
  894-file library), v2.0-c (schema_version=2, manifest.json, locked reporting).
- [x] **Phase 3 — Vision. FORMALLY CLOSED.** See `ARCHITECTURE_ADR_PHASE3_CLOSURE.md` for
  the authoritative record: decisions, verified production evidence (real Shopify
  push confirmed live), deferred work, lessons learned. **The next new phase is Phase 5**
  (Phase 4 already refers to the completed Product Identity/SKU/Manifest/Shopify Export
  milestone) — see the ADR's Prerequisites section before it substantively begins.
- [x] **Phase 4 — Derived SKU + display title + manifest. COMPLETE.** SKU generator,
  padding-insensitive resolver, display titles (generated + manual override), and
  manifest/`skus.csv` export. Spec: `ARCHITECTURE_PHASE4_SKU.md`. All four sign-off
  decisions implemented (pair=base, `-C0n` colourway, length deferred, `display_title`).
- [ ] **Phase 5 — Review UI migration** onto the new identity model.

## Naming / Rule Engine
- [x] **Fabric naming rules. DONE (rules_version 3).** Pattern = design, colourway =
  variant; parser accepts bare `####`, `G####-##`, `####-##`, legacy `####_Name`. Canonical
  standard documented in `FABRIC_NAMING.md`.
- [ ] **Tapestry naming rules.** Classify by folder works; a filename convention is not yet
  defined — needs representative tapestry filenames to design the rule.
- [ ] **Naming-standard normalisation policy.** The `P` family alone has 4 spellings
  (`P4116`, `P  4011`, `P4116-V2`, `P4124-2`). Decide whether to normalise to one
  canonical form at import vs. parsing every legacy spelling forever.

## Library hygiene (read-only audit found; user to action)
- [ ] **Fabric folder cleanup.** Remove non-catalogue noise from `Fabrics/`:
  `*-topaz-upscale-*` (AI upscaler outputs), `WhatsApp Image *` (chat downloads),
  `flag copy.png` / `flags2-02 copy.png` (stray copies). Not catalogue assets.
- [ ] **3 orphaned masters.** PSD/TIF with no matching face — see latest
  `orphaned_masters.csv`. Rename to match their face, or remove if genuinely stray.

## Scale-up
- [~] **Shopify staging catalog.** `shopify_export` produces a Shopify product CSV
  (draft/unpublished) — built and tested. Remaining: choose the staging scope, import via
  Shopify Admin, then a second pass for imagery (CSV needs image URLs; products-first for
  now).
- [ ] **Full-catalogue import.** Promote remaining types into Catalog-Ready
  (per the technical-type folder layout) and re-audit at full scale.

## Prerequisites for Phase 5 (from the Phase 3 closure ADR — `ARCHITECTURE_ADR_PHASE3_CLOSURE.md`)
- [ ] **Decide the standing Shopify sync path** — CSV-staging vs. direct API vs. both,
  with one canonical, plus real sync-state tracking if ongoing use is expected. Both paths
  are now proven working (CSV import and a live direct-API title push were each verified
  against the real Karen Fabrics Staging store); neither is yet decided as authoritative.
- [ ] **Backup strategy for `audit.db`** — still absent; it now holds non-derivable, paid
  AI data with zero redundancy.
- [ ] **Legacy v0.6 code disposition** — remove or clearly quarantine (`app.py`, `db.py`,
  old `ingest.py`/`exporters.py`/`classify.py`, `templates/`, `static/`) before the
  codebase grows further around it.
- [ ] Whatever Phase 5 turns out to be, scope it against real evidence (the same
  discipline used to right-size 3-d.2), not the largest plausible version of the idea.
