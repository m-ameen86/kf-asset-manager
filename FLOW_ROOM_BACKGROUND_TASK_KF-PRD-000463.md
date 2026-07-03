# Flow Room/Background Generation Task — KF-PRD-000463 (Stage B)

> Status: **EXECUTION-READY PROMPT TASK. Documentation only.** No code, no automation,
> no Shopify, no scaling beyond `KF-PRD-000463`. Governed by
> `STAGE_B_PREBUILD_AUDIT_KF-PRD-000463.md` Sections 5–6: Flow generates room/background
> **only** — zero curtain content, zero Karen artwork, zero pattern recreation or
> approximation. The approved Stage A asset (`KF-PRD-000463_MOCKUP_PAIR_v01.jpg`) remains
> the sole fidelity source for the curtain itself, composited in afterward, separately, in
> Photoshop — not part of this generation step.

---

## 1. Exact Flow prompt

```
A softly lit, minimalist living room interior, photographed in a premium home décor
editorial style. Neutral warm-white or soft greige walls, matte light wood or neutral
stone flooring. A single tall, standard rectangular residential window, centered in the
frame with generous plain wall margin on both sides, realistic floor-to-near-ceiling
residential proportions — not an oversized architectural feature.

The window is completely bare: plain, unobstructed glass only. No curtains, no drapes,
no blinds, no shades, no fabric of any kind in or around the window. A slim, minimal
curtain rod or track in matte black or brushed metal is mounted directly above the
window, empty, ready to receive curtains in a later step.

Soft, even, diffused natural daylight enters through the window from one consistent
direction, gentle and even across the whole scene, without harsh shadows, strong
directional contrast, or coloured lighting casts.

The room is styled minimally: at most one or two simple, neutral furniture pieces (a low
armchair or a small side table), placed away from the window, leaving the area directly
around and in front of the window completely clear and unobstructed. No patterned
textiles, no wall art, no patterned rugs, nothing visually competing with the window
itself.

Camera: straight-on, eye-level, pulled back to show the full window and surrounding wall
with generous margin above, below, and to each side — no wide-angle distortion.

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

low resolution, compression artifacts, duplicated elements, asymmetric or impossible
architecture
```

The window-treatment exclusions are deliberately the longest and most repeated
category — this is the single highest-risk failure mode (Section 6 of the Stage B audit):
generative models default toward dressing windows with curtains unless explicitly and
repeatedly told not to.

---

## 3. Composition requirements

- One window only, tall and rectangular, realistic residential proportions — not a
  dramatic architectural statement piece.
- Window centered or gently off-center, with generous clean wall margin on both sides.
- Window completely bare — glass only, no treatment of any kind.
- Curtain rod/track visible, empty, correctly positioned above the window frame.
- Camera straight-on, eye-level, pulled back for full coverage — no wide-angle or fisheye
  distortion that would misrepresent the window's real proportions.
- Generous, clean negative space directly around and in front of the window — this is
  the area the Stage A curtain asset will later be fitted into, so it must not be
  crowded, obstructed, or cropped tightly.
- Minimal additional furniture, positioned clearly away from the window and rod area,
  never overlapping the space a curtain would occupy.

---

## 4. Lighting requirements

- Soft, diffused, even daylight-equivalent lighting throughout.
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
3. Window proportions and placement are usable for compositing — realistic size, not
   distorted, not at an extreme or oblique angle.
4. Rod/track is present, empty, and correctly positioned.
5. Lighting is soft, even, single-direction, neutral colour temperature, no harsh
   shadows.
6. No people, pets, text, logos, or watermark-like artifacts anywhere in frame.
7. **100%-zoom artifact inspection** — no warped furniture geometry, impossible objects,
   or nonsensical hallucinated decor detail (Gate 10 from the Stage B audit, applied
   here at the room-generation stage specifically).
8. Overall styling reads as premium, uncluttered, and market-neutral — not tied to one
   specific region or era.
9. Generous, clean negative space around the window — enough room for the compositor to
   fit and scale the Stage A curtain asset without further scene alteration.
10. Explicit human sign-off recorded before this room/background is approved to move
    into the Photoshop compositing step.

A candidate that fails any item is not approved — regenerate with prompt adjustments
rather than proceeding on a partial pass.

---

## Next Action (one single action only)

**Generate one candidate image in Google Flow using the prompt above, then evaluate it
against the ten-item QC checklist in Section 5 before any Photoshop compositing
begins.** Do not proceed to compositing on an unevaluated candidate.
