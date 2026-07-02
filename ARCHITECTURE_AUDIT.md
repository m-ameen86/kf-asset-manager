# ARCHITECTURE_AUDIT.md

Audited against **Frozen Architecture v1.4**. Most recent phase first.

---

## ★ PHASE 3 CLOSED — see `ARCHITECTURE_ADR_PHASE3_CLOSURE.md`

Phase 3 (Vision: colour extraction, provider scaffolding, real execution, prompt tuning,
AI review, explicit acceptance) is formally closed as of the linked ADR. That document is
the authoritative record — decisions and rationale, verified production evidence
(including live confirmation against the real Shopify staging store), what was
deliberately deferred and why, lessons learned, and named prerequisites for the next
phase. It supersedes the phase-by-phase entries below as the summary of record for
Phase 3; those entries remain as the detailed build history.

**Numbering note:** "Phase 4" already refers to the completed Product Identity / SKU /
Manifest / Shopify Export milestone (below, predates Phase 3-c). **The next new phase is
Phase 5** — see the ADR's Prerequisites section before it substantively begins.

---

## Phase 3-d.2 (revised, right-sized) — Explicit AI Acceptance Workflow

**What changed?** Per the pre-build audit's scope revision: a single, explicit
accept-one-product primitive, not a bulk/threshold workflow. New `vision_accept.py`:
`accept_title(db, product_id, title)` is the **only** function that ever writes
`display_title`, and it does so exclusively via the existing `set_title()` — no new write
path. `accept_ai_suggestion(db, product_id, *, asset_id=None)` is a convenience wrapper
that **refuses** (no write) when a product's per-side AI suggestions conflict and no
`asset_id` is given, returning the exact options instead of silently defaulting to a
representative. `pending_review()` is a read-only list of AI-covered products still
awaiting a title decision (drops a product once accepted). A small, genuinely read-only
addition to `vision_review.py`, `product_ai_options()`, supplies the per-asset breakdown
needed to present a conflict choice. CLI: `--list` (read-only), `--show` (read-only),
`--accept-ai [--asset ID]`, `--accept-title "text"`. No confirmation prompt — this is a
free, local, fully reversible metadata write, unlike the paid vision-execution CLIs; the
CLI invocation itself, naming a specific product and title/asset, is the explicit action.

**Boundary compliance proven, not just designed:** identity/product/asset/source counts
proven byte-identical before and after any accept call; SKU generation proven unaffected
(same design → same SKU); the source `vision_results` row proven byte-identical after
acceptance (only `products.display_title` changes); manifest top-level keys proven to be
exactly the pre-existing set, with `title` correctly reflecting an accepted value through
the **unmodified** `title_for()` call already in `audit.py`; the Shopify exporter proven
to reflect an accepted title with **zero exporter code changes**, via its own unmodified
`title_for()` call. Source-inspected to confirm `vision_accept.py` never imports
`vision_provider`, `colour`/`vision_colour`, or `sku` — no AI/network path, no colour
path, no SKU-writing surface.

**Tests:** `tests_vision_accept` 42/42 — the core primitive, idempotency, the critical
conflict-requires-explicit-choice rule (including the refusal making zero writes and
correctly returning both real options), picking either side correctly and re-picking the
other overwriting correctly, rejection of an unknown/foreign asset_id, the no-AI-coverage
refusal, `pending_review()` correctly dropping an accepted product, every boundary proof
above, and full CLI-level coverage (`--list`, conflict refusal at exit code 2, successful
`--accept-ai --asset`, and `--accept-title`). `tests_vision_review` grew 45→48 for the new
`product_ai_options` helper. Full regression green
(20/43/12/16/8/11/20/22/39/20/17/17/36/28/29/48/11/27/42).

**Deliberately deferred** (per the audit): bulk-accept, confidence thresholds, batch
selection — none justified by the current real data volume (ten reviewed products). A
bulk step, if ever needed, should be a thin loop over `accept_title`/`accept_ai_suggestion`
later, the same pattern 3-c.2 used over 3-c.1.

---

## Schema Migration System (safety fix, pre-3-d.2)

**The gap.** `CREATE TABLE IF NOT EXISTS` does not add columns to a table that already
exists. Invisible while the database was rebuilt on every run; load-bearing the moment it
became preserved by default. Verified directly: opening a database predating the
`is_match`/`display_title`/`source_id` columns with current code threw
`OperationalError: no such column`.

**The fix.** A lightweight, automatic migration system in `model.py`: a `schema_migrations`
tracking table, a declarative `IdentityDB.MIGRATIONS` registry (table, column, column
definition), and `_run_migrations()` — run on every `IdentityDB.__init__`, before any other
code touches the database. Each entry checks column presence via `PRAGMA table_info`,
`ALTER TABLE … ADD COLUMN …` only if missing (SQLite correctly backfills a `DEFAULT` onto
existing rows; columns without one become `NULL`, which is already this codebase's
standard "not set" sentinel everywhere), then records itself as applied — idempotently,
whether or not the `ALTER` actually ran. Four migrations cover every additive column this
project has shipped to an already-existing table: `assets.source_id` (v2.0-a),
`products.source_id` (v2.0-b), `products.display_title` (Phase 4-c), and
`vision_results.is_match` (3-d.1 fix). `--fresh` behaviour is untouched — it still deletes
and rebuilds from nothing, on an explicit, documented, destructive opt-in only.

**Tests:** new `tests_schema_migration` 27/27 — hand-builds a genuinely old-schema
database (missing every migrated column, via raw `sqlite3`, not `IdentityDB`) populated
with a real `vision_results` row and product/asset data, proves opening it with current
code does not crash, every migration is recorded, every new column exists, the `DEFAULT`
backfill lands correctly, the AI result and all identity fields survive **byte-for-byte**,
`set_title` works normally afterward, and re-opening (twice) is fully idempotent with no
duplicate migration rows. Separately verified end-to-end through the **real
`build_graph` CLI** (not just direct `IdentityDB` calls) against the same old-schema
fixture: exit code 0, no crash, the AI data intact afterward — this is the actual
production path, proven, not just the unit-level one. Full regression green
(20/43/12/16/8/11/20/22/39/20/17/17/36/28/29/45/11/27).

**Documentation:** `DATABASE_LIFECYCLE.md` — explains why `audit.db` is non-disposable,
the preserved-by-default behaviour, exactly what `--fresh` destroys, and how the
migration system works and what it deliberately does not attempt (constraint changes,
which would need a full table rebuild, not a simple column add — none currently needed).

---

## CRITICAL FIX — build_graph no longer auto-deletes the database

**The bug.** `build_graph.py` silently deleted `audit.db` and rebuilt from scratch on
*every* run without an explicit `--db` — the routine command everyone actually runs. This
was safe when the database held only re-derivable identity data. It became a real data-loss
bug once `vision_results` existed: **paid AI analysis, local colour extraction, and manual
`display_title` overrides are NOT re-derivable from the image library alone.** The bug was
caught in production: a real 20-image AI batch (19 successful results, real spend) was
silently erased by a subsequent routine `--report` re-run, before Phase 3-d.1's
`ai_review.csv` was even generated — the CSV correctly showed `not_analyzed` for
everything, because by the time it ran, that was true. The `ai_review.csv` code itself
was not at fault.

**The fix.** Default behavior inverted: the database is now **preserved** across runs.
Re-importing is idempotent for identity (proven since Phase 1 — no duplicate rows, IDs
never change), so a routine re-run safely updates/extends identity data while keeping
`vision_results`, colour extraction, and `display_title` overrides intact. A new explicit
**`--fresh`** flag gives a genuine clean wipe when deliberately wanted, with the
destructive consequence spelled out in `--help` (which specific non-derivable data is
lost).

**Tests:** new `tests_build_graph_preserve` 11/11 — runs `build_graph.main()` for real
(not just `model.build_graph()`) to reproduce the exact real-world trigger: a normal run,
simulate real AI/colour/title-override data, run the *same* routine command again, and
prove vision_results + colours + is_match + the manual title override all survive, with
identity staying idempotent (no duplicate designs/products). A third run with `--fresh`
proves the wipe still genuinely works when asked. `--help` text checked for the destructive
warning. Full regression green
(20/43/12/16/8/11/20/22/39/20/17/17/36/28/29/45/11).

**Cost note:** the 19 real AI results lost to this bug are gone (a re-run would cost real
API spend); everything going forward is protected. Re-running the 20-image batch is
optional, at your discretion.

---

## Phase 3-d.1 — AI review surface (read-only, no display_title writes)

**What changed?** New `vision_review.py`: `product_ai_summary()` aggregates every asset
backing a product's variants into an explicit coverage status — `analyzed` (all assets
have a real AI suggestion), `partial` (mixed), `colour_only` (3-a ran, 3-c never did —
correctly NOT counted as analyzed), `not_analyzed` (no vision data at all). The
representative suggestion (name/confidence/reason) is the analyzed asset with the lowest
`asset_id`, deterministic; if analyzed assets on one product **disagree** on the suggested
name (e.g. curtain L vs R), `conflict=True` is raised rather than silently picking a
"winner." Style tags are the union across all analyzed assets, **rechecked against
`STYLE_VOCAB`** at surface time (defense in depth — proven by injecting an invalid tag
directly into the DB and confirming it's dropped). `write_ai_review_csv()` emits one row
per product with full honesty about coverage. `manifest_ai_fields()` returns four
supplementary keys (`ai_suggested_name`, `ai_style_tags`, `ai_match_confidence`,
`ai_review_status`) merged additively into each manifest product entry — `title` is never
touched. Both are wired into `audit.generate_reports()` alongside the existing manifest/
skus.csv output.

**Schema fix discovered and applied:** `is_match` (the model's actual match verdict) was
computed in 3-c.1 but never persisted — only `match_confidence`/`match_reason` were. Rather
than surface a fabricated proxy for it, `vision_results` gained an `is_match` column and
`execute_one`/`record_vision_ai` now store the real value. Purely additive (existing rows
read `is_match=NULL`, correctly distinct from a real True/False); no other 3-c behavior
changed — no batching, caps, confirmation, or retry logic touched.

**Rules honoured (verified, not just designed):** `display_title` appears in this module
only in docstrings/comments — zero write statements (grepped and confirmed). `set_title`/
`title_for` proven unchanged (manual override still wins, tested explicitly). Manifest
`title` field proven equal to `db.title_for()` even after AI fields are merged in. No SKU/
identity/colour-extraction/Shopify code touched. No API calls (module only reads existing
`vision_results`).

**Tests:** `tests_vision_review` 45/45 — every coverage state, conflict detection with a
deterministic representative, tag recheck dropping an injected invalid tag, `display_title`
provably untouched, CSV column completeness, honest empty-vs-not-analyzed distinction,
manifest additive-fields-only-never-title, existing variant/sku structure intact. Full
regression green (20/43/12/16/8/11/20/22/39/20/17/17/36/28/29/45), including with a real
API key present in the shell (no regression on the prior isolation fix).

**Explicitly NOT built (per scope):** no accept action, no bulk-accept, no threshold —
`display_title` can only change via the existing manual `set_title()`. That's Phase 3-d.2.

---

## Phase 3-c.3 — Prompt + vocabulary tuning (from real 20-image results)

**What changed?** Prompt/vocabulary only — no code path, no schema, no execution logic
touched. The real 20-image batch (19 ok, 0 failed) surfaced generic names ("Family Faces
Print Textile") and a style vocabulary with no fitting tag for kids/nursery patterns.
`build_analysis_prompt()` now adds explicit naming guidance: prefer 3–6 words, describe
the actual motif/scene, avoid generic "Textile"/"Print"/"Pattern" endings unless
unavoidable, use warm customer-facing décor language, and prefer kids/nursery wording +
tags when a design visually reads as a children's pattern. `STYLE_VOCAB` gained five
kids-safe commercial tags: `kids`, `nursery`, `playful`, `cartoon`, `novelty` (20 tags
total). The strict JSON contract is unchanged — `validate_response` still enforces the
same three keys, the same confidence range, and MAX_TAGS; only the *set* of allowed tags
grew. `VISION_VERSION` bumped to **2** (prompt/contract materially changed — the version
already existed precisely for this purpose; existing cached results remain valid under
their original version, future re-analysis uses v2).

**Scope honoured:** no real API calls; no batch-execution changes; no manifest/Shopify/
SKU/title/colour/identity mutation.

**Tests:** `tests_vision_ai` grew from 27 → **36** (word-count guidance present, generic-
ending discouragement present, customer-facing language present, kids/nursery nudge
present, all 5 new tags in `STYLE_VOCAB`, a kids-tagged response validates, all 4 new tags
together validate within MAX_TAGS, `novelty` validates alone, dry-run sample prompt
reflects the new guidance). Full regression green
(20/43/12/16/8/11/20/22/39/20/17/17/36/28/29).

**Real-world validation pending:** the tuned prompt/vocab is untested against a real image
— the next real batch run (any size within the existing 2–30 cap) is where we judge whether
naming and tagging actually improved. No new real-call code was added in this step.

---

## Phase 3-c.2 — Batch execution (2–30 images, hard-capped)

**What changed?** New `batch_execute()` in `vision_ai.py`, built entirely by **reusing**
`select_assets` / `needs_ai_analysis` / `preflight` / `execute_one` from 3-c.1 — no
duplicated logic. Hard-capped to `BATCH_MIN=2` / `BATCH_MAX=30`, enforced both in the
function (raises `ValueError` outside range) and the CLI (refuses out-of-range or missing
`--limit`; no override flag, per scope). Confirmation prints real counts computed at
call-time (selected / already cached / would call / estimated cost) before any spend. Each
image commits immediately via the existing `execute_one` → `record_vision_ai` path, so an
interrupted batch resumes cleanly with zero duplicate calls (proven in tests: kill after 2
of 5, resume calls exactly the remaining 3). End-of-batch summary reports ok / failed /
skipped(cached) / calls, plus **actual** accumulated input/output tokens from real `usage`
data (not the nominal estimate). Optional `--delay` adds a courtesy pause between calls.
Review CSV remains append-only across runs (proven: 2 rows from an interrupted run + 3 from
the resume = 5 total). `--limit 1` is untouched and still routes to the 3-c.1 smoke path.

**Scope honoured:** no manifest/Shopify/title/SKU/identity writes; no colour-extraction
changes; no new dependency; no real calls anywhere in tests or implementation.

**Tests:** `tests_vision_batch` 29/29 — the six required scenarios (cap enforcement,
missing-limit refusal, cached-skip count, partial-failure summary, interrupted-run +
clean resume, no-duplicate-calls-on-resume) plus confirmation-shows-real-counts,
decline-makes-zero-calls, actual-token-tally, and identity-unchanged. One 3-c.1 test
updated (`--limit 2` is now a valid batch size, not a refusal — `tests_vision_exec` now
asserts an out-of-range limit instead). Full regression green
(20/43/12/16/8/11/20/22/39/20/17/17/27/28/29).

**Ready for a real run:** `--execute --limit 20` (the approved first real slice; ceiling is
30) will show real selected/cached/would-call/cost, ask to confirm, then run — same
pattern as the successful 3-c.1 single-image smoke, just looped and capped.

---

## Phase 3-c.1 — Real single-image smoke execution

**What changed?** `AnthropicVisionProvider.analyze()` now performs ONE real Messages API
call (stdlib `urllib`, no new dependency): downscales the image (long edge ≤1568) in
`build_request`, POSTs with a timeout + simple transport retries (429/5xx/timeout),
fail-fast on auth (401/403), extracts text, strips ``` fences, parses + returns the
contract dict, and records token `usage`. New `vision_ai` orchestration: `preflight`
(key / model / sha256 / file exists — zero spend on failure), `execute_one` (retry once on
invalid-or-contract-failing JSON, then mark failed cleanly — no partial write), and
`smoke_execute` (cache-aware single image, confirmation prompt showing images/calls/cost/
model, immediate commit). New `record_vision_ai` upserts AI fields only (colours
preserved). New `--execute` CLI **forced to `--limit 1`** for this target; writes only a
`vision_results` row + a `vision_review.csv` line. The API key is never logged or persisted.

**Scope honoured:** one image only; no slice, no bulk; no manifest/SKU/title/colour/Shopify
mutation; identity/counts unchanged. Tests are fully mocked — no real call in CI (the auth
guard raises before any network).

**Tests:** `tests_vision_exec` 25/25 (fence/JSON parse, preflight incl. missing key/sha,
one-call success → one row + one CSV line, cache re-skip, retry-then-success, retry-
exhausted clean failure, auth-no-retry, decline-no-call, `--execute` requires `--limit 1`,
identity unchanged). Full regression green
(20/43/12/16/8/11/20/22/39/20/17/17/27/25).

**Next (not yet built):** 3-c.2 widen to the 20–30 image slice (batch loop over the same
execute path, hard cap + confirmation, real-cost tally).

---

## Phase 3-b — Vision provider adapter scaffolding (no real calls)

**What changed?** Two new modules, no schema change (the `vision_results` AI columns
already exist from 3-a). `vision_provider.py`: the `VisionProvider` interface,
`MockVisionProvider` (offline, for tests), `AnthropicVisionProvider` (key-gated;
`build_request()` pure + tested; `analyze()` intentionally **inert in 3-b, raises** — real
POST deferred to 3-c), the single structured `build_analysis_prompt()` (match + name +
tags in one call), the strict JSON response contract + `validate_response()`, and the
controlled `STYLE_VOCAB`. `vision_ai.py`: scoped selection, `needs_ai_analysis()` cache
(sha256 + vision_version), `plan()` + `dry_run()` (selected / cached / to-call / estimated
calls / estimated cost / sample prompt), and a `--dry-run` CLI.

**Scope honoured:** no real AI calls; no key required for tests or dry-run; missing key
does not fail; manifest untouched (additive-only behaviour from 3-a preserved); no change
to IDs, SKUs, product/design counts, or colour extraction.

**Tests:** `tests_vision_ai` 27/27 (prompt shape, contract validation incl. rejects,
mock provider, pure `build_request`, inert real `analyze`, dry-run makes ZERO calls, cost
estimate, cache-skip, no-key dry-run, identity unchanged). Full regression green
(20/43/12/16/8/11/20/22/39/20/17/17/27).

**3-c plug-in:** implement `AnthropicVisionProvider.analyze()` (POST + json parse), loop
uncached assets in scope, `validate_response`, store to `vision_results`. Everything else is
already built.

---

## Phase 3-a — Local colour extraction (no AI)

**What changed?** New `vision_results` table (derived metadata, keyed by asset, cached by
`sha256` + `vision_version`; AI fields left null until 3-c). New `colour.py`: dominant-
palette extraction via local quantization + nearest-named-colour mapping (KF brand colours
first — Navy/Gold/Ivory/Charcoal — then a general set). New `vision_colour.py` CLI:
opt-in, scopable (`--types`/`--limit`), cached (re-runs skip; `--force` re-extracts),
writes `colours.csv`. The manifest now carries per-variant `colours` when a colour pass has
run. No AI, no key, no cost.

**Identity-safe:** colours are metadata only; running the pass never changes any ID, SKU,
design, or count (proven in tests).

**Tests:** `tests_vision_colour` 17/17 (named mapping incl. KF brand, palette on synthetic
solids/two-tone, caching + force, storage/retrieval, colours.csv, manifest surfacing,
identity-unchanged). Full regression green (20/43/12/16/8/11/20/22/39/20/17/17).

**Next:** 3-b vision provider adapter (one structured call, cache, `--dry-run`, cost
guardrails — mock-tested) → 3-c real AI slice (your key) → 3-d surface name/tags/match.

---

## Shopify Staging Export — `shopify_export` (CSV import path)

**What changed?** New `shopify_export.py`: turns the built graph into a Shopify product-
import CSV. One Shopify product per KF product (curtain pair / each sided cushion / fabric
pattern); Handle = lower-cased base SKU; variants become option rows (`Side`:
Left/Right/Single; `Colour`: 01/02…; single-variant → Title/Default Title). Exports
**draft / unpublished** by default (staging-safe). Images left blank in v1 (products
first). CLI: `python -m kf_asset_manager.shopify_export --db audit.db --out products.csv
[--types Curtain Fabric] [--limit N] [--vendor …] [--status draft]`. The Asset Manager
stays the one-directional source of record — this only *emits an artifact* for manual
Shopify import.

**Also fixed** a cosmetic CLI summary bug: the Phase 4-d loop variable shadowed the
`variants` count, so `build_graph`'s recap printed a list instead of the integer. Renamed;
recap now prints `variants=<n>` correctly. (Data/exports were always correct.)

**Tests:** `tests_shopify` 17/17 (CSV structure, variant grouping, draft/unpublished,
sided-cushion handles, fabric colour options, type + limit filters). Full regression green
(20/43/12/16/8/11/20/22/39/20/17).

**Ready for staging:** generate the CSV, review it, import via Shopify Admin → Products →
Import as drafts; imagery is a planned second pass.

---

## Phase 4-c / 4-d — Display titles + manifest SKU/title export (Phase 4 COMPLETE)

**What changed?** Products gained a nullable `display_title` (manual override; NULL = use
the generated default). New methods: `generated_title` (e.g. `Design 19 Curtain`, and
`Design 19 Cushion (Left)` for a per-source sided product), `title_for` (override-or-
default), `set_title` (set/clear), `variant_title`. `sku.variant_descriptor` gives Shopify-
style option labels (Left / Right / Single / Colour 02). The auditor now emits a
`products` array into `manifest.json` — each product with its base SKU, title, and
variants (option + variant SKU + asset) — and a flat `skus.csv`. Per-source (derived,
sided) products carry their side in the base SKU (`KF-CSH-000019-L`); grouped originals
(curtain pair, fabric pattern) use the bare base.

**Manual title never touches identity or SKU** (proven in tests: override changes the
title, SKU unchanged; clearing falls back to the default).

**Tests:** `tests_phase4` 20/20 (descriptors, generated/override/clear titles, manifest
products, unique variant SKUs, side-specific cushion bases). `tests_sku` 39/39. Full
regression green (20/43/12/16/8/11/20/22/39/20).

**Phase 4 COMPLETE** — the system of record now generates the first real downstream
artifacts (SKUs + titles), and `manifest.json` is directly stageable into Shopify. The
next roadmap step (Shopify staging catalog) can consume the manifest as-is.

---

## Phase 4-a / 4-b — SKU generation + padding-insensitive resolver

**What changed?** New pure module `sku.py`: `product_type → code` map (Fabric → `FAB`),
`design_number()` (reads int/Display ID/internal ID/SKU), `variant_suffix()` deriving the
variant segment from the v2.0 model (curtain pair=base / L / R / SINGLE; cushion side from
Source; fabric colourway → `C0n`), and `sku_for()` / `sku()` composing
`KF-<TYPE>-<DESIGN(6)>-<VARIANT>`. `parse_query()` normalizes any input form. Added
`IdentityDB.resolve(query)` — padding-insensitive lookup accepting `19` / `D19` /
`000019` / `KF-D-000019` / a full SKU, returning the design (and product when the query
carries type/variant). All derived; no identity stored or changed.

**Decisions implemented (signed off):** D1 curtain pair = base SKU; D2 colourway `-C01`;
D3 length/material deferred; D4 (titles) is the next sub-step.

**Tests:** `tests_sku` 39/39 (type codes incl. Fabric→FAB, number parsing, zero-padding,
curtain/cushion/fabric variants, query parsing, resolver against a real build). Full
regression green (20/43/12/16/8/11/20/22/39).

**Next:** 4-c display titles (generated default + manual override), 4-d emit SKU+title into
`manifest.json` + auditor SKU column.

---

## v2.0-c — Finalization (schema_version 2, manifest, locked reporting)

**What changed?** `SCHEMA_VERSION` bumped to **2** (the Artwork Source layer), recorded in
the DB `meta` table and exposed via `db.versions()`. The auditor now emits a real
`manifest.json` from the identity model — the versioned output contract (principle #5) —
carrying schema/rules/design-type versions, counts, and the architecture metrics
(SC1/SC2 retired, Source totals). The `library_summary.md` header now shows the schema
version, and the footer wording was locked to the v2.0 final state (the stale "no
architectural change" footer removed). The legacy v0.6 `exporters.build_manifest` was
deliberately left untouched (Phase 5 migration) — the new manifest comes from the
identity model, not the disconnected legacy path.

**Tests:** `tests_v2b` extended to 20/20 (adds schema_version=2, manifest emitted,
manifest records schema_version 2 and SC1/SC2 = 0). Full regression green
(Phase 1 20, Phase 2 43, derive 12, audit 16, metadata 8, v2.0-a 11, v2.0-b/c 20).

**Artwork Source (v2.0) is COMPLETE.** Built phase-gated, proven on the real 894-file
curtain library (SC1/SC2 collapsed from 174/8 to 0/0), versioned, and documented.

---

## v2.0-b — Products realized from Artwork Sources (bypass + discriminator retired)

**What changed?** Products are now realized from Artwork Sources. The `products` table
dropped `product_discriminator`, `from_derived`, and `source_asset`, and gained
`source_id`; uniqueness moved to `(design_id, product_type, source_id)`. `ensure_product`
takes `source_id` / `derived`: a derived product is authorised by its Source (no
compatibility *bypass*), and distinct derived Sources yield distinct products (no
artificial *discriminator*). Original applications of a type group into one product
(a curtain's Left/Right panels are variants of one Curtain product, `source_id=''`).

**The two special cases are dissolved.** SC1 (compatibility bypass) and SC2 (product
discriminator) are **0 by construction** — the mechanisms they measured no longer exist.
The auditor was rewritten to report this honestly and to add a positive "Artwork Source
model" block (sources total / derived / products-from-derived-source / multi-same-type
designs now distinguished by Source). SC3 (derived artwork) legitimately persists — the
derivation is real and now modeled as Derived Sources.

**Identity preserved.** Opaque `KF-PRD` IDs unchanged; every product is realized and has
≥1 variant; compatibility still holds on the original path (an incompatible original
product like Tote-on-curtain is still refused).

**Tests:** `tests_v2b` 16/16 — columns physically retired, SC1/SC2 = 0 via the auditor,
P4186 still Curtain + 2 Cushion (grouped curtain with L/R variants; two cushions mapped
to two distinct Derived Sources by side), incompatible original refused, identity intact.
`tests_derive` updated to the Source model (12/12). Full regression green
(Phase 1 20, Phase 2 43, derive 12, audit 16, metadata 8, v2.0-a 11, v2.0-b 16).

**Ready for v2.0-c:** Yes (pending sign-off) — update the manifest `schema_version=2` and
finalize report wording; then re-audit the real catalogue to show SC1/SC2 = 0 at scale.

---

## v2.0-a — Artwork Source layer (foundation)

**What changed?** Added the `artwork_sources` table (opaque `KF-SRC` IDs) between Design
and Asset, plus `assets.source_id`. The import now creates one Source per asset — the
*application* of the artwork (Curtain Left, Cushion Right…) — recording origin
(Original/Derived), side, and, for derived applications, a `derived_from_source` link to
the same-side Original source. `counts()` now reports `artwork_sources`.

**Identity-preserving / additive.** Products are untouched in this step (dual-run): the
existing Curtain + derived Cushion products remain exactly as before. No Family / Design
/ Asset / Product ID changes. The bypass and discriminator are *not* retired yet — that
is v2.0-b.

**Compliance.** All five principles hold: `KF-SRC` is opaque; SoT one-directional;
rule engine now also assigns an application; confidence/review untouched; `schema_version`
will bump in v2.0-c when products move onto Sources.

**Tests:** `tests_v2a` 11/11 — Sources created, opaque IDs, P4186 → 4 sources
(Curtain L/R + derived Cushion L/R), derived cushion links to its origin Curtain source,
every asset linked to a source, and the existing product structure proven unchanged.
Full regression green (Phase 1 20, Phase 2 43, derive 12, audit 16, metadata 8).

**Ready for v2.0-b:** Yes (pending sign-off) — map products onto Sources and retire the
`from_derived` bypass + `product_discriminator`, proving SC1 & SC2 → 0.

---

## Phase 2 — Versioned Rule Engine

**What changed?**
Added `rules.py`: an ordered, data-driven set of named parsing rules carried with a
`RULES_VERSION`, plus a normalising engine (`parse`) that returns a canonical result
(asset type, design type, set/family code, side, piece, `design_variant`, flags,
confidence, `design_key`). The model's classification now calls the engine instead of
the placeholder parser; design_type is now determined by the engine (filename-first),
with the folder used only as a low-confidence fallback. Assets gained provenance
columns: `match_rule`, `confidence`, `needs_review`, `design_variant`, `legacy_ab`.
`meta` now records `rules_version`.

**What assumptions were made?**
- Confidence is emitted per rule now; the *combined* multi-signal score (vision +
  metadata + folder) and the configurable review threshold are Phase 3.
- Three rules cover the present library (`batched_set`, `flat_curtain`, `fabric_code`);
  new conventions are added as data entries, not code.

**Does it remain compliant with v1.4?**
Yes. Implements the locked naming policy exactly: legacy curtain `A/B → L/R` (frozen),
legacy non-curtain `A/B` flagged `legacy_ab` (backward-compatible only), new variants
via `D1/D2/D3` (distinct designs), and `A/B` never produced for new assets. Identity
layer unchanged; no business meaning entered any ID.

**Any technical debt introduced?**
- `ingest.parse_name` (legacy parser) is now unused by the model but still present for
  the legacy v0.6 UI; remove during the Phase 5 UI migration.
- `fabric_code` rule is provisional and will be refined against real fabric filenames.

**Recommended improvements before next phase?**
- Phase 3 should feed `legacy_ab` and low-confidence/needs_review assets into the
  review queue surfaced to the user, and add the vision signal to lift `UNK`/fallback.

### ✅ Complies with v1.4
- Rule Engine is versioned (`RULES_VERSION`), data-driven, core untouched by new rules.
- Naming policy enforced: A/B legacy-only, D1/D2/D3 canonical for new variants.
- design_type now filename-authoritative with folder fallback (per v1.4 priority).
- Identity model unchanged; relationships intact.

### ⚠ Deviations (إن وجدت)
- None. Full confidence *combination* (vision/metadata) is deferred to Phase 3 by
  design, not a deviation.

### 📝 Decisions made
- Rule confidences: batched_set 0.95, flat_curtain 0.90, fabric_code 0.80,
  folder_fallback 0.40. Provisional; finalised with the Phase 3 threshold.
- `legacy_ab` boolean marks any A/B parsed by a legacy rule, so generation guards
  (Phase 4) can refuse to emit A/B for new assets.

### 🔄 Open questions
- Real fabric/pattern filename conventions, to harden the `fabric_code` rule.
- Where exactly the review threshold sits (Phase 3, configurable).

### 🚀 Ready for next phase: **Yes** (pending your sign-off)

Tests: Phase 2 **27/27** (`python -m kf_asset_manager.tests_phase2`); Phase 1 regression
**20/20**. Sample validation: engine-driven graph correct, `rules_version` recorded,
D-variants distinct, legacy A/B flagged, 0 unexpected reviews.

---

## Phase 1 — Internal Identity + Relationships

---

## Architecture Verification

**What changed?**
A new identity layer (`model.py`) was added: a normalized SQLite schema with four
entities — `families`, `designs`, `assets`, `products` — plus a `product_variants`
link table, four independent ID counters, and a `meta` table carrying
`schema_version` and `design_types_version`. Designs now carry `design_type`,
`primary_product`, and `compatible_products`, and product creation is
**compatibility-enforced**. A relationship-graph builder (`build_graph`) walks a
folder and mints the entities with foreign keys. The legacy v0.6 single-table modules
were left untouched and still run; this layer is additive and headless for now.

**What assumptions were made?**
- Grouping for *this phase* is derived from the existing v0.6 parser (`parse_name`,
  `detect_type`). That parser is a placeholder here and is replaced wholesale by the
  versioned Rule Engine in Phase 2 — the identity model does not depend on how
  grouping is computed, only that a stable grouping key is supplied.
- Asset natural key = content hash; Design natural key = grouping key; Family natural
  key = set code. These are internal reconciliation keys for idempotent re-scans, not
  identities, and are never exported.
- Each design backs exactly one product (1:1), per the v1.0 model.
- Linked masters (TIF/PSD) attach under their face asset and receive no Asset ID.

**Does it remain compliant with v1.0 architecture?**
Yes, and v1.1 amends the model to **Design→Products (1:N)** per your direction. All four
ID types are opaque (`KF-{ENTITY}-NNNNNN`), minted from independent counters, with no
type/side/family/season meaning encoded. Relationships are carried by foreign keys,
never by shared numbers. A design may now back multiple products via the
`products` table keyed on `(design_id, product_type)`.

**Any technical debt introduced?**
- Two persistence layers coexist (legacy v0.6 tables + new identity tables) until the
  UI migration in Phase 5. Intentional and time-boxed.
- `source_files` (linked masters) is stored as JSON on the asset row rather than a
  normalized `sources` table. Acceptable for now; normalize later only if masters need
  to be queried independently.
- Provisional `variant_label` (Left/Right/Pair/Cushion A…) is set here for relationship
  demonstration; final variant + SKU logic is Phase 4.

**Any recommended improvements before the next phase?**
- None blocking. Phase 2 should make the grouping-key derivation an output of the Rule
  Engine so the placeholder parser can be removed entirely.

---

## ✅ Complies with v1.0
- Internal IDs are opaque, immutable, independent counters, no business meaning.
- Entity-type prefixes only (`FAM`/`D`/`AST`/`PRD`) — not business metadata.
- Relationships via foreign keys; numbers across layers do not match by design.
- Asset identity = content hash (stable across renames/moves).
- Masters linked under face asset, no own ID.
- `schema_version` + `design_types_version` recorded.
- Design→Products is 1:N, gated by per-design compatibility.
- Re-scan is idempotent and ID-preserving (verified by automated test).

## ⚠ Deviations (إن وجدت)
- None from the frozen model. Grouping AND design-type are currently derived
  provisionally from the legacy parser + folder name (a known, temporary stand-in
  scheduled for replacement by the Rule Engine + confidence layer in Phases 2-3) —
  this affects *classification accuracy*, not the identity model or the enforcement
  mechanism, both of which are final.

## 📝 Decisions made
- **Design ↔ Products is 1:N** (amended from 1:1), gated by compatibility.
- **Design-type compatibility** is rule-based (allowed / blocked / conditional /
  requires_transformation / requires_review); initial implementation uses allowed/not,
  and the JSON field accommodates richer rules with no schema change later.
- Official `design_type` taxonomy: `repeat_pattern`, `engineered_panel`,
  `fixed_artwork`, `placed_artwork`, `set_piece`.
- **Family** is a deliberate coordinated visual collection — not a category, season,
  or marketing grouping; standalone designs have no Family.
- **`source_library`** added as optional asset metadata (Legacy / Imported / AI
  Generated / Customer Upload / Internal Design Team); does not affect identity.
- Scan creates the design's **primary** product; other compatible products downstream.
- Family is created only when a set code exists; standalone items have `family_id = NULL`.
- `source_files` kept as JSON on the asset for this phase.

## 🔄 Open questions
- Variant vocabulary (Pair/Left/Right/Single/Cushion A…) to be finalized in Phase 4.
- Authoritative `design_type` determination (vs. the provisional folder/filename
  inference used here) lands with the Rule Engine + confidence layer in Phases 2-3.

## 🚀 Ready for next phase: **Yes** (pending your sign-off)

Tests: **20 / 20 passed** (`python -m kf_asset_manager.tests_phase1`), including
1:N, compatibility-enforcement, placed_artwork taxonomy, and source_library checks.
Architecture frozen at **v1.4** (final contract).
