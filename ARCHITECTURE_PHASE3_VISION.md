# KF Asset Manager — Phase 3 Specification: Vision (image checking, colour, AI names, style)

> Status: **SPECIFICATION for sign-off** — no code yet. Build phase-gated after approval.
> This is the first time the tool calls an external AI, so the integration boundary,
> cost control, and the "suggestions never become identity" rule are designed up front.

## 1. What you asked for, and the one distinction that shapes everything

You picked all four capabilities:

| # | Capability | Needs AI? | Cost |
|---|------------|-----------|------|
| 1 | Verify the image matches the catalogued design | **AI vision** | per-image API call |
| 2 | Extract real colours from the image | **No — local** | free, offline, deterministic |
| 3 | AI-suggested product names | **AI vision** | per-image API call |
| 4 | Style / aesthetic tags | **AI vision** | per-image API call |

The key realization: **colour extraction (2) does not need AI.** Dominant colours come from
the pixels themselves — a local image-processing pass (cluster the pixels, map to named
colours) is deterministic, free, runs offline, and re-runs identically. So it is built
first and separately. The other three (1, 3, 4) are genuine AI-vision work and share one
integration, one cost model, and one cache.

## 2. Architecture — vision is DERIVED, never identity

Every Phase 3 output obeys the same invariants the rest of the system already enforces:

- **Suggestions, never identity.** Nothing vision produces ever changes a `KF-…` ID, a
  SKU, a design key, or compatibility. It is *metadata and suggestions*.
- **Manual always wins, permanently.** An AI-suggested name is a *default the user can
  accept or replace*; a manual value wins and is never overwritten by a later pass —
  exactly the `display_title` rule from Phase 4, extended to names/tags/colours.
- **Cached by content hash.** Results are keyed by the asset's `sha256` (already computed),
  so re-running never re-spends on an unchanged image, and identical images share a result.
- **Versioned.** Each result records the `vision_version` and `model` used, so a later,
  better pass is comparable and re-runnable.
- **Confidence + review.** Low-confidence or mismatched results raise a review flag — this
  is the original Phase 3 purpose (surgically eliminate uncertainty), now extended.

## 3. The four capabilities in detail

**(2) Colour extraction — local, first.** For each face image: quantize to a small palette,
return the dominant colours as `{hex, percentage, named}` where `named` maps to a colour
vocabulary (the KF brand colours first — Navy/Gold/Ivory/Charcoal — then a general named
set). Stored as metadata; surfaced as Shopify tags/options and in reports. No AI, no cost.

**(1) Image-matches-design verification — AI.** Ask the vision model: does this image look
like the catalogued type/attributes (e.g. "an engineered curtain panel", "a repeat-pattern
fabric")? Returns a match confidence + short reason. Low confidence → review flag. This
catches mislabeled files, wrong-folder drops, and junk that slipped past the rules.

**(3) AI-suggested names — AI.** A short, descriptive customer-facing name suggestion
(e.g. "Botanical Damask"). Stored as a *suggestion*; the generated `Design N Type` default
stays until a human (or the suggestion, if you choose auto-accept) replaces it. Manual
override always wins.

**(4) Style / aesthetic tags — AI.** A small set of controlled tags (e.g. floral,
geometric, traditional, modern, minimal). Stored as business metadata; flow into Shopify
tags and faceted navigation later.

## 4. Cost & scale reality (must be designed in)

The full library is ~21,687 images. Three AI calls per image, naively, is tens of
thousands of API calls — real money and time. So the design is **surgical and controlled**:

- **Opt-in scope.** Vision runs only on an explicit scope (a folder, a product type, a
  limit, or "only assets currently needing review") — never the whole library by default.
- **One call per image, not three.** The three AI capabilities (1, 3, 4) are answered in a
  **single structured request** per image, not three separate calls.
- **Cache by hash.** Re-runs and duplicate images cost nothing.
- **Hard cap + dry-run.** A `--limit` and a `--dry-run` (counts calls and shows the prompt,
  spends nothing) so you always know the bill before it happens.

## 5. Decisions to confirm (my recommendations)

- **D1 — Provider + key.** Recommend **Claude vision via the Anthropic API** (strong at
  this, natural fit), behind a clean provider adapter so it can be swapped. **It needs an
  API key you supply on your machine**, and it costs per image. *Confirm: Anthropic API, and
  you'll provide the key?*
- **D2 — First scope.** Recommend proving it on a **small slice first** (e.g. 20–30 curtain
  designs), review the quality and the cost, then decide how wide to go. *Confirm small-
  slice-first.*
- **D3 — Colour vocabulary.** Recommend **KF brand colours first, then a standard named
  set**. *Confirm or supply your own colour list.*
- **D4 — Auto-accept names?** Recommend **suggestions stay suggestions** — they populate a
  `suggested_name` field; you accept into `display_title` in bulk or per-item. Names are
  customer-facing and worth a glance. *Confirm suggestions-not-auto-accept.*
- **D5 — Style tag set.** Recommend a **small controlled vocabulary** (≈10–15 tags) rather
  than free-form, so tags stay consistent and filterable. *Confirm, or give me your tag list.*

## 6. Storage (derived, never identity)

A new `vision_results` table keyed by `asset_id` + `sha256` + `vision_version`:
`suggested_name`, `style_tags` (JSON), `colours` (JSON: hex/pct/named), `match_confidence`,
`match_reason`, `model`, `analyzed_at`. Colours from the local pass live here too. Accepted
names flow into the existing `display_title`; tags/colours surface via business metadata.
None of it is identity.

## 7. Phased build (gated, after sign-off)

| Step | Scope | Needs your key? | Exit gate |
|------|-------|:---:|-----------|
| **3-a** | Local colour extraction → palette/hex/named, cached by hash, in reports | No | tests on sample images; colours in manifest |
| **3-b** | Vision provider adapter: one structured call, cache, `--dry-run`, `--limit`, cost guardrails | scaffold only (mock-tested) | mock tests; dry-run prints prompt + call count, spends nothing |
| **3-c** | The three AI analyses (match / name / style) via the adapter, stored as suggestions + confidence | **Yes** (you run real calls) | a 20-design real slice reviewed for quality + cost |
| **3-d** | Surface: suggestions/tags/colours into reports, manifest, Shopify export; review flags for mismatches; bulk-accept names | No | end-to-end on the slice |

## 8. What I can build & test vs what needs your machine

Honest boundary: I can build all four and fully test **3-a (colour)** and **3-b (the
adapter, via mocks)** here. The **real AI calls (3-c)** run on *your* machine with *your*
key against *your* images — I cannot (and should not) call an external AI with your library
from my build environment. So 3-c ships as working, mock-tested code plus exact commands
for you to run the first real slice; we review the results together.

## 9. What stays unchanged

Identity, Display IDs, SKUs, the v2.0 Source model, compatibility, naming rules — all
untouched. Phase 3 only *reads* assets to *produce derived suggestions and metadata*, with
manual override always winning. Fully consistent with the system-of-record principle.

---

### Recommendation

Approve the spec, and **start with 3-a (local colour extraction)** — it delivers real value
immediately, costs nothing, and needs no key — while you settle D1 (the API key/provider)
for the AI steps. Then 3-b scaffold, then a small real 3-c slice we review together before
spending at any scale.

---

## 3-b — Provider adapter (BUILT, no real calls)

The integration boundary for the AI steps is in place and fully mock-tested — it makes no
network call and needs no key.

**Modules.** `vision_provider.py` (the adapter) + `vision_ai.py` (planning + dry-run).

**Provider interface.** `VisionProvider.analyze(image_path, prompt) -> dict`. Two
implementations: `MockVisionProvider` (deterministic, offline, used by tests) and
`AnthropicVisionProvider` (reads `ANTHROPIC_API_KEY`; `available()` is key-gated; its
`build_request()` is a pure, tested payload builder, but `analyze()` is **intentionally
inert in 3-b and raises** — the real POST is added in 3-c).

**One call per image.** `build_analysis_prompt()` asks for match + name + tags in a single
structured request, so 3-c is one call per image, not three.

**Strict JSON response contract** (validated by `validate_response`):
```
{ "match": {"is_match": bool, "confidence": 0..1, "reason": str},
  "suggested_name": str,
  "style_tags": [ ... 0..4 from the controlled vocabulary ... ] }
```
Tags come from a fixed `STYLE_VOCAB` (~15 tags); anything outside it is rejected.

**Caching.** `needs_ai_analysis()` keys on `sha256` + `vision_version` + presence of a
stored `suggested_name`, mirroring the colour cache — so 3-c never re-spends on an
unchanged image, and the dry-run already reports cached-vs-to-call.

**Dry-run.** `python -m kf_asset_manager.vision_ai --db <db> --dry-run [--types …]
[--limit N] [--provider anthropic|mock] [--cost-per-call 0.01]` prints the selected image
count, cached count, would-analyse count, estimated calls, and estimated cost, plus a
sample prompt — and **sends nothing**. Missing key does not fail it.

**How 3-c plugs in (no rework):** implement `AnthropicVisionProvider.analyze()` to POST
`build_request(...)` to the Messages API and `json.loads` the reply; for each uncached
asset in scope, call it once, run `validate_response`, and store the result via the existing
`vision_results` columns (`suggested_name`, `style_tags`, `match_confidence`,
`match_reason`, `model`). A manual value always wins. Everything else — selection, caching,
cost, the prompt, the contract — is already built and tested here.
