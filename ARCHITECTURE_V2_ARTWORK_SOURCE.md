# KF Asset Manager — v2.0 Specification: Artwork Source Layer

> **Status: IMPLEMENTED (schema_version 2).** Built phase-gated and verified on production
> data: v2.0-a (Source layer) · v2.0-b (products from Sources; bypass + discriminator
> retired; SC1/SC2 → 0 on the real 894-file curtain library) · v2.0-c (schema_version
> bump + manifest + locked reporting). See `ARCHITECTURE_AUDIT.md` for the build record.
> This document is the design contract the implementation was built against.

---

## 1. Why — the evidence (not speculation)

The decision to introduce Artwork Source was deliberately deferred until real production
data justified it. It now does. On a 797-face, 473-design sample spanning all three
technical types:

| Metric | Value |
|--------|------:|
| Designs with derived cushions (SC1 / SC3) | **174 / 473 ≈ 37%** |
| Designs with sided Left+Right cushions (SC2) | 8 |
| Materialised vs estimated SC1 | 174 vs 172 (the engine *models* the pattern, not just detects it) |

Even after blending in 75 cushion-free designs (fabrics + tapestries), the
engineered-curtain-plus-derived-cushion archetype is **over a third of the catalogue** —
routine, not exceptional. Per the rule written into `MAPPING_MATRIX.md` ("adopt Artwork
Source if the awkward shape is routine rather than occasional"), the bar is cleared.

The two recurring "smells" the data exposed are both artefacts of the v1.5 workaround:

- **SC1 — the compatibility *bypass* (`from_derived`)**: a derived cushion has to
  side-step the curtain design's "Curtain-only" compatibility to become a Cushion
  product. Fires on ~37% of designs.
- **SC2 — the product *discriminator***: Left Cushion and Right Cushion need an
  artificial tiebreaker to coexist on one design.

Artwork Source dissolves both — cleanly, and without a new inter-Design relationship.

## 2. The model

A new first-class entity sits between Design and Asset:

```
Family → Design → Artwork Source → Asset
                        │
                        └── Product maps to Sources (variants = Sources)
```

- **Design** — one creative artwork identity. Unchanged. Only *independent
  compositions* (V2/D2 siblings, A/B versions) mint a new Design.
- **Artwork Source** — a specific *application* of that design's artwork to a surface:
  Curtain Left, Curtain Right, Cushion Left, Cushion Right, Runner, Tote, Scarf… Each
  Source records its application, its origin (Original vs Derived), and — if derived —
  what it came from.
- **Asset** — the file(s) realising a Source (JPG face + PSD/TIF masters). An asset now
  belongs to a **Source**, which belongs to a Design.
- **Product** — the sellable unit; its variants map to Sources.

### What each layer answers

| Layer | Question it answers |
|-------|---------------------|
| Family | "What coordinated collection is this part of?" |
| Design | "What artwork *is* this?" |
| Artwork Source | "*How* is this artwork applied — to what surface, original or derived?" |
| Asset | "Which file(s) realise it?" |
| Product | "What is sold, and in which variants?" |

## 3. What it dissolves

**SC1 (bypass) disappears.** A "Cushion" Source *is* a cushion application, so it
produces a Cushion product natively — nothing is side-stepped. Compatibility is reframed
as a single clean gate: `design_type` defines the **allowed applications**, a Source of a
derived application is permitted *because it was explicitly derived*, and a Product simply
requires a Source of its type. The curtain design's "Curtain-only" rule is never
violated, because the cushion lives in a Cushion *Source*, not bolted onto the curtain.

**SC2 (discriminator) disappears.** Cushion Left and Cushion Right are two distinct
Sources, so they are naturally two products (or two variants) — no artificial tiebreaker
on `(design, product_type)`.

**Variants gain a clean origin.** A curtain's Pair / Left / Right are simply its Curtain
Sources grouped under one product.

## 4. Entity & schema design (target)

One new table; existing identity tables keep their IDs.

**`artwork_sources`**

| Field | Meaning |
|-------|---------|
| `source_id` | opaque `KF-SRC-000000` (new independent counter) |
| `design_id` | FK → designs |
| `application` | Curtain / Cushion / Runner / Tablecloth / Tote / Scarf / Fabric / … |
| `origin` | `Original` \| `Derived` |
| `artwork_relationship` | `Original` \| `Cropped` \| `Adapted` \| `Derived` |
| `derived_from_source` | self-FK → artwork_sources (nullable) |
| `side` | `L` \| `R` \| `C` \| null |
| `label` | display label (e.g. "Cushion (Left)") |
| `created_at` / `updated_at` | timestamps |

**Changes to existing tables (additive, identity-preserving):**

- `assets` gains `source_id` (FK → artwork_sources). The asset's parent becomes the
  Source; `design_id` is retained as a kept-in-sync convenience for fast queries.
- `product_variants` reference the **Source** (the application being shown), reaching the
  asset through it.
- The v1.5 derivation fields on `assets` (`artwork_role`, `artwork_relationship`,
  `derived_from_*`) **migrate up** into the Source — that is their natural home. The
  `from_derived` flag and `product_discriminator` on `products` are **retired**, because
  Source identity now carries that information cleanly.

## 5. Migration — identity-preserving

Because we are still pre-production (only audit databases exist), migration is low-risk,
but the spec mandates it be non-destructive regardless:

1. For every existing asset, derive its **application** from its role/type (panel →
   Curtain, cushion → Cushion) and its **origin** from `artwork_role`. Create or attach
   the matching Source, mint a `KF-SRC` id, and re-point `asset.source_id`.
2. Re-map products to their Sources; convert `product_variants` to reference Sources.
3. **No Family / Design / Asset / Product ID ever changes.** Only new `KF-SRC` ids are
   minted. Relationships and all downstream references (Shopify, manifest, future SKUs)
   stay valid.
4. `schema_version` bumps to **2** — the mechanism designed for exactly this.

## 6. Compliance with the five frozen principles

| Principle | v2.0 |
|-----------|------|
| Immutable opaque IDs | ✅ `KF-SRC` is opaque; existing IDs untouched |
| Asset Manager = one-directional System of Record | ✅ unchanged |
| Versioned Rule Engine | ✅ rules still classify; they now also assign an *application* |
| Confidence + review | ✅ unchanged |
| Manifest `schema_version` | ✅ bumps to 2 to absorb the layer |

Artwork Source is consistent with v1.6's *philosophy*; it extends its *structure*. That
is why it is a deliberate v2.0, not a within-v1.6 tweak.

## 7. Worked examples (the awkward cases, dissolved)

**P4186 — sided derived cushions:**
```
Design "P4186"  (one creative identity)
├─ Source  Curtain Left    Original          → Asset P4186-L (+master)
├─ Source  Curtain Right   Original          → Asset P4186-R (+master)
├─ Source  Cushion Left    Derived (Cropped, from Curtain Left)  → Asset P4186-L-cush
├─ Source  Cushion Right   Derived (Cropped, from Curtain Right) → Asset P4186-R-cush
└─ Products: Curtain (variants ← the two Curtain Sources)
             Cushion Left  (← Cushion Left Source)      ← no discriminator, no bypass
             Cushion Right (← Cushion Right Source)
```

**P4204 + P4204-V2 — sibling designs in one family, each with a derived cushion:**
```
Family "P4204"
├─ Design (master)
│   ├─ Source Curtain  Original  → P4204 (+master)
│   ├─ Source Cushion  Derived   → P4204-cush
│   └─ Products: Curtain · Cushion
└─ Design "V2"
    ├─ Source Curtain  Original  → P4204-V2 (+master)
    ├─ Source Cushion  Derived   → P4204-V2-cush
    └─ Products: Curtain · Cushion
```

In both, compatibility is satisfied per-Source, no bypass and no discriminator appear,
and the SC1/SC2 counts drop to **0** — replaced by clean Source records.

## 8. What stays exactly the same

Design-vs-Variant vocabulary, Display IDs (`D87`/`F12`/`A931`/`P742`), the Phase 4 SKU
contract, the Business Metadata layer, the naming policy (legacy A/B, canonical D#/V#),
and rule-based compatibility all carry over unchanged. Artwork Source slots beneath
Design without disturbing any of them.

## 9. Implementation plan (phase-gated, after sign-off)

| Step | Scope | Exit gate |
|------|-------|-----------|
| **v2.0-a** | Add `artwork_sources` table + `KF-SRC` minting; build the import to create Sources and re-point assets. Products unchanged for now (dual-run). | tests + audit green; IDs preserved |
| **v2.0-b** | Map products to Sources; **retire** `from_derived` bypass and `product_discriminator`. | tests prove SC1 & SC2 → 0; full regression green |
| **v2.0-c** | Update the Auditor/reports + manifest `schema_version=2`; recompute SC metrics (expected ≈ 0, replaced by Source counts). | clean blended re-audit |

Each step ends in a review gate, an `ARCHITECTURE_AUDIT.md` entry, and a verification
run — the same discipline as Phases 1–2.

## 10. Tracked follow-ups (separate, NON-gating)

These do **not** block v2.0 and are tracked in `BACKLOG.md`:

- **Fabric / Tapestry naming rules** — the new types use conventions the engine doesn't
  parse yet (`####`, `G####-####`, `####-##`). A later rule addition.
- **Fabric folder hygiene** — the audit found non-catalogue noise in `Fabrics/`
  (`-topaz-upscale`, `WhatsApp Image…`, `flag copy.png`). These are AI-upscaler outputs
  and chat downloads, not catalogue assets, and should be removed before that folder is
  declared catalog-ready.
- **3 orphaned masters** — PSD/TIF with no matching face (`orphaned_masters.csv`).

---

### Recommendation

Adopt this specification. The production data has made the case decisively (~37%
catalogue-wide), the model dissolves the two proven special cases without a new
inter-Design relationship, and every existing ID survives. Build it phase-gated once you
sign off this contract.
