# KF Asset Manager — Phase 4 Specification: Derived SKU + Display Title

> Status: **IMPLEMENTED** — built phase-gated (4-a SKU generator · 4-b resolver · 4-c
> display titles · 4-d manifest/skus.csv export) and verified. All four sign-off decisions
> are live: D1 pair=base, D2 `-C0n` colourway, D3 length deferred, D4 `display_title`.
> See `ARCHITECTURE_AUDIT.md` for the build record.

## 1. What Phase 4 delivers

The first real *downstream artifacts* generated from the system of record:

1. **Business SKU** — a derived, self-describing code identifying the exact
   sellable/printable unit (`KF-CUR-000019-L`). Computed from identity + relationships,
   never stored as identity, regenerable.
2. **Display title** — a customer-facing name (`Design 19 Curtain — Left Panel`),
   generated as a sensible default, with a permanent manual override that always wins.
3. **Padding-insensitive resolver** — typing `19`, `D19`, `000019`, or a full SKU all
   resolve to the right design/product.
4. **Manifest carries both** — every product/variant in `manifest.json` gains its SKU and
   title, so Shopify staging becomes an export, not a manual rebuild.

## 2. SKU format (reconciled with v2.0)

```
KF-<TYPE>-<DESIGN>-<VARIANT>
```

- **`<TYPE>`** — product-type code. NOTE: the existing `config.TYPE_SKU_CODE` is keyed by
  *asset_type*; Phase 4 adds a clean **product_type → code** map (the products table stores
  the canonical product_type):

  | product_type | code | | product_type | code |
  |---|---|---|---|---|
  | Curtain | `CUR` | | Tapestry | `TAP` |
  | Cushion | `CSH` | | Apparel | `WMN` |
  | Runner | `RUN` | | Fabric | `FAB` |
  | Tablecloth | `TBL` | | Flag | `FLG` |
  | Painting | `PNT` | | Unknown | `UNK` (never shipped) |

- **`<DESIGN>`** — the **design's** number, zero-padded to the internal width (6):
  `KF-D-000019` → `000019`. (Not the product or asset number — those are independent
  counters; the design anchors the SKU.)

- **`<VARIANT>`** — derived from the v2.0 model per product type (see §3).

Market is **not** in the SKU (handled by Shopify markets). One SKU is stable worldwide.

## 3. Variant vocabulary — how it derives from v2.0 (the main reconciliation)

The original contract predated Sources and colourways. Here is the reconciled mapping,
computed from the product's `product_type`, its variants, and the realizing Source:

**Curtain** (one grouped product; panels are variants):
- Left panel → `-L`, Right panel → `-R`, merged single → `-SINGLE`.
- The **pair** is the base unit → **no suffix** (`KF-CUR-000019`). *(Recommendation —
  see decision D1.)*

**Cushion** (v2.0: each sided cushion is its own product, realized from a derived Source):
- Source side L → `-L`, side R → `-R`; an unsided single cushion → no suffix.
- The side comes from the **Source**, not a discriminator.

**Fabric** (one product; colourways are variants — the new case):
- Colourway → `-C01`, `-C02`, … (two-digit, from the parsed colourway). *(Recommendation —
  see decision D2.)*
- A single-colour fabric (bare `15`) → no suffix.
- Length/material cuts (`-3M`) are **deferred** — not modeled yet (decision D3).

**Other types** (Runner, Tablecloth, Tapestry, Apparel, Flag, Painting): one product, no
sub-variant → no suffix, unless they later gain sided/colour variants.

## 4. Decisions to confirm (my recommendations — confirm or adjust)

- **D1 — Curtain pair representation.** Recommend: the **pair is the base SKU** (no
  suffix); `-L` / `-R` for individual panels; `-SINGLE` for a merged single. Alternative:
  always-explicit `-PAIR`. *Recommend base = pair (cleaner default for the common buy).*
- **D2 — Colourway suffix.** Recommend `-C01` (the `C` makes it self-describing and avoids
  confusion with a bare panel index). Alternative: bare `-01`. *Recommend `-C01`.*
- **D3 — Fabric length/material.** Recommend **defer** — there's no length/material data in
  the catalogue yet; add when fabric cuts are modeled. *Recommend defer.*
- **D4 — Title override store.** Recommend a dedicated nullable `display_title` on the
  product (generated default when empty; manual value persists and wins). Clean, and keeps
  Business Metadata for tagging only. *Recommend product-level title field.*

## 5. Display title rules

- **Generated default** (deterministic, no AI in Phase 4): `Design <n> <Type>` plus the
  variant in parentheses — e.g. `Design 19 Curtain — Left`, `Design 87 Fabric — Colour 02`.
- **Manual override always wins and is permanent.** Setting a title never changes identity
  or SKU; clearing it falls back to the generated default.
- AI *suggestions* remain a later enhancement (Phase 3-style), not part of Phase 4.

## 6. Padding-insensitive resolver

A single `resolve(query)` accepts and normalizes:
`19` · `D19` · `000019` · `KF-D-000019` · `KF-CUR-000019-L` → design 19 (and, when the
query carries type+variant, the specific product/variant). Powers both human typing (short
number) and the printer/order workflow (full SKU) with no compromise to identity.

## 7. Where SKUs live

SKUs are **derived**, produced by a pure `sku_for(product_type, design_number, variant)`
function and emitted into `manifest.json` per product/variant. They are **not** stored as
identity and can be regenerated or rebranded without touching any `KF-…` ID. (A cached
copy may be written to the manifest for export convenience; the function is the source of
truth.)

## 8. Implementation plan (phase-gated, after sign-off)

| Step | Scope | Exit gate |
|------|-------|-----------|
| **4-a** | `sku.py`: product_type→code map, `sku_for(...)`, variant-suffix resolver from the v2.0 model. Pure functions. | unit tests across all types incl. colourway |
| **4-b** | Padding-insensitive `resolve(query)` over designs/products/SKUs. | tests: every input form resolves |
| **4-c** | Display titles: generated default + manual override store (`display_title`). | tests: default + override + clear-to-default |
| **4-d** | Emit SKU + title into `manifest.json`; auditor surfaces a SKU column. | real-catalogue manifest carries SKUs |

Each step ends in a review gate and an `ARCHITECTURE_AUDIT.md` entry, same discipline as
Phases 1–2 and v2.0.

## 9. What stays unchanged

Opaque internal IDs, Display IDs, the v2.0 Artwork Source model, Business Metadata,
compatibility rules, and all naming policy are untouched. Phase 4 only *reads* identity to
*generate* derived business codes — exactly the "system of record → everything downstream
is generated" principle the architecture was built for.
