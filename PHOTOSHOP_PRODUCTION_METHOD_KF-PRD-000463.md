# Photoshop Production Pass Method — KF-PRD-000463

> Status: **PRODUCTION METHOD, EXECUTION-READY. Documentation only — no code, no
> automation, no Flow.** Scope: the Photoshop technique for making the artwork read as
> genuinely printed into the fabric, for this product only. Does not reopen the media
> architecture, Business Metadata linkage, product/asset selection, L/R assignment,
> blank-base sourcing decision, Flow generation, or Shopify publishing — all remain
> locked exactly as decided in `ARCHITECTURE_MEDIA_WORKFLOW_SOP.md`,
> `MEDIA_PILOT_EXECUTION_PLAN.md`, and `MEDIA_PRODUCTION_BRIEF_KF-PRD-000463.md`.

**Governing principle for this entire method:** the difference between "artwork placed
over fabric" and "artwork printed into fabric" is almost entirely about **whether the
artwork receives the fabric's own light information.** A flat layer looks pasted because
it exists in its own uniform lighting, disconnected from the folds beneath it. Every
technique below exists to make the artwork inherit the base's real shadow, highlight, and
geometric fold behaviour — never to add drama, and never to invent lighting that isn't
already present in the base.

---

## 1–2. PSD layer hierarchy and independent L/R Smart Object structure

```
KF-PRD-000463_MOCKUP_PAIR_v01.psd

├── 00_REFERENCE (non-printing, excluded from export)
│   ├── LEFT_KF-AST-000618_SOURCE_REF     (locked view-only copy of the original TIFF,
│   │                                       for soft-proof comparison throughout)
│   └── RIGHT_KF-AST-000620_SOURCE_REF
│
├── 01_BASE_SCENE (locked/reference — the sourced, licensed mockup, unedited)
│   ├── Base Flattened Reference
│   └── Base Luminosity Extraction          (derived once — see Sections 4/6/7 — the
│                                             single source for both displacement and
│                                             shadow/highlight maps)
│
├── 02_LEFT_KF-AST-000618
│   ├── Smart Object: LEFT_KF-AST-000618_ARTWORK      (pristine source, Normal, 100% —
│   │                                                   never blend-moded or destructively
│   │                                                   edited — see Section 9)
│   ├── LEFT_KF-AST-000618_DISPLACE                    (Smart Filter, non-destructive)
│   ├── LEFT_KF-AST-000618_SHADOW_MULTIPLY
│   ├── LEFT_KF-AST-000618_HIGHLIGHT_SCREEN
│   ├── LEFT_KF-AST-000618_LOCAL_CONTRAST              (fold-detail recovery — Section 11)
│   ├── LEFT_KF-AST-000618_TEXTURE
│   └── LEFT_KF-AST-000618_MASK                        (Section 13)
│
├── 03_RIGHT_KF-AST-000620   — mirrors the structure above exactly, independently:
│   ├── Smart Object: RIGHT_KF-AST-000620_ARTWORK
│   ├── RIGHT_KF-AST-000620_DISPLACE
│   ├── RIGHT_KF-AST-000620_SHADOW_MULTIPLY
│   ├── RIGHT_KF-AST-000620_HIGHLIGHT_SCREEN
│   ├── RIGHT_KF-AST-000620_SHADOW_RECOVERY            (detail protection — Section 10)
│   ├── RIGHT_KF-AST-000620_TEXTURE
│   └── RIGHT_KF-AST-000620_MASK
│
├── 04_EDGE_AND_HEM
│   ├── Top Edge / Heading Treatment
│   ├── Bottom Hem Treatment
│   └── Center Seam / Gap Contact Shadow
│
├── 05_COLOUR_MANAGEMENT (non-destructive, applied per panel via clipping masks — never
│   │                      one global adjustment across both panels)
│   ├── LEFT Soft-Proof Verification Clip
│   └── RIGHT Soft-Proof Verification Clip
│
└── 06_QC_OVERLAY (non-printing — zoom-inspection notes, gate-by-gate markers)
```

**Independence, structurally enforced, not just by convention:** each artwork Smart
Object contains *only* its own original TIFF — never a duplicate, never a flipped copy,
never linked to the other side. All displacement, shadow, highlight, and texture work
happens on layers *above or clipped to* the Smart Object, never inside it or applied
destructively to it. This is what makes the source pixels permanently re-editable and
makes accidental mirroring or swapping structurally harder to do invisibly — it still
must be checked (Section 15), but the file itself resists the mistake.

---

## 3. Order of operations

1. Extract the base's luminosity/shadow/highlight information **once**, before touching
   either artwork (Sections 4, 6, 7).
2. Place each artwork as an independent Smart Object; perspective-match to its panel —
   geometric alignment only, no distortion yet.
3. Lock each panel's vertical anchor point (per the execution plan's requirement) before
   any displacement is applied.
4. Apply displacement (Section 4/5) — geometric fold-following, per panel independently.
5. Rough mask each panel to its physical boundary (fine refinement comes later — edge
   quality is easier to judge once shadow/highlight are visible).
6. Apply the shadow pass (Section 6) — **this is the step that makes the artwork receive
   the fabric's own fold shadow**, the single largest contributor to "printed in" versus
   "pasted on."
7. Apply the highlight pass (Section 7).
8. Apply fine fabric texture (Section 8) — after shadow/highlight, so it reads as sitting
   on the now-lit surface, not floating independently of it.
9. Per-panel local correction — shadow recovery on the Right (Section 10), local contrast
   on the Left (Section 11).
10. Refine masks and edges (Section 13) — now judged against the finished visual result.
11. Top edge, hem, and center-seam treatment (Section 12).
12. Per-panel colour management / soft-proof verification (Section 9), independently.
13. Full-file 100% zoom inspection (Section 14).
14. Flatten **only the export** — the working PSD keeps every layer intact.

---

## 4. Displacement-map creation from the blank curtain base

1. From the base mockup, isolate each panel's fabric area only (no window frame, no
   rod, no room) — one crop per panel.
2. Desaturate to grayscale. This grayscale image *is* the displacement map — Photoshop's
   Displace filter requires it saved as a standalone file, not a live layer: save each as
   its own file (e.g. `LEFT_KF-AST-000618_DISPLACEMENT_SOURCE.psd`).
3. A light Gaussian blur on the grayscale map reduces photographic noise from driving
   spurious micro-displacement. A local contrast boost (Curves/Levels) then makes fold
   peaks and valleys clearly differentiated in value — brighter values read as raised
   fold crests, darker values as recessed valleys, which is what the Displace filter
   interprets as push-direction and magnitude.

## 5. Displacement settings methodology (no invented universal numbers)

The correct displacement magnitude depends on this specific base's actual fold depth and
this specific artwork's resolution — there is no universal constant to state, and stating
one would be exactly the kind of unfounded claim this project avoids elsewhere. The
methodology instead:

1. Start conservative — a small Horizontal/Vertical Scale value.
2. Apply, then check at 100% zoom against a known reference point (e.g. where a specific
   illustrated element crosses a visible fold).
3. Increase incrementally. At each step, check two things: does the artwork now
   convincingly follow the fold contour, **and** are typography and illustrated geometry
   still undistorted and legible?
4. **The correct value is the smallest magnitude that convincingly follows the fold** —
   not the largest that still looks acceptable. Over-displacement is the direct mechanism
   by which Gate 16 (typography) and Gate 15 (composition) would fail.
5. Test at multiple vertical points on each panel (top/gathered area, middle, bottom
   near the hem) — fold depth typically varies across the drop, so a single value tested
   only in one spot can be wrong elsewhere on the same panel.
6. Record the final chosen values in the working file's own notes, as a decision made
   for *this* product's specific base+artwork pairing — not a constant to carry forward
   unexamined to a different product later.

If any text region would require more displacement than it can tolerate without
distortion, apply a locally-reduced displacement strength over that specific region
(a masked, lower-intensity version of the same Smart Filter) rather than compromising the
whole panel's fold realism to protect one detail.

## 6. Shadow extraction method

1. From the base's grayscale luminosity reference, isolate only the dark values —
   push midtones and highlights toward white (Curves/Levels), leaving true shadow
   information as the only remaining dark content. A luminosity-range Blend-If mask
   achieves the same isolation.
2. Place this isolated shadow map as its own layer, clipped to (or grouped with) the
   artwork it applies to, set to **Multiply**.
3. Tune opacity down from 100% only as far as needed to avoid crushing (Section 11) —
   never so far that fold shadow becomes invisible, which would defeat the entire
   purpose of this pass.

## 7. Highlight extraction method

1. Mirror technique: isolate only the bright values from the same luminosity reference —
   push shadows and midtones toward black, leaving highlight information as the only
   remaining bright content.
2. Apply via **Screen** (see Section 8 for why Screen over Overlay), typically at reduced
   opacity — highlights are visually more aggressive than shadows and risk blowing out
   colour fidelity (directly relevant to Section 10) if applied at full strength.

## 8. Blend-mode strategy and why

- **Multiply for shadow** — darkens without shifting hue, the standard, predictable
  choice for shadow-only application.
- **Screen (not Overlay) for highlight** — recommended specifically because Overlay also
  deepens shadow as a side effect, which would compound with the separate Multiply
  shadow pass and risk over-darkening the Left panel (Section 11). Screen is purely
  additive brightening — more controllable given this pair's dark/light asymmetry.
- **Soft Light (not full Overlay) for fine texture** — gentler, lower-contrast-impact
  blend, reducing the risk of texture visually competing with colour fidelity.
- **Normal, 100%, for the artwork itself, always.** The artwork layer is never
  blend-moded or opacity-reduced — it is the fidelity anchor. All lighting/texture effects
  are additive layers *above* it, never modifications *of* it.

## 9. Preserving black, white, yellow, turquoise, and typography fidelity

- The artwork Smart Object is never destructively adjusted — this is the core mechanism
  protecting every colour in the palette simultaneously, not a separate step per colour.
- Soft-proof each panel independently against its own source TIFF (`00_REFERENCE`) at
  multiple points during the process, not only at the end — specifically checking: does
  black shift warm/cool under any layer above it, does white pick up a colour cast from
  the highlight pass, does yellow desaturate under the shadow multiply, does turquoise
  shift hue under any blend layer.
- Typography: work at full native resolution; validate specifically against displacement
  strength (Section 5) — a text region is exactly where distortion is most visible and
  least forgivable.
- No global Curves/Selective Colour "improvement" pass on the artwork itself, ever — any
  necessary calibration is applied for output/monitor matching, never to alter how the
  source artwork actually looks.

## 10. Preventing the white Right panel from losing detail

- Tune the Right panel's highlight-pass opacity **independently** from the Left — they
  should not share a value, since they start from different tonal baselines.
- Use a Curves cap on the highlight extraction layer itself to prevent its brightest
  values from reaching pure white, rather than relying on opacity reduction alone — a cap
  protects only the extreme highlights from clipping while still letting midtone
  highlight information through; opacity reduction dims everything uniformly and is a
  blunter tool.
- Check the histogram for 255 (pure white) clipping specifically on the Right panel after
  the highlight pass — any clipping means the pass is too strong.
- A subtle shadow-recovery Curves adjustment (lifting the very darkest values slightly)
  keeps fold-shadow detail present even within an overall light scene — a light pattern
  still needs *some* shadow information to read as real fabric, not a flat light patch.

## 11. Preventing the black Left panel from crushing fold information

- Mirror concern, mirror technique: tune the Left panel's shadow-pass opacity
  independently, and use a Curves floor on the shadow extraction layer to prevent its
  darkest values from reaching pure black (crush), rather than opacity reduction alone.
- Check the histogram for 0 (pure black) clipping specifically on the Left panel after
  the shadow pass.
- The local-contrast layer in the hierarchy above recovers *mid-shadow* fold structure —
  real fold detail that would otherwise disappear into undifferentiated darkness — while
  keeping the overall tone appropriately dark. This preserves the intended dark scene
  *as a real photographed fabric*, not as a flat black silhouette.

## 12. Top edge and bottom hem handling

- **Top edge/heading:** follows the base mockup's own heading treatment exactly — the
  artwork masks precisely to where real fabric begins, never bleeding into rod/hardware.
  Any heading-fold compression (fabric bunching at pleats) receives the same
  displacement/shadow technique as the rest of the panel, not a shortcut.
- **Bottom hem:** a precise mask edge following the base's actual hem line; a subtle
  contact shadow where hem meets floor (if visible in the base), extracted from the base
  itself the same way as the rest of the shadow information — never invented.
- Both edges are explicit priorities in mask refinement (Section 13) — edge quality is
  often exactly where "printed versus pasted" reads most obviously.

## 13. Mask refinement requirements

- Refine at multiple zoom levels: rough shape first, then fine edge work at 100%+ zoom
  specifically along fold boundaries, the top heading, and the bottom hem.
- Edge softness should match the base photo's own natural edge softness — a real
  photographed fabric edge has natural micro-softness; an artificially hard mask edge is
  one of the fastest ways a composite reads as pasted. But softness must not blur pattern
  detail near the edge either.
- No mask edge should cut through typography or a key illustrated element without
  specific manual attention — a blanket feather setting is not sufficient care at a point
  like that.
- The center seam/gap mask specifically needs a soft contact-shadow transition between
  panels, never a hard graphic line that would look drawn-on rather than physically real.

## 14. 100% zoom artifact inspection procedure

- Systematic, not spot-checked: divide each panel into a grid (thirds or quarters) and
  inspect every region individually at 100%+ zoom.
- Look specifically for: mask edge haloing/fringing, displacement-induced warping at
  high-contrast fold transitions, duplicated/repeated elements from accidental layer
  duplication, colour banding from stacked blend modes, inconsistent shadow direction
  between panels (both should read as lit from the same source), texture over-asserting
  itself, any reference/guide layer left accidentally visible.
- **Each panel gets its own dedicated inspection pass** — Left and Right have different
  risk profiles (Sections 10/11), so a single unified sweep is not sufficient.

## 15. Stage A QC sequence — mapped explicitly to all 19 hard gates

| Gate | What in this method verifies it |
|---|---|
| 1. Identity verification | Confirmed prior to this method (KF-PRD-000463 / KF-AST-000618 / KF-AST-000620) |
| 2. Orientation | Checked at Smart Object placement (Section 3, step 2) and re-checked at final QC |
| 3. Repeat scale | Checked at perspective-matching (Section 3, step 2) |
| 4. Crop and placement | Checked at masking (Section 13) and edge/hem handling (Section 12) |
| 5. Colour fidelity | Per-panel soft-proof (Section 9), checked at multiple points, not only the end |
| 6. Fabric behaviour | The full displacement/shadow/highlight/texture pipeline (Sections 4-8) |
| 7. Lighting purpose | The base's single consistent light source, re-checked at final QC |
| 8. 100% zoom artifact inspection | Section 14 directly |
| 9. Zero generative/AI elements | Structurally true (no generative fill used); confirmed at final QC |
| 10. Filename/folder correct | Checked at export against the locked naming convention |
| 11. Correct L/R assignment | Checked at placement and re-confirmed at final QC |
| 12. No side swapping | Explicit re-check at final QC - labeled groups match intended sides |
| 13. No mirroring | Structurally prevented (Section 1-2); re-verified visually at final QC |
| 14. No false panorama continuation | Checked at seam/gap handling (Section 12) and mask (Section 13) |
| 15. Composition of each scene preserved | Verified by the displacement methodology (Section 5) not distorting geometry |
| 16. Typography preserved | Section 5 (displacement testing against text) and Section 9 |
| 17. Vertical artwork placement preserved | Locked before displacement (Section 3, step 3); re-verified after |
| 18. Wave-band structure and relative alignment | Explicit cross-panel comparison - position/height checked side by side |
| 19. Intended dark/light contrast preserved | Sections 10/11 - independent panel tuning prevents accidental equalization |

All nineteen must pass. None are satisfied implicitly by "the technique was followed" —
each is a specific, separately-checked step.

## 16. Manual now vs. reusable later

**Manual for this pilot — not automated, not assumed systematizable yet:**
- Every artistic judgment call: opacity tuning, displacement magnitude selection
  (Section 5's methodology is inherently iterative and visual), mask edge refinement,
  dark/light balance judgment.
- Colour fidelity soft-proofing and the 100% zoom inspection — both require human visual
  judgment against the source.
- Final sign-off against all 19 gates.

**Observed as potentially reusable later — not built or proposed now:**
- The shadow/highlight *extraction methodology* (grayscale isolation from a base) is a
  repeatable *process*, even though the specific numeric values will always differ per
  product.
- The PSD layer hierarchy itself is a reusable *template shape* — group names change per
  Asset ID, but the structure is consistent.
- The gate-to-technique mapping (Section 15) could become a repeatable checklist pattern
  for future products.
This is an observation for later, not a decision made here — no automation is proposed by
naming it.

---

## Current State

A first proof composite for `KF-PRD-000463` has been produced and visually validated —
the blank base and the asymmetric L/R composition both read correctly, typography is
legible, and the wave bands visually connect the pair. This document defines the full
production-pass method to take that proof to complete Stage A rigor (genuinely printed-in
realism, verified against all 19 hard gates) — it has not yet been executed at that full
level of rigor.

## Risks

**Critical** — none. The proof composite already validated the two highest-risk elements
(base geometry, L/R composition) before this method was written.

**Major**
- **Over-displacement distorting typography or geometry** remains a real risk if the
  incremental methodology in Section 5 isn't actually followed step by step — the
  temptation to "just push the slider until it looks dramatic" is exactly what that
  methodology exists to prevent.
- **Independent per-panel tuning (Sections 10/11) requires real craft judgment.**
  Inconsistent execution between the two panels — e.g. protecting Right-panel highlights
  carefully but rushing the Left-panel shadow floor — could undermine the "one consistent
  light source" requirement (Gate 7) even though the method describes how to prevent it.
- **Extraction quality is capped by the sourced mockup's own photographic quality.** If
  the licensed base has weak or inconsistent lighting information, the shadow/highlight
  extraction technique can only be as good as what's actually present in the source.

**Minor**
- Fine texture strength (Section 8) is a restraint judgment call that should be re-checked
  against colour fidelity each time it's applied, not set once and trusted.

**Observation**
- This method, once proven here, describes a repeatable *process* — not identical
  numbers, but identical methodology — worth remembering as a natural foundation if a
  second curtain pilot is ever approved later. Nothing about that is being decided now.

## Findings

The method is fully executable manually, respects every stated constraint (no code, no
automation proposed, no Flow, no generative fill, no scope expansion, no architecture
reopened), and provides direct, explicit traceability from technique to all 19 existing
Stage A hard gates — no gate is left to be satisfied only implicitly.

## Recommendation

Approve this method as the governing technique for finishing Stage A production on
`KF-PRD-000463`. It is precise enough to execute directly, and disciplined enough that
following it should produce a result the 19-gate QC sequence can actually pass rather
than one that merely looks acceptable at a glance.

## Approval Status

**Ready to execute.** No further planning or architecture decision is outstanding —
identity, base sourcing, and the asymmetric L/R scope were all already locked before this
method was written; this document only specifies *how* to composite within those
decisions.

## Next Action (one single action only)

**Apply this production method to produce the full Stage A candidate, then run the
Section 15 nineteen-gate QC sequence against it** — the proof composite already validated
the concept; this is the pass that determines whether the finished file actually earns
gold-standard approval.
