"""Reviewer workbook for projects whose materials were flagged with methodological issues.

    python -m aipil.export.review_workbook            # write data/processed/flagged_projects_review.xlsx
    python -m aipil.export.review_workbook --import   # read reviewer decisions back -> data/private/qa/reviewer_decisions.json

Private: contains project titles and descriptions of student work. Flags describe project MATERIALS, not students;
a person makes every final call.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone

from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from aipil import paths

OUT = paths.PROCESSED / "flagged_projects_review.xlsx"
CATEGORY_NAMES = {
    "data_leakage": "Data / label leakage", "chance_level_results": "Chance-level results presented as success",
    "contradictory_conclusion": "Conclusion contradicts own evidence", "inconsistent_metrics": "Inconsistent reported numbers",
    "evaluation_design": "Weak evaluation design", "unsupported_claim": "Unsupported claim",
    "incomplete_work": "Incomplete / planned work", "data_or_source_issue": "Dataset or source issue",
    "documentation_gap": "Documentation gap", "other": "Other",
}
STATUS_TEXT = {"hold": "HOLD from recommendations", "caution": "Recommend with caution", "ok": "OK (minor notes only)"}
DECISIONS = ["Confirm hold", "Downgrade to caution", "Clear flag", "Needs discussion"]
F = "Arial"
HDR = PatternFill("solid", start_color="1F2A44")
SEV_FILL = {"critical": "F8D7DA", "moderate": "FFF3CD", "minor": "E2E3E5"}
INPUT_FILL = PatternFill("solid", start_color="FFFF00")
THIN = Border(bottom=Side(style="thin", color="D0D4DC"))


def _header(ws, cols, widths):
    for i, (c, w) in enumerate(zip(cols, widths), 1):
        cell = ws.cell(row=1, column=i, value=c)
        cell.font = Font(name=F, bold=True, color="FFFFFF")
        cell.fill = HDR
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[1].height = 32
    ws.freeze_panes = "A2"


def _body(ws, n_rows, n_cols, wrap_cols=()):
    for r in range(2, n_rows + 2):
        for c in range(1, n_cols + 1):
            cell = ws.cell(row=r, column=c)
            cell.font = Font(name=F, size=10)
            cell.alignment = Alignment(vertical="top", wrap_text=c in wrap_cols)
            cell.border = THIN


def build():
    con = sqlite3.connect(paths.DB_PATH)
    q = lambda s, *a: con.execute(s, a).fetchall()  # noqa: E731
    title = dict(q("SELECT project_id, COALESCE(student_title, title_slide) FROM projects"))
    stype = dict(q("SELECT project_id, COALESCE(student_project_type, '') FROM projects"))
    total = dict(q("SELECT project_id, strict_total FROM rubric_totals"))
    prim = dict(q("""SELECT pt.project_id, COALESCE(p.label, t.label) FROM project_terms pt JOIN taxonomy_terms t USING(term_id)
                     LEFT JOIN taxonomy_terms p ON p.term_id=t.parent_id WHERE pt.dimension='industry' AND pt.is_primary=1"""))
    status = dict(q("SELECT project_id, status FROM recommendation_status"))
    flags = q("""SELECT project_id, severity, category, label, flag_text, student_acknowledged FROM quality_flags
                 ORDER BY project_id, CASE severity WHEN 'critical' THEN 0 WHEN 'moderate' THEN 1 ELSE 2 END, flag_index""")
    by_p: dict[str, list] = {}
    for f in flags:
        by_p.setdefault(f[0], []).append(f)
    order = {"critical": 0, "moderate": 1, "minor": 2}
    projects = sorted(by_p, key=lambda p: (min(order[f[1]] for f in by_p[p]), p))
    prev = {}
    dec_f = paths.PRIVATE / "qa" / "reviewer_decisions.json"
    if dec_f.exists():
        prev = {k: (v.get("decision"), v.get("notes")) for k, v in json.loads(dec_f.read_text()).items()}
    elif OUT.exists():  # preserve any decisions already typed into an earlier version
        try:
            wsp = load_workbook(OUT)["Flagged Projects"]
            for row in wsp.iter_rows(min_row=2, values_only=True):
                if row[0] and (row[11] or row[12]):
                    prev[row[0]] = (row[11], row[12])
        except Exception:  # noqa: BLE001
            prev = {}

    wb = Workbook()
    # ---------------------------------------------------------------- Read Me
    rm = wb.active
    rm.title = "Read Me"
    rm.column_dimensions["A"].width = 26
    rm.column_dimensions["B"].width = 110
    lines = [
        ("Flagged Projects — Reviewer Workbook", None),
        ("Generated", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")),
        ("Purpose", "Projects whose presentation materials show a methodological issue, so they are not accidentally "
                    "recommended to students as model examples before a person has reviewed them."),
        ("Important", "Flags describe the project MATERIALS (slides and reported results), not the students. They are "
                      "not grades and do not change the original rubric scores. A person makes every final call."),
        ("How flags were made", "While reading each presentation, the extraction step recorded internal inconsistencies "
                                "(e.g. conflicting metrics, likely leakage). Each flag was then categorized and given a "
                                "severity (prompts/flag_triage_v1.md). Every CRITICAL call was checked by the lead analyst."),
        ("Severity: critical", "A flaw that makes the headline result invalid or misleading (e.g. target leakage, chance-level "
                               "results presented as success). Project is HELD from student recommendations."),
        ("Severity: moderate", "Results need caution (e.g. numbers that disagree across slides). Project can still be "
                               "recommended, with a caution shown. Flaws the students acknowledged themselves are moderate."),
        ("Severity: minor", "Informational only; no effect on recommendations."),
        ("What to edit", "Only the two yellow columns in 'Flagged Projects': Reviewer decision (drop-down) and Reviewer notes."),
        ("Decision options", "Confirm hold · Downgrade to caution · Clear flag · Needs discussion. Decisions can be imported "
                             "back into the library (python -m aipil.export.review_workbook --import) and override the "
                             "automatic status."),
        ("Example row", "project-XXX | Example title | Healthcare & Life Sciences | ... | Highest severity: critical | "
                        "HOLD from recommendations | Reviewer decision: Confirm hold | Notes: Labels were computed from "
                        "the input features; agree it should not be a model example."),
        ("Privacy", "Internal and private: contains titles of student work. Do not share outside the program."),
    ]
    for i, (k, v) in enumerate(lines, 1):
        a = rm.cell(row=i, column=1, value=k)
        a.font = Font(name=F, bold=True, size=14 if i == 1 else 10)
        if v is not None:
            b = rm.cell(row=i, column=2, value=v)
            b.font = Font(name=F, size=10)
            b.alignment = Alignment(wrap_text=True, vertical="top")
        a.alignment = Alignment(vertical="top")

    # ---------------------------------------------------------------- Flag Detail (built first; others reference it)
    wb.create_sheet("Summary")
    fp = wb.create_sheet("Flagged Projects")
    fd = wb.create_sheet("Flag Detail")
    cols = ["Project ID", "Title", "Severity", "Category", "Error label", "Full flag (as recorded)", "Students acknowledged?"]
    _header(fd, cols, [13, 40, 11, 30, 44, 90, 14])
    r = 2
    for p in projects:
        for (_, sev, cat, label, text, ack) in by_p[p]:
            for c, v in enumerate([p, title.get(p), sev, CATEGORY_NAMES.get(cat, cat), label, text, "Yes" if ack else "No"], 1):
                fd.cell(row=r, column=c, value=v)
            r += 1
    n_flags = r - 2
    _body(fd, n_flags, len(cols), wrap_cols=(2, 5, 6))
    fd.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{n_flags + 1}"
    for sev, color in SEV_FILL.items():
        fd.conditional_formatting.add(f"A2:G{n_flags + 1}", FormulaRule(formula=[f'$C2="{sev}"'],
                                                                         fill=PatternFill("solid", start_color=color)))

    # ---------------------------------------------------------------- Flagged Projects
    cols = ["Project ID", "Title", "Primary industry (inferred)", "Student-provided type", "Rubric total (/25)",
            "Highest severity", "Recommendation status", "# flags", "# critical", "Error labels", "Categories",
            "Reviewer decision", "Reviewer notes"]
    _header(fp, cols, [13, 40, 26, 22, 10, 11, 24, 8, 9, 60, 34, 20, 40])
    for i, p in enumerate(projects, 2):
        fl = by_p[p]
        sev = min((f[1] for f in fl), key=order.get)
        labels = "; ".join(dict.fromkeys(f"[{f[1]}] {f[3]}" for f in fl))
        cats = "; ".join(dict.fromkeys(CATEGORY_NAMES.get(f[2], f[2]) for f in fl))
        dec, notes = prev.get(p, (None, None))
        vals = [p, title.get(p), prim.get(p), stype.get(p), total.get(p), sev, STATUS_TEXT[status.get(p, "ok")],
                f"=COUNTIF('Flag Detail'!$A$2:$A${n_flags + 1},A{i})",
                f"=COUNTIFS('Flag Detail'!$A$2:$A${n_flags + 1},A{i},'Flag Detail'!$C$2:$C${n_flags + 1},\"critical\")",
                labels, cats, dec, notes]
        for c, v in enumerate(vals, 1):
            fp.cell(row=i, column=c, value=v)
    n_p = len(projects)
    _body(fp, n_p, len(cols), wrap_cols=(2, 10, 11, 13))
    for rr in range(2, n_p + 2):
        fp.cell(row=rr, column=12).fill = INPUT_FILL
        fp.cell(row=rr, column=13).fill = INPUT_FILL
    dv = DataValidation(type="list", formula1='"' + ",".join(DECISIONS) + '"', allow_blank=True)
    fp.add_data_validation(dv)
    dv.add(f"L2:L{n_p + 1}")
    fp.cell(row=1, column=12).comment = Comment("Reviewer input: choose from the drop-down.", "AIPIL")
    fp.auto_filter.ref = f"A1:M{n_p + 1}"
    for sev, color in SEV_FILL.items():
        fp.conditional_formatting.add(f"A2:K{n_p + 1}", FormulaRule(formula=[f'$F2="{sev}"'],
                                                                     fill=PatternFill("solid", start_color=color)))

    # ---------------------------------------------------------------- Summary (formulas over the two sheets)
    sm = wb["Summary"]
    sm.column_dimensions["A"].width = 44
    sm.column_dimensions["B"].width = 14
    sm.column_dimensions["C"].width = 14
    FD, FP = f"'Flag Detail'!$C$2:$C${n_flags + 1}", f"'Flagged Projects'!$G$2:$G${n_p + 1}"
    rows = [("Flagged projects — summary", None, None), (None, None, None),
            ("Projects in the library", 188, None),
            ("Projects with at least one flag", f"=COUNTA('Flagged Projects'!$A$2:$A${n_p + 1})", None),
            (None, None, None), ("Recommendation status", "Projects", None)]
    for k in ["hold", "caution", "ok"]:
        rows.append((STATUS_TEXT[k], f'=COUNTIF({FP},"{STATUS_TEXT[k]}")', None))
    rows += [(None, None, None), ("Flags by severity", "Flags", None)]
    for k in ["critical", "moderate", "minor"]:
        rows.append((k.capitalize(), f'=COUNTIF({FD},"{k}")', None))
    rows += [("Total flags", f"=COUNTA('Flag Detail'!$A$2:$A${n_flags + 1})", None), (None, None, None),
             ("Flags by category", "Flags", "of which critical")]
    for key, name in CATEGORY_NAMES.items():
        rng = f"'Flag Detail'!$D$2:$D${n_flags + 1}"
        rows.append((name, f'=COUNTIF({rng},"{name}")', f'=COUNTIFS({rng},"{name}",{FD},"critical")'))
    rows += [(None, None, None), ("Reviewer progress", "Projects", None),
             ("Decisions entered", f"=COUNTA('Flagged Projects'!$L$2:$L${n_p + 1})", None),
             ("Still to review", "STILL_TO_REVIEW", None)]
    for i, (a, b, c) in enumerate(rows, 1):
        for col, v in enumerate([a, b, c], 1):
            cell = sm.cell(row=i, column=col, value=v)
            cell.font = Font(name=F, size=14 if i == 1 else 10,
                             bold=(i == 1 or (isinstance(a, str) and b in ("Projects", "Flags"))))
    dec_row = next(i for i, (a, _, _) in enumerate(rows, 1) if a == "Decisions entered")
    sm.cell(row=dec_row + 1, column=2, value=f"=B4-B{dec_row}")
    sm.cell(row=3, column=2).comment = Comment("Total projects in the source workbook (hardcoded from the import).", "AIPIL")
    wb.move_sheet("Summary", offset=-0)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"wrote {OUT} ({n_p} projects, {n_flags} flags; {len(prev)} prior decisions preserved)")


def import_decisions(path=None):
    src = path or OUT
    wsp = load_workbook(src)["Flagged Projects"]
    out = {}
    for row in wsp.iter_rows(min_row=2, values_only=True):
        if row[0] and row[11]:
            out[row[0]] = {"decision": row[11], "notes": row[12], "source_file": str(src).split("/")[-1],
                           "reviewed_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    f = paths.PRIVATE / "qa" / "reviewer_decisions.json"
    f.write_text(json.dumps(out, indent=1))
    print(f"imported {len(out)} reviewer decisions -> {f}; run `make build export` to apply")


if __name__ == "__main__":
    if "--import" in sys.argv:
        rest = [a for a in sys.argv[1:] if a != "--import"]
        import_decisions(rest[0] if rest else None)
    else:
        build()
