# Production Brief — Blank Base & Photoshop Compositing Setup
## KF-PRD-000463 (Design KF-D-000344) — Asymmetric L/R Curtain Pair

> Status: **EXECUTION-READY PRODUCTION BRIEF. No code, no automation, no architecture
> change.** Governed by `ARCHITECTURE_MEDIA_WORKFLOW_SOP.md` and
> `MEDIA_PILOT_EXECUTION_PLAN.md`. Scope: the blank curtain base and the Photoshop
> compositing setup only, for one exact-fidelity Product Media master. Not a marketing
> hero. Not AI creativity. Not cushions, tapestries, or the full PDP gallery.

---

## 1. Blank room scene

**Room type:** a living room — the same market-neutral choice already locked in the
execution plan, appropriate across Egyptian, Gulf, and UK markets without favouring one.

**Interior style:** minimal, warm-neutral. Walls in a soft greige or warm off-white;
floor in a light-to-mid neutral wood or matte stone. Deliberately unbranded and
timeless — no furniture era, texture, or ornament strong enough to date the shot or bias
it toward one market's taste.

**Wall and floor direction:** a plain, unembellished wall directly around the window —
no wallpaper, no wall art, no strong texture. Floor should recede visually: matte finish,
minimal reflectivity, so it never picks up distracting reflections of the pattern.

**Window type and proportions:** a tall, standard rectangular residential window — not
arched, not a dramatic floor-to-ceiling glass wall. Sized to let both full-length panels
hang with a small margin of wall visible on either side and a deliberate central gap
between them (see Section 2).

**Curtain rod/track:** a simple, slim rod in a neutral tone — matte black or brushed
metal reads well against this pattern's black without competing with it. No ornate
finials or heavy hardware that would pull focus from the fabric.

**Camera angle and distance:** straight-on, eye-level, pulled back far enough that both
full panels sit inside the frame with comfortable margin above, below, and to each side.
No wide-angle distortion — distortion at the edges would misrepresent panel proportions
and repeat scale, which several Stage A gates depend on reading accurately.

**Daylight direction:** soft, even, diffused frontal-to-slight-side light — and
**critically, one consistent lighting setup across the whole window, not different
lighting per panel.** The dark/light contrast between Left and Right comes from the
**pattern's own tonal values**, not from lighting the two panels differently. Lighting
the room unevenly to "help" the contrast read would misrepresent the product and
contaminate Gate 19 (Section 5) rather than support it.

**Room styling restraint:** no additional furniture or props for this specific base.
Styling, props, and mood belong to Stage B (Marketing Media), not Stage A. A completely
bare, well-lit window is the correct level of restraint for a Product Truth reference.

**Preventing the room from competing with the curtain:**
- keep the room's own palette clearly outside the curtain's hue range (avoid turquoise,
  gold, or black room elements that could visually merge with the pattern);
- no additional pattern or heavy texture anywhere else in frame;
- even, non-dramatic lighting — no coloured gels or accent lighting that would tint the
  fabric's apparent colour;
- generous negative space around the window so the curtain is unmistakably the subject;
- full sharpness across the entire curtain, not a shallow-depth-of-field "lifestyle"
  look — Stage A QC requires zoom-level detail everywhere on the fabric, which a blurred
  background would work against, not support.

---

## 2. Curtain geometry for Product Truth QC

**Two independent panels** — required, not optional, given the confirmed non-panorama
pair structure. Each panel must read as its own distinct piece of fabric.

**Fullness:** standard retail convention is roughly 2x–2.5x the track width in flat
fabric relative to the gathered/hung width. **Confirm against the real product's actual
fullness spec if one is documented; use 2x–2.5x as the default only if no spec exists.**

**Fold depth:** moderate — enough to look like real hanging fabric, not flat and pasted,
but not so deep or dramatic that it obscures pattern detail. This directly serves
legibility for the QC gates (below), which is the priority for a Product Truth shot,
not dramatic realism for its own sake.

**Gathering:** light-to-moderate at the heading, relaxing further down the drop —
enough to read as genuinely hung fabric without swallowing the pattern into shadow.

**Visible artwork percentage:** aim for as close to full legibility of each panel's
pattern as natural folding allows — realistically the high end of what's achievable
without looking artificially flattened. Several hard gates (typography, vertical
placement, wave-band alignment) are literally unverifiable if too much of the pattern is
lost into fold shadow, so legibility should be weighted over dramatic fold styling
whenever the two are in tension.

**Panel proportions:** confirm against the real product's documented dimensions if
available. Absent a documented spec, a typical floor-length panel width-to-height ratio
of roughly 1:2 to 1:3 is a reasonable default — **flagged as a default, not a verified
fact about this specific product.**

**Closed / partly open / framing a gap — recommendation: partly closed, with a
deliberate central gap.** Not fully closed/overlapping (risks visually blending the two
distinct scenes at the point they meet, working against the "not a panorama" requirement)
and not pulled fully open to the sides (reduces visible pattern on each panel). A clear
central gap does three things at once: shows each panel's full drop and pattern, looks
like a naturally dressed window, and physically reinforces that these are two separate,
non-continuous panels — directly supporting Gates 11–14 below.

---

## 3. Blank base sourcing method — one primary recommendation

**AI-generated bases remain rejected, unconditionally, per the locked SOP's Gate 9 (zero
generative/AI elements in Product Media).** This applies regardless of which deterministic
option is chosen below — it is not itself the decision being reassessed here.

**Revised recommendation: a professional, licensed photographic/PSD curtain mockup with
genuinely separate, independently-controllable Left and Right panels — not a custom
3D render, not a new in-house photo shoot.**

**Correction from the prior version of this brief:** the original recommendation
(custom 3D render) optimized for long-term architectural purity — full geometric control,
reusable across future pilots — rather than for what *this specific pilot* actually needs
to prove: that the exact-fidelity L/R compositing technique itself works. Building new 3D
capability from scratch, if it doesn't already exist, is exactly the kind of unnecessary
infrastructure this pilot should avoid. That was the wrong trade-off for a first proof.

**Reassessed against the three real options, on speed, fidelity, controllability of two
asymmetric panels, fold/displacement quality, and avoiding unnecessary infrastructure:**

- **A professional licensed PSD/photo mockup with separate L/R panels — recommended.**
  Fastest to acquire and start from (source, verify structure, begin compositing — no new
  pipeline to build). Professional mockups in this category are typically built by
  specialists specifically for smart-object pattern compositing, and commonly ship with
  fold displacement, shadow, and highlight passes **already authored** — work this brief
  would otherwise have to build from scratch is often included. Two-panel curtain mockups
  are a mature, common product category, so genuinely separate L/R smart objects are a
  realistic, findable requirement, not a stretch. The one thing that must be verified at
  sourcing time, not assumed, is that a *specific* candidate file actually has two
  independent panel smart objects and a genuine commercial-use license — that becomes an
  explicit sourcing checklist (below), not a reason to default elsewhere.
- **A controlled in-house photograph of blank curtains — not recommended for this pilot.**
  This is the *most* infrastructure-heavy of the three, not the least: it requires
  sourcing physical blank fabric in the right construction, staging a real shoot, and then
  deriving displacement maps from the resulting photograph after the fact — a real
  production dependency with no shortcut, and slower to start from than either alternative.
  Potentially excellent fidelity once executed, but the wrong trade-off for validating a
  technique quickly.
- **A custom deterministic 3D render — not recommended for this pilot,** for the reason
  stated above. Remains a legitimate option for later, if and when multiple future
  curtain pilots make the up-front investment in reusable 3D geometry worth it — that is
  a scaling decision, explicitly out of scope for proving the technique once.

**Sourcing checklist for the specific mockup file chosen** (verified at Checkpoint 1, not
assumed from a product listing):
- Genuinely two separate, independently-editable smart objects — one per panel — not a
  single drape or one smart object stretched across both sides.
- Native resolution comfortably supporting the compositing without upscaling artifacts,
  in the same spirit as why the 4110×8504px source masters mattered.
- Shadow/highlight/displacement structure present or readily addable per panel.
- A commercial license that explicitly permits production/e-commerce use, not personal or
  preview-only use.
- Room/lighting/camera characteristics matching Section 1 as closely as available — where
  an exact match isn't available, the closest reasonable candidate is chosen and any
  deviation from Section 1's spec is explicitly reviewed, not silently accepted.

---

## 4. Photoshop PSD layer structure

```
KF-PRD-000463_MOCKUP_PAIR_v01.psd

├── GROUP: BASE_SCENE                          (the sourced, verified mockup base — locked/reference)
│   ├── Background / Room
│   ├── Window Frame
│   ├── Rod / Track
│   └── Base Lighting Reference                (ambient/global light pass from the base render)
│
├── GROUP: LEFT_KF-AST-000618
│   ├── Smart Object: LEFT_KF-AST-000618_PATTERN     (source: P4186-L.tif)
│   ├── LEFT_KF-AST-000618_DISPLACE                  (fold/displacement map)
│   ├── LEFT_KF-AST-000618_SHADOW                    (Multiply)
│   ├── LEFT_KF-AST-000618_HIGHLIGHT                 (Screen/Overlay, reduced opacity)
│   ├── LEFT_KF-AST-000618_TEXTURE                   (fabric weave, low opacity)
│   └── LEFT_KF-AST-000618_TRANSLUCENCY              (optional — only if backlit variant produced)
│
├── GROUP: RIGHT_KF-AST-000620
│   ├── Smart Object: RIGHT_KF-AST-000620_PATTERN    (source: P4186-R.tif)
│   ├── RIGHT_KF-AST-000620_DISPLACE
│   ├── RIGHT_KF-AST-000620_SHADOW
│   ├── RIGHT_KF-AST-000620_HIGHLIGHT
│   ├── RIGHT_KF-AST-000620_TEXTURE
│   └── RIGHT_KF-AST-000620_TRANSLUCENCY             (optional)
│
├── GROUP: EDGE_AND_SEAM                        (panel edge treatment; contact shadow at the
│                                                 central gap between panels)
│
└── ADJUSTMENT: Colour Management / Soft-Proof  (non-destructive verification layer)
```

The two Smart Objects named explicitly in your task — `LEFT_KF-AST-000618` and
`RIGHT_KF-AST-000620` — anchor their respective groups, so the working file itself
carries per-side Asset ID traceability at the layer level (per the execution plan's
Section 4). The flattened export is generated at export time and is never part of the
working layer structure.

---

## 5. Compositing sequence

1. **Perspective mapping** — align each pattern's geometry to the base's camera
   perspective and panel curvature first, per panel independently, before any fold
   displacement is applied.
2. **Displacement / fold mapping** — apply the base's authored fold geometry to bend
   each pattern along real fold contours, per panel, using each panel's own displacement
   map (never a shared map between sides).
3. **Fabric texture** — a subtle weave/grain overlay, low opacity, applied *after*
   displacement so the texture follows the already-folded geometry correctly.
4. **Shadow pass** — reapply the base's own shadow detail (Multiply), establishing the
   dark structure before highlights are added on top.
5. **Highlight pass** — reapply the base's highlight/sheen information (reduced-opacity
   Screen/Overlay), sitting correctly on the fabric surface above shadow and texture.
6. **Translucency** — only for the optional backlit variant; sequenced last among the
   light-interaction passes, since it represents light passing through everything already
   assembled.
7. **Edge handling** — clean, anti-aliased panel edges; a subtle contact shadow/occlusion
   at the central gap where the panels meet, reinforcing that they are two distinct
   physical objects (supports Gate 14).
8. **Colour management** — work in one consistent colour space throughout (sRGB
   recommended as the safe default for Shopify/web delivery); soft-proof each panel
   independently against its own source TIFF's colour profile at each major step, not
   only at the end.

---

## 6. Preservation techniques

- **Exact typography:** work at full native resolution; avoid displacement strong enough
  to distort letterforms. If fold displacement would meaningfully distort any text
  region, apply a masked, locally-reduced displacement strength in that region only —
  not a blanket reduction across the whole panel.
- **Exact illustration geometry:** displacement should follow real fabric physics but
  never so aggressively that the illustrated scene's actual shapes/proportions become
  unrecognizable against the source TIFF.
- **Vertical artwork placement:** lock each pattern's vertical anchor point (relative to
  the rod/heading) *before* displacement, and re-verify it hasn't drifted afterward.
- **Bottom wave bands:** check each panel's band height/position independently first,
  then cross-check *relative* alignment between the two panels as its own explicit step —
  do not assume alignment falls out of independent placement.
- **Intended dark/light contrast:** apply colour management/soft-proofing per panel,
  independently — never one global colour adjustment applied across both panels at once,
  which risks quietly equalizing the difference that's supposed to be there.
- **Correct L/R identity:** enforced structurally by the separately labeled Smart Object
  groups (Section 4), and re-verified explicitly at the checkpoint sequence below — the
  file structure makes an accidental swap harder to make invisibly, but it is still
  checked, not just assumed safe because the layers are named correctly.

---

## 7. Checkpoint sequence

A practical, staged review — each checkpoint gets explicit sign-off before the next
begins, so an early error (e.g. wrong perspective mapping) is caught before it's built
on top of, not discovered at the very end:

1. **Blank base approval** — the sourced professional mockup, before any pattern is
   applied: confirmed to genuinely have two independent, separately-editable panel smart
   objects (not one drape stretched across both sides); commercial license verified as
   covering production/e-commerce use; room, window, lighting, and camera angle checked
   against Section 1's spec, with any deviation explicitly reviewed rather than silently
   accepted.
2. **Flat mapping review** — both patterns placed via perspective mapping only (no
   displacement yet), confirming correct L/R assignment, no swap, no mirror, no
   panorama-bridging at this earliest possible point.
3. **Fold/displacement review** — after displacement, texture, shadow, and highlight
   passes: confirming realistic fabric behaviour and that displacement hasn't distorted
   typography, illustration geometry, or wave-band position.
4. **Colour review** — confirming per-panel colour fidelity against each source TIFF
   independently, and that the intended dark/light contrast is intact, not softened.
5. **Final Stage A QC** — the full nineteen-gate pass from the execution plan, performed
   on the finished, flattened export candidate.

---

## 8. Files to prepare before opening Photoshop

- Confirmed access to both verified master files: `P4186-L.tif` and `P4186-R.tif`
  (4110×8504px each — already confirmed to exist).
- The **sourced blank base** (Section 3) — a professional, licensed mockup with genuinely
  separate L/R panel smart objects, acquired and passed through Checkpoint 1 *before* the
  main compositing file is opened — not assumed suitable from a product listing alone.
- Confirmation of the mockup's commercial license terms, kept on file alongside the
  project.
- A defined colour reference/profile to soft-proof against.

**First PSD file name (per the locked naming convention):**
```
KF-PRD-000463_MOCKUP_PAIR_v01.psd
```

---

## Current State

The blank base does not yet exist. No compositing work has started. The prior blockers
(identity mapping, master resolution) are fully resolved; the only new dependency this
brief introduces is the blank base itself, which this document specifies but does not yet
produce.

## Risks

**Critical**
- None. Both previously-Critical risks remain closed from the prior verified plan.

**Major**
- **A specific candidate mockup's panel-separability isn't guaranteed until checked.**
  Not every curtain mockup on the market genuinely has two independent panel smart
  objects — this is a real, per-file verification step (part of Checkpoint 1), not
  something to assume from a product thumbnail or description alone.
- **License scope must be confirmed, not assumed.** A mockup licensed for personal use or
  web preview only would not be appropriate for a commercial gold-standard production
  asset — confirm the specific license terms before compositing begins, not after.
- **Fullness and panel-proportion specs are defaults, not verified facts** about this
  specific product. If a real spec exists, it should override the defaults in Section 2
  before geometry is finalized.

**Minor**
- The optional backlit/translucency variant remains deferred, as in the prior plan —
  log explicitly if this pilot completes without it.

**Observation**
- Choosing a licensed mockup over building new 3D capability is itself an application of
  this project's own standing discipline — right-size to what the current step actually
  needs to prove, rather than building the most capable-looking option by default. If a
  future scale-up to many curtain pilots ever makes a reusable 3D base genuinely worth the
  investment, that remains a legitimate later decision — just not one this first pilot
  should carry.

## Findings

Every specification in this brief is derivable from the locked SOP and the verified
execution plan without reopening either. The sourcing decision was reassessed against the
pilot's actual goal (validating the compositing technique, not building new production
infrastructure) and corrected accordingly — see Section 3. The genuine open dependency is
now sourcing and verifying a suitable licensed mockup, a smaller and faster dependency
than the prior recommendation carried.

## Recommendation

Proceed to sourcing a candidate professional curtain mockup meeting the checklist in
Section 3, then to Checkpoint 1 (verification and approval of that specific file) before
any pattern compositing begins. Do not begin compositing on an unverified base — a
mockup that turns out not to have genuinely separate L/R panels, or an inadequate
license, would mean redoing this step, which is exactly the avoidable rework this
correction is meant to prevent.

## Exact Production Setup

- **Room:** neutral living room, plain wall, matte neutral floor, tall standard window,
  slim neutral rod, no props.
- **Camera:** straight-on, eye-level, pulled back for full-frame both panels, no
  wide-angle distortion.
- **Light:** one soft, even, diffused source across the whole window — never per-panel.
- **Geometry:** two independent panels, moderate fold/gathering tuned for legibility,
  partly closed with a deliberate central gap.
- **Base method:** a professional, licensed PSD/photo mockup with genuinely separate L/R
  panels — not a custom 3D render, not a new in-house shoot, not AI-generated.
- **PSD:** `KF-PRD-000463_MOCKUP_PAIR_v01.psd`, structured per Section 4.

## Next Action (one single action only)

**Source a candidate professional curtain mockup and verify it against the Section 3
checklist** (genuinely separate L/R panel smart objects, adequate resolution, commercial
license covering production use, reasonable fit to Section 1's room/lighting spec) —
this is the one step standing between this brief and starting Checkpoint 1.
