# Support

CONTINUUM is a hackathon project maintained by [Digital Real-Estate
Frontier, LLC](https://digitalrealestatefrontier.com). Support is
best-effort while active development is underway.

## Fastest path by intent

| I want to… | Do this |
|---|---|
| Report a bug | Open a [Bug report](https://github.com/BenDuske/CONTINUUM/issues/new?template=bug_report.yml) |
| Ask a question | Open a [Question](https://github.com/BenDuske/CONTINUUM/issues/new?template=question.yml) |
| Suggest a feature | Open a [Feature request](https://github.com/BenDuske/CONTINUUM/issues/new?template=feature_request.yml) |
| Report a security issue | Email **benduske1979@gmail.com** — do NOT open a public issue |
| Watch the demo | See the [live service](https://continuum-882642985987.us-central1.run.app) and the walkthrough in [`docs/DEMO_VIDEO.md`](docs/DEMO_VIDEO.md) |
| Reproduce the tests | `pip install -e ".[dev]" && pytest -q` — 69 tests, no cloud calls |

## Before you open an issue

1. Search [existing issues](https://github.com/BenDuske/CONTINUUM/issues?q=is%3Aissue) — the answer might be there.
2. Skim [`README.md`](README.md) and [`ARCHITECTURE.md`](ARCHITECTURE.md).
3. If it's a runtime problem, check `/health` on the live service and
   include the JSON in your report.

## What good bug reports include

- The exact command you ran (or the API request).
- What you expected vs. what happened.
- Full traceback / logs (mask credentials).
- Environment: Python version, OS, whether local or Cloud Run.
- Whether `pytest` is green in your checkout.

## Response times

Best-effort. The maintainer has a day job. Security issues take priority.

## License & attribution

Apache License 2.0. See [`LICENSE`](LICENSE).
