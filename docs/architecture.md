# Architecture

```
 Project_Type.xlsx ──► ingestion ──► raw_* tables (immutable) + projects / rubric tables + audit_flags
          │                                   │
          └─ Drive file IDs ─► sources.retrieve ─► data/private/sources/{text,pdf} + manifest.json
                                              │   (redacted text; PDFs for visual checks)
                                              ▼
            LLM reader (prompts/extraction_v1.md) ─► data/private/extractions/<pid>.json
                                              │   validated by extraction.schema (pydantic + taxonomy
                                              │   + verbatim quote grounding)
                                              ▼
   datasets.resolve_urls (code) ─► research/level1/<pid>.json ─► LLM researcher (prompts/research_v1.md)
                                              │                       ─► research/<pid>.json
                                              ▼                    (validated by datasets.research_schema)
                     database.build ─► normalized SQLite (data/processed/aipil.sqlite)
                                              │   + classification.assess (deterministic composites)
                                              ▼
                     embeddings.similarity ─► embeddings, similarity_edges (6 views + blended),
                                              │   clusters + 3D layout, internal originality
                                              ▼
                     export.exports ─► projects_flat.{csv,json}, library.json ─► app/ (React + 3d-force-graph)
                     analysis.report ─► reports/*.md
```

## Key decisions

| Decision | Why |
|---|---|
| **SQLite** as the primary store | Zero-ops, single file, ships with Python, easy to inspect; the schema is plain SQL so migration to Postgres/DuckDB is mechanical. Parquet/CSV/JSON exports cover analytics and the app. |
| **Raw tables are immutable JSON rows** | Every workbook row is preserved verbatim; normalized/derived tables are rebuilt from them and from versioned artifacts, so original grades can never be silently altered. |
| **Per-project JSON artifacts as the LLM boundary** | LLM output is cached on disk, validated before loading, re-loadable without re-running the model (cost control, idempotence, resume support). The database is always rebuildable from artifacts. |
| **Verbatim quote grounding** | Every confirmed attribute carries a page + quote; the validator checks quotes against the cached source (whitespace/ligature/bullet-normalized). Unverifiable claims cannot be loaded silently. |
| **LLM rates components; code computes composites** | Sophistication, difficulty tier, reproduction band and readiness are deterministic functions of anchored component ratings (`config/assessment.yaml`), making every number explainable. |
| **Generic `project_terms` bridge + versioned taxonomy YAML** | One many-to-many bridge serves industries, paradigms, tasks, modalities, methods and tools, each with evidence level and evidence link; algorithms have their own bridge because they carry role/inputs/outputs. Unknown terms enter as provisional (`new:`) and go to the review queue. |
| **Deterministic Level-1 dataset verification** | URLs written in slides are checked by code (HTTP GET + Kaggle's public metadata endpoint, which also yields licenses), reserving web research for genuinely unresolved datasets. |
| **Multi-view sparse kNN graph** | Separate similarity notions (topic, algorithm, industry, technical, dataset, skills) avoid conflating "same method" with "same topic"; sparse kNN keeps the graph legible; each edge stores a generated explanation of what is shared. |
| **React + Vite + 3d-force-graph (three.js)** | 3d-force-graph gives real orbit/zoom/pan/drag/hover/click on WebGL with little code; React handles the catalog, filters and detail views. A static build reads one JSON bundle — no server needed. A list/grid explorer is the accessible fallback. |

## Layout differences from the brief

- Python code lives in a single package `src/aipil/` with the suggested sub-packages (`ingestion`, `sources`,
  `extraction`, `classification`, `datasets`, `originality`→part of `embeddings/similarity.py`, `embeddings`,
  `database`, `analysis`, `export`).
- LLM prompts are versioned in `prompts/`.
- `data/private/` holds every private artifact; `data/processed/` holds derived private outputs. Both are git-ignored.
