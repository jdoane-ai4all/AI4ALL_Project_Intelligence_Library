# AI Project Intelligence Library · AI4ALL edition

> **AI4ALL-branded edition.** Same pipeline, data rules and app as the original, restyled to the AI4ALL Style Guide
> (v1.2): Forest/Miami themes from the brand palette, Miriam Libre and Crimson Text, and the official pill
> logomark. The logo files in `app/public/brand/` were taken unmodified from the style guide's own artwork, as the
> guide requires (never redrawn). Chart palettes are brand-led and checked for colorblind separation and contrast.

An evidence-grounded research database and interactive atlas of **188 student AI/ML projects**: what each
project did, which algorithms and data it actually used, how sophisticated and reproducible it is, how distinctive
it is, which public datasets would let a new student build something comparable, and how projects relate to one
another — alongside the original, unchanged rubric grades.

> **Private by default.** The source workbook, student presentations, extractions, database and app data bundle
> are never committed (see [`docs/governance.md`](docs/governance.md)). This repository contains code, schema,
> taxonomy, prompts, documentation and aggregate QA reports only.

## What's here

| Path | Contents |
|---|---|
| `src/aipil/` | Python pipeline: ingestion & validation, source retrieval & redaction, extraction schema/validator, deterministic assessments, dataset resolution & link checks, similarity/clustering/originality, DB build, exports |
| `config/` | Versioned taxonomy (`taxonomy.yaml`), assessment anchors (`assessment.yaml`), similarity settings |
| `prompts/` | Versioned LLM instructions for extraction and dataset/precedent research |
| `app/` | React + TypeScript + 3d-force-graph app: 3D constellation, explorer, project profiles, guided discovery, insights |
| `tests/`, `app/src/*.test.ts` | Python (pytest) and frontend (vitest) tests on synthetic fixtures |
| `reports/` | Import validation, QA and research reports (aggregate, no student data) |
| `docs/` | Architecture, methodology, taxonomy, governance, user guide |

## Quick start

```bash
pip install -e ".[dev,embeddings]"
```

Place the workbook at `data/private/raw/Project_Type.xlsx`, then:

```bash
make all
```

`make all` runs, in order: `ingest` (import + validate the workbook) → `fetch` (retrieve linked texts/PDFs into
`data/private/sources`) → `build` (load validated extractions/research into SQLite) → `similarity` → `export` →
`report`. LLM extraction and research are run separately (they are the only steps with model cost) following
`prompts/`; their JSON outputs are cached so the rest of the pipeline is reproducible without re-running them.

Run the app against the generated private bundle:

```bash
cd app && npm install && npm run dev
```

## Hosting: private Streamlit app

The atlas is hosted as a **private** Streamlit app shared with named viewers, because the data bundle is private
student work. `scripts/build_streamlit.sh` assembles the deploy folder (app + `library.json` + brand icon) in
`data/processed/streamlit_deploy/` (git-ignored); deploy it from a private repository only. If the app is opened
without bundled data, it asks the viewer to open their own `library.json`, which is read in the browser only.

## Constructs (kept separate on purpose)

- **Original rubric scores** — authoritative historical grades on 5 criteria; never modified (discrepancies are only flagged).
- **Technical sophistication** — what the project demonstrated (6 anchored components → 0–10).
- **Difficulty tier** — Beginner / Intermediate / Advanced background needed for a comparable project.
- **Reproduction effort** — Low / Moderate / High / Very high, from data access, preparation, implementation, compute, dependencies.
- **Adoption readiness** — 7-point checklist for use as a starting point.
- **Originality** — internal (percentile within the collection) and external (precedent search) reported separately.

See [`docs/methodology.md`](docs/methodology.md) for definitions, anchors, validation and limitations.

## Status (current build)

- 188/188 projects ingested, sources retrieved, extracted and researched; 4,044/4,044 evidence quotes verified verbatim.
- 137 projects have their original dataset identified as a public resource (exact/probable); 225 dataset URLs link-checked in code.
- Blind second coding (12-project random sample): algorithm agreement (Jaccard) 0.92, primary sector 0.92.
- 7 stable data-driven clusters (bootstrap ARI 0.95); 3,142 explained similarity edges across 7 views.
- See `reports/` for the QA, agreement, import-validation and exploratory research reports.
