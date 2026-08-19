# CONTINUUM Schema Migrations

Numbered, forward-only DDL. Each file is a single migration; the runner in
[`scripts/init_db.py`](../../../../scripts/init_db.py) applies unapplied
migrations in filename order and records what ran in the
`continuum.schema_migrations` tracking table (created automatically on
first run).

## File naming

```
NNN_<snake_case_summary>.sql
```

- `NNN` = zero-padded 3-digit sequence starting at `001`.
- Never reuse or renumber a migration once it has run somewhere.
- Never edit an applied migration in place — write `004_fix_that.sql` instead.

## Existing migrations

| # | File | What it does |
|---|------|--------------|
| 001 | [`001_init.sql`](001_init.sql) | Core Living Film Graph: `scenes`, `shots`, `takes`, `props`, `wardrobe`, `production_events`, `continuity_issues`, `scene_dependencies` + materialized views. |
| 002 | [`002_vision.sql`](002_vision.sql) | Vision-subsystem tables: `frame_observations`, `take_dialogue`, `vision_verdicts`, `frame_embeddings`. |

## Add a new migration

1. Create `003_<summary>.sql` in this directory.
2. Write forward-only SQL. Prefer `CREATE TABLE IF NOT EXISTS` and
   `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` so a partial re-run is safe.
3. Test locally against a scratch ClickHouse: `python scripts/init_db.py`.
4. Commit both the migration file and any code changes that depend on it
   in the same PR.

## Tracking

The runner creates and reads `continuum.schema_migrations`:

```sql
CREATE TABLE IF NOT EXISTS continuum.schema_migrations (
    version   String,
    applied_at DateTime DEFAULT now()
) ENGINE = MergeTree ORDER BY version;
```

A migration whose `version` (== filename) already appears in that table is
skipped. Delete a row to force a re-run.
