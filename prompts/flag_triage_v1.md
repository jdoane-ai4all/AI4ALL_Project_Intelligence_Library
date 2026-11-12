# Flag triage prompt v1 (`flag_triage_v1`)

Input: `data/private/qa/flags_input.json` — review flags written by extractors about student project *materials*.
Output: `data/private/qa/flag_triage.json` — one entry per input flag:
`{"project_id", "flag_index", "category", "severity", "label", "student_acknowledged"}`.

Flags describe project materials, never students. Do not judge people.

## Categories
- `data_leakage` — target/label information leaks into features; label built from the input features; augmentation or
  preprocessing before the split; circular labels (e.g. a classifier predicting clusters made from the same features).
- `chance_level_results` — performance at or near chance or the majority-class rate, presented as success.
- `contradictory_conclusion` — the conclusion contradicts the project's own evidence (e.g. chosen "best" model is worse).
- `inconsistent_metrics` — reported numbers disagree across slides/charts/workbook or are arithmetically impossible.
- `evaluation_design` — weak evaluation: tiny/unrepresentative test set, no baseline or control, test-set selection,
  confounded data sources, metric misuse.
- `unsupported_claim` — a claim with no supporting evidence in the materials.
- `incomplete_work` — planned/unfinished work, placeholders, no results reported.
- `data_or_source_issue` — dataset unavailable/removed, unnamed, or mismatched with the description.
- `documentation_gap` — missing details (target not stated, library unnamed) without implying a flaw.
- `other` — anything else.

## Severity (for use as an example project for students)
- `critical` — a fundamental methodological flaw that makes the headline result invalid or misleading
  (typically data_leakage, chance_level_results presented as success, contradictory_conclusion on the main result).
  If the students explicitly acknowledged the flaw in their own slides, use `moderate` instead and set
  `student_acknowledged: true`.
- `moderate` — results should be treated with caution but the project remains a reasonable starting point.
- `minor` — informational; does not affect suitability.

`label`: a plain-language error label of at most 12 words (e.g. "Target derived from input features (label leakage)").
