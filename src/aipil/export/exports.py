"""Exports: flattened analytical table (CSV/JSON) and the application data bundle.

The flattened export is a convenience view; the normalized SQLite database is the primary
model. All exports are written to data/processed/ (git-ignored) because they contain
student-authored descriptions. A public catalog requires the explicit review process in
docs/governance.md.
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
from collections import defaultdict

from aipil import paths

CRITERIA = ["Project Description", "Algorithm", "Essential Question", "Next Steps", "Citations"]


_PLACEHOLDER = re.compile(r"^\s*(nan|none|null|n/?a|na|no data submitted|not provided|unknown|undefined|tbd|-|—|\?)?\s*$", re.I)
# enumerations where words like "unknown" carry meaning are left untouched
_ENUM_KEYS = {"level", "role", "match", "relationship", "status", "severity", "category", "id", "view", "source", "target",
              "parent", "family", "kind"}


def clean_for_ui(o, key=None):
    """Display-layer cleanup (source data is untouched): placeholder strings such as 'nan', 'No data submitted',
    'unknown' or '' become None so the UI shows a consistent 'Not provided' / omits the field."""
    if isinstance(o, dict):
        return {k: clean_for_ui(v, k) for k, v in o.items()}
    if isinstance(o, list):
        return [clean_for_ui(v, key) for v in o]
    if isinstance(o, str) and key not in _ENUM_KEYS and _PLACEHOLDER.match(o):
        return None
    if isinstance(o, float) and o != o:  # NaN
        return None
    return o


def _rows(con, sql, *a):
    con.row_factory = sqlite3.Row
    return [dict(r) for r in con.execute(sql, a)]


def project_records(con) -> list[dict]:
    projects = _rows(con, """SELECT p.*, pp.*, rt.strict_total FROM projects p
        LEFT JOIN project_profiles pp USING(project_id) LEFT JOIN rubric_totals rt USING(project_id)
        ORDER BY p.project_id""")
    terms = defaultdict(lambda: defaultdict(list))
    for r in _rows(con, """SELECT pt.project_id, pt.dimension, pt.term_id, t.label, t.parent_id, pt.evidence_level,
            pt.original_term, pt.is_primary, e.page, e.excerpt, e.verified
            FROM project_terms pt JOIN taxonomy_terms t USING(term_id) LEFT JOIN evidence e USING(evidence_id)"""):
        terms[r["project_id"]][r["dimension"]].append(
            dict(id=r["term_id"], label=r["label"], parent=r["parent_id"], level=r["evidence_level"],
                 primary=bool(r["is_primary"]), page=r["page"], quote=r["excerpt"], verified=r["verified"]))
    algs = defaultdict(list)
    for r in _rows(con, """SELECT pa.*, t.label, t.attributes, e.page, e.excerpt, e.verified FROM project_algorithms pa
            JOIN taxonomy_terms t USING(term_id) LEFT JOIN evidence e USING(evidence_id)"""):
        attrs = json.loads(r["attributes"] or "{}")
        algs[r["project_id"]].append(dict(id=r["term_id"], label=r["label"], original=r["original_term"], role=r["role"],
                                          purpose=r["purpose"], inputs=r["inputs"], outputs=r["outputs"],
                                          result=r["reported_result"], level=r["evidence_level"],
                                          family=attrs.get("family"), difficulty=attrs.get("level"),
                                          page=r["page"], quote=r["excerpt"], verified=r["verified"]))
    rub = defaultdict(dict)
    for r in _rows(con, """SELECT s.project_id, s.criterion, s.score, e.score AS eval_score, e.limiting_factors,
            e.rationale, e.slides_cited, e.evidence FROM rubric_scores s
            LEFT JOIN rubric_evaluations e USING(project_id, criterion)"""):
        rub[r["project_id"]][r["criterion"]] = dict(score=r["score"], eval_score=r["eval_score"],
                                                    limiting=r["limiting_factors"], rationale=r["rationale"],
                                                    slides=r["slides_cited"], evidence=r["evidence"])
    asm = defaultdict(lambda: defaultdict(dict))
    for r in _rows(con, "SELECT * FROM assessments"):
        asm[r["project_id"]][r["construct"]][r["component"]] = dict(
            value=r["value_num"], label=r["value_label"], rationale=r["rationale"], method=r["method"],
            confidence=r["confidence"])
    ds = defaultdict(list)
    for r in _rows(con, """SELECT pd.*, d.name, d.canonical_url, d.platform, d.publisher, d.description AS ddesc,
            d.modality, d.access_requirements, d.license, d.availability_status, d.link_status, d.link_checked_at
            FROM project_datasets pd JOIN datasets d USING(dataset_id)"""):
        ds[r["project_id"]].append(dict(id=r["dataset_id"], name=r["name"], url=r["canonical_url"],
                                        platform=r["platform"], publisher=r["publisher"], description=r["ddesc"],
                                        modality=r["modality"], access=r["access_requirements"], license=r["license"],
                                        availability=r["availability_status"], link_status=r["link_status"],
                                        relationship=r["relationship"], match=r["match_level"],
                                        discovery_level=r["discovery_level"], original=r["original_reference"],
                                        evidence=r["evidence"], confidence=r["confidence"], comments=r["comments"]))
    clues = defaultdict(list)
    for r in _rows(con, "SELECT * FROM dataset_clues"):
        clues[r["project_id"]].append(dict(status=r["status"], clue=r["clue"], notes=r["notes"]))
    orig = defaultdict(lambda: defaultdict(dict))
    for r in _rows(con, "SELECT * FROM originality"):
        orig[r["project_id"]][r["scope"]][r["dimension"]] = dict(score=r["score"], label=r["label"],
                                                                 rationale=r["rationale"], confidence=r["confidence"],
                                                                 method=r["method"])
    prec = defaultdict(list)
    for r in _rows(con, "SELECT * FROM external_precedents"):
        prec[r["project_id"]].append(dict(title=r["title"], url=r["url"], kind=r["kind"], date=r["date"],
                                          comparability=r["comparability"]))
    tags = defaultdict(list)
    for r in _rows(con, "SELECT * FROM search_tags"):
        tags[r["project_id"]].append(r["tag"])
    cl = {r["project_id"]: r for r in _rows(con, "SELECT * FROM clusters WHERE view='overall'")}
    rq = defaultdict(list)
    for r in _rows(con, "SELECT * FROM review_queue WHERE status='open'"):
        rq[r["project_id"]].append(dict(field=r["field"], reason=r["reason"], priority=r["priority"]))
    audit = defaultdict(list)
    for r in _rows(con, "SELECT * FROM audit_flags WHERE project_id IS NOT NULL"):
        audit[r["project_id"]].append(dict(check=r["check_name"], severity=r["severity"], detail=r["detail"]))

    qf = defaultdict(list)
    for r in _rows(con, "SELECT * FROM quality_flags ORDER BY project_id, CASE severity WHEN 'critical' THEN 0 WHEN 'moderate' THEN 1 ELSE 2 END"):
        qf[r["project_id"]].append(dict(category=r["category"], severity=r["severity"], label=r["label"], text=r["flag_text"],
                                        acknowledged=bool(r["student_acknowledged"])))
    rs = {r["project_id"]: r for r in _rows(con, "SELECT * FROM recommendation_status")}
    out = []
    for p in projects:
        pid = p["project_id"]
        c = cl.get(pid)
        out.append(dict(
            id=pid,
            title=p["student_title"] or p["title_slide"],
            title_slide=p["title_slide"],
            student_description=p["student_description"],
            student_type=p["student_project_type"],
            summary=dict(plain=p["plain_summary"], technical=p["technical_summary"], question=p["research_question"],
                         problem=p["problem_statement"], beneficiary=p["primary_beneficiary"],
                         domain=p["application_domain"], subdomain=p["subdomain"], inputs=p["inputs"],
                         outputs=p["outputs"], results=p["results_summary"]),
            source=dict(completeness=p["source_completeness"], confidence=p["overall_confidence"],
                        status=p["processing_status"], pdf_url=p["pdf_url"], text_url=p["text_url"]),
            terms={d: v for d, v in terms[pid].items()},
            algorithms=algs[pid], datasets=ds[pid], dataset_clues=clues[pid],
            rubric=dict(total=p["strict_total"], criteria=rub[pid]),
            assessments={k: dict(v) for k, v in asm[pid].items()},
            originality={k: dict(v) for k, v in orig[pid].items()},
            precedents=prec[pid], tags=tags[pid],
            cluster=dict(id=c["cluster_id"], label=c["cluster_label"], x=c["x"], y=c["y"], z=c["z"]) if c else None,
            review=rq[pid], audit=audit[pid], quality_flags=qf[pid],
            recommendation=dict(status=(rs.get(pid) or {}).get("status", "ok"), reason=(rs.get(pid) or {}).get("reason"),
                                reviewer_decision=(rs.get(pid) or {}).get("reviewer_decision"),
                                reviewer_notes=(rs.get(pid) or {}).get("reviewer_notes")),
        ))
    return out


def _labels(rec, dim, top_only=False, levels=("confirmed", "inferred")):
    items = rec["terms"].get(dim, [])
    return sorted({t["label"] for t in items if t["level"] in levels and (not top_only or not t["parent"])})


def flatten(rec) -> dict:
    a = rec["assessments"]
    alg = lambda roles: sorted({x["label"] for x in rec["algorithms"] if x["role"] in roles})  # noqa: E731
    io = rec["originality"].get("internal", {}).get("composite", {})
    eo = rec["originality"].get("external", {}).get("classification", {})
    used = [d for d in rec["datasets"] if d["relationship"] == "used"]
    row = dict(
        project_id=rec["id"], title=rec["title"], summary=rec["summary"]["plain"],
        student_project_type=rec["student_type"],
        industries=_labels(rec, "industry", top_only=True), subdomains=sorted(
            {t["label"] for t in rec["terms"].get("industry", []) if t["parent"]}),
        ml_paradigms=_labels(rec, "paradigm"), task_types=_labels(rec, "task"),
        algorithms_used=alg({"implemented"}), algorithms_compared=alg({"baseline", "compared"}),
        algorithms_proposed=alg({"considered", "proposed"}),
        data_modalities=_labels(rec, "modality"), technical_methods=_labels(rec, "method"), tools=_labels(rec, "tool"),
        dataset_names=[d["name"] for d in used], dataset_urls=[d["url"] for d in used if d["url"]],
        dataset_match_levels=[d["match"] for d in used],
        dataset_link_status=[d["link_status"] for d in used if d["url"]],
        alternative_datasets=[d["name"] for d in rec["datasets"] if d["relationship"] == "alternative"],
        difficulty_tier=a.get("difficulty_tier", {}).get("overall", {}).get("label"),
        technical_sophistication=a.get("sophistication", {}).get("overall", {}).get("value"),
        reproduction_effort=a.get("reproduction_effort", {}).get("overall", {}).get("label"),
        reproduction_effort_score=a.get("reproduction_effort", {}).get("overall", {}).get("value"),
        adoption_readiness=a.get("adoption_readiness", {}).get("overall", {}).get("value"),
        prereq_python=a.get("prerequisites", {}).get("python", {}).get("value"),
        prereq_math_stats=a.get("prerequisites", {}).get("math_stats", {}).get("value"),
        prereq_ml=a.get("prerequisites", {}).get("ml", {}).get("value"),
        prereq_domain=a.get("prerequisites", {}).get("domain", {}).get("value"),
        hardware=a.get("prerequisites", {}).get("hardware", {}).get("label"),
        internal_originality=io.get("score"), internal_originality_pattern=io.get("label"),
        external_originality=eo.get("label"),
        original_rubric_total=rec["rubric"]["total"],
        **{f"rubric_{c.lower().replace(' ', '_')}": rec["rubric"]["criteria"].get(c, {}).get("score") for c in CRITERIA},
        cluster=rec["cluster"]["label"] if rec["cluster"] else None,
        pdf_url=rec["source"]["pdf_url"], extracted_text_url=rec["source"]["text_url"],
        source_completeness=rec["source"]["completeness"], confidence=rec["source"]["confidence"],
        processing_status=rec["source"]["status"], search_tags=rec["tags"],
        open_review_items=len(rec["review"]), audit_flags=[f["check"] for f in rec["audit"]],
        recommendation_status=rec["recommendation"]["status"],
        reviewer_decision=rec["recommendation"]["reviewer_decision"],
        reviewer_notes=rec["recommendation"]["reviewer_notes"],
        quality_flag_labels=[f"{q['severity']}: {q['label']}" for q in rec["quality_flags"]],
    )
    return row


def export_all():
    con = sqlite3.connect(paths.DB_PATH)
    recs = [clean_for_ui(r) for r in project_records(con)]
    paths.PROCESSED.mkdir(parents=True, exist_ok=True)
    flat = [flatten(r) for r in recs]
    (paths.PROCESSED / "projects_flat.json").write_text(json.dumps(flat, indent=1))
    with open(paths.PROCESSED / "projects_flat.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(flat[0].keys()))
        w.writeheader()
        for r in flat:
            w.writerow({k: "; ".join(map(str, v)) if isinstance(v, list) else v for k, v in r.items()})
    con.row_factory = sqlite3.Row
    edges = [dict(r) for r in con.execute("SELECT * FROM similarity_edges")]
    rubric = [dict(r) for r in con.execute("SELECT * FROM rubric_criteria ORDER BY criterion, level DESC")]
    tax = [dict(r) for r in con.execute("SELECT term_id, dimension, label, parent_id, attributes FROM taxonomy_terms")]
    meta = {r[0]: r[1] for r in con.execute("SELECT key, value FROM meta")}
    bundle = dict(meta=meta, projects=recs, edges=edges, rubric=rubric, taxonomy=tax)
    app_data = paths.ROOT / "app" / "public" / "data"
    app_data.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(bundle, separators=(",", ":"))
    (app_data / "library.json").write_text(txt)
    (paths.PROCESSED / "library.json").write_text(txt)
    print(f"exported {len(recs)} projects, {len(edges)} edges -> data/processed/, app/public/data/library.json")


if __name__ == "__main__":
    export_all()
