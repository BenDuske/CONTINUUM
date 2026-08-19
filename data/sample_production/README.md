# Sample Productions

CONTINUUM ships with two very different sample productions so the agents
demonstrate genre-independence — the same agent set, same prompts, same
ClickHouse schema, two productions that stress different things.

| ID | Title | Genre | Scenes | Days | What it stresses |
|---|---|---|---|---|---|
| `tls-001` | [THE LAST SIGNAL](the_last_signal.json) | Sci-fi thriller | 47 | 31 | Multi-location shoot, a damaged prop that must propagate across scenes, coverage math on complex sequences. This is the signature demo (Scene 42, Camera P-14). |
| `sr-002`  | [SUNDAY ROAST](sunday_roast.json) | Family drama · short film | 12 | 4  | Chamber piece — one house, one meal. Tight coverage ratios, subtle prop continuity (wine level, food state, an unnoticed ring), Skeptic-heavy because "the director meant it" is a genuine counter-argument in drama. |

The metadata JSONs above are the human-readable production briefs. The
scene / shot / take / prop rows are seeded into ClickHouse by
[`scripts/load_sample_data.py`](../../scripts/load_sample_data.py) —
currently seeds `tls-001` only; `sr-002` seed data is TODO
([tracked in the issue tracker](../../.github/ISSUE_TEMPLATE/feature_request.yml)).
