# Stage B Marketing Media — Pre-Build Audit (KF-PRD-000463)

> Status: **AUDIT ONLY. Documentation only.** No code, no Flow prompts, no media
> generated, no scaling to other products, no reopening of the locked Stage A
> architecture. Governed by `ARCHITECTURE_MEDIA_WORKFLOW_SOP.md`,
> `MEDIA_PILOT_EXECUTION_PLAN.md`, `MEDIA_PRODUCTION_BRIEF_KF-PRD-000463.md`,
> `PHOTOSHOP_PRODUCTION_METHOD_KF-PRD-000463.md`, and
> `ARCHITECTURE_ADR_PHASE3_CLOSURE.md`.

> **Closure note:** Stage B for `KF-PRD-000463` is now closed —
> see `STAGE_B_CLOSURE_KF-PRD-000463.md`. Section 2's assumption below (that Stage A's
> literal flattened pixels would be the compositing source) was found incorrect during
> production and superseded by `PORTABLE_CURTAIN_ASSET_AUDIT_KF-PRD-000463.md`. The rest
> of this document's content — allowed/prohibited transformations, the reference
> hierarchy, and the QC gate definitions — stood as the governing standard Stage B was
> actually measured against and closed on.

---

## 1. Should Stage B begin now, on this same product, or does another Stage A proof come first?

**Begin now, on this same product. A second Stage A proof is not required, and requiring
one would be inventing a new gate the locked architecture doesn't specify.**

The locked SOP's own Stage B eligibility condition (Section 7) is exactly two things: all
Stage A gates passed, and Business Metadata registration complete. Both are now true for
`KF-PRD-000463`, verified with actual evidence, not attestation alone. Nothing in the
locked documents conditions Stage B on a *second, unrelated* product having also passed
Stage A first.

The important distinction to hold onto here: **Stage B on the same product is not
scaling.** Scaling means starting Stage A on a *new* product (a second curtain, a
cushion, a tapestry) — that remains correctly out of scope. Progressing from Stage A to
Stage B on the *same* product is simply completing this one pilot's full lifecycle, which
is what the pilot was always defined to prove — the Production Brief's own Section 8
already recommended a first Stage B asset "using the approved Product Media as
reference," on this same product, before this audit was ever commissioned.

---

## 2. The exact role of approved Stage A Product Media in Stage B

`KF-PRD-000463_MOCKUP_PAIR_v01.jpg` is the **fidelity anchor** for everything Stage B
produces — not one input among several, but the thing every other input is checked
against.

Concretely: Stage B must not re-derive the curtain's appearance independently from the
raw TIFF masters. Doing so would re-open exactly the fidelity risk Stage A's nineteen
gates were built to close — wrong scale, wrong orientation, subtly wrong colour, none of
which a second, separate compositing pass is guaranteed to avoid just because the first
one succeeded. Instead, **the approved Stage A image is the literal source the curtain
portion of any Stage B image is built from** — composited in, not reinterpreted. Stage B
has real creative latitude over everything *around* the curtain; it has none over the
curtain itself.

---

## 3. Allowed and prohibited transformations in AI-generated marketing imagery

**Allowed — confined to the room/background/context, never the curtain:**
- Generating or extending room environments, furniture, props, ambient mood.
- Lifestyle photographic treatment (depth of field, framing, seasonal/thematic styling)
  of the surrounding scene.
- Camera angle variation for the overall composition, provided the curtain portion still
  reads as the same verified product, not reinterpreted to fit a new angle.

**Prohibited, unconditionally:**
- Any reinterpretation, regeneration, or AI-driven recreation of the curtain's own
  pattern content, in whole or in part — this is Stage B's equivalent of Stage A's Gate 9,
  and it is not weaker for being Stage B.
- Mirroring or swapping L/R, under any framing or justification.
- Adding, removing, or altering any illustrated element, typography, or wave-band
  structure within the artwork.
- Blending or panorama-continuing the two panels into one continuous image.
- Colour-correcting the curtain itself away from its Stage A-verified values — including
  as a side effect of a whole-image mood grade (see the Major risk on this below).
- Any output that could be mistaken for, or substituted in place of, Product Media — the
  locked principle that "Marketing Media never becomes artwork truth" applies with full
  force here.
- Generative fill or any AI editing applied directly to the curtain region, even for
  minor cleanup.

---

## 4. Reference hierarchy

1. **Original TIFF artwork masters** (`P4186-L.tif` / `P4186-R.tif`) — the ultimate
   ground truth for the pattern content itself. Authoritative for resolving any dispute
   about what the artwork actually depicts.
2. **Approved Stage A Product Media** — the verified representation of the *product*
   (pattern + fabric behaviour + geometry, already QC'd). Authoritative for how the
   product should look as a physical object, and the primary input for Stage B's curtain
   content specifically.
3. **Room/style references** — mood boards, brand tone, market positioning. Informative
   for styling decisions only (room type, era, palette of the surroundings). Never
   authoritative over anything curtain-related.
4. **Text prompt instructions** — the lowest authority in this hierarchy. A prompt
   describes intent for the room/context/mood only. If a prompt's instructions would
   imply altering the curtain's appearance in any way, the prompt is out of bounds — not
   the artwork.

---

## 5. Safest workflow for premium lifestyle/hero media while preserving exact L/R identity

Generate or source the room/background **separately and completely independently** from
the curtain, then **composite the already-approved Stage A curtain content into that
environment in Photoshop.** At no point does a generative tool's output contain curtain
pixels. This directly extends the Production Brief's already-locked Section 8
recommendation (Photoshop first, using the approved Product Media as reference) into a
firm structural rule for how any future AI involvement must work, not just a sequencing
preference for who goes first.

---

## 6. Should Flow generate the complete image, or room/background only?

**Room/background only, followed by Photoshop compositing of the untouched Stage A
curtain asset. Not the complete image, and not curtain content generated even under
image-to-image reference conditioning.**

Reasoning: a single "generate everything, curtain included" pass puts the pattern inside
the AI's generative process, where zero-reinterpretation cannot be guaranteed — directly
violating the principle carried over from Stage A. Even reference-conditioned generation
("recreate a room around this curtain") is not the same guarantee as compositing the
literal, already-verified pixels — generative models approximate; they do not reproduce
fine pattern detail, exact typography, or precise asymmetry with certainty. Generating
*only* the negative space the curtain gets composited into afterward is the only version
of this workflow that gives an actual guarantee rather than a "probably close enough"
result.

---

## 7. Stage B output types for this pilot only

**Exactly one deliverable: a single lifestyle/hero image**, produced via the workflow in
Section 5–6, for `KF-PRD-000463` only. Explicitly **not** in scope for this pilot:
multiple room variations, seasonal variants, social-media crops, or anything approaching
a full PDP gallery — all of that is catalogue-scale production, out of bounds here by the
same discipline that kept Stage A to one product.

---

## 8. Marketing Media QC gates

| # | Gate | What it checks |
|---|---|---|
| 1 | L/R identity | The composited curtain in the final image verified side by side against Stage A Product Media — Left is still Left, Right is still Right, same relative position. |
| 2 | No mirroring or swapping | Explicit re-check on the *finished composited image*, not just the isolated asset — same discipline as Stage A Gates 12/13. |
| 3 | Exact pattern fidelity | The composited curtain region is the untouched Stage A asset — no independent regeneration, no pixel-level alteration. |
| 4 | Typography preservation | Legibility re-confirmed after compositing — new room lighting/shadow must not obscure text that Stage A already verified. |
| 5 | Colour truth | The curtain's own colours (black/white/yellow/turquoise) still read correctly against the Stage A reference, even under the new scene's ambient lighting or mood grade. |
| 6 | Material realism | The curtain plausibly belongs in the generated room — consistent scale, consistent implied light direction between room and curtain. This is a compositing-quality gate, distinct from pattern fidelity. |
| 7 | Lighting consistency | The generated room's implied light direction must be plausible relative to the curtain's own baked-in Stage A shadow/highlight information — a mismatch is an immediate failure. |
| 8 | Room styling quality | Genuinely premium, market-appropriate, uncluttered, consistent with brand positioning. **The one gate that is legitimately more a creative judgment call than a mechanical check** — worth naming as such, not treated as equally objective as Gates 1–7. |
| 9 | Premium Karen brand fit | Overall tone consistent with the brand's established visual language — a reference point, not a literal colour-matching requirement against the site's typographic/digital brand tokens. |
| 10 | Absence of AI artifacts | 100%-zoom inspection of the *generated room specifically* — warped geometry, impossible objects, hallucinated text/pattern in furniture or decor, inconsistent internal shadow. A genuinely new inspection surface Stage A never had, since Stage A contained zero AI-generated pixels. |

All ten apply to the finished, composited deliverable — none are satisfied by the room
and the curtain each looking fine in isolation.

---

## 9. Stage B metadata registration convention (existing architecture, unchanged)

Directly extends the already-locked Section 8 convention — Marketing Media ties to
**Design**, not Product, since it concerns the artwork/mood generally rather than one
sellable variant:

```python
db.set_metadata(
    entity_type="design",
    entity_id="KF-D-000344",
    dimension="marketing_media",
    value="APPROVED|<filename-once-produced-and-approved>"
)
```

Illustrative only — no Stage B deliverable exists yet, so no real filename is asserted
here. The convention itself requires no architecture change; it is the same
`set_metadata()` mechanism, the same additive-only behaviour, the same `STATUS|reference`
value format already verified working for Stage A.

---

## 10. Findings

**Critical**
- **If a generative tool ever produces curtain pixels directly — even reference-guided —
  fidelity cannot be guaranteed.** This is why Section 6's rule is structural, not a
  preference: the workflow must make it *impossible* for the curtain to pass through
  generation, not merely discourage it.
- **Without Gate 3 specifically checking that the composited curtain region is the
  unaltered Stage A asset**, there is no mechanical way to catch an accidental
  regeneration or alteration after the fact — this gate is load-bearing, not routine.

**Major**
- **Whole-image colour grading is a real risk to colour truth (Gate 5) even without
  touching the curtain layer directly** — a global mood grade applied across a flattened
  composite would shift the curtain's rendered colours as a side effect. Grading must be
  scoped to the room specifically (a clipping mask excluding the curtain region), not
  applied globally after flattening.
- **Lighting-direction mismatch** between an independently generated room and the
  curtain's own baked-in Stage A shadow information is a real, likely failure mode if not
  checked deliberately (Gate 7) — generative room outputs have no inherent awareness of
  the curtain's existing light logic.
- **Gates 8–9 are inherently more subjective than the rest.** This isn't a flaw to
  correct — Marketing Media legitimately involves creative judgment Product Media
  doesn't — but it should be named plainly so "premium brand fit" isn't quietly treated
  with the same mechanical certainty as "no mirroring."

**Minor**
- No resolution/aspect-ratio target has been set for Stage B hero imagery specifically.
  Stage A's 2048×2048 square target was defined for product photography; a lifestyle
  hero image may reasonably use a different aspect ratio (e.g. wider, for web banner
  use). Not decided here — a real open production detail, not an architecture gap.

**Observation**
- This is the first point in the entire project where AI *generates* pixels, rather than
  *analysing* existing ones (colour extraction, vision review). The room-only-generation
  structural rule is really just this project's standing principle — AI touches only the
  parts of the system where creative latitude is safe, never the parts requiring exact
  fidelity — applied to a genuinely new capability category for the first time.

---

## 11. Verdict

**Approved.** The workflow is fully specified, the risks have concrete structural
mitigations already built into the recommended approach (not open problems awaiting a
future decision), and the QC gates give Stage B the same rigor discipline Stage A had,
correctly adapted for what Marketing Media actually is. Nothing here required reopening
Stage A's locked architecture, the Business Metadata mechanism, or the L/R identity
decision.

## Next Action (one single action only)

**Commission the Flow room/background-only prompt as its own separate, dedicated task —
not undertaken in this document, per the explicit instruction not to generate Flow
prompts yet.** That task's only job is producing a room/background image containing zero
curtain content, ready for Photoshop compositing against the approved
`KF-PRD-000463_MOCKUP_PAIR_v01.jpg` per the workflow defined here.
