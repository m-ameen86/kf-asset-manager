# Karen AI Platform — Phase 3-d.2 Pre-Build Audit

> Status: **AUDIT ONLY.** No code written, no implementation prompts included. This
> document re-examines whether 3-d.2 is still the correct next milestone before auditing
> its implementation — the prior recommendation is not assumed, it is re-tested.

---

## First Question: Is 3-d.2 still the highest-ROI milestone?

**Yes — re-confirmed, not just restated — with one important scope correction below.**

Working through each named alternative on its own merits, not by elimination:

- **Hero Image Pipeline / Google Flow Integration / Media Generation Pipeline** — these are
  three faces of the same open question: is a generated image a `Derived` Artwork Source
  of an existing design, or a new asset class outside the Design/Source model entirely,
  built for marketing rather than product identity? That question has not been answered
  deliberately, and none of these should start until it is — starting now would mean
  building on a decision that hasn't been made. There is also no generation-capable
  provider yet; only the analysis adapter exists. Real new cost, real new governance
  surface, no current usage pressure. Lower ROI, higher risk, right now.
- **Collection Intelligence** — a `collection`/`theme` tagging substrate already exists
  in Business Metadata, but no automation sits on top of it, and nothing in current usage
  suggests this is an active pain point. Legitimate future work; no urgency signal today.
- **Duplicate Detection** — genuinely cheap (exact-hash detection is already built,
  just under-used because routine runs pass `--no-hash`) and worth doing, but it isn't
  blocking anything else and carries no sequencing risk either way. Fine to defer without
  cost.
- **Market Intelligence** — no foundation beyond a tagging dimension; a wholly new,
  externally-fed subsystem. Clearly premature.
- **AI Publishing** — this is not a peer alternative to 3-d.2, it is **gated by it**.
  Publishing needs something human-approved to publish. There is currently no mechanism
  by which an AI suggestion becomes an approved product fact other than a person manually
  invoking a low-level method. Building publishing automation before that exists would be
  building the riskiest capability in the entire roadmap on top of the platform's single
  least-finished piece of plumbing. This alternative actively argues *for* 3-d.2, not
  against it.

**The concrete, current-state argument for 3-d.2**, beyond the architectural reasoning:
there is now real, reviewed, good-quality AI output sitting unused. The second real batch
produced 20 successful analyses across 10 curtain products, with confidence consistently
0.85–0.97 and names that concretely improved after the 3-c.3 tuning. That data has a real
reviewer (you) who has already looked at it and formed a judgment on quality. Right now,
the only way to act on that judgment is a hand-typed Python one-liner calling `set_title()`
directly. That is a genuine, present gap, not a hypothetical one — which is a stronger
justification than any of the alternatives above currently have.

**The scope correction:** the milestone as originally framed risks being over-built for
the data volume that actually exists. Ten products currently have AI suggestions, eight of
which conflict between their two sides. That does not yet justify bulk-accept machinery,
confidence thresholds, or batch UX — it justifies a single, safe, explicit "accept this
one product's suggestion" action, built the same way every other phase in this project has
been sequenced: the smallest safe primitive first (3-c.1 before 3-c.2), proven, then
widened only if real volume demands it. This distinction is developed fully in Sections
3–5 below.

---

## 1. Current State

`vision_results` holds real AI output for 10 curtain products (20 assets), each with a
`suggested_name`, `style_tags`, `match_confidence`, `match_reason`, and (since the 3-d.1
fix) a real persisted `is_match`. `vision_review.py` correctly aggregates this to the
product level, distinguishing `analyzed` / `partial` / `colour_only` / `not_analyzed`
coverage and flagging `conflict=True` when a curtain's two sides disagree — which, in the
real data, is 8 of the 10 analyzed products. `display_title` already exists as a column,
with `title_for()` (override-or-generated-default) and `set_title()` (the only write path,
proven idempotent and identity-safe since Phase 4-c) both fully built, tested, and now
schema-migration-safe on any preserved database. **What does not exist is anything between
"a human looks at `ai_review.csv`" and "`set_title()` gets called."** That gap is the
entirety of what 3-d.2 needs to fill.

---

## 2. Risks

**Critical** — none identified. Every piece 3-d.2 would touch (`set_title`, `title_for`,
`vision_review`) is already built, tested, and proven safe. There is no new external
dependency, no new identity concern, no new schema need.

**Major**
- **Silent conflict resolution.** If an accept action defaults to "just use the
  representative suggestion" without requiring the reviewer to see and choose between
  disagreeing names, it would quietly resolve a genuine disagreement (8 of 10 real cases)
  as if there were none. This is the single most important behavioural requirement for
  the implementation: **when `conflict=True`, the accept action must require an explicit
  choice, not default silently.**
- **Product-level vs. asset-level naming ambiguity**, if not stated explicitly up front.
  This is already resolved by the existing architecture, not something 3-d.2 needs to
  invent: a *grouped* product (a curtain pair, a fabric pattern — `source_id=''`) has
  exactly one title slot, so conflicting per-side suggestions must be resolved to a single
  choice at accept time. A *per-source* product (a sided cushion) already has its own
  independent title slot per side, so it cannot conflict with itself — and indeed, in the
  real data, every conflict occurred on a grouped curtain product, never on a sided
  cushion, which confirms this framing is already correct rather than needing new design.

**Minor**
- **Confidence handling** should inform the reviewer, not gate them. A hard threshold
  that blocks acceptance below some confidence value would duplicate judgement the human
  reviewer is already exercising by looking at `ai_review.csv`, and adds real complexity
  for no current benefit at ten products. Surfacing confidence prominently at accept time
  is sufficient; a hard gate is not warranted yet.
- **Partial coverage acceptance.** A product with only one side analysed should still be
  acceptable — there is a real signal — but the action should make the partial nature
  visible at the moment of acceptance, so a reviewer doesn't mistake one-sided confidence
  for full-coverage confidence.
- **Duplicate/repeat acceptance.** Re-accepting an already-accepted suggestion should be a
  safe no-op. This falls out for free from `set_title()` already being an `UPDATE`, not an
  `INSERT` — worth stating as a proven property, not a new mechanism to build.

**Observation**
- **Future maintainability favours a single, small primitive over a broad workflow.**
  Building one well-tested "accept this one product's chosen title" action first — and
  deferring bulk-accept or threshold-based auto-selection until real catalogue-wide volume
  actually demands it — mirrors exactly how 3-c.1 preceded 3-c.2, and keeps the one new
  write path this milestone introduces small enough to fully reason about.
- No hidden coupling was found. The natural implementation surface (a thin CLI/function
  layer over `vision_review.product_ai_summary()` for the decision and `set_title()` for
  the write) touches no other subsystem.

---

## 3. Findings

**What already exists and is directly reusable:** the entire read side
(`product_ai_summary`, `ai_review.csv`, manifest AI fields) and the entire write side
(`set_title`, `title_for`, the manual-override-always-wins guarantee, now schema-migration
-safe). Nothing about identity, SKU generation, the vision pipeline, or Shopify export
needs to change for 3-d.2 to exist.

**What is missing:** only the connective layer — an explicit action that takes a specific
product and a specific chosen title (the AI suggestion, a reviewer's edited version, or a
manually written one) and calls `set_title()`, with the conflict case forcing an explicit
choice rather than a default. That is the entire net-new surface.

**Hidden coupling:** none found. This is a genuine strength of the existing design — the
accept/reject decision is fully decoupled from SKU, manifest, and Shopify code, all of
which already read `title_for()` and will pick up an accepted change automatically, with
no code of theirs needing to know acceptance happened.

**Reuse:** total. This milestone, correctly scoped, adds no new table, no new column, and
one new thin module reusing three already-proven functions.

---

## 4. Recommendation

**Approved — with a scope revision, not a rejection.**

Build a single, explicit **accept-one-product** primitive first: given a product and an
explicitly chosen title, write it via the existing `set_title()`; require an explicit
choice (not a silent default) whenever `conflict=True`; surface confidence and coverage at
the moment of the decision without gating on them. **Defer bulk-accept, confidence
thresholds, and batch selection** — none are justified by the current data volume (ten
products), and building them now would be scope ahead of evidence, which is exactly the
discipline this project has otherwise followed carefully at every prior phase. If
catalogue-wide AI coverage later grows enough to make one-at-a-time acceptance genuinely
impractical, a bulk step can be added later as a thin loop over this same primitive — the
same pattern 3-c.2 used over 3-c.1.

This is not "audited further" — the read/write substrate is already fully proven and
there is nothing left to investigate before building. It is not "rejected" — the gap is
real and current. It is "approved, right-sized."

---

## 5. Acceptance Criteria

- No write to `display_title` ever happens except through the existing `set_title()` —
  no new write path, no bypass.
- Acceptance is always an explicit action naming a specific product and a specific chosen
  title string — never automatic, never inferred silently from confidence or recency.
- When a product's `conflict` status is `True`, the action must require the reviewer to
  explicitly select which suggestion (or supply their own text) — refusing to proceed on
  an unqualified "accept" for a conflicting product.
- `title_for()`'s existing override-or-default behaviour is provably unchanged before and
  after this milestone (regression, not just new tests).
- Product IDs, Design IDs, Asset IDs, and Family IDs are never read for writing and never
  change as a result of any accept action.
- No SKU is generated, computed, or changed by this milestone.
- Manifest structure gains no new keys and loses none — the manifest already reflects an
  accepted title automatically via the existing `title_for()` call, with zero code changes
  needed there.
- No Shopify export code is modified — the exporter already calls `title_for()` and will
  reflect an accepted title on its next run, unmodified.
- Accepting an already-accepted product a second time is a proven no-op (idempotent,
  inherited from `set_title()`'s `UPDATE` semantics).
- Full existing regression (all suites, currently 18 files / 500+ assertions) remains
  green; new tests are added for the accept primitive and the conflict-requires-explicit-
  choice rule specifically.
- No real API call is made or required by this milestone — it operates entirely on
  already-collected `vision_results` data.

---

## 6. Architectural Boundaries — must NOT be modified

- **Identity** (`families`, `designs`) — untouched.
- **Artwork Source** (`artwork_sources`) — untouched.
- **SKU generation** (`sku.py`) — untouched; SKUs are never a function of title.
- **Vision prompts** (`vision_provider.py`'s `build_analysis_prompt`) — untouched; no
  prompt or vocabulary change of any kind.
- **Vision cache** (`sha256` + `vision_version` keying, `needs_ai_analysis`) — untouched;
  acceptance reads already-cached results, it does not trigger or alter caching.
- **Colour extraction** (`colour.py`, `vision_colour.py`) — untouched.
- **Product IDs, Design IDs, Asset IDs** — never generated, never re-minted, never
  reused by this milestone.
- **Shopify export behaviour** (`shopify_export.py`) — no code change; its existing,
  unmodified call to `title_for()` is what naturally picks up an accepted title on a
  future run, which is a property of the *existing* design, not a change this milestone
  makes.
- **Manifest structure** — no new top-level keys, no removed keys, no schema version bump
  (this is a data-value change flowing through an existing field, not a structural one).
- **No real API calls** of any kind — this milestone is a pure read-existing-data,
  write-via-existing-method operation.

---

## 7. Long-Term Fit

This keeps the platform aligned with the long-term vision precisely because of what it
does *not* do: it closes the loop the AI investment has been building toward without
loosening the trust model that has held throughout — AI proposes, a human's explicit,
specific action is the only thing that ever writes truth. That principle was named in the
prior milestone audit as something that must survive the eventual arrival of generation
and publishing capabilities; this milestone is the first real test of whether it holds
under actual use, not just design intent. Scoping it to a single, explicit, non-bulk
primitive is itself part of that fit — it keeps the one new write surface this milestone
introduces small enough to fully reason about, which matters more here than anywhere else
in the roadmap, since this is the exact mechanism a future, higher-stakes "AI Publishing"
milestone would eventually need to trust.

---

## Deliverables

**Current State:** the read side (AI review, coverage, conflict detection) and the write
primitive (`set_title`) both already exist and are proven; only the explicit connecting
action between them is missing.

**Risks:** no Critical findings. Major: silent conflict resolution must be prevented by
design; product-level vs. asset-level naming is already correctly resolved by the existing
grouped-vs-per-source product model, not a new problem to solve. Minor: confidence should
inform, not gate; partial coverage should be visible, not hidden; repeat acceptance is
already safely idempotent. Observation: favour one small, well-tested primitive over a
broad workflow, matching this project's established sequencing discipline.

**Findings:** total reuse of existing, already-tested infrastructure; zero new tables;
zero hidden coupling; the only net-new code is a thin connective action.

**Recommendation: Approved, with scope revised** to a single explicit accept-one-product
primitive, conflict-choice-required, bulk/threshold logic explicitly deferred until real
volume justifies it.

**Acceptance Criteria:** as enumerated in Section 5 — no silent writes, explicit choice
required on conflict, `set_title()` is the only write path, all identity/SKU/manifest/
Shopify surfaces provably untouched, full regression green, zero real API calls.

**Next Recommended Milestone:** the revised, right-sized 3-d.2 (accept-one-product) itself
remains the correct next build. After it lands and is used against the current real data,
**Duplicate Detection** is the next most natural pickup — it is already partially built,
carries no sequencing dependency on anything else, and is comparatively cheap. Hero
Image/Flow/Media Generation and AI Publishing should each wait for their own prerequisite
design questions (asset-model placement for generation; a proven acceptance mechanism to
build trust on, for publishing) to be deliberately answered first.

**Implementation Complexity** (for the revised, right-sized scope):
- **Engineering effort: Low.** One new thin module plus a small set of tests; no schema
  change; reuses three already-built, already-tested functions in full.
- **Architectural risk: Low.** No new table, no new identity concern, no new external
  dependency, no coupling into SKU/manifest/Shopify code paths.
- **Future maintenance cost: Low,** provided the scope discipline in Section 4 holds —
  the risk profile would rise meaningfully if bulk-accept or threshold automation were
  folded in now rather than deferred to a later, separately-scoped and separately-audited
  step.
