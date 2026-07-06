# Curtain Media Production SOP v1

> Status: **OPERATIONAL SOP. Synthesis of proven, closed pilot evidence — not an
> architecture redesign.** Documentation only. No code, no metadata written, no assets
> registered, no new Product/Design IDs, no Flow prompts generated, no reopening of
> Stage A/Stage B for `KF-PRD-000463`, no expansion to cushions or other categories.
> `ARCHITECTURE_MEDIA_WORKFLOW_SOP.md` remains the governing architecture; this document
> operationalizes it using what production actually proved, including one corrected
> assumption and one methodology-generalization test.

---

## 1. Purpose and scope

This SOP converts the curtain media workflow proven through the `KF-PRD-000463` pilot
into a repeatable process for **curtain products specifically.** It does not redefine
any locked architecture — Business Metadata remains the only linkage mechanism, the
Product Media / Marketing Media distinction remains as locked, and nothing here invents
a new dimension or entity type. Where the pilot's evidence was product-specific, this SOP
says so explicitly rather than presenting it as universal. Cushions, tapestries, and any
other category remain out of scope until their own pilots establish category-specific
rules — nothing here should be assumed to already apply to them.

---

## 2. Required prerequisites before production starts

- **Live-verified identity** — Design ID, Product ID, and every relevant Asset ID,
  confirmed by a read-only query against the system of record. Never assumed from a
  filename or from memory. (Proven practice: `KF-PRD-000463`'s identity was confirmed via
  a `mode=ro` SQLite connection before any Photoshop work began — a connection mode that
  makes a write impossible at the engine level, not just procedurally discouraged.)
- **Confirmed high-resolution master source files** (`.tif`/`.psd` or equivalent),
  verified to exist and to meet or exceed the intended output resolution — not assumed
  from a listing. (`KF-PRD-000463`'s masters were confirmed at 4110×8504px, comfortably
  above the 2048×2048 export target, before compositing began.)
- **Artwork type determined** — asymmetric L/R pair, repeat pattern, or single
  continuous (Section 13) — before choosing a base or planning compositing, since this
  determines which QC gates and which technique apply.
- **A recent database backup**, if any Business Metadata registration is anticipated at
  the end of the workflow.

---

## 3. Artifact taxonomy and ownership rules

| Artifact | What it is | Portable? | Registered? |
|---|---|---|---|
| **Product Media** | Exact-fidelity representation of a product, in its own specific, scene-bound base. Never needs to travel. | No — by design, not a defect. | Yes — `entity_type="product"`. |
| **Portable Curtain Composite Asset** | The curtain content only, built with shading/displacement kept as separate, reusable layers, deliberately scene-agnostic. | Yes — that is its entire purpose. | **Never.** Neither existing dimension describes it; do not invent one. Tracked by filename/folder only. |
| **Marketing Media** | The finished lifestyle/hero deliverable, built *from* the Portable Asset composited into a new scene. | No — it is itself the finished output. | Yes — `entity_type="design"`. |
| **Portability Proof / methodology-test evidence** | Evidence that the *compositing methodology* generalizes — may deliberately use different, ungoverned artwork as a stress test. | N/A — it is validation evidence, not a production artifact. | **Never.** No governed identity exists to register against, structurally, not by policy choice alone. |

**Historical note, stated accurately rather than smoothed over:** the original locked
SOP defined only the first and third rows. Production experience surfaced the second row
as a real, necessary category — and the fourth as a distinct kind of evidence, not a
production artifact at all. Both additions were resolved without touching Business
Metadata; nothing here required an architecture change to accommodate them.

---

## 4. Folder and filename conventions

**Governed production material** (Product Media, Portable Assets, Marketing Media):
```
KF-PRD-<product_id>_<ARTIFACT_TYPE>[_<qualifier>]_v<NN>.<ext>
```
Examples from the closed pilot: `KF-PRD-000463_MOCKUP_PAIR_v01.jpg` (Product Media),
`KF-PRD-000463_MARKETING_HERO_v01.jpg` (Marketing Media). The product-ID prefix means
**ownership** — this file depicts that product.

**Methodology-test / Portability Proof material using non-owned artwork — new rule,
resolving a previously-identified gap:** must **never** use a real Product ID as a
filename prefix, even to indicate "used this pilot's methodology." That prefix's
established meaning throughout this project is ownership, and reusing it for a different
meaning is exactly the ambiguity risk identified during this pilot's closure. Going
forward:
```
METHOD-TEST_<short-description>_v<NN>.<ext>
```
stored under its own folder (e.g. `00_Methodology_Tests/`), not nested inside a specific
product's own folder. **This rule is prospective only** — it does not rename or move any
already-existing file, including the `KF-PRD-000463/90_Portability_Proof/` artifacts from
this pilot, whose governance status is already correctly documented in
`PORTABILITY_METHODOLOGY_TEST_AUDIT.md` and is not altered by this SOP.

---

## 5. Stage A Product Media workflow

1. Verify identity and source masters (Section 2).
2. Source or select a base scene appropriate to *this specific product* — a licensed
   mockup or photograph is the proven default for a first/small-scale run (see Section
   16 on why this is a default, not a permanent rule).
3. Composite per the proven Photoshop technique (Section 8) — independent per-side or
   per-instance Smart Objects, methodology-based displacement tuning, extracted
   shadow/highlight, per-instance independent tonal protection, texture, edge/hem
   handling, per-source colour verification.
4. Run the Stage A QC gates (the original ten, plus any artwork-type-specific gates from
   Section 13) — all must pass; none are satisfied by "looks acceptable overall."
5. Explicit human sign-off, as its own distinct statement.
6. Register: `entity_type="product"`, `dimension="product_media"`,
   `value="APPROVED|<filename>"`.

---

## 6. Portable Curtain Asset workflow

Distinct from Stage A, not a byproduct of it:

1. Select a base **specifically for portability** — separated, non-destructive
   shading/displacement layers, and relatively **neutral** baseline lighting (not
   necessarily the same base used for Stage A, which may legitimately have more specific
   or dramatic lighting since it never needed to travel).
2. Composite the **same governed source masters**, using the same technique discipline
   as Stage A — this is not a lower-rigor pass because the output is "just" an
   intermediate asset.
3. Verify against the eight Portable Asset gates
   (`PORTABLE_CURTAIN_ASSET_AUDIT_KF-PRD-000463.md` Section 6) — with the artwork-type
   caveat that some gates (wave-band alignment, L/R-specific checks) apply only to
   asymmetric-pair artwork and are correctly marked not-applicable, not failed, for other
   artwork types.
4. **Never register.** Track by filename/folder location only, as a working production
   file.

---

## 7. Stage B room/background sourcing or generation workflow

The room/background must contain **zero curtain content and zero pattern content of any
kind** — generated (e.g. via Flow) or sourced as a licensed photograph, either way. The
proven technique for AI generation specifically: state the exclusion from both the
positive prompt (describing the opening as explicitly bare) and the negative prompt
(naming every window-treatment variant separately) — generative models default toward
dressing windows with curtains unless told not to, repeatedly and specifically. Before
any compositing, run a room-acceptance QC pass (per
`FLOW_ROOM_BACKGROUND_TASK_KF-PRD-000463.md` Section 5, generalized): zero window
treatment, opening proportionate to the artwork type being inserted, clean negative
space, single consistent neutral lighting, no AI artifacts, explicit sign-off before
compositing begins.

---

## 8. Photoshop compositing workflow

The proven order of operations, generalized beyond the one pair it was first proven on:

1. Independent Smart Object per side/instance — never a shared or mirrored duplicate.
2. Geometric/perspective alignment first, no distortion yet.
3. Lock vertical anchor placement before displacement.
4. Displacement — tuned by methodology, not a fixed number: start conservative, test
   against a known reference point, increase only until the artwork convincingly follows
   the fold **and** typography/geometry remain undistorted. The correct value is the
   smallest one that works, tested at multiple points since fold depth varies across a
   drop — never assumed from a prior product's value.
5. Shadow pass — extracted from the base's own luminosity information, Multiply
   (darkens without shifting hue — a general property of the blend mode, not a
   product-specific choice).
6. Highlight pass — extracted the same way, applied non-destructively. **No specific
   blend mode is mandatory for every curtain.** The universal rule is at the principle
   level: extract and preserve the curtain form/lighting information non-destructively,
   and protect tonal extremes independently (step 8 below) — the exact blend mode and
   adjustment layers must be selected and validated against *that specific artwork and
   base's* own tonal behaviour, not copied from a prior product by default.
   *Pilot-specific example, not a universal rule:* for `KF-PRD-000463`, Screen was
   chosen over Overlay specifically because it was more controllable for that pair's
   dark/light asymmetry (Overlay would have compounded with the separate shadow pass and
   risked over-darkening the dark panel). A different artwork with a different tonal
   range may call for a different choice — validate against the actual result, don't
   assume this example transfers.
7. Fine texture — Soft Light, low opacity, after shadow/highlight so it reads as sitting
   on the now-lit surface.
8. **Per-instance independent tonal protection** — the general principle behind what was
   first proven as "protect the white panel / protect the black panel": any light-toned
   content needs a highlight cap to avoid blowing out; any dark-toned content needs a
   shadow floor to avoid crushing fold detail. Tune each instance independently; never
   assume one opacity value — or one blend mode — serves every instance or every
   product.
9. Edge, hem, and seam handling.
10. Per-source colour verification — independently, never one global adjustment across
    multiple sources.
11. Flatten only the export; the working file keeps every layer.

---

## 9. Foreground occlusion workflow, where applicable

Proven by the Portability Proof evidence: when a room includes foreground furniture that
should overlap the curtain (a chair, a table edge), that element must exist as its **own
distinct layer, stacked above the curtain composite group** — never baked flatly into the
room background. This keeps the depth relationship editable and is what makes the
occlusion read as genuine depth rather than a flat pasted overlap. Apply this whenever a
scene calls for foreground occlusion; it is not specific to any one room or product.

---

## 10. QC gates and stop conditions at each stage

No stage proceeds on an unresolved gate — proven directly by this pilot's own history
(a room candidate was rejected for an undersized opening before any compositing began,
rather than compositing onto it and hoping). Concretely:

- **Stage A** — ten gates (`PHOTOSHOP_PRODUCTION_METHOD_KF-PRD-000463.md` Section 15),
  plus artwork-type-conditional gates (Section 13). Failing any gate stops progress to
  Portable Asset or Stage B work.
- **Portable Asset** — eight gates (Section 6). Failing any gate means the asset is not
  trusted for Stage B compositing, regardless of how good Stage A looked.
- **Stage B room acceptance** — the room-specific checklist (Section 7). Failing any
  item means regenerate or re-source, not compositing onto a flawed candidate.
- **Stage B final** — ten gates (`STAGE_B_PREBUILD_AUDIT_KF-PRD-000463.md` Section 8).
  Failing any gate stops registration.

---

## 11. Human sign-off requirements

A sign-off is its own **explicit, separate statement** — never inferred from a technical
description of the evidence alone, no matter how favourable that description sounds.
Required at: Stage A approval, Portable Asset approval, Stage B approval, and — if a
methodology/portability test is performed — its own explicit sign-off, scoped precisely
to what was actually tested (proven practice: a sign-off can explicitly state what it does
*not* cover, e.g. "this does not assert identity for the test artwork," and that scoping
must be preserved exactly as given, not paraphrased away).

---

## 12. Metadata registration rules

**Registered:**
- Product Media → `entity_type="product"`, `entity_id=<Product ID>`,
  `dimension="product_media"`, `value="APPROVED|<filename>"`.
- Marketing Media → `entity_type="design"`, `entity_id=<Design ID>`,
  `dimension="marketing_media"`, `value="APPROVED|<filename>"`.

**Never registered, under any dimension:**
- The Portable Curtain Composite Asset — no existing dimension honestly describes a
  reusable production input; do not force it into one.
- Portability Proof / methodology-test evidence — structurally impossible when the test
  artwork has no governed identity, and not to be attempted even if the artwork later
  becomes governed, without a fresh, deliberate decision at that time.

**No new Business Metadata dimension may be created under this SOP.** If a genuine,
recurring need to formally track Portable Assets emerges, that requires its own separate
architecture decision — not an SOP-level workaround.

---

## 13. Decision tree for artwork type

```
Does the artwork consist of two independently composed scenes that are NOT
interchangeable and must not be mirrored, swapped, or panorama-continued?
  -> YES: Asymmetric L/R pair
          Proven: KF-PRD-000463.
          Gates: L/R assignment, no swap, no mirror, no false panorama, preserve
          relative alignment of any coordinating element (e.g. shared bands), preserve
          intended asymmetric contrast.

  -> NO: Is it one motif tiling continuously, with colour differences treated as
        variants of one design, not separate designs?
    -> YES: Repeat pattern
            Exercised (methodology only): the Portability Proof test, using ungoverned
            floral artwork -- proves the COMPOSITING METHODOLOGY generalizes to this
            type; does NOT constitute a governed repeat-pattern product having been
            through this workflow. No governed repeat-pattern curtain product has yet
            completed this SOP end to end.
            Gates: L/R "swap"/wave-band gates do not apply; repeat-scale consistency
            and seamless tiling across fold geometry do.

    -> NO: Is it one continuous image meant to visually continue across the panel gap?
      -> YES: Single continuous artwork
              Defined here for completeness. Not yet proven by any pilot evidence.
              Treat any real use as a fresh, small pilot -- do not assume this SOP's
              general steps are sufficient without validating them against this
              specific, unproven case first.
```

---

## 14. Decision tree for output type

```
What are you producing right now?
  -> The definitive, exact-fidelity photo of this product, in its own scene
     -> Product Media (Section 5)
  -> A reusable, scene-agnostic version of the curtain content, for future compositing
     -> Portable Curtain Composite Asset (Section 6)
  -> A finished lifestyle/hero image, built from a Portable Asset in a new scene
     -> Marketing Media (Section 7-8)
  -> Evidence that the methodology itself works, possibly on different/ungoverned
    artwork, not a customer-facing or registrable deliverable
     -> Portability Proof (governed by PORTABLE_CURTAIN_ASSET_AUDIT_KF-PRD-000463.md
        Section 6 gates and the naming rule in Section 4 above)
```

---

## 15. Production metrics to record

- **Candidate count before acceptance**, per stage — real precedent: one room candidate
  was rejected for architectural scale before a second was accepted. Tracking this over
  time reveals whether prompt/sourcing quality is improving.
- **QC gate failure counts, by specific gate** — identifies recurring failure points
  across products, not just within one.
- **Elapsed time or iteration count**, base-sourcing to Stage A approval, and Stage A
  approval to Stage B approval.
- **File sizes/resolutions** of masters, working PSDs, and final deliverables — supports
  backup and storage planning.
- **Portable Asset reuse count** — whether a single Portable Asset was successfully used
  for more than one Stage B attempt without rebuilding from raw masters. This is the
  direct efficiency measure of whether "build once, reuse" is actually paying off, not
  just theoretically sound.

---

## 16. Explicit exceptions and unresolved limitations

- **Single continuous artwork** is defined but has zero pilot evidence. Do not treat this
  SOP's general steps as pre-validated for it.
- **The Portable Asset has no formal registration or traceability today.** If this
  becomes a frequent, real need, that is a future architecture decision, not something
  this SOP resolves by itself.
- **Identity and colour-truth gates are permanently unanswerable for any test using
  ungoverned artwork** — not a pending gap, a structural fact. This SOP does not, and
  must not, claim the Portability Proof test verified governed identity or colour truth
  for the floral test artwork; that limitation, as recorded exactly in
  `PORTABILITY_METHODOLOGY_TEST_AUDIT.md`, is preserved here without softening.
- **The naming-convention fix in Section 4 is prospective only** — existing Portability
  Proof files from this pilot are not renamed or moved by this SOP.
- **Marketing Media's resolution/aspect-ratio target remains an open production
  decision**, not fixed here — carried forward from the original Stage B pre-build audit,
  unresolved then and unresolved now.
- **The licensed-mockup base-sourcing default (Section 5) was deliberately right-sized
  for a first, small-scale run.** Treat it as the current default, not a permanent
  prohibition on ever building reusable 3D capability if production volume later
  justifies that investment.

---

## 17. Compact operator checklist (daily production use)

- [ ] Identity verified live (Section 2) — not from memory or a filename.
- [ ] Masters confirmed to exist, at adequate resolution (Section 2).
- [ ] Artwork type determined (Section 13) before choosing a base or technique.
- [ ] Output type determined (Section 14) before starting work.
- [ ] Base sourced/selected appropriate to *this* artifact's portability needs
  (Section 5 vs Section 6).
- [ ] Compositing follows the proven order of operations (Section 8) — displacement
  tuned by method, not copied from a prior product's number.
- [ ] Foreground occlusion, if any, is its own layer above the composite (Section 9).
- [ ] All gates for this stage checked individually — none inferred from "looks fine"
  (Section 10).
- [ ] **STOP GATE: if any required QC gate for this stage is FAIL or unresolved, do
  not proceed to the next stage.** Fix or re-source and re-check before advancing —
  never carry an unresolved gate forward on the assumption it will be fine (Section 10).
- [ ] Explicit, separate sign-off recorded — not implied by a favourable description
  (Section 11).
- [ ] Registration, if any, uses only the rule in Section 12 — nothing new invented,
  Portable Assets and Portability Proof evidence never registered.
- [ ] Filenames follow Section 4 — product-owned material uses the product prefix;
  methodology-test material never does.
- [ ] Metrics logged per Section 15 before moving to the next product.
