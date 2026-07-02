# Karen AI Platform — Phase 3 Milestone Architecture Audit

> Status: **REVIEW ONLY.** No code changed as part of this document. Written as a
> principal-architect assessment of the platform as it stands after fifteen completed
> milestones, evaluated for multi-year operation — not just current correctness.

---

## 1. Executive Assessment

**Overall maturity: mid-platform, pre-production-at-scale.** The identity/product core is
genuinely production-grade: proven on a real 894-file library, versioned, idempotent, and
regression-tested at every step (over 500 individual test assertions across sixteen
suites, all currently green). The AI layer is real but deliberately narrow — 20 of roughly
720 curtain assets have been analysed by design, not by limitation, because the cost- and
consent-control discipline built into 3-b/3-c is working exactly as intended. What's
*not* yet mature is the operational shell around both: backup, schema evolution, and the
final human-decision-to-Shopify link are all thinner than the engine they surround.

**Current architecture score: 7.5 / 10.** The deduction is concentrated, not diffuse: one
newly-identified critical gap (schema migration, below), one significant missing link
(the accept workflow that would close the AI → Manifest loop), and a handful of
operational hardening items that are cheap now and will not stay cheap.

**Production readiness: partial, cleanly bounded.** The import → identity → SKU →
manifest → Shopify-staging path is ready for real, repeated use today. The AI-suggestion
path is ready for continued *supervised* small-batch use, not for unattended or bulk
operation — and it was explicitly designed that way, which is a mark in its favour, not
against it.

**Scalability assessment: good for one operator, unproven for a team.** Every phase has
been load-tested against the real curtain library (894 files) and performs well.
Nothing in the identity/rule engine suggests a ceiling before tens of thousands of assets.
The constraint is architectural, not computational: a single SQLite file, a CLI-only
interface, and no concurrency story mean this scales *vertically* (bigger catalogue) very
well and *horizontally* (more operators, live services) not at all yet, by design.

---

## 2. Architecture Review

**Data model.** This is the platform's strongest asset. The five-entity chain — Family →
Design → Artwork Source → Asset → Product, with Business Metadata as a generic,
identity-orthogonal tagging layer — is unusually disciplined for a system this young. The
decision to dissolve the `from_derived` bypass and the product discriminator into first-
class Artwork Sources (v2.0) was validated against real data before it was built (SC1/SC2
measured at 174/8 on the real library, collapsed to 0/0 after), which is the correct order
of operations and rare in practice. Opaque, immutable, never-reused IDs at every level
mean nothing downstream (SKU, manifest, Shopify) has ever had to be told "an ID changed."

**Separation of responsibilities.** Mostly clean: rules (classification) is decoupled
from identity (storage) is decoupled from derivation (SKU/title) is decoupled from
presentation (audit/manifest/export). The one place this is eroding is `audit.py`, which
has become the landing zone for every new "surface this data somewhere" requirement —
manifest assembly, `skus.csv`, `ai_review.csv`, and the original duplicate/review reports
all now live in one large module. It still works, but it is the one file every phase this
session has had to touch, which is the classic early signature of a module accreting
unrelated responsibilities. The same, milder pattern is visible in `vision_ai.py`, which
now holds selection, caching, pre-flight, single-image execution, batch execution, and CLI
parsing together.

**Module boundaries.** The provider-adapter pattern in `vision_provider.py` is the right
shape for a system that expects to add capabilities later — `VisionProvider` as an
interface with a mock and a real implementation is exactly how a future image-*generation*
provider would slot in without disturbing the analysis path. This is a genuine piece of
future-proofing, not accidental convenience.

**Future maintainability.** High for the identity/rule layers (versioned, tested,
documented in a running architecture-decision log). Medium for the reporting/AI-
orchestration layers, for the reason above. Low, currently, for the legacy surface — see
technical debt below.

**Hidden coupling.** Two specific instances worth naming: (1) `build_graph.py`'s CLI now
carries a real business decision — whether to preserve or wipe non-derivable data — inside
argument-parsing code rather than in the domain layer; it works, but the decision belongs
closer to the model. (2) `audit.py` reaches into `vision_review.py`, `sku.py`, and
`model.py` simultaneously to assemble one manifest entry; the coupling is currently benign
because every module it touches is stable, but it means a future change to *any* of those
four modules has a reasonable chance of requiring an `audit.py` edit too.

**Technical debt — named explicitly:**
- The legacy v0.6 stack (`app.py`, `db.py`, `ingest.py`/`exporters.py`/`classify.py`,
  `templates/`, `static/`) still ships inside the package, fully disconnected from the
  identity model it predates. It is inert today, but it is dead weight in every install,
  a source of confusion for any future contributor (or future you, eight months from now),
  and a nonzero risk of being accidentally invoked against the current data model.
- String-typed discriminators (`role` values like `panel-L`, `fabric-c01`, side letters
  `L`/`R`/`C`) work well at the current handful of product types but are a brittleness
  risk as more types (tapestry, apparel) are added — there is no single place that
  enumerates the valid vocabulary the way `STYLE_VOCAB` does for tags.
- **A genuinely new finding, surfaced by this audit and worth treating as the most
  urgent item on this list: schema evolution has no migration path.** Every table is
  created with `CREATE TABLE IF NOT EXISTS`, which is a no-op against a table that
  already exists — it does **not** add new columns. This was invisible for the entire
  project so far because the database was rebuilt from scratch on every run. Now that the
  database-preservation fix is in place (correctly, for good reason), this has flipped
  from irrelevant to load-bearing: I verified directly that opening a database created
  before the `is_match` or `display_title` columns existed, with the *current* code,
  throws `OperationalError: no such column`. Every future additive schema change — and
  this project has made one in nearly every phase — will now crash on any database that
  predates it, unless the operator happens to remember to pass `--fresh` (which also
  destroys the AI data the preservation fix was built to protect). This is the single
  most consequential architectural gap in the platform today, precisely because it was
  created as a side effect of fixing something else.

---

## 3. AI Pipeline Review

**Colour extraction (3-a).** Clean, correct, and slightly underused. It is genuinely free
and instant, runs locally, and is already wired into the manifest — but nothing downstream
(Shopify tags, collection logic) consumes it yet. It is a finished capability waiting for
a consumer.

**Vision pipeline (3-b/3-c).** The strongest AI engineering in the platform. Pre-flight
checks that fail before spending, a hard cap enforced at two layers (function and CLI),
per-image commit (proven to survive an interrupted run without duplicate spend or gaps),
real accumulated token/cost reporting rather than nominal estimates, and a strict,
validated JSON contract with fence-stripping and one bounded retry. This is
production-grade cost and correctness discipline for an external AI dependency — better
than most teams build on a first pass.

**Prompt architecture.** Single-call-per-image (match + name + tags together) is the right
efficiency decision. The prompt was tuned once, from real evidence (the first 20-image
batch), and the tuning demonstrably worked — the second batch's names are concrete and
customer-facing where the first batch's were generic. That is the pipeline operating
exactly as a learning system should: ship small, observe, adjust, re-verify. The one
architectural note: prompt text currently lives as a Python string inside
`vision_provider.py`. That is fine at one prompt; if hero-image or lifestyle-generation
prompts are added later, prompt content will want its own versioned home, separate from
the code that calls it.

**Cache strategy.** Correct and proven: keyed on `sha256` + `vision_version`, verified to
skip already-analysed images and to resume cleanly after interruption with zero duplicate
calls. The one real dependency worth flagging: the cache is only as good as `sha256`
being populated, and it always is (verified directly — `--no-hash` only skips the
*duplicate-detection report*, not asset hashing, despite the flag's name inviting the
opposite assumption). That naming mismatch is a minor but recurring source of confusion
worth fixing in language, not logic.

**Versioning strategy.** A genuine strength, and unusual for a project this size:
`schema_version`, `rules_version`, `design_types_version`, and `VISION_VERSION` are all
real, all exercised in production (rules moved 2→3 for the fabric convention, vision moved
1→2 for the prompt/vocabulary tuning), and all recorded in the manifest. This is the
correct foundation for a system meant to keep evolving without silently reprocessing —
or silently *failing* to reprocess — content under an old contract.

**Human review workflow.** Built through 3-d.1 and stops exactly where it should for
now: `ai_review.csv` and the manifest's supplementary AI fields are honest, correctly
distinguish "not yet analysed" from "analysed but colour-only" from "analysed," and
correctly surface disagreement between a curtain's two sides as a `conflict` flag rather
than silently picking a winner. What does **not** exist yet is the other half: a
mechanism for a human decision on that review data to actually become a `display_title`.
Today that can only happen through a manual `set_title()` call — there is no accept
action, bulk or otherwise. This is the pipeline's most consequential unfinished edge, and
it is a known, already-scoped gap (3-d.2), not a surprise.

---

## 4. Data Flow Review

```
Artwork → Identity → Asset Graph → AI Analysis → Human Review → Manifest → Shopify
```

- **Artwork → Identity → Asset Graph:** Fully built, proven at real scale, versioned,
  idempotent. The strongest three links in the chain by a wide margin.
- **Asset Graph → AI Analysis:** Mechanically complete and safe; *coverage* is
  intentionally minimal (roughly 3% of the curtain library). Not a defect — a deliberate,
  correct sequencing decision — but worth naming plainly so "the AI pipeline works" isn't
  read as "the catalogue has been analysed."
- **AI Analysis → Human Review:** Built (3-d.1), honest, tested against real conflicting
  and colour-only data.
- **Human Review → Manifest: this is the missing link in the chain as drawn.** There is
  no code path from "a human looked at `ai_review.csv` and decided" to "the manifest
  reflects that decision" other than manually invoking `set_title()`. Everything upstream
  of this point is automated and tested; everything downstream of it assumes the decision
  already happened. This is the clearest, single most useful thing this audit can name as
  a missing layer.
- **Manifest → Shopify:** Built as a one-directional, human-reviewed CSV staging export —
  architecturally correct for the stated goal ("Asset Manager is the system of record,
  Shopify is downstream"). What's absent is any **state of the sync itself**: nothing
  records which products have already been pushed, when, or what Shopify assigned as
  their live product ID. A second export today would produce a second CSV with no
  awareness of the first. That's acceptable for a one-time staging test; it is a gap the
  moment this needs to run more than once against a live store.

---

## 5. Readiness for Future AI

- **Google Flow / hero image generation / lifestyle scene generation:** The provider-
  adapter pattern built for vision *analysis* is the correct foundation to extend to
  vision *generation* — but generation raises a question the current model doesn't
  answer: is a generated hero image a `Derived` Artwork Source of an existing design (like
  a cropped cushion), or a new asset class entirely, outside the Design/Source model,
  that exists for marketing rather than product identity? That is a real design decision,
  not an implementation detail, and it should be made deliberately before any generation
  code is written — not discovered halfway through building it.
- **Mockup generation:** Already correctly scoped and separated in the original
  architecture (blank-base-plus-overlay via Kickflip, distinct from full AI-generated
  lifestyle imagery) — conceptually ready; the integration itself is unbuilt.
- **Collection intelligence / automatic merchandising:** The `collection` and `theme`
  dimensions already exist in Business Metadata as manual tagging axes. That is a tagging
  substrate, not intelligence — there is no automation layer yet, and merchandising
  automation is a poor place to start before any collection intelligence exists to drive
  it.
- **Duplicate detection:** Partially built already — exact-hash duplicate detection
  (`duplicate_designs.csv`/`duplicate_assets.csv`) exists in the auditor, ahead of most of
  the items on this list. It is presently under-used because routine runs pass
  `--no-hash`. Near-duplicate / visual-similarity detection (as opposed to byte-identical)
  does not exist and would be a genuine new capability, likely built on the same provider
  pattern as vision analysis.
- **Market intelligence:** No foundation beyond a `market` metadata tag. This would be an
  entirely new, externally-fed subsystem — realistic to build, but with nothing to reuse
  from today's platform beyond the tagging convention.
- **AI-assisted publishing:** The highest-governance capability on this list, and the one
  most important to get right rather than fast. The platform's existing trust model —
  "AI proposes, a human's explicit action is the only thing that writes truth" — is
  exactly the right precedent, and it must **not** be quietly loosened when publishing
  automation eventually arrives. Automatic publishing is a different trust tier from
  automatic tagging, and deserves its own explicit approval/rollback design rather than
  inheriting the current "suggestion" pattern by default.

---

## 6. Operational Readiness

- **Database lifecycle:** Recently and correctly fixed — preserved by default,
  destructive action requires an explicit, documented `--fresh` flag, proven under real
  reproduction of the original failure. This is now a strength. Its sharp edge is the
  schema-migration gap named in Section 2, which the same fix inadvertently exposed.
- **Incremental updates:** Identity import is genuinely incremental and idempotent
  (proven). AI/vision work is incremental via the cache (proven). Manifest generation is
  currently a full rebuild each run — fine at 564 products, worth revisiting well before
  an order of magnitude more.
- **Backup strategy: currently absent, and this is now a real risk, not a theoretical
  one.** The database is a single file on one external drive, and it now holds
  non-derivable, paid-for data. There is no automated copy, snapshot, or off-drive backup
  of `audit.db`. The cost of fixing this today is a few minutes; the cost of not fixing it
  is re-purchasing AI analysis (or worse, losing accepted manual titles) after a drive
  failure.
- **Versioning:** Excellent, and already covered in Section 3 — genuinely one of the
  platform's stronger traits.
- **Cost control:** Strong for the current supervised, small-batch model — dry-run,
  hard caps, explicit confirmation, real token-based cost reporting. What doesn't exist is
  a *cumulative* view (total spend across all runs to date); each run reports its own
  cost with no running ledger. Minor today, worth having before volume increases.
- **Recovery:** Proven for the one failure mode that was explicitly tested — an
  interrupted batch resumes cleanly with no duplicate spend. Unproven, because
  unaddressed, for database corruption or drive loss, which ties directly back to the
  backup gap above.
- **Repeatability:** A genuine strength — deterministic, versioned rules; comprehensive,
  currently-green test suites; and real-data proof points gathered at every phase gate
  before the next phase was approved. This is the discipline that makes the rest of this
  audit possible to write with confidence.

---

## 7. Risks

**Critical**
- **Schema migration gap.** `CREATE TABLE IF NOT EXISTS` does not evolve an existing
  table. Combined with the (correct) decision to stop auto-deleting the database, the
  next additive schema change will crash against any database created before it, with no
  built-in recovery short of a destructive `--fresh` rebuild. This is newly critical, not
  historically critical — it was safe by accident until the preservation fix landed.
- **No backup of non-derivable data.** `vision_results` now contains paid, irreplaceable
  AI analysis and any accepted manual titles, stored as a single file with no redundancy.

**Major**
- **The Human Review → Manifest link is unbuilt.** AI suggestions cannot become product
  truth without a person manually invoking a low-level method; there is no accept
  workflow, bulk or otherwise. This is the platform's most visible functional gap.
- **No Shopify sync-state tracking.** Repeated exports have no memory of what was already
  pushed, so there is no way today to detect drift or avoid duplicate/conflicting imports
  once this moves beyond a one-time staging test.
- **Legacy v0.6 code still ships in the package,** unconnected to the current data model,
  with real potential to confuse future maintenance or be invoked by mistake.

**Minor**
- **`audit.py` and `vision_ai.py` are accreting responsibilities** faster than the rest of
  the codebase — every phase this session has touched `audit.py`. Not urgent, but the
  trend line is worth interrupting before the next few phases make it worse.
- **String-typed role/side vocabulary** works today but has no single source of truth the
  way `STYLE_VOCAB` does, and will get more brittle as product types multiply.
- **`--no-hash` is a misleading name** for a flag that only skips duplicate-detection
  reporting, not asset hashing — a clarity risk, not a functional one.
- **No cumulative cost ledger** across runs, only per-run reporting.

**Observation**
- Manifest regeneration is full-rebuild, not incremental — a non-issue at current scale,
  worth watching as the catalogue grows.
- The provider-adapter pattern used for vision analysis is well-positioned to extend to
  future generation capabilities, provided the Derived-Source-vs-marketing-asset question
  (Section 5) is answered deliberately rather than by default.
- Business Metadata's generic entity/dimension/value design is the right level of
  flexibility for tagging today; worth a second look only if the number of dimensions
  grows substantially, as generic key-value schemas trade query simplicity for
  long-term structure.

---

## 8. Phase Sequencing

**Recommendation: (C) AI Acceptance Workflow — with the schema-migration fix treated as a
mandatory, small, near-immediate prerequisite that should land before or alongside it,
regardless of which "next phase" is chosen.**

The reasoning is architectural, not preferential. Hero Image Generation (A) and Collection
Intelligence (B) are both genuinely valuable, but both build *new* capability on top of a
loop — AI suggestion to accepted product truth — that the platform itself hasn't finished
closing. Building generation or intelligence features before the acceptance workflow
exists would mean the newest, least-proven parts of the system would be the first things
depending on infrastructure that doesn't exist yet. Duplicate Detection (D) is valuable
and comparatively cheap (partially built already), but it is not blocking anything else
and can be picked up any time without sequencing risk — it doesn't need to be next, it
just needs to happen eventually.

Completing the acceptance workflow is also the lowest-risk of the four options: it
extends a pattern (`set_title`, manual-override-always-wins) that is already built,
tested, and proven correct, rather than introducing a new external dependency (image
generation) or a new analytical capability (collection intelligence) with no existing
foundation. It is the natural, already-scoped conclusion of work already in progress, not
a new initiative.

The schema-migration fix is listed as a parallel prerequisite rather than "the next
phase" because it isn't a milestone with user-visible value — it's a landmine defusal.
But it should not wait for a dedicated phase slot; it is small, well-understood, and every
day it's deferred is another day a routine schema change could break a database in the
field.

---

## 9. Long-Term Vision

**Can this evolve into a complete Karen AI Platform? The identity and data foundation:
yes, without reservation. The operational shell around it: not yet, and not without
adding real architectural layers first — not more features, but different kinds of
infrastructure.**

The reasoning for the "yes" half: opaque immutable IDs, a one-directional system of
record, a versioned rule and schema engine, and a metadata layer orthogonal to identity
are precisely the primitives a long-lived platform needs, and they have already been
proven under real data rather than only in tests. Very little of this would need to be
rebuilt as the platform grows — it would need to be *extended*, which is the outcome good
architecture is supposed to produce.

The reasoning for the "not yet" half is specific, not a vague caution:

- **A real schema migration system** must exist before further additive schema changes
  are safe against a persisted, non-derivable database — this is now the platform's
  first true prerequisite, discovered by this very audit.
- **A service or API boundary**, even a lightweight local one, separating "the engine"
  from "the CLI a person types into" — needed the moment more than one surface (a
  scheduled job, a second operator, a future web review UI) needs to talk to the same
  data.
- **A Shopify reconciliation layer** with real sync-state (which products were pushed,
  when, with what Shopify-assigned ID) — needed before publishing can be anything other
  than a one-time manual staging test.
- **A backup and recovery story** for the database file itself — needed now, not later,
  given what it already holds.
- **Removal or clear quarantine of the legacy v0.6 code** — needed before the codebase
  gets much larger, so the "real" system stays unambiguous to whoever touches it next.
- **A governance layer for higher-trust AI actions** (publishing, automatic
  merchandising) distinct from the current "suggestion only" pattern — needed before, not
  during, the first automated-publishing feature, so the trust model is a deliberate
  design rather than an inherited default that turns out to be too permissive.

None of these are large. All of them are the kind of infrastructure that is cheap to add
deliberately and expensive to retrofit after the fact — which is the entire reason for
naming them now, at a milestone review, rather than after the next three features have
been built on top of their absence.

---

## Deliverables

**Overall architecture score: 7.5 / 10**
**Engineering maturity score: 8 / 10** — versioning, testing, and phase-gating discipline
are genuinely above average for a project at this stage.
**AI maturity score: 6 / 10** — the pipeline engineering is excellent; coverage and the
acceptance loop are both intentionally incomplete.
**Business readiness score: 5 / 10** — the staging path works; nothing is yet a closed,
repeatable loop to a live store.
**Scalability score: 6 / 10** — excellent catalogue-size scalability, no concurrency or
multi-operator story yet, by design rather than oversight.
**Production readiness: ~55–60%** — the identity/product/SKU core is production-ready
today; the AI and publishing layers are correctly beta-scoped, not yet ready for
unsupervised or bulk operation.

### 1. What should absolutely NOT be changed
- The opaque, immutable ID scheme and the one-directional system-of-record principle.
- The Artwork Source (v2.0) model — it dissolved real special cases, proven on real data;
  do not regress toward the old bypass/discriminator pattern for any new product type.
- The versioned rule/schema/vision discipline (`rules_version`, `schema_version`,
  `design_types_version`, `VISION_VERSION`) and the running architecture-decision log.
- The core AI governance principle: **AI suggests, an explicit human or manual action is
  the only thing that ever writes identity, SKU, or title.** This must survive the
  addition of generation and publishing capabilities, not just analysis.
- The phase-gated, spec-before-code, tested-and-verified-on-real-data-before-proceeding
  discipline itself, as a way of working — it is why this audit can trust what it's
  reviewing.

### 2. What should be refactored before it becomes expensive
- Add a real schema migration mechanism — the single most urgent item in this entire
  audit.
- Split `audit.py`'s accreting responsibilities (manifest assembly, CSV reporting, AI
  review surfacing) into composable pieces before the next few phases make it worse.
- Introduce a single source of truth for the role/side/application string vocabulary
  before more product types multiply the surface area of ad hoc string matching.
- Remove or clearly quarantine the legacy v0.6 code.

### 3. What should become standalone services in the future
- The vision/AI provider layer — already adapter-shaped, natural to split out once
  generation capabilities join analysis.
- Shopify sync and reconciliation — deserves its own state store once anything beyond a
  one-time staging export is needed.
- Collection/market intelligence — a distinct concern that should consume the manifest as
  input rather than live inside the asset manager.

### 4. The single highest-ROI next milestone
**Completing the AI Acceptance Workflow (3-d.2)** — it closes the one loop the entire AI
investment so far has been building toward, reuses infrastructure that is already built
and proven (`set_title`, manual-override-always-wins), carries the lowest risk of the
available options, and is what makes every future AI capability (generation, collection
intelligence, publishing) something that plugs into a *finished* pipeline instead of an
open one. The schema-migration fix should land alongside it — not as the milestone itself,
but as the prerequisite that keeps the milestone, and everything after it, safe.
