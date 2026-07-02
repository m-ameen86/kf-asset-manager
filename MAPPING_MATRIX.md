# KF Asset Manager — Production Mapping Matrix

Purpose: map every real Karen Fabrics production case onto the **current frozen model**
(Family → Design → Asset → Product, v1.5) and mark where it forces a *special case*.
This is the evidence base for deciding whether **Artwork Source** should become a
first-class entity in v2.0 — *after* the real scan, not before.

## Special-case legend

| Code | Special case | Why it's a smell |
|------|--------------|------------------|
| **SC1** | Compatibility **bypass** (`from_derived`) — a design backs a product type outside its own `design_type` | The compatibility gate stops being the single answer to "what can this design make" |
| **SC2** | Product **discriminator** — more than one product of the same type on one design | `(design, product_type)` is no longer naturally unique |
| **SC3** | Derived-artwork **fields** on the asset (`artwork_role`, `derived_from_*`) | Derivation lives as row attributes, not a first-class concept |
| **SC4** | One asset → **many products** (POD multi-application), no per-application artwork | "Application" is implicit in `product_type`; no identity for it |
| **SC5** | Legacy **A/B** parsing | Backward-compat only; already frozen |
| **SC6** | Set / **Family** grouping | Expected and supported; listed for completeness |

## The matrix

| # | Production case | Example | Family | Design(s) | Assets | Products | Variants live in | Special cases | Verdict |
|---|-----------------|---------|--------|-----------|--------|----------|------------------|---------------|---------|
| 1 | Curtain pair | `Kids-3141-L/R` | — | 1 curtain | 2 panels (+masters) | 1 Curtain | Pair/Left/Right | — | **Clean** |
| 2 | Curtain merged single | `Kids-3061-C` | — | 1 | 1 (+masters) | 1 Curtain | Single | — | **Clean** |
| 3 | Curtain + **derived sided cushions** | `P4134` | — | 1 curtain | 4 (2 orig + 2 derived) | 3 (Curtain + Cushion L + Cushion R) | Curtain: Pair/L/R | **SC1 + SC2 + SC3** | **Awkward** |
| 4 | **Independent compositions** + derived cushion | `P4207` D1/D2 | 1 | 2 (D1, D2) | 2 / design | 2 / design (Curtain + Cushion) | per product | **SC1 + SC3** | **Mild–Awkward** |
| 5 | Repeat pattern, **multi-application POD** | floral tile | — | 1 (repeat_pattern) | 1 (reused) | many (Fabric, Cushion, Tote, Scarf, Runner, Tablecloth) | length / size / colour | **SC4** | **Mild** |
| 6 | Batched coordinated set | Ramadan `C4` | 1 (set) | many pieces | per piece | per design | per product | SC6 (+SC5 legacy; +SC1/SC3 *if* pieces derived) | **Mild** (Awkward if pieces are derived) |
| 7 | Tapestry | fixed artwork | — | 1 (fixed_artwork) | 1 (+master) | 1 Tapestry | size | — | **Clean** |
| 8 | Apparel / **placed artwork** | t-shirt front | — | 1 (placed_artwork) | 1 (+master) | many (Tee, Hoodie, Poster, Canvas, Tote) | size / colour | **SC4** | **Mild** |
| 9 | Fabric-by-the-metre (anchor) | repeat tile | — | 1 (repeat_pattern) | 1 | 1 Fabric | length × material matrix | — | **Clean** |
| 10 | Customer upload / custom POD | upload | — | 1 | 1 | 1+ | per order | — (`source_library` metadata) | **Clean** |
| 11 | Curtain + **independent** cushion | coordinated, separately designed | 1 | 2 (both independent) | per design | per design | per product | SC6 | **Clean** |
| 12 | Multi-master file | `*.jpg + *.psd + *.tif` | n/a | n/a | 1 (masters attached, no own ID) | n/a | n/a | — | **Clean** |

## What the matrix shows

The base entity model holds **cleanly for the majority** of the catalogue — pairs,
singles, tapestries, fabric-by-the-metre, independent coordinated pieces, customer
uploads, and multi-master files all map with **zero** special cases.

The awkwardness is **not spread across the catalogue — it concentrates in exactly one
shape**: *a derived application on a type-restricted design.* Concretely:

- **SC1 (bypass) + SC3 (derived) always travel together**, and only on designs whose
  `design_type` restricts product type — i.e. **engineered curtains that ship with
  cushions** (cases 3 and 4, and any derived pieces in 6). The cushion is a different
  product type than the curtain design allows, so it must bypass the gate.
- **SC2 (discriminator) is rarer still** — it appears *only* when the derived
  application is **sided** (Left Cushion + Right Cushion on one design: case 3).
- **SC4 is mild, not awkward.** On permissive design types (repeat_pattern,
  placed_artwork) one artwork legitimately backs many products with **no bypass**,
  because compatibility already allows them. It works; it's just that "which
  application" is implicit in `product_type` rather than a named thing.

So the single archetype that strains the model is **"engineered curtain + cushion(s)."**
Everything else is clean or mild. That is precisely the case Artwork Source was designed
to absorb — and precisely the case the engineered-panel scan will let us *count*.

## Decision criterion for v2.0 (to apply after the real scan)

Adopt **Artwork Source** as a first-class entity if the scan shows the awkward shape is
**routine rather than occasional**. Measure:

1. **SC1 rate** — share of designs that create a `from_derived` product (a product type
   outside the design's own compatibility). High share ⇒ the bypass is the norm, not an
   exception ⇒ Source pays off.
2. **SC2 frequency** — how often a design carries more than one product of the same type
   (sided derived cushions). Recurring ⇒ the discriminator is load-bearing ⇒ Source.
3. **Derivation depth** — any multi-hop chains (curtain → cushion → tote …). Present ⇒
   attribute-on-asset derivation gets unwieldy ⇒ Source.
4. **POD breadth (SC4)** — if one artwork routinely fans out to many curated
   applications, Source gives each application the identity it currently lacks.

Rough threshold to keep us honest: if **SC1 fires on a large minority of engineered
designs**, or **SC2/derivation-depth recur**, Artwork Source is a *deliberate* v2.0
upgrade. If derived applications are occasional, the three special cases stay localized
and the v1.5 model is good enough — no new entity.

## What to watch during the scan (operationalizes the above)

When you scan the real engineered-panel library, capture per run:

- count of products flagged `from_derived` (SC1) vs total products;
- count of designs with >1 product of the same `product_type` (SC2);
- distribution of `design_type` across designs (sanity on classification);
- every asset routed to **needs_review** (where the Rule Engine was unsure — these also
  surface the naming variants your naming standard must pin down, e.g. `-cush`, `-D#`,
  `P####`);
- any filename that fails to match a rule (drives the **library normalization** +
  **naming standard** work directly).

If you'd like, I can add a `--report` summary to `build_graph` that prints exactly these
counts at the end of a scan, so the evaluation is a single command rather than manual
inspection.
