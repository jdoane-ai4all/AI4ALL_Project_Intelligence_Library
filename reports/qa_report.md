# Data Quality, Provenance & Validation Report

Generated 2026-11-06T16:12:02+00:00

## Coverage

| Metric | Value |
|---|---|
| Projects in workbook | 188 |
| Extracted-text sources retrieved | 188/188 |
| Original PDFs retrieved | 188/188 |
| Projects with validated structured extraction | 188/188 |
| Projects with dataset/precedent research | 188/188 |
| Evidence quotes verified verbatim against source | 3666/3666 (100.0%) |
| Original rubric rows preserved (raw_scores / raw_rationale) | 188 / 940 |

## Extraction confidence and source completeness

| Confidence | n |
|---|---|
| medium | 111 |
| high | 73 |
| low | 4 |

| Source completeness | n |
|---|---|
| partial | 114 |
| complete | 71 |
| poor | 3 |

## Evidence levels of classifications

Confirmed = explicitly stated in source; inferred = derived, not stated.

| Dimension | Level | Tags |
|---|---|---|
| industry | confirmed | 419 |
| industry | inferred | 136 |
| method | confirmed | 1062 |
| method | inferred | 175 |
| modality | confirmed | 224 |
| modality | inferred | 58 |
| paradigm | confirmed | 288 |
| paradigm | inferred | 40 |
| task | confirmed | 551 |
| task | inferred | 60 |
| tool | confirmed | 241 |
| tool | inferred | 324 |

## Algorithm roles

| Role | Evidence level | n |
|---|---|---|
| implemented | confirmed | 317 |
| compared | confirmed | 131 |
| baseline | confirmed | 62 |
| proposed | confirmed | 42 |
| considered | confirmed | 20 |
| unclear | inferred | 19 |
| implemented | inferred | 9 |
| unclear | confirmed | 7 |
| baseline | inferred | 2 |
| proposed | inferred | 2 |
| compared | inferred | 1 |

## Missing-field rates (profiles)

| Field | Missing | Rate |
|---|---|---|
| research_question | 0 | 0.0% |
| primary_beneficiary | 0 | 0.0% |
| inputs | 0 | 0.0% |
| outputs | 0 | 0.0% |
| results_summary | 0 | 0.0% |

## Human review queue

Open items requiring human attention. `extraction_flag` items are mostly inconsistencies *in the student materials* (e.g. conflicting metrics, possible leakage) surfaced by extractors; `uncertainty` items document what the source did not say.

| Field | Priority | Open items |
|---|---|---|
| uncertainty | low | 693 |
| extraction_flag | medium | 175 |
| dataset | low | 148 |
| confidence | high | 4 |
| prerequisites | low | 2 |

## Dataset verification

| Relationship | Match level | Links |
|---|---|---|
| alternative | alternative | 14 |
| mentioned | exact | 23 |
| mentioned | possible | 1 |
| used | exact | 143 |
| used | probable | 36 |
| used | possible | 10 |

| Link check status (unique dataset URLs) | n |
|---|---|
| ok | 193 |
| restricted_or_blocked | 16 |
| error | 4 |
| ok_login_redirect | 1 |
| not checked | 1 |

Unresolved dataset clues: 148

## Methodological flags in project materials

Triaged flags (prompts/flag_triage_v1.md; every critical call checked by the lead analyst). `hold` projects are excluded from student recommendations until a reviewer decides; see the private reviewer workbook `data/processed/flagged_projects_review.xlsx`.

| Recommendation status | Projects |
|---|---|
| caution | 94 |
| ok | 79 |
| hold | 15 |

| Severity | Category | Flags |
|---|---|---|
| critical | data_leakage | 7 |
| critical | chance_level_results | 4 |
| critical | contradictory_conclusion | 3 |
| critical | evaluation_design | 1 |
| critical | data_or_source_issue | 1 |
| moderate | inconsistent_metrics | 18 |
| moderate | evaluation_design | 17 |
| moderate | data_leakage | 15 |
| moderate | contradictory_conclusion | 13 |
| moderate | chance_level_results | 7 |
| moderate | unsupported_claim | 5 |
| moderate | other | 5 |
| moderate | incomplete_work | 4 |
| moderate | data_or_source_issue | 2 |
| minor | inconsistent_metrics | 44 |
| minor | other | 16 |
| minor | documentation_gap | 4 |
| minor | data_or_source_issue | 3 |
| minor | incomplete_work | 2 |
| minor | contradictory_conclusion | 2 |
| minor | unsupported_claim | 1 |
| minor | evaluation_design | 1 |

## Original workbook audit (scores never modified)

| Severity | Check | n |
|---|---|---|
| info | id_gaps | 1 |
| warning | missing_field | 1 |
| warning | placeholder_value | 1 |

## Cross-record consistency checks

Non-zero counts in the last two rows are candidates for review, not necessarily errors.

| Check | Projects |
|---|---|
| Industry tags with exactly one primary | 188 |
| Projects with >=1 implemented algorithm | 186 |
| Projects tagged deep_learning but no neural algorithm used | 1 |
| Projects tagged supervised with no implemented model | 1 |

## Versions

| Item | Value |
|---|---|
| built_at | 2026-11-06T16:11:58+00:00 |
| cluster_stats | {"method": "UMAP(10d, cosine) + Ward; k by silhouette x bootstrap ARI", "k": 7, "silhouette_reduced": 0.6485, "silhouette_original_space": 0.1364, "bootstrap_ari_mean": 0.951, "bootstrap_ari_sd": 0.045, "seed_ari_mean": 0.894} |
| pipeline_version | 0.1.0 |
| schema_version | 1.0.0 |
| semantic_model | sentence-transformers/all-MiniLM-L6-v2 |
| taxonomy_version | 1.2.0 |
| workbook_imported_at | 2026-11-06T03:33:53+00:00 |

