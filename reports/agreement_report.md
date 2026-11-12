# Inter-coder Agreement (blind second coding)

Generated 2026-11-06T03:39:37+00:00

Random sample of **12** projects (seed 42) re-coded blind by a second model with no access to the primary extraction. Taxonomy aliases applied to both. Values are means across projects.

| Field | Agreement | Metric |
|---|---|---|
| algorithms_used | 0.92 | mean Jaccard |
| algorithms_implemented | 0.92 | mean Jaccard |
| primary_sector | 0.92 | exact match rate |
| industries | 0.88 | mean Jaccard |
| paradigms | 1.00 | mean Jaccard |
| tasks | 0.81 | mean Jaccard |
| modalities | 0.94 | mean Jaccard |
| prerequisite: python (original reader rating) | exact 0.67, within-1 1.00, weighted κ 0.70 | ordinal 1–3 |
| prerequisite: math_stats | exact 0.92, within-1 1.00, weighted κ 0.89 | ordinal 1–3 |
| prerequisite: ml | exact 0.92, within-1 1.00, weighted κ 0.90 | ordinal 1–3 |
| prerequisite: python (criteria-based, used in catalog) | exact 0.75, within-1 1.00, weighted κ 0.74 | ordinal 1–3 |

## Per-project algorithm agreement

| Project | Jaccard (used algorithms) | Primary sector agrees | Disagreeing algorithms |
|---|---|---|---|
| project-008 | 1.00 | 1 | — |
| project-026 | 1.00 | 0 | — |
| project-030 | 1.00 | 1 | — |
| project-032 | 1.00 | 1 | — |
| project-039 | 1.00 | 1 | — |
| project-061 | 1.00 | 1 | — |
| project-066 | 1.00 | 1 | — |
| project-074 | 1.00 | 1 | — |
| project-149 | 1.00 | 1 | — |
| project-162 | 0.50 | 1 | naive_baseline, rule_based |
| project-174 | 1.00 | 1 | — |
| project-185 | 0.60 | 1 | naive_baseline, rule_based |

Interpretation: disagreements are inspected manually; typical sources are (a) whether a model shown only as a comparison counts as used, (b) generic vs. specific slugs (e.g. CNN vs. ResNet), and (c) subjective ordinal ratings. Agreement figures bound the reliability of the corresponding catalog fields.
