"""Inter-coder agreement between the primary extraction and a blind second coding of a random sample.

The second coder (a different model, no access to primary outputs) records core facts for a random sample.
We report per-field agreement: Jaccard for multi-label sets, exact agreement for the primary sector, and exact /
within-one agreement plus weighted kappa for ordinal prerequisite ratings. Output: reports/agreement_report.md.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np

from aipil import paths
from aipil.extraction.schema import taxonomy

USED = {"implemented", "baseline", "compared"}


def _norm(dim: str, slug: str) -> str:
    alias = (taxonomy().get("aliases") or {}).get(f"{dim}:{slug}")
    return alias.split(":", 1)[1] if alias else slug


def jaccard(a: set, b: set) -> float:
    return 1.0 if not a and not b else len(a & b) / len(a | b)


def weighted_kappa(x, y, k=3):
    x, y = np.asarray(x) - 1, np.asarray(y) - 1
    O = np.zeros((k, k))
    for i, j in zip(x, y):
        O[i, j] += 1
    W = np.array([[(i - j) ** 2 / (k - 1) ** 2 for j in range(k)] for i in range(k)])
    E = np.outer(O.sum(1), O.sum(0)) / O.sum()
    return 1 - (W * O).sum() / max((W * E).sum(), 1e-9)


def run():
    qdir = paths.PRIVATE / "qa" / "blind"
    rows, per = [], {k: [] for k in ["algorithms_used", "algorithms_implemented", "primary_sector", "industries",
                                     "paradigms", "tasks", "modalities"]}
    pre = {k: ([], []) for k in ["python", "math_stats", "ml"]}
    pre_det = ([], [])
    from aipil.classification.assess import python_level
    for f in sorted(qdir.glob("project-*.json")):
        pid = f.stem
        b = json.loads(f.read_text())
        a = json.loads((paths.EXTRACTIONS / f"{pid}.json").read_text())
        A_used = {_norm("algorithm", x["canonical"]) for x in a["algorithms"] if x["role"] in USED}
        B_used = {_norm("algorithm", x["canonical"]) for x in b["algorithms"] if x["role"] in USED}
        A_imp = {_norm("algorithm", x["canonical"]) for x in a["algorithms"] if x["role"] == "implemented"}
        B_imp = {_norm("algorithm", x["canonical"]) for x in b["algorithms"] if x["role"] == "implemented"}
        per["algorithms_used"].append(jaccard(A_used, B_used))
        per["algorithms_implemented"].append(jaccard(A_imp, B_imp))
        prim = next((t["term"] for t in a["industries"] if t.get("primary")), "")
        prim = _norm("industry", prim).split(".")[0]
        per["primary_sector"].append(float(prim == str(b.get("primary_sector", "")).split(".")[0]))
        A_ind = {_norm("industry", t["term"]) for t in a["industries"]}
        A_ind |= {x.split(".")[0] for x in A_ind}
        B_ind = set(b.get("industries", [])) | {x.split(".")[0] for x in b.get("industries", [])}
        per["industries"].append(jaccard({x.split('.')[0] for x in A_ind}, {x.split('.')[0] for x in B_ind}))
        for key, dim in [("paradigms", "paradigm"), ("tasks", "task"), ("modalities", "modality")]:
            A = {_norm(dim, t["term"]) for t in a[key]}
            B = set(b.get(key, []))
            if dim == "task":  # compare at parent level for classification sub-types
                A = {"classification" if x.endswith("_classification") and x not in {"image_classification", "text_classification", "audio_classification"} else x for x in A}
                B = {"classification" if x.endswith("_classification") and x not in {"image_classification", "text_classification", "audio_classification"} else x for x in B}
            per[key].append(jaccard(A, B))
        if "python" in b.get("prerequisites", {}):
            pre_det[0].append(python_level(a)[0])
            pre_det[1].append(int(b["prerequisites"]["python"]))
        for k in pre:
            if k in a["prerequisites"] and k in b.get("prerequisites", {}):
                pre[k][0].append(a["prerequisites"][k]["score"])
                pre[k][1].append(int(b["prerequisites"][k]))
        rows.append([pid, f"{per['algorithms_used'][-1]:.2f}", f"{per['primary_sector'][-1]:.0f}",
                     ", ".join(sorted(A_used ^ B_used)) or "—"])
    n = len(rows)
    out = ["# Inter-coder Agreement (blind second coding)", "",
           f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}", "",
           f"Random sample of **{n}** projects (seed 42) re-coded blind by a second model with no access to the primary "
           "extraction. Taxonomy aliases applied to both. Values are means across projects.", "",
           "| Field | Agreement | Metric |", "|---|---|---|"]
    for k, v in per.items():
        if v:
            out.append(f"| {k} | {np.mean(v):.2f} | {'exact match rate' if k == 'primary_sector' else 'mean Jaccard'} |")
    for k, (x, y) in pre.items():
        if x:
            ex = np.mean(np.array(x) == np.array(y))
            w1 = np.mean(np.abs(np.array(x) - np.array(y)) <= 1)
            name = "prerequisite: python (original reader rating)" if k == "python" else f"prerequisite: {k}"
            out.append(f"| {name} | exact {ex:.2f}, within-1 {w1:.2f}, weighted κ {weighted_kappa(x, y):.2f} | ordinal 1–3 |")
    if pre_det[0]:
        x, y = pre_det
        ex = np.mean(np.array(x) == np.array(y)); w1 = np.mean(np.abs(np.array(x) - np.array(y)) <= 1)
        out.append(f"| prerequisite: python (criteria-based, used in catalog) | exact {ex:.2f}, within-1 {w1:.2f}, "
                   f"weighted κ {weighted_kappa(x, y):.2f} | ordinal 1–3 |")
    out += ["", "## Per-project algorithm agreement", "", "| Project | Jaccard (used algorithms) | Primary sector agrees | Disagreeing algorithms |",
            "|---|---|---|---|"] + ["| " + " | ".join(r) + " |" for r in rows]
    out += ["", "Interpretation: disagreements are inspected manually; typical sources are (a) whether a model shown only "
            "as a comparison counts as used, (b) generic vs. specific slugs (e.g. CNN vs. ResNet), and (c) subjective "
            "ordinal ratings. Agreement figures bound the reliability of the corresponding catalog fields.", ""]
    (paths.REPORTS / "agreement_report.md").write_text("\n".join(out))
    print("\n".join(out[:20]))


if __name__ == "__main__":
    run()
