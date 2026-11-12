"""Generate the QA report and the exploratory research report from the database.

Two outputs per report:
  reports/<name>.md                 committed; aggregate statistics and project IDs only
  data/processed/<name>_private.md  private; adds project titles for internal use

Statistics are descriptive and exploratory. Correlations use Spearman's rho with bootstrap 95% CIs and
two-sided permutation p-values; with many comparisons, p-values are reported for orientation only
(no correction is applied and none should be read as confirmatory).
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone

import numpy as np

from aipil import paths

CRITERIA = ["Project Description", "Algorithm", "Essential Question", "Next Steps", "Citations"]
RNG = np.random.default_rng(20261105)


# ----------------------------------------------------------------- helpers
def q(con, sql, *a):
    return con.execute(sql, a).fetchall()


def spearman(x, y):
    from scipy.stats import rankdata
    rx, ry = rankdata(x), rankdata(y)
    return float(np.corrcoef(rx, ry)[0, 1])


def spearman_ci(x, y, n_boot=2000, n_perm=2000):
    x, y = np.asarray(x, float), np.asarray(y, float)
    rho = spearman(x, y)
    boots = []
    for _ in range(n_boot):
        i = RNG.integers(0, len(x), len(x))
        if np.std(x[i]) > 0 and np.std(y[i]) > 0:
            boots.append(spearman(x[i], y[i]))
    perm = sum(abs(spearman(x, RNG.permutation(y))) >= abs(rho) for _ in range(n_perm))
    return rho, float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5)), (perm + 1) / (n_perm + 1)


def mean_ci(v, n_boot=2000):
    v = np.asarray(v, float)
    if len(v) < 2:
        return float(v.mean()) if len(v) else float("nan"), float("nan"), float("nan")
    b = [RNG.choice(v, len(v)).mean() for _ in range(n_boot)]
    return float(v.mean()), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return out


class Doc:
    def __init__(self, title):
        self.pub = [f"# {title}", "", f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}", ""]
        self.priv = list(self.pub)

    def add(self, lines, private_lines=None):
        lines = [lines] if isinstance(lines, str) else lines
        self.pub += lines
        self.priv += private_lines if private_lines is not None else lines


# ----------------------------------------------------------------- data
def load(con):
    titles = dict(q(con, "SELECT project_id, COALESCE(student_title, title_slide) FROM projects"))
    asm = defaultdict(dict)
    for pid, cons, comp, num, lab in q(con, "SELECT project_id, construct, component, value_num, value_label FROM assessments"):
        asm[pid][f"{cons}.{comp}"] = lab if lab is not None and num is None else (num if num is not None else lab)
        if lab is not None:
            asm[pid][f"{cons}.{comp}.label"] = lab
    rub = defaultdict(dict)
    for pid, c, s in q(con, "SELECT project_id, criterion, score FROM rubric_scores"):
        rub[pid][c] = s
    tot = dict(q(con, "SELECT project_id, strict_total FROM rubric_totals"))
    orig = defaultdict(dict)
    for pid, scope, dim, sc, lab in q(con, "SELECT project_id, scope, dimension, score, label FROM originality"):
        orig[pid][f"{scope}.{dim}"] = sc if sc is not None else lab
        if lab:
            orig[pid][f"{scope}.{dim}.label"] = lab
    terms = defaultdict(lambda: defaultdict(set))
    for pid, tid, dim, lab, parent in q(con, """SELECT pt.project_id, pt.term_id, pt.dimension, t.label, t.parent_id
            FROM project_terms pt JOIN taxonomy_terms t USING(term_id) WHERE pt.evidence_level != 'unknown'"""):
        terms[pid][dim].add(lab)
        if dim == "industry" and parent is None:
            terms[pid]["sector"].add(lab)
    prim = {}
    for pid, lab, parent_label in q(con, """SELECT pt.project_id, t.label, p.label FROM project_terms pt
            JOIN taxonomy_terms t USING(term_id) LEFT JOIN taxonomy_terms p ON p.term_id = t.parent_id
            WHERE pt.dimension='industry' AND pt.is_primary=1"""):
        prim[pid] = parent_label or lab
    algs = defaultdict(set)
    fam = defaultdict(set)
    for pid, lab, attrs in q(con, """SELECT pa.project_id, t.label, t.attributes FROM project_algorithms pa
            JOIN taxonomy_terms t USING(term_id) WHERE pa.role IN ('implemented','baseline','compared')"""):
        algs[pid].add(lab)
        f = json.loads(attrs or "{}").get("family")
        if f:
            fam[pid].add(f)
    pids = [r[0] for r in q(con, "SELECT project_id FROM project_profiles ORDER BY project_id")]
    return dict(titles=titles, asm=asm, rub=rub, tot=tot, orig=orig, terms=terms, prim=prim, algs=algs, fam=fam, pids=pids)


# ----------------------------------------------------------------- QA report
def qa_report(con) -> Doc:
    d = Doc("Data Quality, Provenance & Validation Report")
    n_proj = q(con, "SELECT COUNT(*) FROM projects")[0][0]
    n_ext = q(con, "SELECT COUNT(*) FROM project_profiles")[0][0]
    n_res = q(con, "SELECT COUNT(*) FROM projects WHERE processing_status='researched'")[0][0]
    src = dict(((k, s), n) for k, s, n in q(con, "SELECT kind, access_status, COUNT(*) FROM source_documents GROUP BY 1,2"))
    ev = q(con, "SELECT COUNT(*), SUM(verified) FROM evidence WHERE verified IS NOT NULL")[0]
    d.add(["## Coverage", ""] + table(["Metric", "Value"], [
        ["Projects in workbook", n_proj],
        ["Extracted-text sources retrieved", f"{src.get(('text', 'retrieved'), 0)}/{n_proj}"],
        ["Original PDFs retrieved", f"{src.get(('pdf', 'retrieved'), 0)}/{n_proj}"],
        ["Projects with validated structured extraction", f"{n_ext}/{n_proj}"],
        ["Projects with dataset/precedent research", f"{n_res}/{n_proj}"],
        ["Evidence quotes verified verbatim against source", f"{ev[1]}/{ev[0]} ({100 * ev[1] / max(ev[0], 1):.1f}%)"],
        ["Original rubric rows preserved (raw_scores / raw_rationale)",
         f"{q(con, 'SELECT COUNT(*) FROM raw_scores')[0][0]} / {q(con, 'SELECT COUNT(*) FROM raw_rationale')[0][0]}"],
    ]) + [""])
    d.add(["## Extraction confidence and source completeness", ""] + table(
        ["Confidence", "n"], q(con, "SELECT overall_confidence, COUNT(*) FROM project_profiles GROUP BY 1 ORDER BY 2 DESC")) + [""] +
        table(["Source completeness", "n"], q(con, "SELECT source_completeness, COUNT(*) FROM project_profiles GROUP BY 1 ORDER BY 2 DESC")) + [""])
    lv = q(con, "SELECT dimension, evidence_level, COUNT(*) FROM project_terms GROUP BY 1,2 ORDER BY 1,2")
    d.add(["## Evidence levels of classifications", "", "Confirmed = explicitly stated in source; inferred = derived, not stated.", ""]
          + table(["Dimension", "Level", "Tags"], lv) + [""])
    roles = q(con, "SELECT role, evidence_level, COUNT(*) FROM project_algorithms GROUP BY 1,2 ORDER BY 3 DESC")
    d.add(["## Algorithm roles", ""] + table(["Role", "Evidence level", "n"], roles) + [""])
    miss = []
    for col in ["research_question", "primary_beneficiary", "inputs", "outputs", "results_summary"]:
        m = q(con, f"SELECT COUNT(*) FROM project_profiles WHERE {col} IS NULL OR TRIM({col})=''")[0][0]
        miss.append([col, m, f"{100 * m / max(n_ext, 1):.1f}%"])
    d.add(["## Missing-field rates (profiles)", ""] + table(["Field", "Missing", "Rate"], miss) + [""])
    rq = q(con, "SELECT field, priority, COUNT(*) FROM review_queue WHERE status='open' GROUP BY 1,2 ORDER BY 3 DESC")
    d.add(["## Human review queue", "",
           "Open items requiring human attention. `extraction_flag` items are mostly inconsistencies *in the student "
           "materials* (e.g. conflicting metrics, possible leakage) surfaced by extractors; `uncertainty` items document "
           "what the source did not say.", ""] + table(["Field", "Priority", "Open items"], rq) + [""])
    dsl = q(con, "SELECT relationship, match_level, COUNT(*) FROM project_datasets GROUP BY 1,2 ORDER BY 1,3 DESC")
    lk = q(con, "SELECT COALESCE(link_status,'not checked'), COUNT(*) FROM datasets WHERE canonical_url IS NOT NULL GROUP BY 1 ORDER BY 2 DESC")
    d.add(["## Dataset verification", ""] + table(["Relationship", "Match level", "Links"], dsl) + [""] +
          table(["Link check status (unique dataset URLs)", "n"], lk) + [""] +
          [f"Unresolved dataset clues: {q(con, 'SELECT COUNT(*) FROM dataset_clues WHERE status=' + chr(39) + 'unresolved' + chr(39))[0][0]}", ""])
    rs = q(con, "SELECT status, COUNT(*) FROM recommendation_status GROUP BY 1 ORDER BY 2 DESC")
    qf = q(con, "SELECT severity, category, COUNT(*) FROM quality_flags GROUP BY 1,2 ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'moderate' THEN 1 ELSE 2 END, 3 DESC")
    d.add(["## Methodological flags in project materials", "",
           "Triaged flags (prompts/flag_triage_v1.md; every critical call checked by the lead analyst). `hold` projects are "
           "excluded from student recommendations until a reviewer decides; see the private reviewer workbook "
           "`data/processed/flagged_projects_review.xlsx`.", ""] + table(["Recommendation status", "Projects"], rs) + [""] +
          table(["Severity", "Category", "Flags"], qf) + [""])
    af = q(con, "SELECT severity, check_name, COUNT(*) FROM audit_flags GROUP BY 1,2 ORDER BY 1")
    d.add(["## Original workbook audit (scores never modified)", ""] + table(["Severity", "Check", "n"], af) + [""])
    # consistency checks
    cons = []
    cons.append(["Industry tags with exactly one primary", q(con, """SELECT COUNT(*) FROM (SELECT project_id FROM project_terms
        WHERE dimension='industry' AND is_primary=1 GROUP BY project_id HAVING COUNT(*)=1)""")[0][0]])
    cons.append(["Projects with >=1 implemented algorithm", q(con, "SELECT COUNT(DISTINCT project_id) FROM project_algorithms WHERE role='implemented'")[0][0]])
    cons.append(["Projects tagged deep_learning but no neural algorithm used", q(con, """SELECT COUNT(*) FROM project_terms pt WHERE term_id='paradigm:deep_learning'
        AND NOT EXISTS (SELECT 1 FROM project_algorithms pa JOIN taxonomy_terms t USING(term_id) WHERE pa.project_id=pt.project_id
        AND pa.role IN ('implemented','compared','baseline') AND (t.attributes LIKE '%neural%' OR t.attributes LIKE '%transformer%'
        OR t.attributes LIKE '%generative%' OR t.attributes LIKE '%multimodal%'))""")[0][0]])
    cons.append(["Projects tagged supervised with no implemented model", q(con, """SELECT COUNT(*) FROM project_terms pt WHERE term_id='paradigm:supervised'
        AND NOT EXISTS (SELECT 1 FROM project_algorithms pa WHERE pa.project_id=pt.project_id AND pa.role='implemented')""")[0][0]])
    d.add(["## Cross-record consistency checks", "", "Non-zero counts in the last two rows are candidates for review, not necessarily errors.", ""]
          + table(["Check", "Projects"], cons) + [""])
    meta = dict(q(con, "SELECT key, value FROM meta"))
    d.add(["## Versions", ""] + table(["Item", "Value"], [[k, v] for k, v in sorted(meta.items())]) + [""])
    return d


# ----------------------------------------------------------------- research report
def research_report(con) -> Doc:
    D = load(con)
    pids, asm, rub, tot, orig, terms = D["pids"], D["asm"], D["rub"], D["tot"], D["orig"], D["terms"]
    T = D["titles"]
    d = Doc("Exploratory Research Report: The AI Project Landscape")
    d.add(["> Exploratory, descriptive analysis of the enriched catalog. Rubric scores measure compliance with the "
           "presentation rubric, not holistic quality. Sophistication, tier, effort and originality are estimates from "
           "a documented framework (docs/methodology.md). Correlations are reported with bootstrap 95% CIs and "
           "uncorrected permutation p-values; none is confirmatory. Any figure used externally must be verified "
           "against the primary source first.", "", f"Projects analyzed: **{len(pids)}**.", ""])

    # 1. methods
    alg_c = Counter(a for p in pids for a in D["algs"][p])
    par_c = Counter(x for p in pids for x in terms[p]["paradigm"])
    task_c = Counter(x for p in pids for x in terms[p]["task"])
    mod_c = Counter(x for p in pids for x in terms[p]["modality"])
    d.add(["## 1. Distribution of ML methods", "", "### Most common algorithms (implemented, baseline or compared)", ""]
          + table(["Algorithm", "Projects", "%"], [[a, n, f"{100 * n / len(pids):.0f}%"] for a, n in alg_c.most_common(20)]) + [""]
          + ["### Paradigms", ""] + table(["Paradigm", "Projects"], par_c.most_common()) + [""]
          + ["### Data modalities", ""] + table(["Modality", "Projects"], mod_c.most_common()) + [""]
          + ["### Task types (top 15)", ""] + table(["Task", "Projects"], task_c.most_common(15)) + [""])
    sectors = Counter(D["prim"].get(p, "Unclassified") for p in pids)
    top_algs = [a for a, _ in alg_c.most_common(8)]
    rows = []
    for s, n in sectors.most_common():
        ps = [p for p in pids if D["prim"].get(p) == s]
        rows.append([s, n] + [f"{100 * sum(a in D['algs'][p] for p in ps) / len(ps):.0f}%" for a in top_algs])
    d.add(["### Algorithm use by primary industry (% of projects in the industry)", ""] + table(["Primary industry", "n"] + top_algs, rows) + [""])

    # 2. industries
    multi = Counter(x for p in pids for x in terms[p]["sector"])
    sub = Counter(x for p in pids for x in terms[p]["industry"] if x not in terms[p]["sector"])
    all_sectors = [r[0] for r in q(con, "SELECT label FROM taxonomy_terms WHERE dimension='industry' AND parent_id IS NULL")]
    under = sorted([s for s in all_sectors if multi.get(s, 0) <= 3], key=lambda s: multi.get(s, 0))
    st_vs = Counter((q(con, "SELECT student_project_type FROM projects WHERE project_id=?", p)[0][0] or "Not provided",
                     D["prim"].get(p, "Unclassified")) for p in pids)
    agree = sum(n for (a, b), n in st_vs.items() if a == b)
    disagree = sum(n for (a, b), n in st_vs.items() if a != b)
    te_share = sum(n for (a, b), n in st_vs.items() if a != b and a == "Technology & Engineering") / max(disagree, 1)
    d.add(["## 2. Industry patterns", "", "Projects can belong to several industries; counts are multi-label.", ""]
          + table(["Sector (multi-label)", "Projects"], multi.most_common()) + [""]
          + ["### Most common subdomains", ""] + table(["Subdomain", "Projects"], sub.most_common(15)) + [""]
          + [f"**Underexplored sectors** (≤3 projects): {', '.join(f'{s} ({multi.get(s, 0)})' for s in under)}.", "",
             f"**Student-selected type vs. independently inferred primary industry:** agree for {agree}/{len(pids)} "
             f"({100 * agree / len(pids):.0f}%). The student categories are coarse (5 options); "
             f"{100 * te_share:.0f}% of the disagreements are projects filed under *Technology & Engineering* whose "
             "primary application domain is more specific (most often Cybersecurity).", ""]
          + table(["Student type", "Inferred primary industry", "n"],
                  [[a, b, n] for (a, b), n in st_vs.most_common() if a != b][:12]) + [""])

    # 3. sophistication
    soph = {p: asm[p].get("sophistication.overall") for p in pids}
    def by_group(groups):
        rows = []
        for g, ps in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            v = [soph[p] for p in ps if soph[p] is not None]
            if len(v) >= 5:
                m, lo, hi = mean_ci(v)
                rows.append([g, len(v), f"{m:.1f}", f"[{lo:.1f}, {hi:.1f}]"])
        return rows
    gi = defaultdict(list)
    for p in pids:
        gi[D["prim"].get(p, "Unclassified")].append(p)
    gf = defaultdict(list)
    for p in pids:
        for f in D["fam"][p]:
            gf[f].append(p)
    gm = defaultdict(list)
    for p in pids:
        for m in terms[p]["modality"]:
            gm[m].append(p)
    tiers = Counter(asm[p].get("difficulty_tier.overall.label") for p in pids)
    eff = Counter(asm[p].get("reproduction_effort.overall.label") for p in pids)
    sv = [v for v in soph.values() if v is not None]
    d.add(["## 3. Technical sophistication", "",
           f"Sophistication (0–10): mean {np.mean(sv):.2f}, median {np.median(sv):.1f}, IQR {np.percentile(sv, 25):.1f}–{np.percentile(sv, 75):.1f}.", "",
           "### By primary industry (groups with ≥5 projects; bootstrap 95% CI)", ""] + table(["Industry", "n", "Mean", "95% CI"], by_group(gi))
          + ["", "### By algorithm family used", ""] + table(["Family", "n", "Mean", "95% CI"], by_group(gf))
          + ["", "### By data modality", ""] + table(["Modality", "n", "Mean", "95% CI"], by_group(gm))
          + ["", "### Difficulty tier and reproduction effort", ""] + table(["Tier", "n"], [[k, tiers[k]] for k in ["Beginner", "Intermediate", "Advanced"]])
          + [""] + table(["Reproduction effort", "n"], [[k, eff[k]] for k in ["Low", "Moderate", "High", "Very high"]]) + [""])
    comps = ["algorithmic_complexity", "data_processing", "methodological_breadth", "validation_rigor", "engineering", "mathematical_depth"]
    d.add(["### Sophistication components (mean, 0–3)", ""] + table(["Component", "Mean"],
          [[c, f"{np.mean([asm[p][f'sophistication.{c}'] for p in pids if f'sophistication.{c}' in asm[p]]):.2f}"] for c in comps]) + [""])

    # 4. originality
    io = {p: orig[p].get("internal.composite") for p in pids}
    top = sorted([p for p in pids if io[p] is not None], key=lambda p: -io[p])[:12]
    pat = Counter(orig[p].get("internal.composite.label") for p in pids)
    ext = Counter(orig[p].get("external.classification.label") or orig[p].get("external.classification") for p in pids)
    clu = defaultdict(list)
    for p, cid, lab in q(con, "SELECT project_id, cluster_id, cluster_label FROM clusters WHERE view='overall'"):
        clu[(cid, lab)].append(p)
    import pickle
    try:
        cache = pickle.load(open(paths.PROCESSED / "similarity_cache.pkl", "rb"))
        idx = {p: i for i, p in enumerate(cache["pids"])}
        Ssem = cache["sims"]["semantic"]
    except Exception:  # noqa: BLE001
        idx, Ssem = {}, None
    crow = []
    for (cid, lab), ps in sorted(clu.items(), key=lambda kv: -len(kv[1])):
        coh = ""
        if Ssem is not None and len(ps) > 1:
            ii = [idx[p] for p in ps if p in idx]
            sub_ = Ssem[np.ix_(ii, ii)]
            coh = f"{(sub_.sum() - np.trace(sub_)) / (len(ii) * (len(ii) - 1)):.2f}"
        crow.append([cid, lab, len(ps), coh])
    import networkx as nx
    G = nx.Graph()
    G.add_nodes_from(pids)
    for s, t, w in q(con, "SELECT source, target, weight FROM similarity_edges WHERE view='overall'"):
        G.add_edge(s, t, weight=w, distance=1 - w)
    cl_of = {p: cid for (cid, _), ps in clu.items() for p in ps}
    btw = nx.betweenness_centrality(G, weight="distance")
    bridges = []
    for p in sorted(btw, key=lambda x: -btw[x])[:20]:
        nb_clusters = {cl_of.get(n) for n in G.neighbors(p)} - {cl_of.get(p)}
        if nb_clusters:
            bridges.append((p, btw[p], len(nb_clusters)))
    stats = json.loads(dict(q(con, "SELECT key, value FROM meta")).get("cluster_stats", "{}"))
    pub_top = table(["Project", "Internal originality (pctl)", "Pattern"], [[p, f"{io[p]:.0f}", orig[p].get("internal.composite.label")] for p in top])
    prv_top = table(["Project", "Title", "Internal originality (pctl)", "Pattern"], [[p, T[p], f"{io[p]:.0f}", orig[p].get("internal.composite.label")] for p in top])
    pub_br = table(["Project", "Betweenness", "Other clusters linked"], [[p, f"{b:.3f}", k] for p, b, k in bridges[:10]])
    prv_br = table(["Project", "Title", "Betweenness", "Other clusters linked"], [[p, T[p], f"{b:.3f}", k] for p, b, k in bridges[:10]])
    head = ["## 4. Originality landscape", "",
            "Internal originality is a percentile within this collection (semantic isolation, algorithm rarity, domain "
            "rarity, method–domain combination rarity). External originality is a separate, search-based judgement.", "",
            "### Most distinctive within the collection", ""]
    d.add(head + pub_top, head + prv_top)
    d.add(["", "### Internal originality patterns", ""] + table(["Pattern", "Projects"], pat.most_common()) + ["",
           "### External originality (precedent search)", "", "Absence of found precedents is not proof of novelty.", ""]
          + table(["Classification", "Projects"], [[k or "not researched", n] for k, n in ext.most_common()]) + ["",
           "### Clusters", "",
           f"Method: {stats.get('method')}. k = {stats.get('k')}; silhouette {stats.get('silhouette_reduced')} in the "
           f"reduced space (optimistic) and {stats.get('silhouette_original_space')} in the original space (conservative); "
           f"bootstrap ARI {stats.get('bootstrap_ari_mean')} ± {stats.get('bootstrap_ari_sd')}; UMAP-seed ARI "
           f"{stats.get('seed_ari_mean')}. Clusters are stable but overlapping: boundaries are soft. Cohesion = mean "
           "pairwise semantic similarity within the cluster (higher = more alike).", ""]
          + table(["Cluster", "Label (most over-represented terms)", "n", "Cohesion"], crow) + ["",
           "### Bridge projects (connect otherwise separate regions)", ""])
    d.add(pub_br + [""], prv_br + [""])

    # 5. rubric relationships
    metrics = {"Technical sophistication": soph,
               "Internal originality": io,
               "Difficulty tier (1-3)": {p: asm[p].get("difficulty_tier.overall") for p in pids},
               "Reproduction effort (0-15)": {p: asm[p].get("reproduction_effort.overall") for p in pids}}
    rows = []
    for name, m in metrics.items():
        for target in ["Rubric total"] + CRITERIA:
            ps = [p for p in pids if isinstance(m.get(p), (int, float)) and (tot.get(p) if target == "Rubric total" else rub[p].get(target)) is not None]
            x = [m[p] for p in ps]
            y = [tot[p] if target == "Rubric total" else rub[p][target] for p in ps]
            rho, lo, hi, pv = spearman_ci(x, y, 1000, 1000)
            rows.append([name, target, len(ps), f"{rho:+.2f}", f"[{lo:+.2f}, {hi:+.2f}]", f"{pv:.3f}"])
    crit_var = []
    for c in CRITERIA:
        groups = defaultdict(list)
        for p in pids:
            for f in D["fam"][p]:
                groups[f].append(rub[p][c])
        means = [np.mean(v) for v in groups.values() if len(v) >= 8]
        crit_var.append([c, f"{np.std([rub[p][c] for p in pids]):.2f}", f"{max(means) - min(means):.2f}" if means else "—"])
    d.add(["## 5. Rubric relationships (exploratory)", "",
           "Spearman correlations between newly derived characteristics and the original rubric scores. "
           f"{len(rows)} comparisons, no multiple-comparison correction: treat p < 0.05 as a lead, not a finding.", "",
           "**Shared-source caveat.** Both the rubric and the derived ratings are read from the same slide decks. A deck "
           "that explains its pipeline well earns rubric points *and* exposes more demonstrable sophistication, so a "
           "positive correlation partly reflects documentation quality rather than an independent link between "
           "technical depth and grading. Disentangling the two would require code-level evidence.", ""]
          + table(["Derived metric", "Rubric score", "n", "rho", "95% CI", "perm. p"], rows) + ["",
          "### Which rubric criteria vary most across technical approaches?", "",
          "SD across all projects, and the spread (max − min) of criterion means across algorithm families with ≥8 projects.", ""]
          + table(["Criterion", "SD overall", "Spread of family means"], crit_var) + [""])

    # 6. datasets
    used_ok = {p for p, in q(con, "SELECT DISTINCT project_id FROM project_datasets WHERE relationship='used' AND match_level IN ('exact','probable')")}
    alt_only = {p for p, in q(con, "SELECT DISTINCT project_id FROM project_datasets WHERE relationship='alternative'")} - used_ok
    researched = {p for p, in q(con, "SELECT project_id FROM projects WHERE processing_status='researched'")}
    plat = q(con, """SELECT COALESCE(d.platform,'?'), COUNT(DISTINCT pd.project_id) FROM project_datasets pd JOIN datasets d USING(dataset_id)
                     WHERE pd.relationship='used' AND pd.match_level IN ('exact','probable') GROUP BY 1 ORDER BY 2 DESC LIMIT 12""")
    rows = []
    for s, ps in sorted(gi.items(), key=lambda kv: -len(kv[1])):
        r = [p for p in ps if p in researched]
        if r:
            rows.append([s, len(r), f"{100 * sum(p in used_ok for p in r) / len(r):.0f}%"])
    d.add(["## 6. Dataset accessibility", "", f"Researched projects: {len(researched)}/{len(pids)}.", "",
           f"- Original dataset identified as a public resource (exact/probable): **{len(used_ok)}** projects",
           f"- Only an alternative/substitute dataset available: **{len(alt_only)}** projects",
           f"- Neither: **{len(researched - used_ok - alt_only)}** researched projects", "",
           "### Hosting platforms of identified datasets", ""] + table(["Platform", "Projects"], plat)
          + ["", "### Share of projects with an identified public dataset, by primary industry", ""]
          + table(["Industry", "Researched", "Identified"], rows) + [""])

    # 7. reproducibility sweet spot
    sweet = [p for p in pids if asm[p].get("reproduction_effort.overall.label") in ("Low", "Moderate")
             and (asm[p].get("adoption_readiness.overall") or 0) >= 5 and p in used_ok]
    sw_ind = Counter(D["prim"].get(p) for p in sweet)
    sw_tier = Counter(asm[p].get("difficulty_tier.overall.label") for p in sweet)
    best = sorted(sweet, key=lambda p: -((io[p] or 0) / 100 + (soph[p] or 0) / 10))[:12]
    head = ["## 7. Reproducibility landscape", "",
            f"'Sweet spot' = Low/Moderate reproduction effort, readiness ≥5/7, and an identified public dataset: "
            f"**{len(sweet)}** projects.", ""] + table(["Industry", "Sweet-spot projects"], sw_ind.most_common()) + [""] + \
        table(["Tier", "n"], sw_tier.most_common()) + ["", "### Most interesting sweet-spot projects (originality + sophistication)", ""]
    d.add(head + table(["Project", "Tier", "Effort", "Originality", "Sophistication"],
                       [[p, asm[p].get("difficulty_tier.overall.label"), asm[p].get("reproduction_effort.overall.label"),
                         f"{io[p]:.0f}" if io[p] is not None else "—", soph[p]] for p in best]) + [""],
          head + table(["Project", "Title", "Tier", "Effort", "Originality", "Sophistication"],
                       [[p, T[p], asm[p].get("difficulty_tier.overall.label"), asm[p].get("reproduction_effort.overall.label"),
                         f"{io[p]:.0f}" if io[p] is not None else "—", soph[p]] for p in best]) + [""])
    d.add(["## Limitations", "",
           "- Extraction is LLM-based; every confirmed tag is grounded by a verified quote, but ratings (sophistication, "
           "prerequisites, effort) are judgements against written anchors and have not yet been double-coded by humans.",
           "- Presentations, not code, were analyzed: what a slide deck shows is a lower bound on what was built.",
           "- Several extractors flagged internally inconsistent metrics or likely leakage in student results; these are "
           "in the review queue and reported metrics are recorded as reported, not validated.",
           "- External originality rests on a small number of web searches per project and is low-confidence by design.",
           "- Correlations are exploratory, uncorrected, and cannot support causal claims.", ""])
    return d


def main():
    con = sqlite3.connect(paths.DB_PATH)
    paths.REPORTS.mkdir(exist_ok=True)
    for name, fn in [("qa_report", qa_report), ("research_report", research_report)]:
        doc = fn(con)
        (paths.REPORTS / f"{name}.md").write_text("\n".join(doc.pub) + "\n")
        (paths.PROCESSED / f"{name}_private.md").write_text("\n".join(doc.priv) + "\n")
        print(f"wrote reports/{name}.md and data/processed/{name}_private.md")


if __name__ == "__main__":
    main()
