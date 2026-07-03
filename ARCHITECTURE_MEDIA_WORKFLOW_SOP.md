# Pre-Build Audit / SOP — Gold-Standard Media Workflow (Pilot: One Curtain)

> Status: **AUDIT + SOP. No code, no implementation prompts.** This resolves the one
> architectural question the Phase 3 closure ADR deliberately left open — is composited/
> generated media a Derived Artwork Source, or a separate class? A narrow contract check
> (below) found the originally-proposed mechanism (`artwork_relationship = "Mockup"`)
> would silently corrupt SKU generation, reproduced against the running code. The
> corrected model — Business Metadata for both media classes — is what the rest of this
> document specifies.

---

## Narrow Contract Check — was `artwork_relationship = "Mockup"` safe to add?

**Verdict: No. Rejected on the merits, with reproduced evidence — not a Derived Artwork
Source relationship. The SOP below reflects the corrected model.**

The original proposal treated a pattern-accurate mockup the same way a cropped cushion is
treated: a Derived Artwork Source of the Design. That analogy breaks down on inspection,
and the break is concrete, not stylistic.

**Why the analogy fails.** A cropped cushion's pixels *are* the curtain's own pixels — the
same photographed/rendered material, reduced. A Kickflip-style mockup composites the exact
pattern onto an **entirely separate base image** (folds, backdrop, rod, lighting, shadow)
that has nothing to do with the artwork's own identity. It is still the *same product*
(a Curtain), just presented — not a different application of the artwork to a different
product type, which is what "Derived" was built to model (Curtain → Cushion).

**The concrete failure this would cause, reproduced against the real running code:**
```
REAL product:   KF-PRD-000001 -> SKU: KF-CUR-000001-L
MOCKUP product: KF-PRD-000002 -> SKU: KF-CUR-000001-L   <- IDENTICAL SKU, different product_id
Total Curtain-type products on this one design: 2  (should always be exactly 1)
```
SKU generation (`sku.py`) is a pure function of `(product_type, design_id, side)` — it has
no awareness of `origin`, `artwork_relationship`, or `source_id`. Any second Artwork
Source sharing the same `product_type` and `side` as the original — regardless of
`origin` — silently produces a **second product with a colliding SKU**. Nothing in the
current schema prevents this at write time; it would only surface downstream (e.g. two
different products competing for the same Shopify handle). This is exactly the kind of
silent contract erosion the check was asked to catch, and it would have shipped invisibly
if the SOP alone had "approved" the relationship value without checking against the code.

**The corrected model.** Both Product Media and Marketing Media use the **same existing
mechanism** — Business Metadata — differentiated only by dimension, never by mechanism.
`set_metadata()` is explicitly documented to have "no effect on IDs, SKUs, design
identity, or compatibility," which is precisely the property needed here: media references
must never be able to spawn a phantom product or collide with a real SKU. Product Media
earns its "governs product truth" status through the **QC discipline and traceability**
defined below, not by being modeled as if it were sellable inventory.

---

## The architectural decision this resolves — LOCKED

**Status: LOCKED.** This is now an adopted architectural decision, not a proposal under
review. Reopening it requires the same discipline that closed it — a deliberate,
evidenced re-check — not a quiet exception for one convenient case.

- **Product Media is not an Artwork Source.**
- **Marketing Media is not an Artwork Source.**
- **Both are linked through Business Metadata only.**
- **Product Media earns trust through Product Truth QC**, not through identity or
  artwork lineage.
- **Marketing Media remains downstream creative output** and never becomes artwork
  truth.
- **No product, SKU, design, asset, or source identity is ever affected by media
  registration** — linking or unlinking media can never mint, alter, or delete a
  product, a Source, or a SKU.

**Decision: two media classes, one linkage mechanism, differentiated by dimension and by
the fidelity discipline applied before linking — no new Artwork Source relationship, no
schema change.**

| | **Product Media** | **Marketing Media** |
|---|---|---|
| **What it is** | The exact catalogued pattern, composited onto a controlled mockup base. Zero creative reinterpretation. Fidelity-governed, tied to what the customer is actually buying. | Lifestyle, hero, campaign, social, AI-generated contextual imagery. May be creative, but never artwork truth. |
| **Fidelity requirement** | Must pass Product Truth QC (below) before it exists as an approved asset. | Must remain linked to the product/design; fidelity to the literal pattern is not the point. |
| **Where it lives in the data model** | `business_metadata`: `entity_type="product"`, `dimension="product_media"`, value = `"APPROVED\|<file reference>"` (filename already encodes Product/Design ID + side, per Section 2). | `business_metadata`: `entity_type="design"`, `dimension="marketing_media"`, value = `"APPROVED\|<file reference>"`. |
| **Who/what produces it** | Human, in Photoshop, from a QC-verified source pattern. | AI (Google Flow or similar), only after Product Media is approved. |

This reuses `set_metadata()` (v1.6) exactly as it already works — proven, tested,
identity-safe by construction. **Nothing here requires new code to be functionally
correct.** A dedicated ingestion tool (for convenience at scale) remains legitimate future
work, not built here.

---

## 1. Asset class: product media vs. marketing media

Settled above (and corrected by the contract check). The dividing line is fidelity, not
file format, tool used, or data-model mechanism — both classes link the same way
(Business Metadata). If it claims to show the real pattern, it's Product Media and must
pass Product Truth QC before it exists as an approved asset. If it's mood/context/
generated scenery, it's Marketing Media and must never be presented as, or confused with,
an accurate depiction of the product.

**This line must never move by default.** A future person adding "just one AI-touched
product shot" without going through this distinction — or a future change that models
Product Media as an Artwork Source without re-running the contract check above — would be
exactly the kind of default-by-accident decision this document exists to prevent.

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

## 4. QC checklist (two stages — Product Truth QC must pass first, always)

Per requirement #9: Product Truth and Marketing Quality are **separate QC passes**.
Nothing proceeds to Marketing Quality QC — or to any AI generation step — until Product
Truth QC has passed in full.

### Stage A — Product Truth QC (hard gates, all mandatory)

1. **Identity verification.** Confirm Product ID, Design ID, Asset ID, and the correct
   L/R side **before compositing begins** — looked up against the system of record
   (`db.get_vision()` / the product's Artwork Sources), never assumed or eyeballed. This
   is the highest-risk single step in the whole workflow (see Critical risk below) and
   must happen first, not as an afterthought.
2. **Orientation.** No unintended flip (horizontal or vertical) or rotation of the pattern
   relative to the source artwork.
3. **Repeat scale.** Pattern repeat scale verified against the intended physical product
   dimensions — a mockup that silently rescales the repeat misrepresents what the
   customer will actually receive.
4. **Crop and placement.** Commercially strong composition, without misrepresenting the
   actual product (e.g. hiding a repeat seam that would be visible in reality, or cropping
   out a design element that's actually part of the pattern).
5. **Colour fidelity.** Matches the approved artwork; no unwanted warm (or any directional)
   colour grading introduced by the mockup's rendering or lighting in shots intended to be
   colour-truth references.
6. **Realistic fabric behaviour.** Folds, seams, hems, heading style, translucency,
   gravity, and shadow all read as physically plausible for the actual product — not
   generic or implausible drape that would misrepresent how the fabric hangs.
7. **Lighting purpose, distinguished deliberately.** For curtains specifically: backlight
   used for translucency/pattern-glow shots, raking side light used for fold/texture
   shots — these serve different evidentiary purposes and should not be conflated or
   substituted for each other without a reason.
8. **100% zoom artifact inspection.** Every mockup inspected at full pixel resolution for
   mask edges, warped motifs, duplicated elements, AI/rendering artifacts, impossible
   folds, and inconsistent shadow direction — a defect invisible at thumbnail size is
   still a defect.
9. **Zero generative/AI elements present.** This is Product Media; any AI touch at this
   stage disqualifies it from the gold-standard category, full stop.
10. **Filename and folder correct.** Matches the Section 2 naming convention exactly
    (including the `<side>` tag) and sits in `00_Working` until every gate above passes.

**Only after all ten items pass** does the file move to `01_Product_Mockups` and get
linked into the Asset Manager as an `"APPROVED|…"` entry (Section 8). This is the gate for
"gold standard," not a subjective judgment call.

### Stage B — Marketing Quality QC (separate pass, Product Media only as input)

Applies only to Marketing Media, and only once the Product Media it's built from has
already passed Stage A in full. Composition, mood, brand consistency, and platform framing
are evaluated here — but this pass never re-litigates pattern fidelity, since that was
already the entire point of Stage A. A defect in Stage B never excuses skipping Stage A;
they are independent, sequential gates, not alternates.

### Benchmark

**The first curtain product to pass both stages becomes the gold-standard benchmark** —
the concrete reference future mockups are judged against, not just a description in this
document. Nothing scales to cushions or tapestries until that benchmark exists and has
been reviewed.

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

## 8. How final media links back to Asset Manager product/design IDs — LOCKED

Neither media class ever becomes an Artwork Source or a Product — both link via
**Business Metadata only** (`set_metadata` / `get_metadata` / `find_by_metadata`),
explicitly guaranteed to have no effect on IDs, SKUs, identity, or compatibility. This
section specifies the exact, simple convention — grounded in what the existing API
actually does today, not a capability that doesn't yet exist.

**What the real API supports today, precisely:** `set_metadata()` is additive only
(`INSERT OR IGNORE`) — there is no update or delete method. Any design for "status" or
"reversibility" has to work within that, not assume a capability that isn't there.

**The convention:**

- **Dimension:** `"product_media"` for Product Media, `"marketing_media"` for Marketing
  Media. `entity_type="product"` for Product Media (tied to the sellable unit),
  `entity_type="design"` for Marketing Media (tied to the artwork generally, per Section 2).
- **Value format:** a single, explicit, human-readable string — `"<STATUS>|<file
  reference>"`. No JSON, nothing opaque. Example:
  `set_metadata("product", "KF-PRD-000001", "product_media", "APPROVED|KF-PRD-000001_MOCKUP_L_v01.jpg")`
- **The file reference itself already encodes Product ID, Design ID, and side** (Section
  2's naming convention), so every link is independently verifiable in both directions —
  from the database out to the file, and from the filename back to a specific, checkable
  ID — without needing to trust the metadata row alone.

**How this stays reversible without a delete operation:** nothing is ever destructively
removed — consistent with this project's data-preservation discipline everywhere else
(never silently lose a record). "Reversing" a link means **recording a new status
entry**, not deleting the old one:
- Superseding v01 with v02: write `"SUPERSEDED|…_v01.jpg"` and `"APPROVED|…_v02.jpg"` as
  two new rows. The v01 approval record still exists — an honest history, not an erased
  one.
- Rejecting a link made in error: write `"REJECTED|…_v01.jpg"` as a new row.
- The **current, effective** link for a product is: the most recent row (by `created_at`,
  a real column already in the schema) for that entity+dimension whose status is
  `APPROVED`. This is a plain, documented query pattern against the existing table — not
  new application code, just how to read what's already there.

**Explicitly deferred, not built here:** a convenience helper (e.g. "get the current
approved media for this product" in one call) would make the query pattern above nicer to
use, but is legitimate future tooling work, not part of this SOP. For this pilot, linking
is a manual, documented action — a human runs `set_metadata()` once per status change, the
same way early acceptance work was done by hand before `vision_accept.py` existed.

---

## Risks

**Critical**
- **Wrong side/source used in the mockup.** This is not hypothetical — real production
  data from this same catalogue showed 80% of fully-analysed curtain pairs have genuinely
  different Left/Right artwork. Compositing the wrong side's pattern into a mockup would
  produce a confidently wrong "gold standard." Stage A gate #1 exists specifically because
  of this measured, real risk, not as a generic caution.
- **Modeling Product Media as a Derived Artwork Source (the original proposal) — checked,
  reproduced, and rejected.** Confirmed against the running code: a same-product-type
  Derived Source silently produces a second product with a colliding SKU (`KF-CUR-000001-L`
  generated by two different `product_id`s simultaneously), and a design incorrectly ends
  up with two "Curtain" products where exactly one should exist. Closed by the corrected
  model above (Business Metadata only) — recorded here so the reasoning stays visible for
  whoever reads this later, not just the conclusion.

**Major**
- **No automated verification (yet) that the composited pattern actually matches the
  claimed source ID.** For this pilot, that check is entirely human (Stage A gate #1). A
  future perceptual-hash comparison between the smart object's source layer and the
  actual asset file is a reasonable later enhancement, explicitly deferred here.
- **Naming/folder discipline is a human process risk**, not a code risk, until a
  dedicated tool exists. Mitigated by making the convention in Sections 2–3 as explicit
  and ID-anchored as possible.

**Minor**
- PSD storage location/backup coverage is not yet decided — connects to, but does not
  reopen, the backup work just completed.

**Observation**
- Once proven on one curtain, scaling to cushions and tapestries is a **rollout of this
  same SOP**, not a new design — the Business Metadata linkage and the two-stage QC
  discipline already generalize across product types without modification, and without
  any of the collision risk the rejected model would have introduced.

---

## Pilot scope and scale-up gate

**In scope now:** one curtain product, through the full pipeline — correct-source
verification, Photoshop compositing, the full two-stage QC checklist, manual linking via
`set_metadata()`.

**Explicitly not in scope now:** any code/tooling, any AI generation (Flow or otherwise),
scaling to a second product of any type, exact export-resolution specs for Shopify.

**Gate before scaling to cushions/tapestries:** the one curtain pilot completes the full
checklist, is reviewed, and the linking step is confirmed correct in the database — the
same "prove one small thing before widening" discipline this project has used at every
prior phase (one image before a batch, one accept before bulk). Scaling to a second
product type should not begin until that review has actually happened, not once the
pattern merely "seems like it'll work."
