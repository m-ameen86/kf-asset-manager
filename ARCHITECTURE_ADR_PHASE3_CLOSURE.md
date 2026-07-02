# ADR — Phase 3 Closure: Vision, AI Review, and Explicit Acceptance

> **Status: ACCEPTED — CLOSED.** This record permanently closes Phase 3. No further
> Phase 3-x sub-phases will be opened; any continuation of this work is new work under a
> subsequent phase. Documentation only — no code changed as part of this record.
> **Date:** July 2026.

---

## Context

The system of record (Identity Engine, Asset Graph, Artwork Source v2.0, Product
Identity, SKU System, Display Title System, Manifest, Shopify Export) was complete and
proven on real data before Phase 3 began. What it could not yet do was *look at* an
image. Phase 3 was opened to answer a specific request: verify that an image matches its
catalogued design, extract real colour, suggest a customer-facing name, and tag its
style — while preserving the one invariant the rest of the system had already earned:
**nothing but an explicit human or manual action ever writes identity or product truth.**

That constraint was not incidental to Phase 3 — it was its central design problem. Vision
capabilities are inherently probabilistic and externally sourced (a paid third-party API);
the system of record they were being attached to is deterministic, versioned, and
proven. The entire phase is best understood as the work of connecting those two things
without letting the second inherit the first's uncertainty.

---

## Decision

Nine decisions define the shape of what was built, each made at a specific point where a
simpler or faster alternative was available and deliberately not taken:

1. **Colour extraction is local, not AI (3-a).** Dominant colour is a pixel-level
   computation, not a judgment call — extracting it locally cost nothing, ran offline,
   and needed no key, while genuine AI capability was reserved for the three tasks that
   actually required judgment (match verification, naming, style tagging).

2. **One provider interface, two implementations, from the start (3-b).** Building
   `VisionProvider` as an abstraction — with a deterministic mock for tests and a real,
   initially inert Anthropic implementation — meant every subsequent phase (3-c.1 through
   3-c.3) was an extension of already-tested scaffolding, never a rewrite. This is also
   the seam a future *generation* provider (hero images, lifestyle scenes) would extend,
   not replace.

3. **Cost is a designed-in constraint, not an afterthought.** Pre-flight checks that fail
   before any spend, a hard cap enforced at two independent layers, mandatory explicit
   confirmation showing real counts before a call is made, and per-image commit proven to
   survive an interrupted run with zero duplicate spend — all decided and built before the
   first real API call was ever made, not retrofitted after a scare.

4. **One structured call answers all three AI questions per image.** Match verification,
   name suggestion, and style tags are answered in a single request with a strict,
   validated JSON contract — a deliberate efficiency decision that also simplified the
   cache (one cache key covers all three answers) and the failure model (one call either
   succeeds or is retried once, never partially).

5. **The cache key is content, not intent.** `sha256` + `vision_version` — never a
   filename, never a timestamp — means identical images share results, unrelated re-runs
   never re-spend, and a deliberate prompt change (3-c.3) can invalidate exactly the right
   scope by bumping one integer, without touching a single cached result's data.

6. **AI output is metadata until a human says otherwise.** `vision_results` was designed
   from its first line as data a person reviews, never data that writes itself into
   `display_title`. This was tested as an explicit property, repeatedly, at every
   subsequent phase — not assumed and left unchecked.

7. **When evidence disagrees, say so — don't average it away.** The discovery that a
   grouped product's two sides can produce genuinely different AI suggestions (Section
   "Verified Production Evidence" below) was treated as a fact to surface, not a nuisance
   to resolve algorithmically. `conflict=True` and a required explicit choice were the
   direct architectural response.

8. **Scope was corrected against real volume, not hypothetical scale, before building
   3-d.2.** The pre-build audit for the acceptance workflow found the originally-scoped
   bulk/threshold design was ahead of the evidence — ten reviewed products did not justify
   automation. The decision to build one small, explicit, fully-reasoned-about primitive
   instead, and defer the rest, was made deliberately and before code, not discovered as a
   limitation afterward.

9. **Database preservation and schema migration were treated as first-class phase work,
   not incidental fixes.** Once `vision_results` made the database non-derivable, its
   *lifecycle* — what survives a routine run, what a destructive rebuild costs, how the
   schema evolves under a database that no longer resets itself — became exactly as much
   Phase 3's responsibility as the vision pipeline itself. Both were addressed with the
   same rigor: audited, fixed, and proven against a reproduction of the real incident, not
   patched and moved past.

---

## Consequences

**What this enables.** A working, cost-bounded, human-supervised path from a raw image to
a reviewed, accepted, and published product title — proven, not theoretical, on the real
Karen Fabrics Staging store (see evidence below). Every future AI capability this platform
adds — generation, collection intelligence, eventually publishing automation — now has a
concrete, working precedent for how AI output should be allowed to touch product truth:
never directly, always through an explicit, auditable acceptance step.

**What this costs.** AI coverage is intentionally tiny relative to the catalogue (21 real
images analysed against roughly 720 curtain assets) — Phase 3 optimized for *proof of a
safe pattern*, not *coverage of the library*. Scaling coverage is now a volume decision for
a future phase, not a capability gap. The acceptance workflow is deliberately
one-product-at-a-time; reviewing hundreds of products this way would be tedious, which is
an accepted, named tradeoff (see Deferred Work) rather than an oversight.

**What this changed structurally.** Two changes were forced on already-shipped code, not
planned in advance: the database went from disposable-by-default to preserved-by-default
(inverting `build_graph`'s prior behaviour), and the schema gained its first real migration
mechanism. Both are now permanent parts of the platform's operating model, not Phase-3-only
artifacts.

---

## Verified Production Evidence

This ADR closes Phase 3 on the strength of real, verified outcomes, not test counts alone
(though those exist too — 19 test files, 466 individual assertions, all green throughout
this closure).

- **21 real AI analyses were performed** across two real batches: 1 image (3-c.1's smoke
  proof) and 20 images (3-c.2's batch, 19 ok / 0 failed / 41,428 input + 2,286 output
  tokens, real cost, not estimated).
- **A real production incident occurred and was fixed within the phase.** The first
  smoke result and an entire prior colour pass were silently erased by `build_graph`'s
  default database deletion — discovered because `ai_review.csv` honestly reported
  `not_analyzed` for data that had, in fact, already been analysed. The fix (preserve by
  default, `--fresh` as an explicit destructive opt-in) was verified against a
  reproduction of the exact failing sequence before being trusted.
- **A second, latent defect was found and fixed proactively, before it could cause a
  second incident** — the schema migration gap, discovered while auditing the first fix
  rather than by a second failure. This distinction matters: it marks a shift from
  reactive to proactive defect discovery within the same phase.
- **Ten curtain products reached full AI coverage** (both panels analysed). Of those,
  **eight of ten (80%) had genuinely disagreeing suggestions between their two sides** —
  confirmed, on inspection of the actual source images for one case, to reflect real
  design difference (a chevron-pattern panel paired with an illustrated unicorn-scene
  panel), not an AI error. This is a real, quantified fact about the catalogue surfaced as
  a byproduct of building the vision pipeline: coordinating-but-different panel pairs are
  common enough (80% of this sample) to be a structural property worth remembering in any
  future catalogue or collection work, not an edge case.
- **All ten were reviewed and explicitly accepted** through the 3-d.2 workflow — nine via
  `--accept-ai` (two clean, seven requiring an explicit conflict choice, one of which was
  escalated to visual inspection of the source files before a decision was made), none
  automatic.
- **The full loop was proven end-to-end against the real, connected Shopify store**
  ("Karen Fabrics Staging"). All ten accepted titles were confirmed live via an
  independent read-back query — not assumed from the write response — with SKUs,
  variants, and draft status all correctly unaffected.
- **One unplanned operational discovery was made and is recorded here rather than
  silently absorbed:** the final Shopify update in this phase was pushed directly via the
  connected Shopify API, not through the CSV-staging path the export tooling was
  originally built around. Both paths now demonstrably work; which one is the standing
  default going forward is an open decision, not yet made (see Prerequisites).

---

## Deferred Work (explicit, with reasoning)

Nothing below is a gap discovered late — each was identified during the phase and
deliberately not built, for a stated reason:

- **Bulk-accept / confidence-threshold automation** — audited and explicitly rejected as
  premature at ten real reviewed products; revisit only if real coverage volume grows
  enough to make one-at-a-time review genuinely impractical.
- **AI coverage beyond the current 21 images** — a volume decision, not a capability gap;
  the batch mechanism (2–30 images, hard-capped) already supports repeating this at will.
- **Formal Shopify sync-state / CSV-vs-API reconciliation** — the phase proved both paths
  work; it did not decide which is canonical, or build any record of what was pushed via
  which path. This is now a named open question, not an oversight.
- **Hero image / lifestyle generation, Google Flow integration** — correctly identified as
  depending on an unmade design decision (is a generated image a Derived Artwork Source or
  a new asset class entirely) that Phase 3 deliberately left unmade rather than answer by
  default.
- **Collection intelligence, market intelligence, AI-assisted publishing** — each named in
  the Phase 3 milestone audit as depending on infrastructure this phase does not provide;
  publishing in particular is explicitly gated by the acceptance mechanism this phase just
  finished proving, not a parallel option to it.
- **Legacy v0.6 code removal, `audit.py`/`vision_ai.py` module-boundary cleanup, a backup
  strategy for `audit.db`** — all named in the milestone audit, all still true, all
  explicitly carried forward rather than considered resolved by this closure.

---

## Lessons Learned

**Small-batch-first discipline paid for itself, repeatedly, not just once.** Colour before
AI, one image before a batch, one product before bulk-accept — each step could have been
skipped in favour of building the "real" version immediately. Every time the smaller step
was built first, it either caught a real problem before it could compound (the schema gap,
found via audit before a second data-loss incident) or confirmed the bigger step wasn't
needed yet (bulk-accept, correctly deferred at real volume).

**Real usage found defects that a comprehensive test suite, on its own, did not and could
not.** The database-deletion incident was invisible to every test written against fresh,
disposable databases — because until real preserved AI data existed, the bug had no
observable effect to test for. This is not a testing failure; it is a reminder that
production evidence and test coverage answer different questions, and a phase isn't truly
closed until both have been consulted.

**The provider-adapter decision (3-b) was the single highest-leverage architectural choice
in the phase.** Every subsequent step — real execution, batching, prompt tuning — extended
existing, tested scaffolding rather than rewriting anything, and the same seam is already
positioned to carry future generation capability without another rewrite.

**Naming discipline matters for a project meant to last years, not just weeks.** This
closure record itself exists partly because "Phase 4" was already in use before Phase 3-c
even began — a naming collision that would have quietly confused the architecture history
had it not been caught before being written down permanently.

---

## Prerequisites for the Next Phase

**Numbering note, load-bearing for the rest of this project's history:** "Phase 4" already
refers to the completed Product Identity / SKU / Manifest / Shopify Export milestone,
finished before Phase 3-c began. **The next new phase is Phase 5.** Any future document,
prompt, or conversation that says "Phase 4" meaning *new* work is referring to the wrong
milestone and should be corrected on sight.

Before Phase 5 substantively begins, the following should be explicitly decided or
addressed — carried forward from this phase's own findings, not newly invented:

1. **Decide the standing Shopify sync path** (CSV-staging vs. direct API vs. both, with
   which as canonical) and, if ongoing use is expected, give it real sync-state tracking —
   this phase proved both work but decided neither is authoritative.
2. **A backup strategy for `audit.db`** — still absent, still holding non-derivable, paid
   data, unchanged in risk since it was first named.
3. **Legacy v0.6 code disposition** — remove or clearly quarantine before the codebase
   grows further around it.
4. Whatever Phase 5 turns out to be, it should be **scoped against real evidence**, the
   same way 3-d.2 was corrected — not against the largest plausible version of the idea.

---

## Formal Closure

**Phase 3 is CLOSED.** Its scope — colour extraction, vision provider scaffolding, real
single-image and batch execution, prompt tuning from real evidence, an honest AI review
surface, and an explicit, human-gated acceptance workflow — is complete, tested, and
verified against real production use, including a real, connected Shopify store. The two
critical defects discovered during the phase (database preservation, schema migration)
were fixed and independently verified before this closure, not left open against it.

This record is the authoritative statement of what Phase 3 delivered and did not deliver.
Future work may reference it, but reopening Phase 3 itself — rather than opening a new,
appropriately-numbered phase — would require a new ADR explicitly superseding this one.
