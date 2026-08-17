# Vision Subsystem — Blueprint Disclosure

**Purpose:** Record that the vision subsystem's *idea* originated from a
prior internal project (AVI — an Audio/Video/Imaging suite the author
maintains), and to make clear that **no code or architecture was copied**
into CONTINUUM. This file is part of CONTINUUM's compliance record for the
Agentic Cinema Hackathon.

## What was taken

Only the high-level *idea* that a media-analysis pipeline is useful to a
production-intelligence system. The idea came from AVI; every design and
implementation decision in `src/continuum/vision/` was made fresh to fit
CONTINUUM's Google Cloud stack.

## What was NOT taken

- No source files, functions, classes, or type definitions were copied from
  AVI or any other pre-existing project.
- No architectural diagrams, module layouts, or configuration files were
  reused verbatim.
- AVI's engines (local CV models, custom detectors) are **not** invoked at
  runtime by CONTINUUM. The vision subsystem calls only Google Cloud
  services (Video Intelligence, Vertex AI, Gemini, Imagen).

## Why this is compliant

The Contest Rules require that "the Project must be Your original creation
not a modification or extension of Your or anyone else's existing work."
CONTINUUM is a new project created inside the Contest Period; the vision
subsystem is a new module of that project. Naming a prior project as the
source of an *idea* is not a modification or extension of that prior
project — no artifact of AVI ships in this repository.

## Verification

- `git log --follow src/continuum/vision/` shows all files were introduced
  during the Contest Period on the `feat/vision-google` branch.
- `grep -rn 'AVI' src/` returns 0 results — no code references to the
  external project.
- The provider allow-list in `src/continuum/vision/registry.py` restricts
  every engine to Google Cloud SDKs; `tests/vision/test_registry.py`
  enforces this at test time.
