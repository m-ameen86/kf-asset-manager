# KF Asset Manager — Architecture Review & Production Readiness Gate

Reviewed at **architecture v1.6**, Phases 1–2 approved. This is a review and readiness
assessment, **not** a redesign. v1.5/v1.6 remains the baseline; no new *core* entity is
introduced. The only structural addition is the metadata-only Business Metadata layer
you explicitly requested (one generic table, identity-inert). Everything else is
confirmation, recommendation, and the readiness checklist.

---

## 1. Business Metadata Layer — added (metadata only)

Introduced as a **single generic key/value store** (`business_metadata`), not a set of
per-dimension tables, and deliberately *loose* (it references entity IDs as data, not as
foreign keys into identity). Dimensions: `business_line`, `market`, `room`, `collection`,
`theme` — extensible.

**Hard invariant:** it never affects internal IDs, SKU generation, or design identity. It
exists only for search, filtering, Shopify collections, AI, SEO, and merchandising.
Proven by `tests_metadata.py` (8/8): tagging a design changes neither its ID nor its
`design_type`, no business column leaks onto the identity tables, dimensions are
multi-valued, and `find_by_metadata` supports collection-style filtering.

Why one table and not five: it satisfies the request with the smallest possible
footprint (no new core entity, no new relationship into identity, no schema churn when a
new dimension appears) — consistent with point 9.

## 2. Design Types stay technical — confirmed

`repeat_pattern`, `engineered_panel`, `fixed_artwork`, `placed_artwork`, `set_piece`
remain **technical** classifications. Business concepts (Kids, Ramadan, Luxury…) live in
Business Metadata, never in design types.

**On evolving `engineered_panel`** (for future Roman blinds, wall panels) — trade-offs,
as requested, with **no change made**:

- *Rename to an umbrella* (e.g. `engineered_textile` / `structured_panel`): one type
  spans many structured products, but it **churns a frozen technical name** (rule engine,
  `design_types_version`, manifests, any imported data) and **conflates compatibility** —
  a Roman blind's product mapping isn't a curtain's, so one umbrella type would need
  conditional compatibility to stay correct.
- *Add sibling types* later (`roman_blind`, `wall_panel`), each with its own
  compatibility: no churn, no rename, and compatibility stays clean per type.

**Recommendation:** keep `engineered_panel` exactly as-is now. When those products
actually arrive, prefer **adding sibling technical types** over renaming; reserve a
rename for a deliberate major-version migration if ever justified. No production driver
exists today, so freezing it is correct.

## 3. Import Library, not Scan Folder — terminology updated

The Asset Manager is the permanent database, so the read-a-folder operation is an
**Import**. Documentation and CLI wording now use:

- **Import Library** — first load of a catalog-ready folder.
- **Refresh / Synchronize Library** — re-import for additions/edits. Already supported
  and **idempotent**: identities key off content hash + grouping key, so a refresh never
  changes an existing ID or drops metadata.

"Scan" is retained only where it means the literal filesystem walk inside an import.

## 4. Validation sequence — confirmed

Yes, this is the recommended order, unchanged:

1. Organize the Catalog-Ready library
2. **Import** Library
3. Run the Production Auditor (`--report`)
4. Evaluate the reports
5. Measure SC1–SC4 (materialised + estimated)
6. Decide whether v2.0 (Artwork Source) is justified

No new entity before step 6. The auditor's **estimated SC** block is the decision input;
the **materialised SC** block will stay near-zero until an engineered-panel (`P####`)
rule exists — which is itself a step to schedule *after* you've seen the real numbers.

## 5. Folder Organization — recommendation

**Principle: top-level folders are TECHNICAL (drive `design_type`); business groupings
are METADATA, never parser or ID logic.** This directly answers your question — *Kids /
Paintings / Ramadan should be Business Metadata, not parser logic.*

Recommended Catalog-Ready layout:

```
00_Catalog-Ready/
├── Engineered_Panels/      → design_type = engineered_panel
├── Repeat_Patterns/        → design_type = repeat_pattern
├── Fixed_Artwork/          → design_type = fixed_artwork
├── Placed_Artwork/         → design_type = placed_artwork
└── Sets/ (or Coordinated/) → set_piece / Families
```

Business line as an **optional second level**, read into metadata at import — not into
identity:

```
Engineered_Panels/
├── Kids/         → business_line = Kids   (metadata)
├── Paintings/    → business_line = Paintings
└── Ramadan/      → business_line = Ramadan
```

So the importer assigns `design_type` from the **first** folder level (deterministic,
high-confidence) and `business_line` from the **second** level into Business Metadata.
The opaque Design ID is unaffected by either. Note the same word may appear in legacy
*filenames* (`Kids-3141`): keep parsing it for backward compatibility, but treat the
"Kids" token as **business metadata**, not design identity.

## 6. Naming Standard — review

**Legacy (frozen — keep parsing, never regenerate):**

| Pattern | Meaning |
|---------|---------|
| `Kids-3141-L` / `-R` | line + number + curtain side (A/B → L/R legacy) |
| `P4134-L` / `-R` | engineered panel code + side |
| `P4134-L-cush` | derived cushion artwork from that panel |
| `P4207-D2` | independent composition (D2) |

**Forward standard (recommended; backward-compatible — applies to new files only):**

```
<CODE>[-D#][-<side>][-<application>]
```

- **`<CODE>`** — the base design code (e.g. `P4134`). Human-readable line prefixes are
  fine but are *metadata*, not identity.
- **Independent designs / design variants** — `-D2`, `-D3` (D1 implicit). Canonical and
  already locked. **Never `A/B` for new variants** (A/B is legacy-curtain-side only).
- **Side** — `-L`, `-R`, or `-C` (merged single).
- **Derived application/artwork** — an explicit token: `-cush`, `-runner`, `-tote`,
  `-scarf`. Signals "derived artwork for application X." Combine as `P4134-L-cush`.
- **Repeat patterns** — give them a distinct code space (e.g. `RP-####`) so they are not
  confused with engineered panels; `design_type = repeat_pattern`.
- **Masters** — same stem, different extension (`.psd` / `.tif`); they attach, never mint
  their own ID.

Backward compatibility rule stays absolute: legacy rules are frozen, A/B keeps its
legacy curtain-side meaning, and the engine still parses old names unchanged. New files
*should* follow the standard, but nothing old breaks.

## 7. ID Readability — confirmed (already implemented)

Internal IDs stay immutable and opaque (`KF-D-000087`). The UI uses **Display IDs**
(`D87`, `P42`, `A931`, `F12`), derived on the fly, never stored, never used as
identifiers. Long internal IDs are shown only when debugging. Implemented in
`display.py`.

## 8. Production Readiness Checklist

| Question | Answer |
|----------|--------|
| **Is the architecture production-ready?** | **Yes for the validated scope** (identity, relationships, rule engine, compatibility, derivation primitives, metadata, Display IDs) — *pending one thing*: the engineered-panel (`P####`) convention is not yet parsed, so real engineered-panel import needs that rule before its numbers are meaningful. The data model itself is ready. |
| **What still needs validation?** | Real-catalogue import + audit; SC1–SC4 on real data; rule coverage / unmatched rate on real filenames; design-type distribution; duplicate levels; naming consistency. All produced by the Production Auditor. |
| **What is frozen forever?** | The five core principles; opaque immutable IDs and their entity prefixes; "Design = artwork identity"; the Design-vs-Variant vocabulary; A/B = legacy curtain side only; Display-ID scheme; one-directional System-of-Record generation. |
| **What can still evolve?** | The Rule Engine (versioned `rules_version`); the design-type taxonomy (versioned, **additive** — e.g. `roman_blind`); compatibility rules (JSON field, allowed→conditional/etc.); the Business Metadata vocabulary; confidence + vision (Phase 3); the v2.0 Artwork Source decision (data-driven). |
| **What should NOT be changed anymore?** | Anything that would alter an existing ID or its meaning; the identity/relationship core; the A/B legacy semantics; the frozen vocabulary. Changes here would invalidate already-minted IDs and downstream references. |

## 9. No New Features — honored

No new **core** entity, table-of-relationships, or identity relationship was added. The
single addition is the metadata-only `business_metadata` store you requested in point 1,
which is orthogonal to identity and inert until populated. Focus stays on **validating
the current architecture against the real production library**; structural change (v2.0
Artwork Source) is recommended **only if the auditor proves it necessary**. Stability
before scale.

---

### Bottom line

The architecture is ready to meet the real catalogue. The one genuine gap is rule
coverage for engineered panels (`P####`), which the auditor will quantify rather than
assume. Recommended next action remains: organize Catalog-Ready → **Import** → audit →
read SC1–SC4 together → then, and only then, decide on Phase 3 and v2.0.
