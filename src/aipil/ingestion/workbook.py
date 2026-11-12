"""Workbook ingestion and original-data validation.

The workbook is the authoritative historical record. This module:
  * copies every row verbatim into raw_* tables (immutable),
  * populates normalized projects / rubric tables,
  * runs integrity checks and writes findings to audit_flags.
It NEVER modifies scores. Inconsistencies are only flagged.
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

CRITERIA = ["Project Description", "Algorithm", "Essential Question", "Next Steps", "Citations"]
TOTAL_COL = "Strict total (scored criteria)"
SCORES_SHEET, RATIONALE_SHEET, RUBRIC_SHEET = "Scores", "Rationale & evidence", "Rubric"
ID_RE = re.compile(r"^project-\d{3}$")
DRIVE_RE = re.compile(r"/file/d/([A-Za-z0-9_-]+)")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def drive_id(url) -> str | None:
    if not isinstance(url, str):
        return None
    m = DRIVE_RE.search(url)
    return m.group(1) if m else None


def _clean(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if hasattr(v, "item"):
        return v.item()
    return v


@dataclass
class Workbook:
    scores: pd.DataFrame
    rationale: pd.DataFrame
    rubric: pd.DataFrame


def load_workbook(path: Path) -> Workbook:
    if not Path(path).exists():
        raise FileNotFoundError(f"Workbook not found at {path}. Copy Project_Type.xlsx into data/private/raw/.")
    xl = pd.ExcelFile(path)
    missing = {SCORES_SHEET, RATIONALE_SHEET, RUBRIC_SHEET} - set(xl.sheet_names)
    if missing:
        raise ValueError(f"Workbook missing sheets: {missing}")
    return Workbook(
        scores=pd.read_excel(path, sheet_name=SCORES_SHEET),
        rationale=pd.read_excel(path, sheet_name=RATIONALE_SHEET),
        rubric=pd.read_excel(path, sheet_name=RUBRIC_SHEET),
    )


def parse_rubric(rubric: pd.DataFrame) -> list[dict]:
    """Rubric columns look like '5\\nExceeds Requirements'. Return (criterion, level, level_name, description)."""
    out = []
    for col in rubric.columns[1:]:
        parts = str(col).split("\n", 1)
        level = int(parts[0].strip())
        name = " ".join(parts[1].split()) if len(parts) > 1 else ""
        for _, row in rubric.iterrows():
            desc = _clean(row[col])
            out.append(dict(criterion=str(row[rubric.columns[0]]).strip(), level=level,
                            level_name=name, description=desc))
    return out


# ---------------------------------------------------------------- validation
@dataclass
class Finding:
    check_name: str
    severity: str
    detail: str
    project_id: str | None = None
    scope: str = "workbook"


@dataclass
class ValidationReport:
    stats: dict = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)

    def add(self, *a, **k):
        self.findings.append(Finding(*a, **k))

    @property
    def errors(self):
        return [f for f in self.findings if f.severity == "error"]


def validate(wb: Workbook) -> ValidationReport:
    r = ValidationReport()
    s, e = wb.scores, wb.rationale
    r.stats["n_score_rows"] = len(s)
    r.stats["n_unique_projects"] = int(s["project_id"].nunique())
    r.stats["n_rationale_rows"] = len(e)
    r.stats["n_rubric_criteria"] = len(wb.rubric)

    # IDs
    dup = s["project_id"][s["project_id"].duplicated()].tolist()
    for pid in dup:
        r.add("duplicate_project_id", "error", "project_id appears more than once in Scores", pid)
    for pid in s["project_id"]:
        if not ID_RE.match(str(pid)):
            r.add("malformed_project_id", "error", f"unexpected id format: {pid!r}", str(pid))
    nums = sorted(int(str(p).split("-")[1]) for p in s["project_id"] if ID_RE.match(str(p)))
    gaps = sorted(set(range(nums[0], nums[-1] + 1)) - set(nums)) if nums else []
    r.stats["id_range"] = [nums[0], nums[-1]] if nums else None
    r.stats["id_gaps"] = [f"project-{g:03d}" for g in gaps]
    if gaps:
        r.add("id_gaps", "info", f"{len(gaps)} gaps in ID sequence (expected; IDs are stable and not relabeled)")

    # Scores
    for _, row in s.iterrows():
        pid = row["project_id"]
        vals = []
        for c in CRITERIA:
            v = row[c]
            if pd.isna(v):
                r.add("missing_score", "error", f"{c} missing", pid)
                continue
            if not float(v).is_integer() or not 1 <= int(v) <= 5:
                r.add("score_out_of_range", "error", f"{c}={v}", pid)
            vals.append(int(v))
        if len(vals) == 5 and int(row[TOTAL_COL]) != sum(vals):
            r.add("total_mismatch", "error", f"total {row[TOTAL_COL]} != sum {sum(vals)}", pid)
        for col in ["Title from title slide", "PDF Link", "Extracted Text", "Student-Provided Project Name",
                    "Student-Provided Project Description", "Student-Provided Project Type"]:
            v = row[col]
            if pd.isna(v) or str(v).strip() == "":
                r.add("missing_field", "warning", f"{col} empty", pid)
            elif str(v).strip().lower() in {"no data submitted", "n/a", "none"}:
                r.add("placeholder_value", "warning", f"{col} = {str(v).strip()!r}", pid)
        for col in ["PDF Link", "Extracted Text"]:
            if isinstance(row[col], str) and not drive_id(row[col]):
                r.add("unparseable_link", "warning", f"{col} is not a Drive file link", pid)

    # Shared Drive files across projects
    for col in ["PDF Link", "Extracted Text"]:
        ids = s[col].map(drive_id)
        d = ids[ids.notna() & ids.duplicated(keep=False)]
        for pid, fid in zip(s.loc[d.index, "project_id"], d):
            r.add("shared_source_file", "warning", f"{col} file {fid} used by multiple projects", pid)

    # Title vs student-provided title (informational only)
    def norm(t):
        return re.sub(r"[^a-z0-9]", "", str(t).lower())
    diff = s[s["Title from title slide"].map(norm) != s["Student-Provided Project Name"].map(norm)]
    r.stats["n_title_differs_from_student_title"] = len(diff)

    # Rationale table
    known = set(s["project_id"])
    for pid in sorted(set(e["project_id"]) - known):
        r.add("orphan_rationale", "error", "rationale rows for unknown project", pid)
    counts = e.groupby("project_id").size()
    for pid in known:
        n = int(counts.get(pid, 0))
        if n != 5:
            r.add("rationale_count", "error", f"{n} criterion rows (expected 5)", pid)
    dupe = e[e.duplicated(["project_id", "Criterion"], keep=False)]
    for pid in dupe["project_id"].unique():
        r.add("duplicate_rationale_criterion", "error", "duplicate criterion row", pid)
    bad_crit = set(e["Criterion"]) - set(CRITERIA)
    if bad_crit:
        r.add("unknown_criterion", "error", f"unknown criterion names: {bad_crit}")
    merged = e.merge(s.melt(id_vars="project_id", value_vars=CRITERIA, var_name="Criterion", value_name="sheet_score"),
                     on=["project_id", "Criterion"], how="left")
    for _, m in merged[merged["Score"] != merged["sheet_score"]].iterrows():
        r.add("score_sheet_mismatch", "error",
              f"{m['Criterion']}: rationale sheet={m['Score']} vs scores sheet={m['sheet_score']}", m["project_id"],
              scope="rationale")
    for col in ["Rationale", "Evidence", "Slides cited"]:
        for _, m in e[e[col].isna() | (e[col].astype(str).str.strip() == "")].iterrows():
            r.add(f"missing_{col.lower().replace(' ', '_')}", "warning", f"{m['Criterion']}: {col} empty",
                  m["project_id"], scope="rationale")
    r.stats["limiting_factors_values"] = (
        e["Limiting factors"].fillna("<blank>").astype(str).str.split(r"\s*[;,]\s*").explode().value_counts().to_dict())

    # Rubric
    crit = set(wb.rubric.iloc[:, 0].astype(str).str.strip())
    if crit != set(CRITERIA):
        r.add("rubric_criteria_mismatch", "error", f"rubric criteria {crit} differ from score columns")

    # Descriptive stats
    r.stats["student_project_type_counts"] = s["Student-Provided Project Type"].fillna("<missing>").value_counts().to_dict()
    r.stats["total_score"] = s[TOTAL_COL].describe().round(2).to_dict()
    r.stats["criterion_means"] = s[CRITERIA].mean().round(2).to_dict()
    r.stats["criterion_distribution"] = {c: s[c].value_counts().sort_index().to_dict() for c in CRITERIA}
    return r


# ---------------------------------------------------------------- loading
def init_db(con: sqlite3.Connection) -> None:
    schema = (Path(__file__).resolve().parents[1] / "database" / "schema.sql").read_text()
    con.executescript(schema)


def import_workbook(wb: Workbook, con: sqlite3.Connection, report: ValidationReport) -> None:
    from aipil import PIPELINE_VERSION, SCHEMA_VERSION
    ts = now()
    cur = con.cursor()
    for t in ["raw_scores", "raw_rationale", "raw_rubric", "rubric_criteria", "rubric_scores", "rubric_totals",
              "rubric_evaluations", "audit_flags"]:
        cur.execute(f"DELETE FROM {t}")
    for i, row in wb.scores.iterrows():
        cur.execute("INSERT INTO raw_scores VALUES (?,?,?,?)",
                    (int(i), row["project_id"], json.dumps({k: _clean(v) for k, v in row.items()}, default=str), ts))
    for i, row in wb.rationale.iterrows():
        cur.execute("INSERT INTO raw_rationale VALUES (?,?,?,?)",
                    (int(i), row["project_id"], json.dumps({k: _clean(v) for k, v in row.items()}, default=str), ts))
    for i, row in wb.rubric.iterrows():
        cur.execute("INSERT INTO raw_rubric VALUES (?,?,?)",
                    (int(i), json.dumps({k: _clean(v) for k, v in row.items()}, default=str), ts))

    for r in parse_rubric(wb.rubric):
        cur.execute("INSERT INTO rubric_criteria VALUES (?,?,?,?)",
                    (r["criterion"], r["level"], r["level_name"], r["description"]))

    for _, row in wb.scores.iterrows():
        pid = row["project_id"]
        cur.execute(
            """INSERT INTO projects (project_id,title_slide,student_title,student_description,student_project_type,
               pdf_url,text_url,pdf_drive_id,text_drive_id) VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(project_id) DO UPDATE SET title_slide=excluded.title_slide,
               student_title=excluded.student_title, student_description=excluded.student_description,
               student_project_type=excluded.student_project_type, pdf_url=excluded.pdf_url,
               text_url=excluded.text_url, pdf_drive_id=excluded.pdf_drive_id, text_drive_id=excluded.text_drive_id""",
            (pid, _clean(row["Title from title slide"]), _clean(row["Student-Provided Project Name"]),
             _clean(row["Student-Provided Project Description"]), _clean(row["Student-Provided Project Type"]),
             _clean(row["PDF Link"]), _clean(row["Extracted Text"]),
             drive_id(row["PDF Link"]), drive_id(row["Extracted Text"])))
        for c in CRITERIA:
            cur.execute("INSERT INTO rubric_scores VALUES (?,?,?)", (pid, c, _clean(row[c])))
        cur.execute("INSERT INTO rubric_totals VALUES (?,?)", (pid, _clean(row[TOTAL_COL])))
    for _, row in wb.rationale.iterrows():
        cur.execute("INSERT OR REPLACE INTO rubric_evaluations VALUES (?,?,?,?,?,?,?)",
                    (row["project_id"], row["Criterion"], _clean(row["Score"]), _clean(row["Limiting factors"]),
                     _clean(row["Rationale"]), _clean(row["Slides cited"]), _clean(row["Evidence"])))
    for f in report.findings:
        cur.execute("INSERT INTO audit_flags (project_id,scope,check_name,severity,detail,created_at) VALUES (?,?,?,?,?,?)",
                    (f.project_id, f.scope, f.check_name, f.severity, f.detail, ts))
    for k, v in {"schema_version": SCHEMA_VERSION, "pipeline_version": PIPELINE_VERSION,
                 "workbook_imported_at": ts}.items():
        cur.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (k, v))
    con.commit()


def write_report(report: ValidationReport, path: Path) -> None:
    from collections import Counter
    lines = ["# Import Validation Report", "", f"Generated: {now()}", "",
             "Original rubric scores are authoritative and were **not modified**. Issues below are flags only.", "",
             "## Counts", ""]
    st = report.stats
    lines += [f"- Score rows: {st['n_score_rows']}", f"- Unique projects: {st['n_unique_projects']}",
              f"- Rationale rows: {st['n_rationale_rows']} (expected {5 * st['n_unique_projects']})",
              f"- Rubric criteria: {st['n_rubric_criteria']}",
              f"- ID range: project-{st['id_range'][0]:03d} to project-{st['id_range'][1]:03d}; "
              f"{len(st['id_gaps'])} unused IDs (intentional, not relabeled)",
              f"- Projects whose slide title differs from student-provided title: {st['n_title_differs_from_student_title']}",
              "", "## Rubric score summary", "",
              "| Criterion | Mean | 1 | 2 | 3 | 4 | 5 |", "|---|---|---|---|---|---|---|"]
    for c, mean in st["criterion_means"].items():
        d = st["criterion_distribution"][c]
        lines.append(f"| {c} | {mean} | " + " | ".join(str(d.get(k, 0)) for k in range(1, 6)) + " |")
    t = st["total_score"]
    lines += ["", f"Strict total: mean {t['mean']}, sd {t['std']}, min {t['min']}, median {t['50%']}, max {t['max']}", "",
              "## Student-provided project type", ""]
    lines += [f"- {k}: {v}" for k, v in st["student_project_type_counts"].items()]
    lines += ["", "## Limiting-factor tags in rationale sheet", ""]
    lines += [f"- `{k}`: {v}" for k, v in st["limiting_factors_values"].items()]
    lines += ["", "## Findings", ""]
    c = Counter((f.severity, f.check_name) for f in report.findings)
    if not c:
        lines.append("No findings.")
    lines += ["| Severity | Check | Count |", "|---|---|---|"]
    lines += [f"| {s} | {n} | {k} |" for (s, n), k in sorted(c.items())]
    lines += ["", "### Detail", ""]
    for f in report.findings:
        lines.append(f"- **{f.severity}** `{f.check_name}` {f.project_id or ''}: {f.detail}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
