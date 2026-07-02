# KF Asset Manager — Database Lifecycle & Schema Migrations

> Status: **implemented.** Explains why `audit.db` is no longer disposable, how it's
> preserved by default, what `--fresh` actually destroys, and how schema migrations keep
> a preserved database working as the code evolves.

## Why `audit.db` is now non-disposable

For most of this project's history, `audit.db` held only *re-derivable* data: designs,
products, and SKUs computed deterministically from the image library. Rebuilding it from
scratch on every run was safe and simple — run the importer again, get the same result.

That stopped being true once the database began holding data that **cannot be
regenerated from the image library alone**:

- **AI vision results** (`vision_results` — suggested names, style tags, match
  confidence/reason) are the output of a real, paid API call. Losing them means paying
  again to get them back.
- **Local colour extraction** is free to regenerate, but is still meaningful accumulated
  work worth preserving.
- **Manual `display_title` overrides** are a human decision. There is no way to
  regenerate "the title someone approved" from the image file.

A database holding any of this is not a cache — it's a record of real work and real
money. Treating it as disposable was the root cause of a real incident: a routine
`--report` re-run silently deleted a completed 20-image AI batch before it could even be
reviewed.

## The default: preserved

`build_graph` **preserves the database across runs by default.** Re-importing the same
library into an existing database is safe because identity import is idempotent —
proven since Phase 1 (a re-scan adds no duplicate rows, and no opaque ID is ever changed
or reused). So a routine, repeated run of:

```bash
python -m kf_asset_manager.build_graph --root <library> --report --out <reports_dir> --no-hash
```

will safely update/extend identity data on top of whatever already exists in
`<reports_dir>/audit.db`, while leaving every AI result, colour extraction, and manual
title override exactly as it was.

## `--fresh`: the explicit, destructive option

When a genuinely clean, throwaway database is wanted, pass `--fresh`:

```bash
python -m kf_asset_manager.build_graph --root <library> --report --out <reports_dir> --no-hash --fresh
```

`--fresh` deletes the existing database file and rebuilds from nothing. It is
**destructive** and prints a warning before doing so. It erases, permanently:

- every AI vision result (name/tags/confidence — real spend, gone)
- every local colour extraction
- every manual `display_title` override

Only use `--fresh` when that loss is deliberate and acceptable — for example, when testing
against a disposable scratch library, not against your real catalogue.

## Schema migrations

Preserving the database across runs introduced a second problem, distinct from the
delete-on-every-run issue above: **the code's schema changes over time, but a preserved
database on disk does not change itself.**

Every table in this project is created with `CREATE TABLE IF NOT EXISTS`. That statement
is a no-op against a table that **already exists** — critically, it does **not** add
columns that were introduced to that table after it was first created. This was invisible
for the entire project because the database was always rebuilt from scratch, so every
table was always created fresh with its full, current column set. Once the database is
preserved, that safety net disappears: opening an older, preserved database with newer
code that expects a column added since would fail with `sqlite3.OperationalError: no such
column`.

**The fix is a lightweight, automatic migration system**, run every time a database is
opened (`IdentityDB.__init__` → `_run_migrations()`), before any other code touches the
database:

1. A `schema_migrations` table tracks which migrations have been applied, by name.
2. Each migration is a simple, declarative entry: a table, a column, and the SQL needed
   to add that column (`IdentityDB.MIGRATIONS`).
3. For each migration, the system checks whether the column already exists
   (`PRAGMA table_info`). If not, it runs `ALTER TABLE … ADD COLUMN …` to add it. If the
   column has a `DEFAULT`, SQLite correctly backfills that default onto every existing
   row — for example, `products.source_id` backfills to `''` (the "grouped original"
   sentinel already used throughout the codebase), so no old data needs any further
   massaging.
4. The migration is then recorded in `schema_migrations`, whether or not the `ALTER` ran
   (a brand-new database already has every column via `CREATE TABLE`, and simply gets the
   migration recorded without a redundant `ALTER`).
5. This is fully idempotent: running it again — on the same open, or on a later open —
   never re-applies a migration or errors on a column that's already there.

Columns without a `DEFAULT` (like `vision_results.is_match` or `products.display_title`)
are added as `NULL` for pre-existing rows. This is correct, not a gap: `NULL` is already
the platform's standard "not set" sentinel everywhere — `title_for()` already treats a
`NULL` `display_title` as "use the generated default," and a `NULL` `is_match` on an old
row honestly reflects that the verdict genuinely wasn't captured at the time, rather than
inventing a value that was never actually computed.

### What this does and doesn't cover

This migration system handles the case that matters in practice: **additive columns**,
which is the only kind of schema change this project has made to an already-shipped
table so far. It deliberately does not attempt to rebuild a table to change or add a
`UNIQUE`/constraint definition (SQLite requires a full table rebuild — rename, recreate,
copy, drop — for that, which is a meaningfully bigger and riskier operation). No such
constraint change is currently needed against any real preserved database, since the
`products` table's `UNIQUE(design_id, product_type, source_id)` constraint was
established before database preservation began. If a future change ever needs to alter a
constraint on an existing table, that will need a dedicated, more careful migration — not
a simple entry in this registry.

### Practical effect

You do not need to do anything differently. Running the normal command continues to work
exactly as before; migrations run silently and automatically. If you ever need to confirm
what's been applied to a given database:

```bash
python -c "
from kf_asset_manager import model
db = model.IdentityDB('<path-to-audit.db>')
print(db.applied_migrations())
"
```
