# Flow Room/Background Generation Task — KF-PRD-000463 (Stage B)

> Status: **EXECUTION-READY PROMPT TASK. Documentation only.** No code, no automation,
> no Shopify, no scaling beyond `KF-PRD-000463`. Governed by
> `STAGE_B_PREBUILD_AUDIT_KF-PRD-000463.md` Sections 5–6: Flow generates room/background
> **only** — zero curtain content, zero Karen artwork, zero pattern recreation or
> approximation. The approved Stage A asset (`KF-PRD-000463_MOCKUP_PAIR_v01.jpg`) remains
> the sole fidelity source for the curtain itself, composited in afterward, separately, in
> Photoshop — not part of this generation step.

> **Revision note (Candidate 02):** Candidate 01 correctly contained zero curtains/window
> treatments and had neutral, consistent lighting — both preserved unchanged below. It was
> rejected solely because the architectural opening was too narrow for the approved
> asymmetric L/R pair at believable scale. Only the opening's width/proportions, the rod
> description, floor-contact zones, and furniture-cropping guidance were revised to
> correct this. The room-only workflow, the lighting approach, and the full strength of
> the window-treatment exclusions are unchanged.

---

## 1. Exact Flow prompt

```
A softly lit, minimalist living room interior, photographed in a premium home décor
editorial style. Neutral warm-white or soft greige walls, matte light wood or neutral
stone flooring. A broad, centered pair of French windows or French doors (or, as an
acceptable alternative, a single wide glazed opening of equivalent total width) — sized
generously so the full opening clearly reads as wide enough to hang a substantial
two-panel curtain pair side by side at believable, realistic residential scale, not a
narrow single-window opening. Ample plain wall visible on both sides of the opening.
Realistic floor-to-near-ceiling residential proportions, a genuine architectural feature
of the room, not an oversized statement piece.

The opening is completely bare: plain, unobstructed glass only, full width, full height.
No curtains, no drapes, no blinds, no shades, no fabric of any kind anywhere in or around
it. A single, slim, continuous curtain rod or track — in matte black or brushed metal —
spans the full width of the opening, mounted directly above it, empty, proportionate to
the opening's width, ready to receive a full curtain pair in a later step. The floor
directly beneath both the left and right portions of the opening is clearly visible and
unobstructed, providing genuine full-height space, ceiling to floor, for curtain panels
to hang on both sides.

Soft, even, diffused natural daylight enters through the full width of the opening from
one consistent direction, gentle and even across the whole scene, without harsh shadows,
strong directional contrast, or coloured lighting casts.

The room is styled minimally: at most one or two simple, neutral furniture pieces (a low
armchair or a small side table), fully visible within the frame — never cropped or cut
off at the frame's edge — and placed well away from the opening, leaving the area
directly around and in front of it completely clear and unobstructed on both sides. No
patterned textiles, no wall art, no patterned rugs, nothing visually competing with the
opening itself. The composition should read as a genuine, premium editorial residential
interior — a real room someone would live in — not an empty staging wall built only to
hold a product photo.

Camera: straight-on, eye-level, pulled back to show the full opening and surrounding wall
with generous, believable margin above, below, and to each side — no wide-angle
distortion. The composition should be symmetrical or clearly balanced around the opening,
appropriate to a curtain pair rather than a single off-center panel.

Photographed in a clean, sharp-focus, architectural-digest editorial style — no artistic
blur, no vignette, no heavy colour grading. The mood is calm, premium, and timeless,
appropriate for a high-end textile brand's lifestyle photography, without strong regional
or era-specific styling cues. Still image, not video.
```

---

## 2. Negative prompt / exclusions

```
curtains, drapes, blinds, shades, window treatments, fabric on window, sheer fabric,
valance, cornice with fabric, any textile covering the window, patterned fabric anywhere
in the scene, artwork, wall décor, patterned rugs, wallpaper, ornate or gilded furniture,
clutter, multiple competing focal points

people, human figures, hands, faces, pets, animals

text, typography, writing, logos, brand marks, watermarks, signage, visible text on books
or objects

harsh directional shadows, coloured gel lighting, lens flare, motion blur, artistic blur,
vignette, oversaturated colour, HDR over-processing, heavy colour grading

fisheye distortion, wide-angle distortion, warped geometry, extra windows, arched window,
round window, floor-to-ceiling glass wall, oblique/crooked framing

narrow window, small window, single undersized window, opening too narrow for a curtain
pair, off-center asymmetric architecture, furniture cropped or cut off at frame edge,
empty staging wall, blank studio backdrop

low resolution, compression artifacts, duplicated elements, asymmetric or impossible
architecture
```

The window-treatment exclusions are deliberately the longest and most repeated
category — this remains the single highest-risk failure mode (Section 6 of the Stage B
audit): generative models default toward dressing windows with curtains unless
explicitly and repeatedly told not to. The opening-scale exclusions (added for Candidate
02) address the separate failure mode that caused Candidate 01's rejection — an
undersized opening — without weakening the window-treatment exclusions in any way.

---

## 3. Composition requirements

- **A broad, centered French-window/double-door opening (or equivalent-width single wide
  opening)** — not a narrow single window. The opening's total width must clearly and
  believably accommodate a full-height, two-panel curtain pair at realistic scale.
- Symmetrical or clearly balanced architecture around the opening — proportionate to a
  pair, not a single off-center panel.
- Opening completely bare — glass only, full width and height, no treatment of any kind.
- **A single continuous curtain rod/track spanning the full width of the opening**,
  proportionate to it, empty, correctly positioned above the frame.
- **Clear, unobstructed floor contact zones directly beneath both the left and right
  portions of the opening** — genuine full-height space, ceiling to floor, for each
  panel to hang independently.
- Camera straight-on, eye-level, pulled back for full coverage — no wide-angle or
  fisheye distortion that would misrepresent the opening's real proportions.
- Generous **but believable** negative space directly around and in front of the
  opening — enough for the compositor to fit the Stage A curtain asset at real scale,
  without reading as an artificially empty staging wall built only to hold a product
  photo. This should look like a genuine, premium residential room.
- Minimal, restrained furniture, fully visible within the frame — **never cropped or cut
  off at the frame's edge** — positioned clearly away from the opening and the space
  either curtain panel would occupy.

---

## 4. Lighting requirements

- Soft, diffused, even daylight-equivalent lighting throughout — reading as entering
  evenly across the **full width** of the now-wider opening, not concentrated at one
  narrow point.
- **One consistent light direction only** — no mixed or competing light sources, which
  would create a lighting logic the later-composited curtain (with its own baked-in
  Stage A shadow/highlight information) cannot plausibly match.
- No harsh specular highlights or strong directional shadow contrast.
- Neutral colour temperature — not strongly warm or cool. A strong colour cast baked into
  the generated room would need correcting before compositing to protect the curtain's
  colour truth later (the whole-image-grading risk named in the Stage B audit) — starting
  neutral avoids that correction being necessary at all.

---

## 5. QC checklist for accepting the generated room/background

1. **Zero curtain/drape/blind/fabric window treatment present anywhere** — the single
   most important check; confirm at full resolution, not a glance.
2. Zero Karen artwork or pattern present anywhere in the generated scene.
3. **Opening is wide enough for believable insertion of both approved L/R panels at
   realistic scale** — not a narrow single-window opening (the specific defect that
   rejected Candidate 01).
4. **Architecture is symmetrical or clearly compositionally balanced**, proportionate to
   a curtain pair, not a single off-center panel.
5. **Full-height insertion space confirmed on both the left and right sides**, with clear
   floor contact zones beneath each.
6. Rod/track spans the full width of the opening, present, empty, correctly positioned.
7. Lighting is soft, even, single-direction, neutral colour temperature, no harsh
   shadows, no global warm colour cast — reading evenly across the full opening width.
8. No people, pets, text, logos, or watermark-like artifacts anywhere in frame.
9. **100%-zoom artifact inspection** — no warped furniture geometry, impossible objects,
   or nonsensical hallucinated decor detail (Gate 10 from the Stage B audit, applied
   here at the room-generation stage specifically).
10. Overall styling reads as premium, uncluttered, and market-neutral — a genuine
    residential interior, not an empty mockup staging wall — with no furniture cropped
    or cut off at the frame edge.
11. Generous but believable negative space around the opening — enough for the
    compositor to fit and scale the Stage A curtain asset without further scene
    alteration, without looking artificially bare.
12. Candidate remains room/background only — zero curtain content, zero pattern content,
    at every check above.
13. Explicit human sign-off recorded before this room/background is approved to move
    into the Photoshop compositing step.

A candidate that fails any item is not approved — regenerate with prompt adjustments
rather than proceeding on a partial pass.

---

## Next Action (one single action only)

**Generate Candidate 02 in Google Flow using the revised prompt above, then evaluate it
against the thirteen-item QC checklist in Section 5 — with particular attention to items
3–5 (opening width, architectural balance, full-height insertion zones) before any
Photoshop compositing begins.** Do not proceed to compositing on an unevaluated
candidate.
