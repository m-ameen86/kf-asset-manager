# KF Asset Manager — Fabric Naming Convention

> Status: **implemented** (rules_version 3). Fabrics are a new catalogue category with no
> prior production convention, so this defines the standard rather than retrofitting one.

## The decision (mirror of the engineered-panel case)

Fabrics are `repeat_pattern` designs. Unlike engineered panels — where `P4204` vs
`P4204-V2` are **sibling designs** (different artwork) — a fabric's numeric suffix is a
**colourway**: the *same* pattern in a different colour. Per the locked Design-vs-Variant
policy:

- **Pattern code = the Design.** `G122` is one repeat-pattern design.
- **Colour suffix = a Variant.** `G122-1`, `G122-2`, `G122-3` are colourways of that one
  design — commerce variants, exactly like a curtain's Left/Right or a size option. They
  do **not** mint new designs.

So all colourways of a pattern collapse into one Design, one Fabric Artwork Source
(Original), and one Fabric product carrying the colours as variants.

## What the parser accepts (tolerant — no file renaming required)

The `fabric_code` rule reads every real form found in the library:

| Form | Example | Pattern (design) | Colourway (variant) |
|------|---------|------------------|---------------------|
| bare number | `15`, `16` | 15, 16 | — (single) |
| G-prefixed | `G122-2` | G122 | 02 |
| numeric pair | `1003-01` | 1003 | 01 |
| legacy named | `4011_Floral` | 4011 | — (line "Floral") |

- The pattern token (any leading letters + digits) is upper-cased and used as the design
  key (`FAB|G122`), so it never collides with curtain (`PANEL|…`) or set (`SET|…`) codes.
- A trailing `-<n>` / `_<n>` is the colourway, zero-padded to two digits (`1` → `01`).
- Colour is recorded as the variant axis (`role=fabric-c02`, label "Colour 02") and is
  deliberately kept OUT of the design key, so colourways group into one design.
- `.tif` / `.psd` masters attach to their matching face by stem (no own identity).

## Going-forward standard (recommended)

The parser is tolerant, but for new fabrics use the clean canonical form:

```
<PATTERN>-<CC>
```

- **PATTERN** — a short pattern code, letters optional, digits zero-padded (e.g. `G0122`,
  `1003`). Keep an existing code if the design already has one; assign a new one per new
  pattern.
- **CC** — a two-digit colourway, starting at `01`. The base/first colour is `-01`
  (prefer explicit `G122-01` over bare `G122` for anything with more than one colour).
- One file per colourway face; masters share the stem (`G0122-01.tif`).
- No spaces; no AI-upscaler or chat artefacts in the catalogue folder (see hygiene note).

This keeps pattern-vs-colour unambiguous and parses at high confidence with zero review.

## Not catalogue (excluded by design)

Files that are not catalogue assets are intentionally **not** matched and remain flagged
for review so they surface for cleanup, never silently entering the catalogue:
`*-topaz-upscale-*` (AI upscaler outputs), `WhatsApp Image *` (chat downloads),
`flag copy.png` / `flags2-02 copy.png`. Remove these from `Fabrics/` before declaring it
catalog-ready (tracked in `BACKLOG.md`).

## Tapestries — still open

Tapestries (`fixed_artwork`) live in their own folder and classify by folder type, but a
filename convention for them has not been defined yet — pending a look at representative
tapestry filenames. Tracked in `BACKLOG.md`.
