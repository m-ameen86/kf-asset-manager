# Pre-Build Audit / SOP — Gold-Standard Media Workflow (Pilot: One Curtain)

> Status: **AUDIT + SOP. No code, no implementation prompts.** This resolves the one
> architectural question the Phase 3 closure ADR deliberately left open (is a generated
> or composited image a Derived Artwork Source, or a new asset class?) — for the specific
> pilot approved: Kickflip-style pattern-accurate mockup first, AI room/hero context only
> after human approval, on one curtain product before scaling.

---

## The architectural decision this resolves

The ADR named this as unmade on purpose, because answering it by default (rather than
deliberately) was the risk. The pilot's own shape answers it cleanly: a mockup that must
preserve **exact pattern fidelity** is not the same kind of thing as a **AI-generated
room scene**, and they should not be modeled the same way.

**Decision: two distinct asset classes, mapped onto two pieces of infrastructure that
already exist and are already proven — no new schema, no new table.**

| | **Product Media** (this pilot) | **Marketing Media** (later, gated) |
|---|---|---|
| **What it is** | The exact catalogued pattern, composited onto a controlled mockup base. Zero creative reinterpretation. | AI-generated room/lifestyle context. Mood and composition, not a literal product record. |
| **Fidelity requirement** | Must be traceable, pixel-faithful to a specific Artwork Source. | Not required — that's not its job. |
| **Where it lives in the data model** | A new **Derived Artwork Source** of the existing Design — the same mechanism already used for cropped cushions. New `artwork_relationship` value: `"Mockup"`. | **Business Metadata** — the existing generic entity/dimension/value table, tagging the design/product with a reference, not claiming to be the artwork. |
| **Who/what produces it** | Human, in Photoshop, from an approved source pattern. | AI (Google Flow or similar), only after Product Media is approved. |

This reuses `ensure_source()` (v2.0-a) and `set_metadata()` (v1.6) exactly as they already
work. **Nothing here requires new code to be functionally correct** — only a dedicated
ingestion tool (to make it convenient rather than a manual one-off) would be future work,
and that is explicitly not in scope for this document.

---

## 1. Asset class: product media vs. marketing media

Settled above. The dividing line is fidelity, not file format or tool used: if it claims
to show the real pattern, it's Product Media and must be traceable to a specific,
verified Artwork Source. If it's mood/context/generated scenery, it's Marketing Media and
must never be presented as, or confused with, an accurate depiction of the product.

**This line must never move by default.** A future person adding "just one AI-touched
product shot" without going through this distinction would be exactly the kind of
default-by-accident decision this document exists to prevent.

---

## 2. File naming

Keyed to opaque KF IDs, never to English/marketing text — consistent with how the source
library itself is named (codes, not descriptions).

**Product Media (mockups):**
```
KF-PRD-<product_id>_MOCKUP[_<side>]_v<NN>.psd    (working file, smart object intact)
KF-PRD-<product_id>_MOCKUP[_<side>]_v<NN>.jpg    (flattened deliverable)
```
`<side>` (`L`/`R`/blank for unsided) is **required whenever the product has more than one
Source** — see the Critical risk below on why this is non-negotiable, not a nicety.

Example: `KF-PRD-000001_MOCKUP_L_v01.psd` / `.jpg`

**Marketing Media (later, gated):**
```
KF-D-<design_id>_MARKETING-HERO_v<NN>.jpg
```
Keyed to the **Design**, not the Product — a mood/lifestyle image is about the artwork
generally, not a specific sellable variant.

**Version numbers** (`v01`, `v02`…) always increment on re-composite; never overwrite a
prior version in place. QC failures produce a new version, not a silent edit.

---

## 3. Folder structure

A new top-level area, separate from the raw source library — these are **outputs**
derived from approved source, not catalog inputs:

```
05_Media/
├── 00_Working/              draft PSDs, pre-QC — not yet approved, not yet linked
│   ├── Curtains/
│   ├── Cushions/
│   └── Tapestries/
├── 01_Product_Mockups/      approved, exact-fidelity — the "gold standard" deliverables
│   ├── Curtains/
│   ├── Cushions/
│   └── Tapestries/
└── 02_Marketing/            AI-generated, approved Product Media only, clearly gated
    ├── Curtains/
    ├── Cushions/
    └── Tapestries/
```

Nothing moves from `00_Working` into `01_Product_Mockups` without passing the QC
checklist below. `02_Marketing` stays empty for this pilot until a Product Mockup has
been approved for that specific product.

---

## 4. QC checklist (Product Media — must pass before anything is "gold standard")

- [ ] **Correct Source/side verified against the system of record** — looked up via
  `db.get_vision()` / the product's Artwork Sources, not eyeballed or assumed. This is
  the single highest-risk step (see Critical risk below).
- [ ] Pattern scale and repeat match the source artwork exactly — no stretching,
  squashing, or unintended tiling drift.
- [ ] Colour fidelity — the mockup's rendered colours match the source pattern, not
  shifted by the mockup base's lighting/rendering.
- [ ] Correct product-type base used (a curtain base, not a cushion or tapestry base).
- [ ] Filename matches the naming convention exactly, including the correct `<side>` tag.
- [ ] **Zero generative/AI elements present** — this is Product Media; any AI touch at
  this stage disqualifies it from the gold-standard category.
- [ ] Export format/resolution meets the intended downstream use (exact platform specs
  are a separate, later decision — not blocking this pilot).
- [ ] Reviewer identified and sign-off recorded (even if that's just you, for now — the
  point is an explicit, recorded approval step, not an implicit one).

Only after every item passes does the file move from `00_Working` to
`01_Product_Mockups` and get linked into the Asset Manager (Section 8).

---

## 5. What is manual vs. AI

| Step | Manual | AI |
|---|---|---|
| Selecting the correct source pattern | ✅ (verified against system of record) | |
| Photoshop compositing (smart object, masking) | ✅ | |
| QC / approval gate | ✅ (always — never automated, never skipped) | |
| Colour extraction, existing vision pipeline | *(already built, untouched by this SOP)* | ✅ *(unchanged, separate)* |
| Room/lifestyle scene generation | | ✅ — **only after Product Media is approved** |

The existing vision pipeline (colour, naming, tags) is a completely separate, already-
proven system and this workflow does not touch it, extend it, or depend on it.

---

## 6. When Google Flow (or any generative image tool) is allowed

- **Never** for Product Media, in this pilot or as a standing rule until a future,
  equally deliberate decision revisits it.
- **Only** after the corresponding Product Mockup has passed QC and is sitting in
  `01_Product_Mockups`.
- **Only** for Marketing Media, and the output must be clearly labeled as AI-generated in
  its filename/metadata — the same honesty discipline already applied to `vision_results`
  (nothing AI-produced is ever allowed to masquerade as verified fact).
- Marketing Media generation is **out of scope to actually build or run in this pilot** —
  this document only defines the boundary for when it becomes allowed later.

---

## 7. How the Photoshop overlay fits

The `.psd` (with the smart object) is the **working source of truth for the mockup
itself** — not disposable scratch. The smart object must reference a specific, identified
source pattern file (traceable to a `KF-AST-…` asset ID), not "whatever was dragged in."
Keeping the PSD means a future change to the mockup base template doesn't require redoing
the compositing work from scratch — the pattern can be re-rendered into a new base.

The flattened `.jpg`/`.png` export is the **deliverable** that actually gets used
downstream (Shopify, etc.). Both PSD and export follow the naming convention in Section 2
and live together once approved.

**Storage note:** a smart-object PSD represents real, non-trivial human compositing
effort — closer in kind to the non-derivable data the recent backup work protects than to
freely-regenerable output. Worth keeping in mind when deciding where `05_Media/` lives
relative to backup coverage; not re-litigated here, just flagged as a live connection to
the backup work just completed.

---

## 8. How final media links back to Asset Manager product/design IDs

**This works today, with zero new code**, using functions that already exist and are
already tested:

- **Product Media** → recorded as a Derived Artwork Source of the Design:
  `ensure_source(design_id, "Curtain", origin="Derived", artwork_relationship="Mockup", derived_from_source=<original_source_id>, side=<L/R/None>)`
  — exactly the same call shape already proven for derived cushions in v2.0-a, just a new
  `artwork_relationship` value.
- **Marketing Media** (once it exists, later) → recorded via
  `set_metadata(entity_type="design", entity_id=design_id, dimension="marketing_media", value=<file reference>)`
  — the existing, already-tested Business Metadata table, purely as a tag/pointer, never
  as identity.

For this pilot, that linking step is a **manual, documented action** — a human runs the
existing function once, the same way early acceptance work was done by hand before
`vision_accept.py` existed. A dedicated ingestion command (to make this convenient at
scale) is legitimate future work, but is explicitly not built here.

---

## Risks

**Critical**
- **Wrong side/source used in the mockup.** This is not hypothetical — real production
  data from this same catalogue showed 80% of fully-analysed curtain pairs have genuinely
  different Left/Right artwork. Compositing the wrong side's pattern into a mockup would
  produce a confidently wrong "gold standard." The QC checklist's first item exists
  specifically because of this measured, real risk, not as a generic caution.

**Major**
- **No automated verification (yet) that the composited pattern actually matches the
  claimed source ID.** For this pilot, that check is entirely human — a future perceptual-
  hash comparison between the smart object's source layer and the actual asset file is a
  reasonable later enhancement, explicitly deferred here.
- **Naming/folder discipline is a human process risk**, not a code risk, until a
  dedicated tool exists. Mitigated by making the convention in Sections 2–3 as explicit
  and ID-anchored as possible.

**Minor**
- PSD storage location/backup coverage is not yet decided — connects to, but does not
  reopen, the backup work just completed.

**Observation**
- Once proven on one curtain, scaling to cushions and tapestries is a **rollout of this
  same SOP**, not a new design — the Derived-Source mechanism and the QC discipline
  already generalize across product types without modification.

---

## Pilot scope and scale-up gate

**In scope now:** one curtain product, through the full pipeline — correct-source
verification, Photoshop compositing, QC checklist, manual linking via `ensure_source()`.

**Explicitly not in scope now:** any code/tooling, any AI generation (Flow or otherwise),
scaling to a second product of any type, exact export-resolution specs for Shopify.

**Gate before scaling to cushions/tapestries:** the one curtain pilot completes the full
checklist, is reviewed, and the linking step is confirmed correct in the database — the
same "prove one small thing before widening" discipline this project has used at every
prior phase (one image before a batch, one accept before bulk). Scaling to a second
product type should not begin until that review has actually happened, not once the
pattern merely "seems like it'll work."
