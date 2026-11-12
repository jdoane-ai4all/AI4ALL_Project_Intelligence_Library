# Methodology

This document defines every construct in the library, how it is produced, and how it was validated. Current
figures are in the generated reports: [`reports/qa_report.md`](../reports/qa_report.md),
[`reports/research_report.md`](../reports/research_report.md), [`reports/agreement_report.md`](../reports/agreement_report.md),
[`reports/import_validation.md`](../reports/import_validation.md).

## 1. Source data and authority

- The workbook (188 projects, 940 criterion evaluations, 5-criterion rubric) is imported verbatim into `raw_*` tables.
  Rubric scores, rationales, limiting factors and evidence are **authoritative historical records** and are never
  modified. The import audit found one genuine discrepancy (a criterion score differing between the two sheets for
  one project); it is flagged, shown in the UI with a warning, and left unchanged.
- Project IDs are stable; gaps in the sequence are intentional and IDs are never relabeled.
- For each project, the linked extracted-text file and original PDF were retrieved (188/188 each) and cached
  privately with SHA-256 hashes. Text is redacted for personal identifiers before caching (see `docs/governance.md`).

## 2. Evidence-grounded extraction

An LLM reader follows a versioned prompt (`prompts/extraction_v1.md`, v1.1) per project and writes a JSON record
validated against a typed schema (`src/aipil/extraction/schema.py`). Rules that matter for trustworthiness:

- **Evidence levels.** `confirmed` = explicitly stated in the source; `inferred` = reasonably derived, with the
  reasoning recorded in `uncertainties`; unknown items are omitted rather than guessed.
- **Verbatim grounding.** Every confirmed tag and algorithm carries a page number and a quote. The validator checks
  each quote against the cached source after normalizing whitespace, ligatures and bullet glyphs; a record with
  an unverifiable quote cannot pass. Facts visible only in slide images use `pdf_visual` evidence (page + description).
- **Implemented vs mentioned.** Algorithms carry a role (`implemented`, `baseline`, `compared`, `considered`,
  `proposed`, `unclear`). Paradigms, tasks and modalities describe what the project did, not its future work.
  Datasets are `used`, `mentioned`, or `alternative`.
- **Reported results are recorded as reported.** When extractors noticed internal inconsistencies (conflicting
  metrics, chance-level performance, likely target leakage), they added a `review_flags` entry instead of
  "correcting" the student's numbers. These flags are in the human review queue.
- **Source text is untrusted.** Prompts instruct readers to ignore any instructions inside slides or web pages.

### Pilot (15 projects) and what it changed

A stratified pilot (5 student-provided types, rubric totals 8–23, OCR-quality flags, document lengths 3–15k chars)
ran before scale-up. All 15 records validated with 100% quote grounding; the pilot surfaced systematic ambiguities
that were resolved in v1.1 of the prompt, taxonomy and anchors:

| Ambiguity | Resolution (v1.1) |
|---|---|
| Kaggle data behind a free login: data_access 0 or 1? | Free-account portals = 0 |
| validation_rigor 3 awarded for any single time-based split | Level 3 requires **two** listed practices |
| Plots-only work: engineering 0 or 1? | Charts alone = 0 |
| Pretrained model use vs. training deep models for the ML prerequisite | Using pretrained/hosted = 2; training/fine-tuning = 3 |
| Random forest: taxonomy level 1 but "ensemble" anchor = 2 | Different constructs; documented explicitly |
| ARIMA/Prophet paradigm | `statistical_rule_based` |
| Planned vs executed steps | `inferred` + role `unclear` |
| Student handles in Kaggle/HF/GitHub URLs | Keep public dataset publishers; drop student-owned URLs |
| Ligatures and bullets breaking quote matching | Validator normalization |
| Missing redaction of contact rows and user paths | Redactor strengthened; all sources re-redacted |

The 15 pilot records were then revised to v1.1 so the whole collection is rated under one set of anchors.

### Taxonomy

`config/taxonomy.yaml` (v1.2) defines multi-label, hierarchical dimensions: industry (sector → subdomain), paradigm,
task, modality, method, tool, algorithm (with family and a 1–3 learning level). Extractors may propose `new:` terms;
these are consolidated through a versioned **alias map** (deterministic normalization), so raw LLM artifacts are
never edited. Notably, vague model references ("a deep learning model", "an unspecified classifier") map to a single
`unspecified` term so they cannot masquerade as rare algorithms in the originality metrics.

## 3. Assessments (separate constructs)

LLM readers rate **components** against written anchors (`config/assessment.yaml`), each with a one-sentence
rationale; **composites are computed in code** (`src/aipil/classification/assess.py`).

| Construct | Components | Composite rule |
|---|---|---|
| Technical sophistication | algorithmic complexity, data processing, methodological breadth, validation rigor, engineering, mathematical depth (0–3 each) | mean ÷ 3 × 10 → 0–10 |
| Prerequisites | math/stats, ML, domain (1–3); minimum hardware | — |
| Python level | observable criteria (`python_level` in `config/assessment.yaml`): Level 3 = trains/fine-tunes a deep model, system-level engineering, a back-end stack, or RL; Level 2 = interactive app/API, external APIs or scraping, pretrained models via libraries, multi-source or multi-component pipelines; Level 1 otherwise | computed in code; each project lists the criteria it met. The reader's free rating is kept as `python_llm`. Agreement with the blind coder: κ 0.74 (vs 0.70 for the free rating). Projects with no implemented model are marked low-confidence. |
| Difficulty tier | from prerequisites + highest learning level among algorithms actually used | Advanced if ML = 3, or level-3 algorithms with ML ≥ 2, or (max = 3 and Python+math+ML ≥ 7); Beginner if all ≤ 1 or (sum ≤ 4 and only level-1 algorithms); else Intermediate |
| Reproduction effort | data access, data preparation, implementation, compute, dependencies (0–3) | sum → Low ≤3, Moderate ≤7, High ≤11, Very high ≤15, with time estimates |
| Adoption readiness | 7 yes/no criteria | count → Not ready / Needs work / Good / Excellent starting point |

Sophistication rates what was **demonstrated**; tier and effort describe what a **new student** would face. A
sophisticated project with a clean public dataset can legitimately be easier to reproduce than a simple project
built on hard-to-collect data. None of these constructs uses the rubric scores.

## 4. Datasets

Discovery hierarchy: (1) URL in source → (2) named dataset → (3) described dataset → (4) suitable alternative.

- **Level 1 is verified in code** (`src/aipil/datasets/resolve_urls.py`): URLs written in slides are normalized and
  checked by HTTP GET; Kaggle datasets are confirmed through Kaggle's public dataset-metadata endpoint, which also
  yields title, creator and license. A resolving in-source URL is an `exact` match.
- **Levels 2–4 use web research** (`prompts/research_v1.md`, v1.1): no invented URLs; mirrors allowed only when the
  original is not findable, with the original publisher recorded; unnamed datasets matched by a quantitative
  fingerprint (e.g. identical row counts) are at most `probable`; alternatives are labelled as such.
- All canonical URLs are then re-checked by code (`linkcheck.py`). Restricted/login pages are recorded as
  restricted, not broken.

## 5. Originality

Reported as two **separate** measures; neither is a claim of invention.

- **Internal** (computed, `embeddings/similarity.py`): percentile ranks within the collection of (a) semantic
  isolation — 1 − mean cosine similarity to the 5 nearest neighbours in sentence-embedding space
  (all-MiniLM-L6-v2); (b) algorithm rarity — max inverse frequency of algorithms used; (c) domain rarity — max inverse
  frequency of industry subdomains; (d) combination rarity — mean of the three rarest algorithm×sector and
  task×sector pairs. Composite = mean of the four percentiles, plus a pattern label distinguishing *common methods
  in an unusual application* from *unusual methods for a familiar problem*.
- **External** (researched): 1–2 web searches per project for comparable papers, repositories, notebooks and
  tutorials; up to three precedents recorded with URLs; classification into *established*, *distinctive
  application*, *unusual combination*, *potentially novel (requires verification)*; five 1–5 dimension ratings;
  explicit search coverage and confidence. Thin searches yield low confidence by design.

## 6. Similarity, graph and clusters

- Six views: semantic (sentence embeddings of title, question, summaries), algorithm (IDF-weighted algorithm and
  family sets), industry (hierarchical tags), technical (tasks, modalities, paradigms, methods), dataset (shared
  exact/probable datasets) and skills (standardized prerequisite/effort profile), plus a weighted blend
  (`config/similarity.yaml`).
- Each view keeps a sparse union of top-k neighbours above a threshold, so the graph never becomes all-to-all and
  cross-cluster bridges survive. Each edge stores a generated explanation of what is shared and what differs.
- Clusters: UMAP (10-d, cosine) on a blended representation, Ward linkage, k chosen by silhouette × bootstrap
  stability. Reported diagnostics: silhouette in the reduced space (optimistic) and original space (conservative),
  bootstrap ARI and UMAP-seed ARI. Labels are the most over-represented taxonomy terms (support × log-lift), so they
  are interpretable and reproducible. The 3D layout is a separate 3-d UMAP projection.

## 7. Validation and QA

- Workbook import validation (counts, IDs, ranges, totals, sheet consistency, missing values).
- Schema + taxonomy + quote-grounding validation of every extraction and research record.
- Code-based link verification of every dataset URL.
- **Blind second coding** of a random sample by a different model with no access to primary outputs; agreement
  per field in `reports/agreement_report.md`.
- Automated cross-record consistency checks (e.g. deep-learning paradigm without a neural model) in the QA report.
- A human review queue (`review_queue` table) holds every validation problem, extractor flag, uncertainty,
  low-confidence record and unresolved dataset. Missing values are preferred to confident guesses.
- Tests: pytest (ingestion, validation, redaction, quote matching, composites, FK-safe rebuild) and vitest (filters,
  recommendation scoring, prompt parsing), all on synthetic fixtures.

## 8. Methodological flags and recommendation holds

While reading each deck, extractors recorded internal problems in the *materials* (conflicting metrics, likely
leakage, chance-level results presented as success, conclusions contradicted by the project's own evidence). Each
flag is triaged (`prompts/flag_triage_v1.md`) into a category and severity; every critical call was checked by the
lead analyst. Projects with a critical flag are **held** — excluded from the guided recommender by default and
labelled in the catalog — until a person reviews them in `data/processed/flagged_projects_review.xlsx`. Moderate
flags show a caution. Flaws the students acknowledged themselves are not critical. Reviewer decisions entered in the
workbook are imported back (`python -m aipil.export.review_workbook --import`) and override the automatic status.
Flags never alter the original rubric grades and describe materials, not students.

## 9. Source corrections

The workbook is the authority for grades. Corrections enter only as a new version of the owner's source sheet,
diffed cell-by-cell before import and logged in `reports/workbook_changelog.md` (e.g. project-052, 2026-11-06).

## 10. Known limitations

- Ratings are single-coder LLM judgements against anchors; only a sample has been double-coded and no human
  coding has yet been done.
- Slides are a lower bound on what was built; code repositories were not analyzed.
- Embedding similarity on short summaries is coarse; clusters overlap.
- Dataset research is bounded (≈2–4 searches per project); "unresolved" means "not found within budget".
- External originality is low-confidence for most projects and must not be read as evidence of novelty.
