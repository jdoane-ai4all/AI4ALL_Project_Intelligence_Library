# Exploratory Research Report: The AI Project Landscape

Generated 2026-11-06T16:12:02+00:00

> Exploratory, descriptive analysis of the enriched catalog. Rubric scores measure compliance with the presentation rubric, not holistic quality. Sophistication, tier, effort and originality are estimates from a documented framework (docs/methodology.md). Correlations are reported with bootstrap 95% CIs and uncorrected permutation p-values; none is confirmatory. Any figure used externally must be verified against the primary source first.

Projects analyzed: **188**.

## 1. Distribution of ML methods

### Most common algorithms (implemented, baseline or compared)

| Algorithm | Projects | % |
|---|---|---|
| Random forest | 96 | 51% |
| Logistic regression | 68 | 36% |
| XGBoost | 43 | 23% |
| Rule-based / heuristic scoring | 32 | 17% |
| Linear regression | 25 | 13% |
| BERT-family encoder | 16 | 9% |
| Support vector machine | 16 | 9% |
| Decision tree | 15 | 8% |
| ResNet | 15 | 8% |
| Convolutional neural network (custom) | 13 | 7% |
| K-means | 12 | 6% |
| Naive Bayes | 11 | 6% |
| Multilayer perceptron / feed-forward NN | 11 | 6% |
| LightGBM | 8 | 4% |
| Gradient boosting (sklearn/generic) | 8 | 4% |
| EfficientNet | 7 | 4% |
| TF-IDF + linear model pipeline | 7 | 4% |
| Lexicon sentiment (VADER/TextBlob) | 7 | 4% |
| Stacking / voting ensemble | 7 | 4% |
| LSTM | 6 | 3% |

### Paradigms

| Paradigm | Projects |
|---|---|
| Supervised learning | 173 |
| Deep learning | 59 |
| Transfer learning / pretrained models | 46 |
| Unsupervised learning | 18 |
| Hybrid ML + rules/statistics | 11 |
| Non-ML statistical or rule-based | 10 |
| Generative AI | 9 |
| Reinforcement learning | 1 |
| Self-supervised learning | 1 |

### Data modalities

| Modality | Projects |
|---|---|
| Tabular | 118 |
| Text | 45 |
| Time series | 44 |
| Image | 34 |
| Geospatial / remote sensing | 13 |
| Sensor / IoT | 10 |
| Audio | 7 |
| Multimodal | 6 |
| Video | 4 |
| Structured grid / board state | 1 |

### Task types (top 15)

| Task | Projects |
|---|---|
| Classification | 133 |
| Binary classification | 96 |
| Exploratory data analysis | 48 |
| Regression | 48 |
| Multi-class classification | 44 |
| Risk scoring | 29 |
| Forecasting | 29 |
| Image classification | 25 |
| Text classification | 24 |
| Sentiment / emotion analysis | 18 |
| Time-series modeling | 17 |
| Anomaly detection | 13 |
| Clustering | 12 |
| Recommendation | 11 |
| Geospatial analysis | 11 |

### Algorithm use by primary industry (% of projects in the industry)

| Primary industry | n | Random forest | Logistic regression | XGBoost | Rule-based / heuristic scoring | Linear regression | BERT-family encoder | Support vector machine | Decision tree |
|---|---|---|---|---|---|---|---|---|---|
| Healthcare & Life Sciences | 50 | 46% | 38% | 20% | 22% | 6% | 2% | 6% | 8% |
| Finance & Business | 44 | 55% | 41% | 27% | 9% | 20% | 11% | 7% | 5% |
| Cybersecurity | 20 | 55% | 60% | 35% | 5% | 0% | 35% | 20% | 10% |
| Entertainment & Media | 14 | 36% | 29% | 0% | 29% | 14% | 7% | 29% | 7% |
| Energy | 10 | 60% | 10% | 70% | 20% | 40% | 0% | 0% | 10% |
| Retail & E-commerce | 7 | 57% | 43% | 14% | 0% | 0% | 0% | 14% | 14% |
| Accessibility & Assistive Technology | 6 | 33% | 17% | 0% | 33% | 17% | 17% | 0% | 0% |
| Technology & Engineering | 6 | 33% | 50% | 17% | 0% | 0% | 0% | 0% | 17% |
| Education | 6 | 33% | 33% | 17% | 17% | 0% | 17% | 0% | 17% |
| Environmental Science & Climate | 6 | 67% | 33% | 33% | 33% | 0% | 0% | 0% | 0% |
| Public Services & Government | 5 | 80% | 0% | 0% | 0% | 40% | 0% | 0% | 0% |
| Manufacturing & Infrastructure | 4 | 75% | 25% | 50% | 50% | 25% | 0% | 0% | 0% |
| Transportation & Mobility | 3 | 67% | 0% | 0% | 33% | 33% | 0% | 0% | 0% |
| Sports | 3 | 67% | 33% | 0% | 33% | 33% | 0% | 0% | 67% |
| Travel | 2 | 100% | 50% | 0% | 50% | 50% | 0% | 50% | 0% |
| Legal | 1 | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |
| Archaeology & Cultural Heritage | 1 | 0% | 0% | 0% | 0% | 0% | 0% | 0% | 0% |

## 2. Industry patterns

Projects can belong to several industries; counts are multi-label.

| Sector (multi-label) | Projects |
|---|---|
| Healthcare & Life Sciences | 60 |
| Finance & Business | 51 |
| Entertainment & Media | 27 |
| Cybersecurity | 24 |
| Environmental Science & Climate | 21 |
| Technology & Engineering | 18 |
| Education | 16 |
| Social Equity & Fairness | 14 |
| Energy | 14 |
| Public Services & Government | 12 |
| Accessibility & Assistive Technology | 10 |
| Transportation & Mobility | 9 |
| Manufacturing & Infrastructure | 7 |
| Retail & E-commerce | 7 |
| International Development & Humanitarian | 3 |
| Sports | 3 |
| Travel | 2 |
| Legal | 2 |
| Agriculture & Food | 1 |
| Archaeology & Cultural Heritage | 1 |

### Most common subdomains

| Subdomain | Projects |
|---|---|
| Diagnosis & Screening | 26 |
| Markets | 24 |
| Medical Imaging | 16 |
| Public Health & Epidemiology | 16 |
| Mental Health | 12 |
| Business Operations & Analytics | 11 |
| Clinical Operations & Care Delivery | 11 |
| Misinformation & Content Integrity | 10 |
| Social Media & Online Content | 9 |
| AI Assistants & LLM Applications | 8 |
| Personal Finance | 8 |
| Climate & Weather | 8 |
| Fraud Detection | 7 |
| Phishing | 7 |
| Network & System Security | 7 |

**Underexplored sectors** (≤3 projects): Agriculture & Food (1), Archaeology & Cultural Heritage (1), Travel (2), Legal (2), Sports (3), International Development & Humanitarian (3).

**Student-selected type vs. independently inferred primary industry:** agree for 101/188 (54%). The student categories are coarse (5 options); 70% of the disagreements are projects filed under *Technology & Engineering* whose primary application domain is more specific (most often Cybersecurity).

| Student type | Inferred primary industry | n |
|---|---|---|
| Technology & Engineering | Cybersecurity | 15 |
| Technology & Engineering | Healthcare & Life Sciences | 8 |
| Technology & Engineering | Education | 6 |
| Technology & Engineering | Energy | 6 |
| Technology & Engineering | Accessibility & Assistive Technology | 4 |
| Technology & Engineering | Environmental Science & Climate | 4 |
| Technology & Engineering | Retail & E-commerce | 4 |
| Entertainment & Media | Cybersecurity | 3 |
| Technology & Engineering | Public Services & Government | 3 |
| Finance & Business | Retail & E-commerce | 3 |
| Finance & Business | Cybersecurity | 2 |
| Technology & Engineering | Manufacturing & Infrastructure | 2 |

## 3. Technical sophistication

Sophistication (0–10): mean 5.94, median 6.1, IQR 5.0–7.2.

### By primary industry (groups with ≥5 projects; bootstrap 95% CI)

| Industry | n | Mean | 95% CI |
|---|---|---|---|
| Healthcare & Life Sciences | 50 | 6.3 | [5.7, 6.7] |
| Finance & Business | 44 | 5.7 | [5.3, 6.2] |
| Cybersecurity | 20 | 6.1 | [5.6, 6.5] |
| Entertainment & Media | 14 | 5.1 | [4.1, 6.0] |
| Energy | 10 | 6.6 | [5.8, 7.4] |
| Retail & E-commerce | 7 | 5.6 | [4.3, 6.9] |
| Accessibility & Assistive Technology | 6 | 6.7 | [5.4, 7.8] |
| Technology & Engineering | 6 | 6.0 | [4.7, 7.1] |
| Education | 6 | 5.5 | [4.2, 6.8] |
| Environmental Science & Climate | 6 | 5.5 | [3.6, 7.0] |
| Public Services & Government | 5 | 6.3 | [4.9, 7.7] |

### By algorithm family used

| Family | n | Mean | 95% CI |
|---|---|---|---|
| tree_ensemble | 112 | 6.1 | [5.9, 6.4] |
| linear | 97 | 5.9 | [5.6, 6.2] |
| rule_based | 40 | 6.5 | [5.9, 7.0] |
| neural_vision | 32 | 6.7 | [6.2, 7.1] |
| transformer | 27 | 6.9 | [6.5, 7.3] |
| kernel | 16 | 5.5 | [4.9, 6.1] |
| tree | 15 | 5.6 | [5.0, 6.1] |
| clustering | 12 | 6.3 | [5.5, 7.1] |
| neural | 12 | 6.2 | [5.5, 6.8] |
| probabilistic | 11 | 5.7 | [5.0, 6.4] |
| neural_sequence | 10 | 6.7 | [6.0, 7.5] |
| dimensionality_reduction | 8 | 6.1 | [5.3, 6.9] |
| ensemble | 7 | 6.4 | [5.9, 6.8] |
| retrieval | 6 | 6.5 | [5.4, 7.5] |

### By data modality

| Modality | n | Mean | 95% CI |
|---|---|---|---|
| Tabular | 118 | 5.7 | [5.4, 6.0] |
| Text | 45 | 6.2 | [5.8, 6.5] |
| Time series | 44 | 6.3 | [5.8, 6.9] |
| Image | 34 | 6.5 | [6.0, 7.0] |
| Geospatial / remote sensing | 13 | 6.2 | [5.1, 7.2] |
| Sensor / IoT | 10 | 6.8 | [6.0, 7.7] |
| Audio | 7 | 6.7 | [5.6, 7.7] |
| Multimodal | 6 | 6.9 | [6.0, 7.6] |

### Difficulty tier and reproduction effort

| Tier | n |
|---|---|
| Beginner | 19 |
| Intermediate | 95 |
| Advanced | 74 |

| Reproduction effort | n |
|---|---|
| Low | 41 |
| Moderate | 104 |
| High | 41 |
| Very high | 2 |

### Sophistication components (mean, 0–3)

| Component | Mean |
|---|---|
| algorithmic_complexity | 2.22 |
| data_processing | 2.07 |
| methodological_breadth | 1.84 |
| validation_rigor | 2.08 |
| engineering | 1.29 |
| mathematical_depth | 1.20 |

## 4. Originality landscape

Internal originality is a percentile within this collection (semantic isolation, algorithm rarity, domain rarity, method–domain combination rarity). External originality is a separate, search-based judgement.

### Most distinctive within the collection

| Project | Internal originality (pctl) | Pattern |
|---|---|---|
| project-189 | 95 | uncommon combination of method and domain |
| project-146 | 92 | uncommon combination of method and domain |
| project-116 | 91 | uncommon combination of method and domain |
| project-021 | 89 | uncommon combination of method and domain |
| project-152 | 88 | uncommon combination of method and domain |
| project-121 | 87 | uncommon combination of method and domain |
| project-034 | 85 | uncommon combination of method and domain |
| project-087 | 83 | uncommon combination of method and domain |
| project-128 | 81 | uncommon combination of method and domain |
| project-196 | 80 | common methods in an unusual application |
| project-166 | 80 | uncommon combination of method and domain |
| project-024 | 80 | uncommon combination of method and domain |

### Internal originality patterns

| Pattern | Projects |
|---|---|
| moderately distinctive | 71 |
| well-trodden within this collection | 45 |
| unusual methods for a familiar problem area | 28 |
| uncommon combination of method and domain | 24 |
| common methods in an unusual application | 20 |

### External originality (precedent search)

Absence of found precedents is not proof of novelty.

| Classification | Projects |
|---|---|
| established | 126 |
| distinctive_application | 44 |
| unusual_combination | 17 |
| potentially_novel | 1 |

### Clusters

Method: UMAP(10d, cosine) + Ward; k by silhouette x bootstrap ARI. k = 7; silhouette 0.6485 in the reduced space (optimistic) and 0.1364 in the original space (conservative); bootstrap ARI 0.951 ± 0.045; UMAP-seed ARI 0.894. Clusters are stable but overlapping: boundaries are soft. Cohesion = mean pairwise semantic similarity within the cluster (higher = more alike).

| Cluster | Label (most over-represented terms) | n | Cohesion |
|---|---|---|---|
| 2 | Healthcare & Life Sciences · Tabular · Random forest | 37 | 0.35 |
| 1 | Image · Image classification · ResNet | 32 | 0.44 |
| 3 | Markets · Time series · Forecasting | 27 | 0.43 |
| 4 | Text classification · Cybersecurity · Text | 27 | 0.45 |
| 6 | Finance & Business · Tabular · Random forest | 24 | 0.48 |
| 0 | Entertainment & Media · Tabular · Recommendation | 23 | 0.35 |
| 5 | Energy · Environmental Science & Climate · Regression | 18 | 0.47 |

### Bridge projects (connect otherwise separate regions)

| Project | Betweenness | Other clusters linked |
|---|---|---|
| project-031 | 0.133 | 3 |
| project-161 | 0.062 | 3 |
| project-045 | 0.061 | 2 |
| project-057 | 0.054 | 2 |
| project-102 | 0.050 | 1 |
| project-107 | 0.049 | 1 |
| project-124 | 0.048 | 2 |
| project-197 | 0.047 | 2 |
| project-146 | 0.045 | 2 |
| project-134 | 0.043 | 2 |

## 5. Rubric relationships (exploratory)

Spearman correlations between newly derived characteristics and the original rubric scores. 24 comparisons, no multiple-comparison correction: treat p < 0.05 as a lead, not a finding.

**Shared-source caveat.** Both the rubric and the derived ratings are read from the same slide decks. A deck that explains its pipeline well earns rubric points *and* exposes more demonstrable sophistication, so a positive correlation partly reflects documentation quality rather than an independent link between technical depth and grading. Disentangling the two would require code-level evidence.

| Derived metric | Rubric score | n | rho | 95% CI | perm. p |
|---|---|---|---|---|---|
| Technical sophistication | Rubric total | 188 | +0.48 | [+0.36, +0.58] | 0.001 |
| Technical sophistication | Project Description | 188 | +0.33 | [+0.18, +0.45] | 0.001 |
| Technical sophistication | Algorithm | 188 | +0.41 | [+0.30, +0.52] | 0.001 |
| Technical sophistication | Essential Question | 188 | +0.41 | [+0.28, +0.52] | 0.001 |
| Technical sophistication | Next Steps | 188 | +0.20 | [+0.05, +0.35] | 0.006 |
| Technical sophistication | Citations | 188 | +0.33 | [+0.20, +0.47] | 0.001 |
| Internal originality | Rubric total | 188 | +0.09 | [-0.06, +0.24] | 0.253 |
| Internal originality | Project Description | 188 | +0.11 | [-0.04, +0.25] | 0.157 |
| Internal originality | Algorithm | 188 | -0.02 | [-0.17, +0.12] | 0.817 |
| Internal originality | Essential Question | 188 | -0.03 | [-0.17, +0.10] | 0.656 |
| Internal originality | Next Steps | 188 | +0.10 | [-0.05, +0.25] | 0.178 |
| Internal originality | Citations | 188 | +0.13 | [-0.00, +0.27] | 0.071 |
| Difficulty tier (1-3) | Rubric total | 188 | +0.23 | [+0.09, +0.36] | 0.002 |
| Difficulty tier (1-3) | Project Description | 188 | +0.12 | [-0.02, +0.25] | 0.095 |
| Difficulty tier (1-3) | Algorithm | 188 | +0.14 | [-0.00, +0.28] | 0.060 |
| Difficulty tier (1-3) | Essential Question | 188 | +0.19 | [+0.05, +0.31] | 0.008 |
| Difficulty tier (1-3) | Next Steps | 188 | +0.10 | [-0.05, +0.26] | 0.184 |
| Difficulty tier (1-3) | Citations | 188 | +0.20 | [+0.04, +0.33] | 0.009 |
| Reproduction effort (0-15) | Rubric total | 188 | +0.18 | [+0.05, +0.32] | 0.012 |
| Reproduction effort (0-15) | Project Description | 188 | +0.08 | [-0.07, +0.23] | 0.261 |
| Reproduction effort (0-15) | Algorithm | 188 | +0.15 | [+0.01, +0.29] | 0.036 |
| Reproduction effort (0-15) | Essential Question | 188 | +0.14 | [+0.00, +0.26] | 0.050 |
| Reproduction effort (0-15) | Next Steps | 188 | +0.11 | [-0.04, +0.25] | 0.117 |
| Reproduction effort (0-15) | Citations | 188 | +0.18 | [+0.04, +0.31] | 0.014 |

### Which rubric criteria vary most across technical approaches?

SD across all projects, and the spread (max − min) of criterion means across algorithm families with ≥8 projects.

| Criterion | SD overall | Spread of family means |
|---|---|---|
| Project Description | 0.94 | 0.85 |
| Algorithm | 0.87 | 1.17 |
| Essential Question | 0.75 | 0.81 |
| Next Steps | 1.01 | 0.95 |
| Citations | 1.26 | 1.38 |

## 6. Dataset accessibility

Researched projects: 188/188.

- Original dataset identified as a public resource (exact/probable): **137** projects
- Only an alternative/substitute dataset available: **10** projects
- Neither: **41** researched projects

### Hosting platforms of identified datasets

| Platform | Projects |
|---|---|
| Kaggle | 66 |
| doi.org | 7 |
| Hugging Face | 7 |
| UCI Machine Learning Repository | 6 |
| Zenodo | 5 |
| GitHub | 5 |
| Mendeley Data | 3 |
| Baselight (mirror of Kaggle) | 3 |
| researchgate.net | 2 |
| open-meteo.com | 2 |
| challenge.isic-archive.com | 2 |
| tradingeconomics.com | 1 |

### Share of projects with an identified public dataset, by primary industry

| Industry | Researched | Identified |
|---|---|---|
| Healthcare & Life Sciences | 50 | 80% |
| Finance & Business | 44 | 73% |
| Cybersecurity | 20 | 80% |
| Entertainment & Media | 14 | 64% |
| Energy | 10 | 80% |
| Retail & E-commerce | 7 | 57% |
| Accessibility & Assistive Technology | 6 | 67% |
| Technology & Engineering | 6 | 100% |
| Education | 6 | 67% |
| Environmental Science & Climate | 6 | 67% |
| Public Services & Government | 5 | 20% |
| Manufacturing & Infrastructure | 4 | 75% |
| Transportation & Mobility | 3 | 67% |
| Sports | 3 | 33% |
| Travel | 2 | 50% |
| Legal | 1 | 100% |
| Archaeology & Cultural Heritage | 1 | 100% |

## 7. Reproducibility landscape

'Sweet spot' = Low/Moderate reproduction effort, readiness ≥5/7, and an identified public dataset: **106** projects.

| Industry | Sweet-spot projects |
|---|---|
| Healthcare & Life Sciences | 31 |
| Finance & Business | 28 |
| Cybersecurity | 10 |
| Entertainment & Media | 8 |
| Energy | 6 |
| Technology & Engineering | 4 |
| Education | 4 |
| Accessibility & Assistive Technology | 3 |
| Retail & E-commerce | 3 |
| Environmental Science & Climate | 3 |
| Transportation & Mobility | 2 |
| Travel | 1 |
| Manufacturing & Infrastructure | 1 |
| Legal | 1 |
| Sports | 1 |

| Tier | n |
|---|---|
| Intermediate | 65 |
| Advanced | 27 |
| Beginner | 14 |

### Most interesting sweet-spot projects (originality + sophistication)

| Project | Tier | Effort | Originality | Sophistication |
|---|---|---|---|---|
| project-121 | Advanced | Moderate | 87 | 8.9 |
| project-116 | Intermediate | Moderate | 91 | 7.2 |
| project-163 | Advanced | Moderate | 64 | 9.4 |
| project-166 | Intermediate | Moderate | 80 | 7.8 |
| project-077 | Advanced | Moderate | 71 | 8.3 |
| project-083 | Intermediate | Moderate | 73 | 7.8 |
| project-068 | Intermediate | Moderate | 74 | 7.2 |
| project-078 | Advanced | Moderate | 73 | 7.2 |
| project-181 | Advanced | Moderate | 67 | 7.8 |
| project-010 | Advanced | Moderate | 70 | 7.2 |
| project-036 | Advanced | Moderate | 79 | 6.1 |
| project-089 | Intermediate | Moderate | 69 | 6.7 |

## Limitations

- Extraction is LLM-based; every confirmed tag is grounded by a verified quote, but ratings (sophistication, prerequisites, effort) are judgements against written anchors and have not yet been double-coded by humans.
- Presentations, not code, were analyzed: what a slide deck shows is a lower bound on what was built.
- Several extractors flagged internally inconsistent metrics or likely leakage in student results; these are in the review queue and reported metrics are recorded as reported, not validated.
- External originality rests on a small number of web searches per project and is low-confidence by design.
- Correlations are exploratory, uncorrected, and cannot support causal claims.

