# Pre-Merge Audit — CURTAIN_MEDIA_PRODUCTION_SOP_V1.md

> Status: **AUDIT ONLY. No repository file modified, including the SOP itself.** No
> code, no metadata, no registration, no Flow prompts, no reopening of any closed pilot,
> Stage A, Stage B, or Portability Proof. No expansion to other categories.

---

## Current State

`CURTAIN_MEDIA_PRODUCTION_SOP_V1.md` exists as a drafted, not-yet-merged operational
document, synthesized from nine closed governing/pilot documents. This audit checks it
against those source documents and against the fourteen specific risk categories
requested, before it becomes the standard anyone actually follows.

## Risks

**Critical** — none found anywhere in the document.

**Major**
- **Confirmed: a pilot-specific, conditionally-justified technique was generalized into
  an unconditional mandate.** Section 8, step 6 states "Screen (not Overlay), to avoid
  compounding with the separate shadow pass" as a flat rule. The source document
  (`PHOTOSHOP_PRODUCTION_METHOD_KF-PRD-000463.md`) gives the *same* instruction but with
  an explicit condition the SOP dropped: Screen was recommended "more controllable
  **given this pair's dark/light asymmetry**." The SOP presents a choice that was
  justified for one specific, high-contrast case as if it were universally correct for
  any curtain artwork's tonal range. Confirmed by direct textual comparison, not
  inference.
- **The compact operator checklist (Section 17) does not contain an explicit,
  standalone stop-gate line.** The detailed SOP's Section 10 states the single most
  load-bearing principle in the whole document — "no stage proceeds on an unresolved
  gate" — and real pilot history exists specifically because this discipline was
  followed (a room candidate was rejected before compositing began, not after). The
  checklist references Section 10 by number but never states the advancement-blocking
  rule as its own explicit line; "all gates checked individually" implies but does not
  say "and do not proceed if any fail."
- **First-use validation for unproven artwork structures is directionally correct but
  under-specified.** Section 13/16 correctly say "treat any real use of single
  continuous artwork as a fresh, small pilot," but never define what minimum rigor that
  pilot must clear (a full Stage A + Stage B cycle with its own explicit sign-off, by
  analogy to `KF-PRD-000463`?). Left undefined, different future operators could apply
  inconsistent rigor to the same unproven case.

**Minor**
- Section 7's "the proven technique" (stating the prompt-exclusion approach) reads more
  prescriptive than the underlying claim needs — the *behavioural fact* about generative
  models is genuinely general, but the phrasing doesn't leave room for equally valid
  alternative phrasing approaches achieving the same result.
- Section 9 labels the foreground-occlusion layering technique "proven by the
  Portability Proof evidence." This is accurately sourced (it does not claim governed
  product status) but "proven" is a strong word for a structural Photoshop technique
  observed once; "demonstrated" would be marginally more precise.

**Observation**
- Section 4's discussion of the existing (unrenamed) Portability Proof files reads as
  correctly scoped — prospective-only, explicitly not reopening the closed audit — worth
  a second reader's confirmation, but I did not find an actual violation on close
  reading.

---

## Findings — the fourteen specific checks

1. **Pilot-specific technique generalized into a mandatory universal rule:** **Found** —
   Section 8 step 6 (see Major risks above). This is the confirmed, real instance of
   exactly the risk this audit was commissioned to catch.
2. **Architecture change introduced without authorization:** **Not found.** No new
   entity_type, no new dimension, no Artwork Source reintroduction, no schema change
   anywhere in the document.
3. **Metadata rule inconsistent with locked architecture:** **Not found.** Section 12's
   two registered categories and their exact `entity_type`/`dimension` pairs match the
   locked SOP and the actually-executed, actually-verified registrations exactly.
4. **Confusion between the four artifact categories:** **Not found.** The Section 3
   taxonomy table is consistently referenced throughout; no section conflates Product
   Media with the Portable Asset or Marketing Media with Portability Proof evidence.
5. **Ungoverned floral artwork treated as governed product evidence:** **Not found.**
   Every reference to it (Sections 9, 13, 16) explicitly labels it as Portability Proof
   evidence, and Section 16 contains an explicit, direct statement preserving the exact
   limitation from `PORTABILITY_METHODOLOGY_TEST_AUDIT.md` without softening.
6. **Repeat-pattern claimed as a completed governed product lifecycle:** **Not found.**
   Section 13 explicitly states the opposite: "does NOT constitute a governed
   repeat-pattern product having been through this workflow. No governed repeat-pattern
   curtain product has yet completed this SOP end to end."
7. **Single continuous artwork claimed as proven:** **Not found.** Explicitly stated as
   unproven in both Section 13 and Section 16.
8. **First-use validation explicit enough for unproven structures:** **Partially —
   directionally correct, under-specified.** See Major risks above.
9. **Naming/folder rules preserve ownership and traceability:** **Yes, and this is a
   genuine strength of the document.** The new `METHOD-TEST_` rule directly resolves a
   previously-identified, real governance gap, and does so prospectively without
   touching existing files.
10. **Compact checklist consistent with the detailed SOP, no omitted load-bearing stop
    gate:** **One omission found** — see Major risks above (the explicit stop-gate line).
    Everything else in the checklist maps correctly to its corresponding detailed
    section.
11. **Human sign-off requirements preserved:** **Yes.** Section 11 correctly requires an
    explicit, separate statement at every stage and explicitly preserves the precedent
    that a sign-off can state its own scope limits.
12. **Registration allowed only for approved Product/Marketing Media under existing
    dimensions:** **Yes, confirmed exactly as required.**
13. **Portable Assets and Portability Proof evidence explicitly non-registered:** **Yes,
    stated plainly and repeated in the operator checklist itself, not just cross-
    referenced.**
14. **Separation of universal rules / proven methodology / pilot-specific examples /
    unproven cases:** **Mostly clean, with the one confirmed exception in Section 8
    step 6** — this is the same underlying issue as finding #1, surfacing again under
    this lens.

---

## Section-by-section audit result

| Section | Result |
|---|---|
| 1. Purpose and scope | Clean |
| 2. Prerequisites | Clean — pilot-specific numbers correctly presented as examples, not requirements |
| 3. Artifact taxonomy | Clean |
| 4. Naming/folder conventions | Clean — resolves a real prior gap correctly |
| 5. Stage A workflow | Clean — base-sourcing correctly framed as a default, not a mandate |
| 6. Portable Asset workflow | Clean |
| 7. Stage B room sourcing | Clean, with a Minor wording note |
| 8. Photoshop compositing | **Major issue confirmed — step 6 blend-mode over-generalization** |
| 9. Foreground occlusion | Clean, with a Minor wording note |
| 10. QC gates and stop conditions | Clean in the detailed text itself |
| 11. Human sign-off | Clean |
| 12. Metadata registration rules | Clean — matches locked architecture exactly |
| 13. Artwork-type decision tree | Clean — explicit, correct unproven/methodology-only labeling |
| 14. Output-type decision tree | Clean |
| 15. Production metrics | Clean |
| 16. Exceptions and limitations | Clean — does most of the document's safety work well |
| 17. Compact operator checklist | **Major issue — missing explicit stop-gate line** |

---

## The flagged special-attention question, answered directly

- **Is the underlying principle (extract shadow/highlight from the base, apply via blend
  modes, protect tonal extremes independently) safely generalizable?** **Yes.** Step 8's
  "per-instance independent tonal protection" is correctly written at the level of a
  principle, with no invented numbers and no unconditional mandate — this part of the
  generalization was done correctly.
- **Is the exact Photoshop implementation (Screen, never Overlay) incorrectly
  mandatory?** **Yes — confirmed.** This is the one place the generalization overreached,
  by dropping the original document's own stated condition.
- **Does the current wording already preserve sufficient operator flexibility?**
  **No, not in step 6 specifically.** Step 8 preserves flexibility correctly; step 6 does
  not.

---

## Blocking corrections required before merge

1. **Section 8, step 6** — reword to restore the original conditional reasoning: Screen
   is the demonstrated choice *for high-contrast, asymmetric-tone artwork* (worked
   example: `KF-PRD-000463`), not an unconditional rule. The operator should be told to
   choose based on the artwork's own tonal range, with the Screen-over-Overlay
   compounding-shadow reasoning offered as a worked example, not a blanket instruction.
2. **Section 17** — add an explicit, standalone checklist line stating the advancement-
   blocking rule directly: work does not proceed to the next stage while any gate for
   the current stage remains unresolved.

## Non-blocking future validation notes

- Define a minimum concrete validation protocol for any future unproven artwork
  structure (e.g., single continuous artwork) before one is actually attempted — "treat
  as a fresh, small pilot" should eventually specify what that pilot must include.
- Consider softening Section 7's "the proven technique" to "a proven technique" and
  Section 9's "Proven" to "Demonstrated," for precision, though neither is a safety
  issue.

---

## Final verdict

**Revised.** Not Approved — two Major, confirmed, correctable issues exist. Not
Rejected — the document's architecture, registration rules, and artifact-category
discipline are all sound; nothing here is fundamentally broken. Not Audited Further —
nothing more needs investigating; what needs to happen is a specific, known, small
correction to specific, named lines.

## SAFE TO MERGE — **NO**

Not because the document is unsafe in a broad sense, but because it contains one
confirmed instance of exactly the failure mode this audit was built to catch — a
pilot-specific, conditionally-justified choice presented as an unconditional rule — and
merging it as-is would let that instruction propagate to future products where the
condition that justified it may not hold.

## Next Action (one single action only)

**Correct the two blocking items identified above** — Section 8 step 6's blend-mode
conditionality and Section 17's missing stop-gate line — in a separate, explicit editing
task, then re-submit for a follow-up pre-merge check before this becomes the operational
standard.
