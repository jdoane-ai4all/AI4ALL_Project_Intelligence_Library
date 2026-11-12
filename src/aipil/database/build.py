"""Load validated extractions and research outputs into the normalized database.

Idempotent: every derived table is rebuilt from the JSON artifacts on each run, while the
raw_* and rubric tables (from the workbook) are never touched here.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone

import yaml

from aipil import PIPELINE_VERSION, paths
from aipil.classification import assess
from aipil.extraction.schema import (load_source_text, norm_text, quote_found, taxonomy,
                                     validate_extraction)

# Deletion order matters: children before parents (foreign keys are enforced).
DERIVED = ["quality_flags", "recommendation_status", "project_terms", "project_algorithms", "project_profiles", "evidence", "extraction_runs",
           "assessments", "search_tags", "review_queue", "dataset_clues", "project_datasets", "datasets",
           "external_precedents", "taxonomy_terms"]


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_taxonomy(con):
    tax = taxonomy()
    for dim, spec in tax["dimensions"].items():
        for slug, t in spec["terms"].items():
            attrs = {k: v for k, v in t.items() if k not in {"label", "parent", "description"}}
            con.execute("INSERT OR REPLACE INTO taxonomy_terms VALUES (?,?,?,?,?,?,?)",
                        (f"{dim}:{slug}", dim, t["label"], f"{dim}:{t['parent']}" if t.get("parent") else None,
                         t.get("description"), json.dumps(attrs) if attrs else None, tax["version"]))
    con.execute("INSERT OR REPLACE INTO meta VALUES ('taxonomy_version', ?)", (tax["version"],))


def _term_id(con, dim, term, pid, queue):
    """Map a slug to a taxonomy term id. Proposals ('new:x') are first resolved through the versioned alias map;
    unmapped proposals become provisional terms + review items."""
    alias = (taxonomy().get("aliases") or {}).get(f"{dim}:{term}")
    if alias:
        return alias
    if term.startswith("new:"):
        slug = term[4:]
        tid = f"{dim}:{slug}"
        con.execute("INSERT OR IGNORE INTO taxonomy_terms VALUES (?,?,?,?,?,?,?)",
                    (tid, dim, slug.replace("_", " ").capitalize(), None, "PROVISIONAL: proposed during extraction",
                     json.dumps({"provisional": True}), "proposed"))
        queue.append((pid, f"{dim}", f"Provisional taxonomy term proposed: {slug}", "low"))
        return tid
    return f"{dim}:{term}"


def _evidence_id(pid, label, ev):
    h = hashlib.sha1(f"{pid}|{label}|{ev.page}|{ev.quote}".encode()).hexdigest()[:12]
    return f"ev-{h}"


def load_extractions(con):
    stats = {"loaded": 0, "invalid": 0, "quotes": 0, "verified": 0}
    acfg_ver = yaml.safe_load((paths.CONFIG / "assessment.yaml").read_text())["version"]
    for f in sorted(paths.EXTRACTIONS.glob("project-*.json")):
        pid = f.stem
        data = json.loads(f.read_text())
        src = load_source_text(pid)
        ex, problems, st = validate_extraction(data, src)
        queue = []
        if ex is None:
            stats["invalid"] += 1
            con.execute("INSERT INTO review_queue (project_id,field,reason,priority,created_at) VALUES (?,?,?,?,?)",
                        (pid, "extraction", "; ".join(problems)[:1000], "high", _now()))
            continue
        stats["loaded"] += 1
        stats["quotes"] += st["quotes"]
        stats["verified"] += st["verified"]
        run_id = f"{pid}:{ex.prompt_version}:{hashlib.sha1(f.read_bytes()).hexdigest()[:10]}"
        con.execute("INSERT INTO extraction_runs VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (run_id, pid, PIPELINE_VERSION, ex.prompt_version, taxonomy()["version"], "claude-code-subagent",
                     datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
                     "valid" if not problems else "valid_with_problems", json.dumps(ex.sources_used),
                     ex.source_notes))
        s = ex.summary
        con.execute("INSERT INTO project_profiles VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (pid, s.plain_language, s.technical, s.research_question, s.problem, s.primary_beneficiary,
                     s.application_domain, s.subdomain, s.inputs, s.outputs, s.results, ex.source_completeness,
                     ex.overall_confidence, run_id))
        src_norm = norm_text(src) if src else ""

        def add_ev(label, ev):
            if not ev or not (ev.quote or ev.page):
                return None
            eid = _evidence_id(pid, label, ev)
            verified = None
            if ev.source == "text" and ev.quote:
                verified = int(quote_found(ev.quote, src_norm))
            con.execute("INSERT OR REPLACE INTO evidence VALUES (?,?,?,?,?,?)",
                        (eid, pid, f"{pid}:pdf" if ev.source == "pdf_visual" else f"{pid}:text", ev.page,
                         ev.quote, verified))
            return eid

        for dim, items in [("industry", ex.industries), ("paradigm", ex.paradigms), ("task", ex.tasks),
                           ("modality", ex.modalities), ("method", ex.methods), ("tool", ex.tools)]:
            for t in items:
                tid = _term_id(con, dim, t.term, pid, queue)
                eid = add_ev(f"{dim}:{t.term}", t.evidence)
                con.execute("INSERT OR REPLACE INTO project_terms VALUES (?,?,?,?,?,?,?)",
                            (pid, tid, dim, t.evidence_level, t.original_term, eid, int(t.primary)))
                # parents of hierarchical terms are implied (inferred) memberships
                parent = con.execute("SELECT parent_id FROM taxonomy_terms WHERE term_id=?", (tid,)).fetchone()
                if parent and parent[0]:
                    con.execute("INSERT OR IGNORE INTO project_terms VALUES (?,?,?,?,?,?,?)",
                                (pid, parent[0], dim, t.evidence_level, None, eid, 0))
        for a in ex.algorithms:
            tid = _term_id(con, "algorithm", a.canonical, pid, queue)
            eid = add_ev(f"algorithm:{a.canonical}", a.evidence)
            if not tid.startswith("algorithm:"):   # e.g. SMOTE re-classified as a method
                con.execute("INSERT OR IGNORE INTO project_terms VALUES (?,?,?,?,?,?,?)",
                            (pid, tid, tid.split(":")[0], a.evidence_level, a.original_name, eid, 0))
                continue
            con.execute("INSERT OR REPLACE INTO project_algorithms VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (pid, tid, a.original_name, a.role, a.purpose, a.inputs, a.outputs, a.reported_result,
                         a.evidence_level, eid))
        for d in ex.datasets:
            con.execute("INSERT INTO dataset_clues VALUES (?,?,?,?)",
                        (pid, json.dumps(d.model_dump(exclude_none=True)), "extracted", d.relationship))

        # ---- assessments
        def put(construct, component, num, label, rationale, conf, method):
            con.execute("INSERT OR REPLACE INTO assessments VALUES (?,?,?,?,?,?,?,?)",
                        (pid, construct, component, num, label, rationale, conf, method))
        method_llm = f"llm-rated anchors (assessment v{acfg_ver})"
        method_det = f"deterministic composite (assessment v{acfg_ver})"
        conf = ex.overall_confidence
        for k, v in ex.sophistication.items():
            put("sophistication", k, v.score, None, v.rationale, conf, method_llm)
        soph = assess.sophistication({k: v.score for k, v in ex.sophistication.items()})
        put("sophistication", "overall", soph, None, "mean of six components scaled to 0-10", conf, method_det)
        prereq = {k: v.score for k, v in ex.prerequisites.items()}
        py_level, py_hits = assess.python_level(json.loads(ex.model_dump_json()))
        crit = yaml.safe_load((paths.CONFIG / "assessment.yaml").read_text())["python_level"]["levels"][py_level]["any_of"]
        for k, v in ex.prerequisites.items():
            if k == "python":
                put("prerequisites", "python_llm", v.score, None, v.rationale, conf, method_llm)
                continue
            put("prerequisites", k, v.score, None, v.rationale, conf, method_llm)
        prereq["python"] = py_level
        incomplete = not any(a.role == "implemented" for a in ex.algorithms)
        py_note = "Criteria met: " + "; ".join(crit.get(h, h) for h in py_hits)
        if incomplete:
            py_note += (" — NOTE: no model was implemented in the presentation (incomplete or planned work); this level "
                        f"reflects demonstrated work only. Reader's estimate for a finished version: {ex.prerequisites['python'].score}/3.")
            queue.append((pid, "prerequisites", "Python level computed from incomplete work; compare with reader estimate", "low"))
        put("prerequisites", "python", py_level, None, py_note, "low" if incomplete else "high",
            f"deterministic criteria (assessment v{acfg_ver} python_level)")
        put("prerequisites", "hardware", None, ex.hardware, None, conf, "llm")
        alg_level = assess.max_algorithm_level([a.model_dump() for a in ex.algorithms])
        tier, why = assess.difficulty_tier(prereq, alg_level)
        put("difficulty_tier", "overall", {"Beginner": 1, "Intermediate": 2, "Advanced": 3}[tier], tier, why, conf,
            method_det)
        for k, v in ex.reproduction.items():
            put("reproduction_effort", k, v.score, None, v.rationale, conf, method_llm)
        tot, band, est = assess.reproduction_band({k: v.score for k, v in ex.reproduction.items()})
        put("reproduction_effort", "overall", tot, band, f"{est} (sum of five 0-3 components = {tot}/15)", conf,
            method_det)
        for k, v in ex.adoption_readiness.items():
            put("adoption_readiness", k, int(v), None, None, conf, method_llm)
        n, lab = assess.adoption_band(ex.adoption_readiness)
        put("adoption_readiness", "overall", n, lab, f"{n}/7 readiness criteria satisfied", conf, method_det)
        put("team_suitability", "overall", None, ex.team_suitability, None, conf, "llm")
        for i, idea in enumerate(ex.extension_ideas):
            put("extension_ideas", f"idea_{i + 1}", None, idea, None, conf, "llm (from source next steps)")

        for tag in ex.search_tags:
            con.execute("INSERT OR IGNORE INTO search_tags VALUES (?,?,?)", (pid, tag.strip().lower(), "extraction"))

        for p in problems:
            queue.append((pid, "validation", p, "medium"))
        for fl in ex.review_flags:
            queue.append((pid, "extraction_flag", fl, "medium"))
        if ex.overall_confidence == "low":
            queue.append((pid, "confidence", "Overall extraction confidence is low", "high"))
        for u in ex.uncertainties:
            queue.append((pid, "uncertainty", u, "low"))
        for q in queue:
            con.execute("INSERT INTO review_queue (project_id,field,reason,priority,created_at) VALUES (?,?,?,?,?)",
                        (*q, _now()))
        con.execute("UPDATE projects SET processing_status='extracted' WHERE project_id=?", (pid,))
    return stats


_SLUG = re.compile(r"[^a-z0-9]+")


def dataset_id(name: str, url: str | None) -> str:
    if url:
        u = re.sub(r"^https?://(www\.)?", "", url.strip().lower()).split("?")[0].split("#")[0].rstrip("/")
        return "ds-" + hashlib.sha1(u.encode()).hexdigest()[:10]
    return "ds-" + _SLUG.sub("-", name.lower()).strip("-")[:60]


_NO_SEARCH = ("no_search", "budget", "no search", "not searched", "no web", "exhaust", "background knowledge")


def search_performed(r: dict) -> bool:
    """True when the record's external-originality judgement rests on an actual precedent search."""
    cov = (r.get("external_originality") or {}).get("search_coverage", "").lower()
    return bool(r.get("precedents")) or not any(k in cov for k in _NO_SEARCH)


def load_research(con):
    """Load dataset research + external precedents from data/private/research/<pid>.json."""
    rdir = paths.RESEARCH
    n = 0
    if not rdir.exists():
        return n
    links = {}
    lc = rdir / "link_checks.json"
    if lc.exists():
        links = json.loads(lc.read_text())
    cur_f = paths.PRIVATE / "qa" / "dataset_curation.json"
    curation = json.loads(cur_f.read_text())["entries"] if cur_f.exists() else {}
    for f in sorted(rdir.glob("project-*.json")):
        pid = f.stem
        r = json.loads(f.read_text())
        for c in curation.get(pid, []):  # program-reviewer curation overrides research artifacts (which stay unedited)
            for d in r.get("datasets", []):
                if d.get("name") == c["match_name"]:
                    d.update(c["set"])
                    d["comments"] = ((d.get("comments") or "") + " [curated by program reviewer]").strip()
        n += 1
        for d in r.get("datasets", []):
            did = dataset_id(d["name"], d.get("canonical_url"))
            chk = links.get(d.get("canonical_url") or "", {})
            kg = chk.get("kaggle") or {}
            if kg.get("license") and (not d.get("license") or d.get("license") == "unknown"):
                d["license"] = f"{kg['license']} (from Kaggle metadata)"
            if kg.get("creator") and not d.get("publisher"):
                d["publisher"] = kg["creator"]
            con.execute("""INSERT INTO datasets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(dataset_id) DO UPDATE SET
                  description=COALESCE(datasets.description, excluded.description),
                  publisher=COALESCE(datasets.publisher, excluded.publisher),
                  license=COALESCE(datasets.license, excluded.license)""",
                        (did, d["name"], d.get("canonical_url"), d.get("platform"), d.get("publisher"),
                         d.get("description"), d.get("modality"), d.get("access_requirements"), d.get("license"),
                         d.get("availability_status"), chk.get("status"), chk.get("http_code"), chk.get("checked_at"),
                         None))
            con.execute("INSERT OR REPLACE INTO project_datasets VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (pid, did, d["relationship"], d["match_level"], d.get("discovery_level"),
                         d.get("original_reference"), d.get("evidence"), d.get("confidence"),
                         r.get("researched_at"), d.get("comments")))
        for u in r.get("unresolved", []):
            con.execute("INSERT INTO dataset_clues VALUES (?,?,?,?)", (pid, u.get("clue"), "unresolved", u.get("notes")))
            con.execute("INSERT INTO review_queue (project_id,field,reason,priority,created_at) VALUES (?,?,?,?,?)",
                        (pid, "dataset", f"Unresolved dataset: {u.get('clue', '')[:200]}", "low", _now()))
        for p in r.get("precedents", []):
            con.execute("INSERT INTO external_precedents (project_id,title,url,kind,date,comparability,searched_at) "
                        "VALUES (?,?,?,?,?,?,?)", (pid, p.get("title"), p.get("url"), p.get("kind"), p.get("date"),
                                                    p.get("comparability"), r.get("researched_at")))
        ext = r.get("external_originality")
        if ext and not search_performed(r):
            # No evidence-based precedent search happened: never load a knowledge-only judgement.
            con.execute("INSERT OR REPLACE INTO originality VALUES (?,?,?,?,?,?,?,?)",
                        (pid, "external", "classification", None, "not_assessed",
                         "Precedent search did not run (search budget exhausted or unavailable).", "none",
                         f"coverage: {ext.get('search_coverage', '')[:200]}"))
            con.execute("INSERT INTO review_queue (project_id,field,reason,priority,created_at) VALUES (?,?,?,?,?)",
                        (pid, "external_originality", "Precedent search not performed; re-run research", "medium", _now()))
            ext = None
        if ext:
            for dim, v in ext.get("dimensions", {}).items():
                con.execute("INSERT OR REPLACE INTO originality VALUES (?,?,?,?,?,?,?,?)",
                            (pid, "external", dim, v.get("score"), v.get("label"), v.get("rationale"),
                             ext.get("confidence"), f"web precedent search; coverage: {ext.get('search_coverage', '')}"))
            con.execute("INSERT OR REPLACE INTO originality VALUES (?,?,?,?,?,?,?,?)",
                        (pid, "external", "classification", None, ext.get("classification"), ext.get("rationale"),
                         ext.get("confidence"), f"web precedent search; coverage: {ext.get('search_coverage', '')}"))
        con.execute("UPDATE projects SET processing_status='researched' WHERE project_id=?", (pid,))
    return n


def load_quality(con):
    """Load triaged flags (data/private/qa/flag_triage.json) and derive recommendation status.

    Human reviewer decisions (data/private/qa/reviewer_decisions.json, exported from the review workbook) override the
    automatic status when present."""
    tri_f = paths.PRIVATE / "qa" / "flag_triage.json"
    if not tri_f.exists():
        return 0
    tri = {(t["project_id"], t["flag_index"]): t for t in json.loads(tri_f.read_text())}
    for f in sorted(paths.EXTRACTIONS.glob("project-*.json")):
        pid = f.stem
        for i, text in enumerate(json.loads(f.read_text()).get("review_flags", [])):
            t = tri.get((pid, i), {})
            con.execute("INSERT INTO quality_flags VALUES (?,?,?,?,?,?,?,?)",
                        (pid, i, t.get("category", "other"), t.get("severity", "moderate"), t.get("label") or text[:80],
                         text, int(bool(t.get("student_acknowledged"))), "llm triage (prompts/flag_triage_v1.md)" if t else "untriaged"))
    dec_f = paths.PRIVATE / "qa" / "reviewer_decisions.json"
    decisions = json.loads(dec_f.read_text()) if dec_f.exists() else {}
    for (pid,) in con.execute("SELECT project_id FROM projects").fetchall():
        sev = [r[0] for r in con.execute("SELECT severity FROM quality_flags WHERE project_id=?", (pid,))]
        labels = [r[0] for r in con.execute("SELECT label FROM quality_flags WHERE project_id=? AND severity!='minor' "
                                            "ORDER BY CASE severity WHEN 'critical' THEN 0 ELSE 1 END", (pid,))]
        status = "hold" if "critical" in sev else "caution" if "moderate" in sev else "ok"
        d = decisions.get(pid, {})
        rank = {"ok": 0, "caution": 1, "hold": 2}
        override = {"Confirm hold": "hold", "Downgrade to caution": "caution", "Clear flag": "ok",
                    # under discussion: keep the stricter of the automatic status and a caution
                    "Needs discussion": max(status, "caution", key=rank.get)}.get(d.get("decision"))
        con.execute("INSERT INTO recommendation_status VALUES (?,?,?,?,?,?)",
                    (pid, override or status, "; ".join(labels) or None, d.get("decision"), d.get("notes"), d.get("reviewed_at")))
    return len(tri)


def build():
    con = sqlite3.connect(paths.DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    for t in DERIVED:
        con.execute(f"DELETE FROM {t}")
    con.execute("DELETE FROM originality WHERE scope='external'")
    con.execute("UPDATE projects SET processing_status='imported'")
    load_taxonomy(con)
    st = load_extractions(con)
    nr = load_research(con)
    load_quality(con)
    con.execute("INSERT OR REPLACE INTO meta VALUES ('built_at', ?)", (_now(),))
    con.commit()
    print(f"extractions loaded={st['loaded']} invalid={st['invalid']} quotes verified {st['verified']}/{st['quotes']}; "
          f"research files={nr}")
    return st
