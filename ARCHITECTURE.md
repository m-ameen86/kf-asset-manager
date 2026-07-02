# KF Asset Manager — Frozen Architecture (v1.6)

> Status: **FROZEN** · **v2.0 — the Artwork Source layer is now implemented** (schema_version
> 2): Family → Design → Artwork Source → Asset, with Products realized from Sources. The
> v1.5 `from_derived` bypass and the product discriminator are retired. · v1.6 added the
> metadata-only Business Metadata layer · v1.5 added the artwork-origin model and Display
> IDs · The Asset Manager is the permanent **System of Record** and database — not merely
> a scanner. Everything downstream is generated from it.
>
> Full v2.0 design contract: `ARCHITECTURE_V2_ARTWORK_SOURCE.md`. Build history and audit:
> `ARCHITECTURE_AUDIT.md` (entries v2.0-a → v2.0-b → v2.0-c).

---

## 1. Layered model

Three independent layers. A change in one never forces a change in another.

```
INTERNAL IDENTITY      immutable · opaque · no business meaning
        │
        ▼
RELATIONSHIPS          foreign keys between identities
        │
        ▼
BUSINESS SKU           generated · human-readable · may evolve with business rules
        │
        ▼
DISPLAY TITLE          customer-facing · fully independent
```

- **Internal identity** is a meaningless surrogate key. It never changes, no matter
  how the asset is re-categorised, re-seasoned, re-collected, or re-priced.
- **Business SKU** is *derived* from identity + current business rules. It may be
  regenerated when conventions change. It is never a primary key.
- **Display title** is independent of both and may be edited freely for the storefront.

---

## 2. The five frozen principles

1. **IDs are immutable and carry no business meaning.** No collection, market,
   season, style, or type is ever encoded in an internal ID. Those live in metadata.
2. **The Asset Manager is the System of Record.** Generation is one-directional:
   `Asset Manager → Manifest → Shopify CSV → Metaobjects → Products → Kickflip → Mockups → Search → AI`.
   Nothing edits a downstream system first and syncs backward.
3. **Parsing is a versioned Rule Engine**, not hardcoded regex. Conventions evolve by
   adding rules (data), never by editing the parser core. Carries a `rules_version`.
4. **Classification uses confidence scoring** across Filename Rules, Vision, existing
   Metadata, and Folder Hint (lowest). Below a configurable threshold → **Needs Review**
   rather than a forced (wrong) classification.
5. **Manifests are versioned** with a `schema_version` so the metadata model can
   evolve without breaking compatibility.

---

## 3. Entities & internal identities

All internal IDs: `KF-{ENTITY}-{NNNNNN}`, zero-padded, drawn from an **independent
counter per entity**. The entity prefix denotes the *kind of record*, not business
metadata, so it is compliant. Numbers across layers do **not** match each other —
relationships are carried by foreign-key fields, never by shared numbers.

| Entity | ID format | Meaning |
|---|---|---|
| Family | `KF-FAM-000000` | A coordinated collection (e.g. set `C4`). Optional. |
| Design | `KF-D-000000` | A shared artwork identity. A curtain pair = one design. |
| Asset | `KF-AST-000000` | One physical file/panel. Opaque — side is metadata, not in the ID. |
| Product | `KF-PRD-000000` | A commerce unit (what Shopify sells), with variants. |

### What a Family is — and is not

A **Family** is a *coordinated design collection*: multiple independent Designs that
were **intentionally created to be merchandised together as one visual collection**.

Examples: a Ramadan `C4` set; a Coordinated Bedroom Collection; a Coordinated Living
Room Collection.

A Family is **not**:
- a generic category (e.g. "Cushions"),
- a season (e.g. "Summer 2026"),
- a marketing grouping or campaign,
- a sales/merchandising bucket of unrelated items.

A standalone design simply **has no Family** (`family_id = NULL`). Family membership
means the designs are a deliberate, coordinated visual set — nothing looser.

**Relationships** (foreign keys, not encoded in IDs):

```
Family 1 ──< Design 1 ──< Asset            (a design has many assets)
                   1 ──< Product            (1:N — one artwork, many product types)
Product 1 ──< Variant >── Asset             (variants map to the panels/pieces)
```

A single design can back **many products over its lifetime** — the same artwork sold
as a curtain, a cushion, a tapestry, fabric-by-the-metre, a tote, a scarf, and future
types. This is a core platform capability, not an edge case. One product per
(design, product_type).

### Design type & product compatibility

Not every design can generate every product. Each design carries:
- **`design_type`** — the nature of the artwork. Official taxonomy:
  `repeat_pattern`, `engineered_panel`, `fixed_artwork`, `placed_artwork`, `set_piece`.
  - `repeat_pattern` — seamless/tileable; backs many products.
  - `engineered_panel` — a curtain panel engineered for placement; curtain only.
  - `fixed_artwork` — a fixed composition such as a tapestry; that product only.
  - `placed_artwork` — a single-placement print (t-shirt front, poster, canvas) —
    neither a repeat pattern nor a fixed tapestry.
  - `set_piece` — a piece within a coordinated Family; bound to its own type.
- **`primary_product`** — the default product type for that design.
- **`product_compatibility`** — a **rule-based** model (not just a flat list)
  describing which products the design may back and under what conditions.

**Product compatibility is rule-based.** Each entry pairs a product type with a rule:
- `allowed` — may be generated freely.
- `blocked` — must never be generated.
- `conditional` — allowed only when stated conditions hold.
- `requires_transformation` — allowed only after a defined asset transformation.
- `requires_review` — allowed only after human approval.

The initial implementation may use only `allowed` / not-allowed, but the data model
(a JSON field) already accommodates the richer rule objects, so the compatibility
logic can expand **without a schema change**. The Asset Manager **enforces** these
rules so downstream systems (Shopify, Kickflip, mockup generation, AI) only ever
generate **valid** products. `design_type` rules are versioned config
(`design_types_version`); authoritative classification comes from the Rule Engine +
confidence layer (Phases 2-3).

### Source library (metadata)

Each asset may carry an optional **`source_library`** describing where it originated:
`Legacy`, `Imported`, `AI Generated`, `Customer Upload`, `Internal Design Team`, …
This is **metadata only** — it never affects identity, grouping, or compatibility.

Linked source masters (layered TIF/PSD) attach to their **face Asset** — same piece,
different format — and do **not** receive their own Asset ID.

---

## 4. Business SKU (derived)

Generated from the design/family and current rules. Human-readable; regenerable.
This is the value written to Shopify's SKU field. Internal IDs are unaffected if
these rules change later.

**Standalone curtain** (no family):
```
Product SKU      KF-CUR-000325            (CUR = type, 000325 = design's number)
  variant Pair   KF-CUR-000325            (default)
  variant Left   KF-CUR-000325-L
  variant Right  KF-CUR-000325-R
```

**Coordinated family** (e.g. `C4`) — all pieces read the family's number:
```
Curtain          KF-CUR-000012            variants Pair / Left / Right
Cushion A        KF-CSH-000012-A
Cushion B        KF-CSH-000012-B
Cushion (numbered) KF-CSH-000012-1 / -2
Runner           KF-RUN-000012
```

Type codes: `CUR` curtain · `CSH` cushion · `RUN` runner · `TBL` tablecloth ·
`TAP` tapestry · `PAT` pattern · `FAB` fabric · (extensible). There is **no `UNK`
in a finished catalog** — an unresolved type is *Needs Review*, never a shipped SKU.

---

## 5. Display title (independent)

Customer-facing name, separate from ID and SKU. AI may *suggest* it; a manual value
always wins and is permanent. Editing the title never affects identity or SKU.

---

## 6. Rule Engine (versioned)

Filename parsing is an ordered list of named rules carried as **data**, with a
`rules_version`. Each rule declares: name, matcher, field extractors, priority.
The engine applies rules in priority order; the core code never changes when a
convention is added.

Rules cover the known conventions and any future ones:
- `flat_curtain` — `Kids-3141-L`, `Paintings 4111-R`, `Kids-3061-C` (merged single)
- `batched_set` — `(18-11) C4-A`, `(18-11) C4-A-cushion`, `(18-11) C6-cushion 1`
- `fabric` / `pattern` / future formats — added as new rule entries

### Vocabulary: Design vs Variant (locked)

These two words mean different things and must never be conflated:

- **Design (`D1 / D2 / D3`)** — a *different artwork composition* within the same
  family. Each `D` is its own **Design**, may become its own independent **Product**,
  with its own assets, pricing, SEO, and merchandising. `D` is a DAM-layer concept.
- **Variant** — a *commerce option on a single product*: size, material, colour,
  pair / left / right. Variants live on one Product. `Variant` is a storefront concept.

### Naming-convention policy (versioned, frozen rules)

- Legacy curtain `A/B` → **Left / Right** sides. Frozen; never extended.
- Legacy non-curtain `A/B` → existing distinct-design suffixes. **Backward-compatible
  only** — parsed for pre-existing files, never generated.
- New design compositions → **`D1 / D2 / D3`** (canonical).
- **`A/B` must never be generated for new assets.**

This keeps the DAM model, the Rule Engine, and the Shopify product model semantically
consistent: `D` separates artworks; `Variant` separates commerce options.

### Artwork origin: Original vs Derived (what creates a new Design)

A **new Design is created only for independently created artwork.** Artwork that is
*derived* — cropped or adapted from an existing design — does **not** become a new
Design; it stays in its **parent Design**, linked by an explicit relationship, and may
still produce its own Product.

Every asset carries:
- **`artwork_role`** — `Original` or `Derived`.
- **`artwork_relationship`** — `Original`, `Derived`, `Adapted`, or `Cropped`.
- **`derived_from_design`** / **`derived_from_asset`** — what a derived asset came from.

A derived asset **authorises its own product type** on the parent design (a cushion
cropped from a curtain is itself a valid cushion artwork), without widening the
parent design's `compatible_products`. Several products of one type can coexist on a
design via a discriminator (e.g. a Left Cushion and a Right Cushion), each recording
its realising `source_asset` and flagged `from_derived`.

Master files (`.tif` **or** `.psd`) attach to their panel's asset and never mint their
own Asset ID.

**Situation 1 — Derived artwork (`P4134`).** The cushions are cropped from the curtain
panels, so they are *not* new designs:
```
Design  (engineered curtain)              ← one independently created composition
├─ Asset  P4134-L  Original   (+ .psd master)
├─ Asset  P4134-R  Original   (+ .tif master)
├─ Asset  P4134-L-cush  Derived (Cropped, from P4134-L)
├─ Asset  P4134-R-cush  Derived (Cropped, from P4134-R)
├─ Product  Curtain         [variants: Pair / Left / Right]   ← from Original panels
├─ Product  Cushion (Left)  from_derived → P4134-L-cush
└─ Product  Cushion (Right) from_derived → P4134-R-cush
        → 1 design · 4 assets · 3 products · no Family (single composition)
```

**Situation 2 — Independent compositions (`P4207`).** `D1` and `D2` are genuinely
different compositions, so each is its own Design; their cushions are derived from
their own curtain:
```
Family  P4207                              ← groups the coordinated independent designs
├─ Design D1
│   ├─ Asset  P4207        Original  (+ .tif master)
│   ├─ Asset  P4207-cush   Derived (Cropped, from P4207)
│   ├─ Product Curtain
│   └─ Product Cushion     from_derived → P4207-cush
└─ Design D2
    ├─ Asset  P4207-D2      Original  (+ .psd master)
    ├─ Asset  P4207-D2-cush Derived (Cropped, from P4207-D2)
    ├─ Product Curtain
    └─ Product Cushion      from_derived → P4207-D2-cush
        → 1 family · 2 designs · each with its own curtain + derived cushion
```

The difference between the two is **artwork origin, not product type**: `P4134` is one
composition with derived cushions (one Design); `P4207` has two independent
compositions (two Designs), each carrying its own derived cushion.

### Business Metadata (metadata only)

Business facts about a design — which line, market, room, collection, or theme it
belongs to — are **metadata, not identity.** They live in one generic key/value store
(`business_metadata`), keyed loosely by `(entity_type, entity_id, dimension, value)`,
**not** as per-dimension tables and **not** as columns on the identity tables.

Dimensions (extensible vocabulary): `business_line` (Kids, Paintings, Ramadan, Luxury,
Hotels, Outdoor), `market` (Egypt, GCC, Europe, USA), `room` (Kids Room, Living Room,
Bedroom, Dining), `collection` (Summer 2027, Ramadan 2027, Classic Collection),
`theme` (Floral, Islamic, Modern, Vintage).

**Hard invariant — Business Metadata NEVER affects:** internal IDs, SKU generation, or
design identity. It is consumed only by search, filtering, Shopify collections, AI,
SEO, and merchandising. A design's `business_line = Kids` is a label on an opaque ID,
never a part of it. (This is why folder names like *Kids* / *Paintings* / *Ramadan*
are captured here, not parsed into identity — see the folder/naming guidance.)

Design types stay **technical** (`repeat_pattern`, `engineered_panel`, `fixed_artwork`,
`placed_artwork`, `set_piece`) and are never mixed with these business concepts.

### Terminology: Import, not Scan

The Asset Manager is the permanent database, so the operation that reads a folder into
it is an **Import**, not a one-off "scan":

- **Import Library** — first load of a (catalog-ready) folder into the database.
- **Refresh / Synchronize Library** — re-import to pick up additions/edits. This is
  **idempotent**: identities are keyed by content hash and grouping key, so re-importing
  never changes an existing ID or loses metadata. Masters re-link, new files mint new
  IDs, unchanged files are untouched.

### Display IDs (UI only)

Each entity's immutable internal ID (`KF-D-000087`) has a derived **Display ID**
(`D87` / `Design #87`) for the interface. Display IDs are never stored and never used
as identifiers — they are computed from the internal ID purely for readability. The
same applies to Family (`F12`), Asset (`A931`), and Product (`P742`). Long internal IDs
are never shown to users except when debugging.

### Identity vs SKU — the three layers (Phase 4 contract)

> Specification for Phase 4 (Derived SKU + display title + manifest). Documented now so
> it is settled; **not yet implemented**. No code changes here.

Three layers, deliberately kept separate so none can corrupt another:

| Layer | Example | Role | Changes? |
|-------|---------|------|----------|
| **Internal ID** | `KF-D-000019` | Identifies the *artwork*. Opaque, immutable, never reused, used in the database, relationships, manifest, and Shopify references. | **Never** |
| **Display ID** | `D19` | Human-readable label for the UI only. Derived; never stored; never an identifier. | n/a (derived) |
| **SKU** | `KF-CUR-000019-L` | Identifies the *exact sellable/printable thing*. A self-describing **business code**, generated from identity + relationships. | May be regenerated; identity stays put |

**Why the SKU is not the Design ID, and not a bare `19`.** A Design ID identifies an
artwork; a SKU must identify the precise unit going to the printer — and one design
yields many (Left panel, Right panel, Pair, Left cushion, Right cushion, a fabric
length…). `KF-D-000019` cannot say *which*. A bare `19` is worse: the design, product,
and asset counters are independent, so design 19 / product 19 / asset 19 all exist —
`19` alone is ambiguous and carries no variant. So the SKU is a derived, meaningful code
and the Design ID stays an opaque anchor.

**SKU format:**

```
KF-<TYPE>-<DESIGN>-<VARIANT>

KF-CUR-000019-L        curtain · design 19 · left panel
KF-CUR-000019-PAIR     curtain · design 19 · the pair
KF-CSH-000019-R        cushion · design 19 · right (derived) cushion
KF-FAB-000087-3M       fabric  · design 87 · 3-metre cut
```

- **`<TYPE>`** — the product-type code (already defined in config): `CUR` curtain,
  `CSH` cushion, `RUN` runner, `TBL` tablecloth, `TAP` tapestry, `PAT`/`FAB` fabric,
  `WMN` apparel, `PNT` painting, `FLG` flag.
- **`<DESIGN>`** — the design number, **zero-padded to the internal width** (`000019`),
  so the SKU and the internal ID read identically and sort/scan cleanly.
- **`<VARIANT>`** — the commerce option: `L` / `R` / `PAIR` / `SINGLE` for curtains,
  `L` / `R` for sided cushions, `3M` / material for fabric, etc.
- **Market is NOT in the SKU.** Egypt / GCC / Europe / USA are business metadata, handled
  by Shopify markets, so one SKU stays stable across all regions.

**Search must be padding-insensitive.** Typing `19`, `D19`, `000019`, or the full
`KF-CUR-000019-L` all resolve to design 19. This gives the short human number for typing
and the structured code for the order — both, with no compromise to identity.

**Printer workflow.** The order line carries the full SKU; the printer scans or pastes
it and the Asset Manager resolves directly to the exact print-ready asset — no guessing
which panel. Because the SKU is *derived*, the format can be rebranded or restructured
later and every `KF-D-000019` (and all order/printer references to it) stays valid.

---

## 7. Confidence scoring

Each signal votes with a weight; the combiner picks the highest-scoring type and
records the score and contributing sources.

| Signal | Default weight |
|---|---|
| Filename rule (matched) | high |
| Vision classification | medium-high |
| Existing metadata | medium |
| Folder hint | low (fallback only) |

If the combined confidence is below a **configurable threshold**, the asset is marked
**Needs Review** instead of being force-classified. Weights and threshold are config,
not code.

Detection priority: **filename rules → vision → metadata → folder (fallback)**. Vision
runs surgically (on unknown / low-confidence assets), not on every file, to keep scans
fast and free.

---

## 8. Status lifecycle

`Draft → Needs Review → Approved → Archived`. Only **Approved** assets flow downstream.
AI fields are always suggestions (`ai_*`); manual edits (`manual_*`) are permanent and
always win — re-scans and re-classification only ever write `ai_*`.

---

## 9. Manifest contract

Every export stamped with `schema_version` (metadata model) and `rules_version`
(parsing). Downstream consumers read the manifest; they never write back. Because
identities are stable, regeneration is idempotent and safe to re-run at any time.

---

## 10. What is frozen vs. what may evolve

- **Frozen forever:** internal IDs and their immutability; the layer separation; the
  System-of-Record direction; the five principles.
- **May evolve (versioned):** SKU conventions, parsing rules, confidence weights and
  threshold, the metadata/taxonomy model, the display-title style.
