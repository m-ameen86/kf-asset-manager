# Gold-Standard Media Pilot — Execution Plan (One Curtain Product)

> Status: **EXECUTION PLAN, REVISED WITH VERIFIED EVIDENCE. No code, no automation, no
> batch.** Operates strictly within the locked `ARCHITECTURE_MEDIA_WORKFLOW_SOP.md`.
> Both blockers from the prior version are now resolved with real, read-only-verified
> data — no identity reference in this document is provisional.

---

## Verified evidence (resolves both prior blockers)

**Identity mapping — confirmed against the live database:**

| Reference | Value |
|---|---|
| Curtain Product (pilot scope) | `KF-PRD-000463` |
| Design | `KF-D-000344` |
| Left asset | `KF-AST-000618` — `P4186-L.jpg`, master `P4186-L.tif`, **4110 × 8504 px** |
| Right asset | `KF-AST-000620` — `P4186-R.jpg`, master `P4186-R.tif`, **4110 × 8504 px** |
| Cushion products from the same design | `KF-PRD-000462`, `KF-PRD-000464` — **explicitly excluded from this pilot** |

**High-resolution source blocker — resolved, removed.** Both sides have a genuine `.tif`
production master at 4110 × 8504 px — far above the 2048 × 2048 px Shopify export
target, with substantial headroom for zoom, print, and re-crop. There is no fidelity
compromise in sourcing from these files. Compositing begins from the `.tif` masters, not
the `.jpg` catalog faces.

**L/R scope question — resolved by direct visual inspection, not assumption.** Left and
Right are **two different scenes**, intentionally designed as one **asymmetric** pair —
one side dark, one side light — coordinated by shared wave bands and a common palette
(black, ivory, yellow/gold, turquoise). They are:
- **not** interchangeable colourways,
- **not** a continuous panorama,
- **not** mirrorable or auto-continuable across the pair.

**Left-only is rejected as insufficient for the pilot.** A single side would misrepresent
what the product actually is — an intentionally asymmetric pair is only "the product"
when both sides are shown together. **Stage A Product Media must represent the complete
L+R pair as one coordinated deliverable.**

---

## 1. Choosing the best first curtain design

Selection criteria are unchanged from the original plan (full existing proof trail,
unambiguous identity, standalone design) and remain satisfied by the verified candidate.
**Confirmed pilot product: `KF-PRD-000463` / `KF-D-000344`.**

The two cushion products sharing this design (`KF-PRD-000462`, `KF-PRD-000464`) are
**explicitly out of scope** — this pilot governs the curtain product only. Nothing in
this plan authorizes, prepares, or implies cushion media work.

---

## 2. Required source files and identity references — verified

| Reference | Value | Status |
|---|---|---|
| Product ID | `KF-PRD-000463` | **Verified** |
| Design ID | `KF-D-000344` | **Verified** |
| Left Asset ID | `KF-AST-000618` | **Verified** |
| Right Asset ID | `KF-AST-000620` | **Verified** |
| Left source | `P4186-L.jpg` (catalog) / `P4186-L.tif` (master, 4110×8504px) | **Verified** |
| Right source | `P4186-R.jpg` (catalog) / `P4186-R.tif` (master, 4110×8504px) | **Verified** |
| Scope | Complete L+R pair, one coordinated deliverable | **Confirmed by inspection** |

No provisional identity references remain in this plan.

---

## 3. Blank curtain base / mockup specification

Unchanged from the original plan in its technical specification, with one structural
addition made necessary by the confirmed asymmetric pair:

**Resolution and aspect ratio** — Shopify's current, consistently-recommended standard
(verified this session): 2,048 × 2,048 px, 1:1 square, for the final export; minimum
800×800 for zoom to function; upload ceiling 5,000×5,000px / 20MB. The 4110×8504px
masters comfortably support this with room to spare.

**One master base, two panels within it.** The base mockup must depict **both curtain
panels together, correctly positioned Left and Right**, in one continuous scene (a
two-panel window/curtain setup) — not two separate, disconnected base images. This is
what makes it possible to judge the pair's relative alignment and intended dark/light
contrast as a single composition, which is the entire point of treating this as one
pilot deliverable rather than two.

**Room type, camera angle, lighting, fabric behaviour:** unchanged from the original
plan — neutral market-agnostic living-room setting, straight-on eye-level angle, soft
diffused primary lighting for the colour-truth/fold-texture shot, backlit translucency
variant still explicitly optional and deferred for this pilot.

---

## 4. Photoshop workflow — each TIFF mapped independently to its correct physical panel

1. **Source prep, per side, independently.** Open `P4186-L.tif` and `P4186-R.tif`
   separately. Colour-calibrate/soft-proof each against its own reference — they are
   different scenes with an intentional dark/light contrast, so they must **not** be
   colour-matched to each other. Matching them would destroy the intended contrast this
   pair is designed around.
2. **Repeat scale lock, per side.** Each TIFF's physical scale is set independently
   against the real product dimensions for its own panel — no shared scale assumption
   between L and R.
3. **Two independent Smart Objects, explicitly labeled.** Place `P4186-L.tif` as its own
   Smart Object layer, named/labeled with its Asset ID (`KF-AST-000618`); place
   `P4186-R.tif` as a separate Smart Object layer, labeled with its Asset ID
   (`KF-AST-000620`). This layer-level labeling is what preserves per-side traceability
   inside the working file — the flattened export can't encode two Asset IDs in its
   filename alone, so the PSD's own layer structure carries that record.
4. **Positional lock: Left TIFF → left physical panel, Right TIFF → right physical panel.**
   No swap, no mirror, no flip, on either side, at any point in the workflow.
5. **No panorama bridging.** Do not extend, blend, or continue either scene across the
   panel boundary — the gap/seam between panels must read as two distinct compositions
   coordinated by the shared wave band and palette, not one image split in half.
6. **Wave-band alignment, deliberately checked.** The shared bottom wave-band element
   must align correctly in **relative** position and height between the two panels —
   this is a coordination cue, not a literal continuation, and needs to be verified as
   its own step, not assumed to fall out of independent placement.
7. **Geometric displacement, shadow/highlight, texture passes** — applied independently
   to each panel per the original plan's technique (Section 4 steps 5–8 of the prior
   version), preserving each scene's own fold geometry and lighting rather than sharing
   one displacement map across both.
8. **Flatten only the export**, never the working file. The PSD retains both labeled
   Smart Objects and every intermediate layer for future re-use or correction.

---

## 5. Stage A Product Truth QC procedure — expanded with pair-specific hard gates

The original ten SOP gates remain the governing checklist, **plus** the following
hard gates specific to this asymmetric pair, all mandatory:

**Original ten gates (Section 4/5 of the locked SOP), applied per panel where relevant:**
1. Identity verification — both Asset IDs, both filenames, confirmed against the system
   of record (now satisfied — see verified evidence above; re-confirm at QC time
   regardless, per the SOP's own discipline of never trusting a document over the live
   system).
2. Orientation — no unintended flip or rotation, **on either panel independently.**
3. Repeat scale — matches real physical dimensions, per panel.
4. Crop and placement — commercially strong, not misrepresentative.
5. Colour fidelity — each panel matches its **own** approved artwork; the intended
   dark/light contrast between panels is a feature to preserve, not an inconsistency to
   correct (see gate 10 below).
6. Fabric behaviour — folds, seams, hems, heading, gravity, shadow, physically plausible
   on both panels.
7. Lighting purpose distinguished — primary deliverable is the raking/soft-light
   colour-truth shot; backlit variant remains optional/deferred.
8. 100% zoom artifact inspection — **both panels**, full resolution.
9. Zero generative/AI elements present.
10. Filename and folder correct (Section 6 below).

**Additional hard gates, required by the confirmed pair structure:**
11. **Correct L/R assignment** — the Left TIFF is composited onto the physically left
    panel and the Right TIFF onto the physically right panel; verified explicitly, not
    inferred from layer order.
12. **No side swapping** — a distinct check from #11: confirm the finished composite
    hasn't had panels transposed at any export/flatten step.
13. **No mirroring** — neither panel is a flipped/mirrored copy of the other; they are
    two genuinely different source files and must remain visibly, compositionally
    different.
14. **No false panorama continuation** — the two scenes do not bleed, blend, or appear
    to continue into one another across the panel seam.
15. **Composition of each scene preserved** — nothing in the compositing process
    (crop, warp, displacement) has altered what each individual scene actually depicts.
16. **Typography preserved**, if present in either source — any text/lettering elements
    in the artwork must render clean, undistorted, and legible at the deliverable's
    final resolution.
17. **Vertical artwork placement preserved** — each scene's vertical positioning within
    its panel matches the source master, not shifted during compositing.
18. **Bottom wave-band structure and relative alignment preserved** — the shared band
    aligns correctly in height/position between panels, verified as an explicit,
    deliberate check (per Section 4 step 6), not assumed.
19. **Intended dark/light contrast preserved** — the two panels' brightness/mood
    difference is confirmed as intentional and intact, not accidentally corrected toward
    matching in colour grading or exposure.

All nineteen items — the original ten plus these nine — must pass before the file is
eligible to move forward. None are optional; none are satisfied by "looks fine overall."

---

## 6. File naming and folder placement — revised for the pair deliverable

```
05_Media/
├── 00_Working/Curtains/
│   └── KF-PRD-000463_MOCKUP_PAIR_v01.psd          ← working file; two labeled Smart
│                                                      Objects (KF-AST-000618, KF-AST-000620)
├── 01_Product_Mockups/Curtains/
│   ├── KF-PRD-000463_MOCKUP_PAIR_v01.jpg          ← flattened deliverable (2048x2048 export,
│   │                                                  once approved) — shows BOTH panels
│   └── KF-PRD-000463_MOCKUP_PAIR_v01_REVIEW.jpg   ← QC working copy, may carry zoom
│                                                      crops/annotations per gate
```

`_PAIR` replaces the earlier `_L`/`_R` side-suffix convention for this specific
deliverable, since the file represents both sources together, not one side. The
individual Asset IDs remain traceable through the PSD's own labeled layers (Section 4
step 3), not through the flattened filename.

---

## 7. The exact point of Stage B eligibility

Unchanged in mechanism: **only after all nineteen Stage A gates have passed AND the
pair deliverable has been registered in Business Metadata with `APPROVED` status**
(Section 9). Not before.

---

## 8. Recommendation for the first Stage B asset (no prompt generated)

Unchanged: **Photoshop-composited room styling first, Google Flow second**, for the same
reasoning as the original plan — the first-ever Stage B asset shouldn't be the least
controlled step in the whole pipeline. No prompt content is generated here.

---

## 9. Manual Business Metadata registration — verified IDs, existing capability only

Locked architecture unchanged — Business Metadata remains the only linkage mechanism,
`set_metadata()` remains the only write path. Applied here with the verified Product ID:

```python
db.set_metadata(
    entity_type="product",
    entity_id="KF-PRD-000463",          # verified
    dimension="product_media",
    value="APPROVED|KF-PRD-000463_MOCKUP_PAIR_v01.jpg"
)
```

One registration call, run once, only after all nineteen Stage A gates pass. This is
usage of an already-existing function — no schema or architecture change, consistent
with the locked SOP's Section 8.

---

## 10. Measurable acceptance criteria — pilot success

- [ ] All nineteen Stage A gates (original ten + nine pair-specific) passed and
  individually accounted for.
- [ ] Working PSD (`KF-PRD-000463_MOCKUP_PAIR_v01.psd`) exists with both TIFFs present as
  distinct, correctly labeled Smart Objects.
- [ ] Approved deliverable exists at `01_Product_Mockups/Curtains/`, correctly named,
  meeting the 2048×2048 1:1 export target.
- [ ] The deliverable shows both panels together, correctly assigned, unmirrored, not
  panorama-bridged, with the intended dark/light contrast and wave-band alignment intact.
- [ ] Business Metadata entry exists (`APPROVED|KF-PRD-000463_MOCKUP_PAIR_v01.jpg` under
  `entity_type="product"`, `entity_id="KF-PRD-000463"`, `dimension="product_media"`) and
  is independently retrievable via `get_metadata("product", "KF-PRD-000463")`.
- [ ] Explicit human sign-off recorded, separate from and after the checklist.
- [ ] Cushion products `KF-PRD-000462`/`KF-PRD-000464` remain untouched by this pilot.
- [ ] The result is genuinely usable as the literal benchmark future mockups (cushions,
  tapestries, additional curtains) will be judged against.

Only once every box is checked does scaling to a second product, of any type, become
appropriate.

---

## Internal consistency check

- No occurrence of the earlier provisional IDs (`KF-PRD-000001` / `KF-D-000001`) remains
  anywhere in this document — every reference now uses the verified `KF-PRD-000463` /
  `KF-D-000344` / `KF-AST-000618` / `KF-AST-000620`.
- No occurrence of a "Left-only" pilot scope remains — every section now specifies the
  complete L+R pair as one deliverable.
- Cushion products are named explicitly as out-of-scope in three places (Section 1,
  Section 6's acceptance criteria, and here) rather than left as an implicit assumption.
- File naming, QC gates, and the Business Metadata registration value all reference the
  same filename (`KF-PRD-000463_MOCKUP_PAIR_v01.jpg`) consistently.
- Stage B remains gated behind Stage A in Section 7; no Flow prompt appears anywhere in
  this document.
- Business Metadata remains the sole linkage mechanism; no Artwork Source reference was
  reintroduced anywhere in this revision.

## Current State

Both blockers from the prior version are resolved with verified, read-only-checked
evidence. Identity mapping is confirmed, high-resolution masters exist with substantial
headroom over the export target, and the L/R scope question is resolved by direct visual
inspection rather than assumption. No further verification is required before Photoshop
work can begin.

## Risks (updated)

**Critical** — none remaining. Both previously-Critical risks (wrong-side compositing,
wrong-resolution source) are closed by the verified evidence above; the expanded QC gate
list (11–19) exists specifically to keep the wrong-side risk closed *through* the
compositing process, not just at the identity-lookup stage.

**Major**
- No automated verification that the composite matches the claimed source IDs — remains
  entirely human, per the locked SOP, now with two independently-labeled Smart Objects to
  check rather than one.
- The intended dark/light contrast (gate 19) is a real judgment call at the edges — worth
  a second reviewer's eyes if available, since "was this contrast preserved or
  accidentally softened" is more subjective than the purely geometric gates.

**Minor**
- The optional backlit/translucency variant remains deferred; log it explicitly if this
  pilot completes without it, so it isn't silently forgotten at scale-up time.

**Observation**
- The confirmed complexity here (asymmetric pair, not a simple repeat) is actually a
  *harder* first case than a symmetric pair would have been — succeeding on this pilot
  sets a genuinely rigorous, not a lucky-easy, gold standard for cushions and tapestries
  to be judged against later.

## Findings

Every reference in this plan is now grounded in verified, read-only-checked data. The
plan requires no further architecture decisions — Business Metadata linkage, the QC gate
structure, and the file/folder convention all extend cleanly to the confirmed pair
scenario without any change to the locked SOP.

## Recommendation

**Ready to commit.** Both blockers are closed with real evidence, the plan is internally
consistent (checked above), scope remains exactly one curtain product with cushions
explicitly excluded, and no locked architecture was touched or reopened.

## Git

```bash
cd /Volumes/Work_4TB/kf-asset-manager
git add MEDIA_PILOT_EXECUTION_PLAN.md
git status
```
Confirm only `MEDIA_PILOT_EXECUTION_PLAN.md` is staged (or already tracked and modified —
check for anything unexpected before committing), then:
```bash
git commit -m "Revise media pilot plan with verified identity mapping and confirmed asymmetric L/R pair scope

Blockers resolved: identity mapping (KF-PRD-000463/KF-D-000344) and high-resolution
master verification (4110x8504px TIFFs) confirmed via read-only checks. Visual
inspection confirmed an intentional asymmetric L/R pair, not interchangeable/mirrorable
sides — pilot scope revised to require the complete pair as one Stage A deliverable.
Nine additional hard QC gates added for pair-specific integrity."
git push origin main
```

## Next Action (one single action only)

**Run the git commands above to commit and push the revised, verified plan** — no
further verification or document work is outstanding before Photoshop compositing can
begin on `KF-PRD-000463`.
