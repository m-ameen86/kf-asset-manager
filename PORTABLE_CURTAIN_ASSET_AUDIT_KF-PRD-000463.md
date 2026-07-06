# Architecture Correction Audit — Portable Curtain Composite Asset (KF-PRD-000463)

> Status: **AUDIT ONLY. Documentation only.** No code, no Flow prompts, no scaling
> beyond `KF-PRD-000463`, no invalidation of Stage A. This corrects one specific,
> narrow assumption in `STAGE_B_PREBUILD_AUDIT_KF-PRD-000463.md` — that literal Stage A
> pixels could be composited directly into a new Stage B scene — discovered false during
> real production work, not during planning. Everything else in that audit, and in
> `ARCHITECTURE_MEDIA_WORKFLOW_SOP.md`, remains as locked.

> **Confirmed implemented:** the corrected workflow specified here was verified as
> actually built, not just adopted on paper — see `STAGE_B_CLOSURE_KF-PRD-000463.md` for
> the structural layer-tree evidence. Section 5's recommendation not to register the
> Portable Curtain Asset in Business Metadata remains in effect.

---

## 1. Three distinct things, not two

The discovery reveals a genuine category this project's architecture hasn't needed
before, because Stage A never needed portability:

- **Product Media** (unchanged, still valid, still Stage A's deliverable) — the exact-
  fidelity representation of the product *as photographed in its own specific base
  scene*. Its job is to be the definitive answer to "what does this product actually
  look like," full stop, in its own right. It was never required to be portable, and
  nothing about this correction changes that requirement or its Stage A approval.
- **Portable Curtain Composite Asset (new, not yet built)** — the curtain content
  itself (both panels, correctly assigned, correct fidelity/typography/scale/colour),
  constructed deliberately to be scene-agnostic, so it can be dropped into an arbitrary
  future room without carrying baked-in lighting/shadow information tied to one specific
  base. This is a new kind of production artifact, not a renaming of anything that
  already exists.
- **Marketing Media** (unchanged in definition, still not yet produced) — the finished
  Stage B lifestyle/hero image, built *from* the Portable Composite Asset composited into
  a Flow-generated room, QC'd, and registered exactly as already specified.

Product Media and the Portable Composite Asset are related — both must trace back to
identical fidelity — but they are not the same artifact and must not be treated as
interchangeable. That conflation is exactly what caused the discovered problem.

---

## 2. Does the "literal Stage A pixels" assumption need revising?

**Yes — narrowly, and precisely here, not throughout the architecture.**

The original reasoning behind that assumption was sound in principle: reusing an
already-verified result avoids re-deriving fidelity from scratch and re-risking the
errors Stage A eliminated. What that reasoning missed is that "already verified" and
"portable" are different properties. Stage A's shading, highlight, and displacement
passes were correctly extracted *from one specific base scene* (per
`PHOTOSHOP_PRODUCTION_METHOD_KF-PRD-000463.md`) — they were never designed or tested to
survive being moved to a different scene with different lighting logic. Forcing their
reuse verbatim is what produced the inconsistent lighting, edges, and contact behaviour.

**The corrected principle:** the fidelity source remains the original TIFF masters and
the already-proven Stage A identity facts (correct L/R assignment, orientation, scale,
colour, typography) — **not necessarily the literal flattened Stage A JPG pixels.** What
must never change is the *content*; what's now allowed to differ is *which specific
composited artifact* carries that content into a new scene. The reference hierarchy in
the Stage B audit (TIFFs → Product Media → room references → prompts) remains correct
and unchanged — this correction only affects which intermediate artifact Stage B actually
composites, not which sources are authoritative.

---

## 3. Selection criteria for a suitable curtain PSD mockup (for the Portable Asset)

Distinct from, and stricter than, the original Stage A base-sourcing checklist, because
this asset must generalize rather than serve one fixed scene:

- Genuinely two independent, separately-editable L/R panel Smart Objects (unchanged
  requirement).
- **Shading, highlight, and displacement exposed as separate, non-destructive layers or
  Smart Filters — never pre-baked into a single flattened result.** This is the specific
  property that makes re-deriving lighting against a *new* base's luminosity information
  possible later, rather than dragging one scene's baked lighting into an incompatible
  one.
- **Relatively neutral, even baseline lighting** in the mockup itself — not one highly
  stylized, dramatic lighting setup. A neutral starting point adapts to more future
  contexts; a dramatic one looks wrong almost everywhere else.
- Clean, isolatable curtain content — minimal background bleed, clean mask/alpha
  separation, so the panels can be lifted independently of whatever room the mockup
  itself originally depicted.
- Commercial license covering production use (unchanged requirement).

---

## 4. Preserving exact identity, fidelity, typography, scale, and colour truth

No relaxation here — the Portable Composite Asset is built from the **same original
TIFF masters** (`P4186-L.tif`, `P4186-R.tif`), using the same techniques already
documented in `PHOTOSHOP_PRODUCTION_METHOD_KF-PRD-000463.md` (displacement by methodology
not invented numbers, independent per-panel tuning, per-panel colour soft-proofing). This
is a Stage-A-equivalent rigor pass applied to a new artifact — not a shortcut, and not a
lower bar because it's "just" an intermediate asset.

---

## 5. Business Metadata registration — should the Portable Asset be registered, and under what?

**No. It should not be registered under either existing dimension, and no new dimension
should be invented in this audit.**

Neither existing convention fits honestly:
- `product_media` describes a finished, customer-facing product photo — the Portable
  Asset is not that; it's a reusable production input.
- `marketing_media` describes a finished lifestyle/hero deliverable — the Portable Asset
  is not that either; it's what a future one gets built *from*.

Forcing it into either would misrepresent what the metadata actually records — the same
discipline this project applied when it rejected `artwork_relationship = "Mockup"`
earlier: don't stretch an existing mechanism to cover a case it wasn't built for. The
correct answer right now is to treat the Portable Composite Asset as a **working
production file** — tracked by filename and folder location only (the same
`00_Working`-style discipline already established), not as a formally registered entity.
If this pattern turns out to recur across future products, *that* would be the moment to
deliberately design a dedicated dimension for it — not now, on the evidence of one
product's first correction.

---

## 6. Measurable acceptance gates for the Portable Asset proof

A distinct gate set from Stage A's nineteen — because the specific new risk is
portability, which Stage A never had to prove:

1. Identity preserved — same TIFFs, same verified L/R assignment, checked against source.
2. No mirroring, no swap, no orientation error (standing requirement, re-verified here).
3. Typography, illustration geometry, vertical placement, and wave-band alignment
   preserved, per the existing Photoshop Production Method's techniques.
4. Colour truth — each panel matches its own source TIFF independently.
5. **Portability proof (the new, load-bearing gate):** the asset is test-composited into
   the actual Stage B candidate room (or a generic neutral placeholder scene) and
   checked for lighting plausibility, believable edge/contact behaviour, and the absence
   of any visible residue from the original mockup's own scene (a shadow or reflection
   that only made sense in a context this asset no longer lives in).
6. **Re-derivability check:** confirm the shading/displacement layers can actually be
   adjusted against a *new* base's luminosity information without redoing the full
   compositing from the raw TIFFs — proving the portability goal was structurally
   achieved, not just hoped for.
7. Zero AI-generated content anywhere in the asset's own construction — unconditional,
   unchanged from every other gate set in this project.
8. Explicit human sign-off that the result, once dropped into the actual Stage B
   candidate scene, looks convincingly integrated — not merely technically compliant on
   a checklist.

---

## 7. Documentation requiring amendment (identified only, not implemented)

- **`STAGE_B_PREBUILD_AUDIT_KF-PRD-000463.md`** — Section 2 needs revision to reflect the
  three-way distinction in Section 1 above and correct the literal-pixels assumption;
  Section 9 needs a note that the Portable Asset is explicitly *not* registered under
  either existing dimension, per Section 5 above.
- **`PHOTOSHOP_PRODUCTION_METHOD_KF-PRD-000463.md`** — needs a new section distinguishing
  the Stage A Master PSD (scene-bound, complete, already correct) from the Portable
  Composite Asset (a distinct deliverable, built with shading/displacement kept as
  reusable layers rather than flattened).
- **`MEDIA_PRODUCTION_BRIEF_KF-PRD-000463.md`** — Section 3's sourcing checklist needs a
  note distinguishing Stage A base-sourcing criteria from the stricter, portability-
  focused criteria in Section 3 of this audit.
- **`MEDIA_PILOT_EXECUTION_PLAN.md`** — no correction to its own (closed, valid) Stage A
  acceptance criteria; a note should eventually reference that Stage B's own future
  closure depends on the new gate set in Section 6 above, in addition to what's already
  there.
- **`FLOW_ROOM_BACKGROUND_TASK_KF-PRD-000463.md`** — **does not need amendment.** This
  document concerns generating the room only; it makes no assumption about how the
  curtain itself is prepared, so it is unaffected by this correction.

None of these edits are made in this audit — this is the list to action next, separately.

---

## Current State

Stage A remains valid, approved, and closed as Product Media — nothing about that status
changes. A real technical constraint was discovered during Stage B preparation, before
any Stage B media was produced: the Stage A deliverable's pixels are scene-bound, not
portable, making the original plan to composite them directly into a new room
unworkable. No Stage B compositing has occurred; this was caught in time.

## Risks

**Critical**
- **If a genuine Portable Composite Asset isn't actually built** — if the correction is
  skipped and the Stage A JPG is reused anyway on the theory that it's "close enough" —
  the same lighting/edge/contact failure will recur in the finished hero image, silently
  undermining the whole premium/gold-standard premise. This is the one risk this audit
  exists to close, not a residual one left open.

**Major**
- Building a genuinely portable asset is real, non-trivial additional production work —
  not a documentation fix, a cost worth naming plainly rather than understating.
- The new sourcing criteria (Section 3) are unproven — the first attempt at a Portable
  Asset could itself fail to generalize if the chosen mockup's lighting still isn't
  neutral/re-derivable enough. This is exactly why Gate 5/6 (Section 6) exist as
  mandatory proof, not optional nice-to-haves.
- Risk of future confusion between Product Media and the Portable Composite Asset if the
  documentation amendments (Section 7) aren't actually made before this work continues —
  precision here matters as much as the technical fix itself.

**Minor**
- Not registering the Portable Asset in Business Metadata means it has less formal
  traceability than Product or Marketing Media — an accepted, deliberate gap for now, not
  an oversight.

**Observation**
- This correction mirrors the same evidence-based discipline already applied twice
  earlier in this project (the SKU-collision rejection of `artwork_relationship =
  "Mockup"`, the 3D-vs-licensed-mockup sourcing correction) — a real problem caught
  before it compounded, not papered over. Worth recognizing as a healthy pattern, not
  just a one-off fix.

## Findings

Three distinct artifact types now need to be held apart conceptually and in
documentation, where only two existed before. The Stage B audit's compositing assumption
needs a precise, narrow revision — not a reopening of the workflow's core principles
(room-only generation, human QC, zero AI touch on the artwork all remain exactly as
locked). Selection criteria and acceptance gates for the new artifact can be fully
specified now. Business Metadata should explicitly not be extended to cover it yet — the
existing architecture doesn't have an honest slot for it, and inventing one now would be
premature. A precise, bounded list of documentation needing amendment has been
identified, deliberately not yet actioned.

## Recommendation

Adopt the corrected model: build a genuine Portable Curtain Composite Asset from the
original TIFF masters, using scene-agnostic technique, proven against the Section 6 gates
before it is trusted for any Stage B compositing. Do not register it in Business
Metadata. Amend the five identified documents as a separate, subsequent task.

## Verdict

**Revised.** The underlying Stage B goal and workflow remain sound and approved in
spirit — nothing about room-only generation, human QC, or the prohibition on AI touching
the artwork changes. What is revised is narrow and specific: which artifact Stage B
actually composites, corrected from "the literal Stage A JPG" to "a dedicated Portable
Composite Asset built from the same original masters." This is not a rejection of Stage B,
and it does not reopen or invalidate Stage A.

## Next Action (one single action only)

**Source and select a candidate curtain PSD mockup against the Section 3 portability-
focused criteria** — separate shading/displacement layers, neutral baseline lighting,
clean isolatable panels, commercial license — as the base for constructing the Portable
Curtain Composite Asset. Documentation amendments and Flow prompt work remain deferred
until that asset exists and passes the Section 6 gates.
