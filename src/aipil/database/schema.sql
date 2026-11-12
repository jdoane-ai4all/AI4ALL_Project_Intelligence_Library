-- AI Project Intelligence Library: normalized schema (SQLite).
-- Conventions: raw_* tables are immutable verbatim copies of the source workbook.
-- Everything derived is stored separately with provenance, confidence and method.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);

-- ---------- Immutable raw import ----------
CREATE TABLE IF NOT EXISTS raw_scores (
  row_index INTEGER PRIMARY KEY, project_id TEXT NOT NULL, row_json TEXT NOT NULL, imported_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS raw_rationale (
  row_index INTEGER PRIMARY KEY, project_id TEXT NOT NULL, row_json TEXT NOT NULL, imported_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS raw_rubric (
  row_index INTEGER PRIMARY KEY, row_json TEXT NOT NULL, imported_at TEXT NOT NULL);

-- ---------- Core entities ----------
CREATE TABLE IF NOT EXISTS projects (
  project_id TEXT PRIMARY KEY,               -- stable ID from workbook (gaps are intentional; never relabel)
  title_slide TEXT,
  student_title TEXT,
  student_description TEXT,
  student_project_type TEXT,                 -- original student-selected category, preserved verbatim
  pdf_url TEXT, text_url TEXT,
  pdf_drive_id TEXT, text_drive_id TEXT,
  processing_status TEXT NOT NULL DEFAULT 'imported',
  human_review_status TEXT NOT NULL DEFAULT 'unreviewed'
);

CREATE TABLE IF NOT EXISTS rubric_criteria (
  criterion TEXT NOT NULL, level INTEGER NOT NULL CHECK(level BETWEEN 1 AND 5),
  level_name TEXT NOT NULL, description TEXT, PRIMARY KEY (criterion, level));

CREATE TABLE IF NOT EXISTS rubric_scores (           -- from Scores sheet (authoritative)
  project_id TEXT NOT NULL REFERENCES projects(project_id),
  criterion TEXT NOT NULL, score INTEGER, PRIMARY KEY (project_id, criterion));
CREATE TABLE IF NOT EXISTS rubric_totals (
  project_id TEXT PRIMARY KEY REFERENCES projects(project_id), strict_total INTEGER);

CREATE TABLE IF NOT EXISTS rubric_evaluations (      -- from Rationale & evidence sheet (authoritative)
  project_id TEXT NOT NULL REFERENCES projects(project_id),
  criterion TEXT NOT NULL, score INTEGER, limiting_factors TEXT, rationale TEXT,
  slides_cited TEXT, evidence TEXT, PRIMARY KEY (project_id, criterion));

CREATE TABLE IF NOT EXISTS audit_flags (
  flag_id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, scope TEXT NOT NULL,
  check_name TEXT NOT NULL, severity TEXT NOT NULL CHECK(severity IN ('info','warning','error')),
  detail TEXT, created_at TEXT NOT NULL);

-- ---------- Sources ----------
CREATE TABLE IF NOT EXISTS source_documents (
  doc_id TEXT PRIMARY KEY,                   -- e.g. project-002:text
  project_id TEXT NOT NULL REFERENCES projects(project_id),
  kind TEXT NOT NULL CHECK(kind IN ('pdf','text')),
  drive_file_id TEXT, url TEXT,
  access_status TEXT NOT NULL,               -- retrieved | failed | not_attempted | missing_link
  retrieved_at TEXT, sha256 TEXT, n_bytes INTEGER, n_pages INTEGER, n_chars INTEGER,
  redactions INTEGER, error TEXT);

-- ---------- Extraction provenance ----------
CREATE TABLE IF NOT EXISTS extraction_runs (
  run_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(project_id),
  pipeline_version TEXT, prompt_version TEXT, taxonomy_version TEXT, extractor TEXT,
  created_at TEXT, status TEXT, sources_used TEXT, notes TEXT);

CREATE TABLE IF NOT EXISTS evidence (
  evidence_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(project_id),
  doc_id TEXT, page TEXT, excerpt TEXT, verified INTEGER  -- 1 if excerpt found verbatim (normalized) in source
);

CREATE TABLE IF NOT EXISTS project_profiles (
  project_id TEXT PRIMARY KEY REFERENCES projects(project_id),
  plain_summary TEXT, technical_summary TEXT, research_question TEXT,
  problem_statement TEXT, primary_beneficiary TEXT, application_domain TEXT, subdomain TEXT,
  inputs TEXT, outputs TEXT, results_summary TEXT,
  source_completeness TEXT, overall_confidence TEXT, extraction_run_id TEXT);

-- ---------- Taxonomy & multi-label classification ----------
CREATE TABLE IF NOT EXISTS taxonomy_terms (
  term_id TEXT PRIMARY KEY,                  -- dimension:slug
  dimension TEXT NOT NULL, label TEXT NOT NULL, parent_id TEXT, description TEXT,
  attributes TEXT, taxonomy_version TEXT);

CREATE TABLE IF NOT EXISTS project_terms (     -- bridge: industries, paradigms, tasks, modalities, methods, tools
  project_id TEXT NOT NULL REFERENCES projects(project_id),
  term_id TEXT NOT NULL REFERENCES taxonomy_terms(term_id),
  dimension TEXT NOT NULL,
  evidence_level TEXT NOT NULL CHECK(evidence_level IN ('confirmed','inferred','unknown')),
  original_term TEXT, evidence_id TEXT, is_primary INTEGER DEFAULT 0,
  PRIMARY KEY (project_id, term_id));

CREATE TABLE IF NOT EXISTS project_algorithms (
  project_id TEXT NOT NULL REFERENCES projects(project_id),
  term_id TEXT NOT NULL REFERENCES taxonomy_terms(term_id),     -- algorithm:<slug>
  original_term TEXT,
  role TEXT NOT NULL CHECK(role IN ('implemented','baseline','compared','considered','proposed','unclear')),
  purpose TEXT, inputs TEXT, outputs TEXT, reported_result TEXT,
  evidence_level TEXT NOT NULL, evidence_id TEXT,
  PRIMARY KEY (project_id, term_id, role));

-- ---------- Datasets (many-to-many) ----------
CREATE TABLE IF NOT EXISTS datasets (
  dataset_id TEXT PRIMARY KEY, name TEXT NOT NULL, canonical_url TEXT, platform TEXT,
  publisher TEXT, description TEXT, modality TEXT, access_requirements TEXT, license TEXT,
  availability_status TEXT, link_status TEXT, link_http_code INTEGER, link_checked_at TEXT,
  notes TEXT);
CREATE TABLE IF NOT EXISTS project_datasets (
  project_id TEXT NOT NULL REFERENCES projects(project_id),
  dataset_id TEXT NOT NULL REFERENCES datasets(dataset_id),
  relationship TEXT NOT NULL CHECK(relationship IN ('used','mentioned','alternative')),
  match_level TEXT NOT NULL CHECK(match_level IN ('exact','probable','possible','alternative','unresolved')),
  discovery_level INTEGER CHECK(discovery_level BETWEEN 1 AND 4),
  original_reference TEXT, evidence TEXT, confidence TEXT, verified_at TEXT, comments TEXT,
  PRIMARY KEY (project_id, dataset_id, relationship));
CREATE TABLE IF NOT EXISTS dataset_clues (       -- data descriptions that could not be resolved
  project_id TEXT NOT NULL REFERENCES projects(project_id), clue TEXT, status TEXT, notes TEXT);

-- ---------- Assessments (separate constructs; never mixed with rubric) ----------
CREATE TABLE IF NOT EXISTS assessments (
  project_id TEXT NOT NULL REFERENCES projects(project_id),
  construct TEXT NOT NULL,      -- sophistication | difficulty_tier | reproduction_effort | adoption_readiness | prerequisites
  component TEXT NOT NULL,      -- 'overall' or sub-dimension
  value_num REAL, value_label TEXT, rationale TEXT, confidence TEXT, method TEXT,
  PRIMARY KEY (project_id, construct, component));

CREATE TABLE IF NOT EXISTS originality (
  project_id TEXT NOT NULL REFERENCES projects(project_id),
  scope TEXT NOT NULL CHECK(scope IN ('internal','external')),
  dimension TEXT NOT NULL, score REAL, label TEXT, rationale TEXT, confidence TEXT, method TEXT,
  PRIMARY KEY (project_id, scope, dimension));
CREATE TABLE IF NOT EXISTS external_precedents (
  precedent_id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES projects(project_id),
  title TEXT, url TEXT, kind TEXT, date TEXT, comparability TEXT, searched_at TEXT);

-- ---------- Representations & graph ----------
CREATE TABLE IF NOT EXISTS embeddings (
  project_id TEXT NOT NULL REFERENCES projects(project_id), view TEXT NOT NULL, model TEXT,
  dim INTEGER, vector BLOB, PRIMARY KEY (project_id, view));
CREATE TABLE IF NOT EXISTS similarity_edges (
  source TEXT NOT NULL, target TEXT NOT NULL, view TEXT NOT NULL, weight REAL NOT NULL,
  rank INTEGER, explanation TEXT, shared TEXT, PRIMARY KEY (source, target, view));
CREATE TABLE IF NOT EXISTS clusters (
  project_id TEXT NOT NULL, view TEXT NOT NULL, cluster_id INTEGER, cluster_label TEXT,
  x REAL, y REAL, z REAL, PRIMARY KEY (project_id, view));
CREATE TABLE IF NOT EXISTS search_tags (
  project_id TEXT NOT NULL REFERENCES projects(project_id), tag TEXT NOT NULL, basis TEXT,
  PRIMARY KEY (project_id, tag));

-- ---------- QA ----------
CREATE TABLE IF NOT EXISTS quality_flags (       -- triaged methodological flags about project MATERIALS (not students)
  project_id TEXT NOT NULL REFERENCES projects(project_id), flag_index INTEGER NOT NULL,
  category TEXT, severity TEXT CHECK(severity IN ('critical','moderate','minor')), label TEXT, flag_text TEXT,
  student_acknowledged INTEGER, triage_method TEXT, PRIMARY KEY (project_id, flag_index));
CREATE TABLE IF NOT EXISTS recommendation_status (
  project_id TEXT PRIMARY KEY REFERENCES projects(project_id),
  status TEXT NOT NULL CHECK(status IN ('hold','caution','ok')), reason TEXT,
  reviewer_decision TEXT, reviewer_notes TEXT, reviewed_at TEXT);
CREATE TABLE IF NOT EXISTS review_queue (
  item_id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, field TEXT, reason TEXT,
  priority TEXT, status TEXT DEFAULT 'open', created_at TEXT);
