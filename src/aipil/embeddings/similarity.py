"""Project representations, multi-view similarity graph, clustering and 3D layout.

Views (each a separate, explainable notion of relatedness):
  semantic   - sentence embedding of title + summaries + research question
  algorithm  - implemented/compared algorithms (weighted by inverse frequency) + algorithm families
  industry   - hierarchical industry tags (subdomain match > sector match)
  technical  - tasks, modalities, paradigms, methods
  dataset    - shared datasets (exact/probable matches only)
  skills     - prerequisite profile + difficulty + reproduction components
  overall    - weighted blend of the above (weights in config/similarity.yaml)

Graphs are sparse: each project keeps its top-k neighbors per view above a threshold
(union of directed kNN), which avoids an everything-connected hairball while preserving
cross-cluster bridges.
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict

import numpy as np
import yaml

from aipil import paths

ALG_ROLES = ("implemented", "baseline", "compared")


def _cfg():
    return yaml.safe_load((paths.CONFIG / "similarity.yaml").read_text())


# ------------------------------------------------------------------ data access
def load_features(con: sqlite3.Connection) -> dict:
    pids = [r[0] for r in con.execute(
        "SELECT p.project_id FROM projects p JOIN project_profiles pp USING(project_id) ORDER BY p.project_id")]
    feats = {p: defaultdict(set) for p in pids}
    for pid, tid, dim in con.execute("SELECT project_id, term_id, dimension FROM project_terms "
                                     "WHERE evidence_level != 'unknown'"):
        if pid in feats:
            feats[pid][dim].add(tid)
    fam = {r[0]: json.loads(r[1] or "{}").get("family") for r in
           con.execute("SELECT term_id, attributes FROM taxonomy_terms WHERE dimension='algorithm'")}
    for pid, tid, role in con.execute("SELECT project_id, term_id, role FROM project_algorithms"):
        if pid in feats and role in ALG_ROLES:
            feats[pid]["algorithm"].add(tid)
            if fam.get(tid):
                feats[pid]["algorithm_family"].add(f"family:{fam[tid]}")
    for pid, did in con.execute("SELECT project_id, dataset_id FROM project_datasets "
                                "WHERE relationship='used' AND match_level IN ('exact','probable')"):
        if pid in feats:
            feats[pid]["dataset"].add(did)
    texts = {}
    for pid, title, plain, tech, rq in con.execute(
            "SELECT p.project_id, COALESCE(p.student_title, p.title_slide), pp.plain_summary, pp.technical_summary, "
            "pp.research_question FROM projects p JOIN project_profiles pp USING(project_id)"):
        texts[pid] = " ".join(x for x in [title, rq, plain, tech] if x)
    skills = {}
    for pid, comp, v in con.execute("SELECT project_id, construct||'.'||component, value_num FROM assessments "
                                    "WHERE construct IN ('prerequisites','reproduction_effort','difficulty_tier') "
                                    "AND value_num IS NOT NULL AND component != 'overall' OR "
                                    "(construct='difficulty_tier' AND component='overall')"):
        skills.setdefault(pid, {})[comp] = v
    labels = {r[0]: r[1] for r in con.execute("SELECT term_id, label FROM taxonomy_terms")}
    return dict(pids=pids, feats=feats, texts=texts, skills=skills, labels=labels)


# ------------------------------------------------------------------ embeddings
def embed_texts(texts: list[str]) -> tuple[np.ndarray, str]:
    """Sentence-transformer embeddings when available; otherwise TF-IDF + LSA (documented fallback)."""
    model_name = _cfg()["semantic_model"]
    try:
        from sentence_transformers import SentenceTransformer
        m = SentenceTransformer(model_name)
        X = m.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(X, dtype=np.float32), model_name
    except Exception:  # noqa: BLE001
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer
        tf = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=2, sublinear_tf=True)
        T = tf.fit_transform(texts)
        k = min(100, T.shape[1] - 1, T.shape[0] - 1)
        X = TruncatedSVD(k, random_state=0).fit_transform(T)
        X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
        return X.astype(np.float32), f"tfidf-lsa-{k}"


def _set_matrix(pids, feats, dims, idf=True):
    vocab = sorted({t for p in pids for d in dims for t in feats[p][d]})
    idx = {t: i for i, t in enumerate(vocab)}
    M = np.zeros((len(pids), len(vocab)), dtype=np.float32)
    for i, p in enumerate(pids):
        for d in dims:
            for t in feats[p][d]:
                M[i, idx[t]] = 1.0
    if idf and len(vocab):
        df = M.sum(0)
        M *= np.log((1 + len(pids)) / (1 + df)) + 1
    n = np.linalg.norm(M, axis=1, keepdims=True)
    return M / np.where(n == 0, 1, n), vocab


def view_matrices(F: dict) -> dict[str, tuple[np.ndarray, str]]:
    pids, feats = F["pids"], F["feats"]
    X_sem, model = embed_texts([F["texts"].get(p, "") for p in pids])
    out = {"semantic": (X_sem, model)}
    out["algorithm"] = (_set_matrix(pids, feats, ["algorithm", "algorithm_family"])[0], "idf-weighted sets")
    out["industry"] = (_set_matrix(pids, feats, ["industry"])[0], "idf-weighted hierarchical tags")
    out["technical"] = (_set_matrix(pids, feats, ["task", "modality", "paradigm", "method"])[0], "idf-weighted sets")
    out["dataset"] = (_set_matrix(pids, feats, ["dataset"])[0], "shared datasets")
    keys = sorted({k for v in F["skills"].values() for k in v})
    S = np.array([[F["skills"].get(p, {}).get(k, 0) for k in keys] for p in pids], dtype=np.float32)
    if S.size:
        S = (S - S.mean(0)) / (S.std(0) + 1e-6)
        S /= np.linalg.norm(S, axis=1, keepdims=True) + 1e-9
    out["skills"] = (S, "standardized prerequisite/effort profile")
    return out


def cosine(X):
    return np.clip(X @ X.T, -1, 1)


# ------------------------------------------------------------------ graph
def explain(a: str, b: str, F: dict, view: str) -> tuple[str, dict]:
    fa, fb, L = F["feats"][a], F["feats"][b], F["labels"]

    def shared(dim):
        return sorted(L.get(t, t) for t in fa[dim] & fb[dim])

    def only(dim, f1, f2):
        return sorted(L.get(t, t) for t in f1[dim] - f2[dim])
    sh = {d: shared(d) for d in ["algorithm", "task", "modality", "paradigm", "industry", "dataset", "method"]}
    sh = {k: v for k, v in sh.items() if v}
    parts = []
    if sh.get("algorithm"):
        parts.append("both use " + ", ".join(sh["algorithm"][:3]))
    if sh.get("task"):
        parts.append("share the task " + ", ".join(sh["task"][:2]))
    if sh.get("modality") and not parts:
        parts.append("work with " + ", ".join(sh["modality"][:2]) + " data")
    if sh.get("dataset"):
        parts.append("use the same dataset")
    ia = [L.get(t, t) for t in fa["industry"] if "." in t] or [L.get(t, t) for t in fa["industry"]]
    ib = [L.get(t, t) for t in fb["industry"] if "." in t] or [L.get(t, t) for t in fb["industry"]]
    if sh.get("industry"):
        parts.append("are both in " + ", ".join([x for x in sh["industry"] if x in ia or x in ib][:1] or sh["industry"][:1]))
    elif ia and ib:
        parts.append(f"but one focuses on {ia[0]} and the other on {ib[0]}")
    if view == "semantic" and not sh.get("algorithm"):
        oa, ob = only("algorithm", fa, fb), only("algorithm", fb, fa)
        if oa and ob:
            parts.append(f"approach it differently ({oa[0]} vs {ob[0]})")
    if view == "semantic":
        lead = "Similar project descriptions"
    elif view == "skills":
        lead = "Similar prerequisite and effort profile"
    else:
        lead = f"Related by {view}"
    text = lead + (": these projects " + "; ".join(parts) if parts else "") + "."
    return text, sh


def build_edges(F: dict, views: dict, cfg: dict) -> list[tuple]:
    pids = F["pids"]
    n = len(pids)
    edges = []
    sims = {}
    for view, (X, _) in views.items():
        if X.size == 0 or not np.any(X):
            continue
        sims[view] = cosine(X)
    w = cfg["overall_weights"]
    tot = sum(w[v] for v in sims if v in w)
    sims["overall"] = sum(sims[v] * w[v] for v in sims if v in w) / tot
    for view, S in sims.items():
        k = cfg["k"].get(view, cfg["k"]["default"])
        thr = cfg["threshold"].get(view, cfg["threshold"]["default"])
        S = S.copy()
        np.fill_diagonal(S, -1)
        keep = set()
        for i in range(n):
            order = np.argsort(-S[i])[:k]
            for rank, j in enumerate(order):
                if S[i, j] >= thr:
                    keep.add((min(i, j), max(i, j)))
        for i, j in keep:
            text, sh = explain(pids[i], pids[j], F, view)
            r_i = int((S[i] > S[i, j]).sum()) + 1
            edges.append((pids[i], pids[j], view, float(round(S[i, j], 4)), r_i, text, json.dumps(sh)))
    return edges, sims


# ------------------------------------------------------------------ clusters
def cluster(X: np.ndarray, kmin=6, kmax=14, seed=0):
    """Cluster in a 10-d UMAP reduction (Ward), choosing k by silhouette x bootstrap stability.

    Diagnostics are reported honestly: silhouette in the reduced space (optimistic), silhouette of the same labels in
    the original blended space (conservative), bootstrap ARI (resampling stability) and seed ARI (stability of the
    whole pipeline across UMAP random seeds)."""
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.metrics import adjusted_rand_score, silhouette_score
    import umap

    def reduce(rs):
        return umap.UMAP(n_components=10, n_neighbors=15, min_dist=0.0, metric="cosine", random_state=rs).fit_transform(X)

    Z = reduce(seed)
    rng = np.random.default_rng(seed)
    best = None
    for k in range(kmin, min(kmax, len(X) - 1) + 1):
        lab = AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(Z)
        sil = silhouette_score(Z, lab)
        aris = []
        for _ in range(15):
            idx = rng.choice(len(Z), int(0.8 * len(Z)), replace=False)
            aris.append(adjusted_rand_score(lab[idx], AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(Z[idx])))
        score = sil * float(np.mean(aris))
        if best is None or score > best[0]:
            best = (score, k, lab, sil, aris)
    _, k, lab, sil, aris = best
    seed_aris = [adjusted_rand_score(lab, AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(reduce(rs)))
                 for rs in (1, 2, 3)]
    return lab, {"method": "UMAP(10d, cosine) + Ward; k by silhouette x bootstrap ARI", "k": int(k),
                 "silhouette_reduced": float(round(sil, 4)),
                 "silhouette_original_space": float(round(silhouette_score(X, lab, metric="cosine"), 4)),
                 "bootstrap_ari_mean": float(round(np.mean(aris), 3)), "bootstrap_ari_sd": float(round(np.std(aris), 3)),
                 "seed_ari_mean": float(round(np.mean(seed_aris), 3))}


def label_clusters(lab, F) -> dict[int, str]:
    """Interpretable labels: the most over-represented taxonomy terms in each cluster (lift x support)."""
    pids, feats, L = F["pids"], F["feats"], F["labels"]
    dims = ["industry", "task", "algorithm", "modality"]
    glob = Counter(t for p in pids for d in dims for t in feats[p][d])
    out = {}
    for c in sorted(set(lab)):
        members = [p for p, l in zip(pids, lab) if l == c]
        cnt = Counter(t for p in members for d in dims for t in feats[p][d])
        scored = []
        for t, n in cnt.items():
            support = n / len(members)
            lift = support / (glob[t] / len(pids))
            if support >= 0.3:
                scored.append((support * np.log1p(lift), t))
        scored.sort(reverse=True)
        picks, seen_dims = [], set()
        for _, t in scored:
            d = t.split(":")[0]
            if d in seen_dims and len(picks) >= 2:
                continue
            picks.append(L.get(t, t))
            seen_dims.add(d)
            if len(picks) == 3:
                break
        out[int(c)] = " · ".join(picks) if picks else f"Cluster {c}"
    return out


def layout_3d(X: np.ndarray, seed=0) -> np.ndarray:
    try:
        import umap
        Y = umap.UMAP(n_components=3, n_neighbors=12, min_dist=0.35, metric="cosine", random_state=seed).fit_transform(X)
    except Exception:  # noqa: BLE001
        from sklearn.manifold import TSNE
        Y = TSNE(3, metric="cosine", random_state=seed, init="random", perplexity=15).fit_transform(X)
    Y = Y - Y.mean(0)
    return Y / (np.abs(Y).max() + 1e-9) * 100


# ------------------------------------------------------------------ internal originality
def internal_originality(F: dict, sims: dict) -> dict[str, dict]:
    pids, feats = F["pids"], F["feats"]
    n = len(pids)

    def pct(vals):
        order = np.argsort(np.argsort(vals))
        return (order / max(1, n - 1) * 100).round(1)

    S = sims["semantic"].copy()
    np.fill_diagonal(S, -1)
    k = 5
    isolation = 1 - np.sort(S, axis=1)[:, -k:].mean(1)

    def rarity(dim, leaf_only=False):
        c = Counter(t for p in pids for t in feats[p][dim] if not leaf_only or "." in t or dim != "industry")
        vals = []
        for p in pids:
            ts = [t for t in feats[p][dim] if not leaf_only or "." in t or dim != "industry"]
            vals.append(max((np.log(n / c[t]) for t in ts), default=0.0))
        return np.array(vals)

    alg_r = rarity("algorithm")
    dom_r = rarity("industry", leaf_only=True)
    # combination rarity: task x industry-sector and algorithm x industry-sector pairs
    def sector(t):
        return t.split(":")[1].split(".")[0]
    combos = {p: {(a, sector(i)) for a in feats[p]["algorithm"] for i in feats[p]["industry"]} |
                 {(t, sector(i)) for t in feats[p]["task"] for i in feats[p]["industry"]} for p in pids}
    cc = Counter(c for p in pids for c in combos[p])
    combo_r = np.array([np.mean(sorted((np.log(n / cc[c]) for c in combos[p]), reverse=True)[:3]) if combos[p] else 0
                        for p in pids])
    ds_c = Counter(d for p in pids for d in feats[p]["dataset"])
    data_r = np.array([np.mean([1.0 if ds_c[d] == 1 else 0.0 for d in feats[p]["dataset"]]) if feats[p]["dataset"]
                       else np.nan for p in pids])
    comps = {"semantic_isolation": pct(isolation), "algorithm_rarity": pct(alg_r), "domain_rarity": pct(dom_r),
             "combination_rarity": pct(combo_r)}
    out = {}
    for i, p in enumerate(pids):
        c = {k: float(v[i]) for k, v in comps.items()}
        composite = round(float(np.mean(list(c.values()))), 1)
        if c["algorithm_rarity"] < 50 and c["domain_rarity"] >= 75:
            pattern = "common methods in an unusual application"
        elif c["algorithm_rarity"] >= 75 and c["domain_rarity"] < 50:
            pattern = "unusual methods for a familiar problem area"
        elif c["combination_rarity"] >= 80:
            pattern = "uncommon combination of method and domain"
        elif composite < 35:
            pattern = "well-trodden within this collection"
        else:
            pattern = "moderately distinctive"
        out[p] = dict(components=c, composite=composite, pattern=pattern,
                      raw=dict(isolation=float(round(isolation[i], 4)),
                               unique_dataset_share=None if np.isnan(data_r[i]) else float(data_r[i])))
    return out


# ------------------------------------------------------------------ orchestration
def run():
    import pickle
    cfg = _cfg()
    con = sqlite3.connect(paths.DB_PATH)
    F = load_features(con)
    if len(F["pids"]) < 10:
        print("not enough extracted projects for similarity")
        return
    views = view_matrices(F)
    edges, sims = build_edges(F, views, cfg)
    for t in ["embeddings", "similarity_edges", "clusters"]:
        con.execute(f"DELETE FROM {t}")
    con.execute("DELETE FROM originality WHERE scope='internal'")
    for view, (X, model) in views.items():
        for p, v in zip(F["pids"], X):
            con.execute("INSERT INTO embeddings VALUES (?,?,?,?,?)", (p, view, model, int(X.shape[1]),
                                                                      np.asarray(v, np.float32).tobytes()))
    con.executemany("INSERT OR REPLACE INTO similarity_edges VALUES (?,?,?,?,?,?,?)", edges)
    # clusters on a combined representation (semantic + technical + algorithm + industry)
    blend = np.hstack([views[v][0] * np.sqrt(cfg["cluster_weights"][v]) for v in cfg["cluster_weights"]])
    lab, cstats = cluster(blend, cfg["clusters"]["kmin"], cfg["clusters"]["kmax"])
    names = label_clusters(lab, F)
    xyz = layout_3d(blend)
    for p, l, (x, y, z) in zip(F["pids"], lab, xyz):
        con.execute("INSERT INTO clusters VALUES (?,?,?,?,?,?,?)", (p, "overall", int(l), names[int(l)],
                                                                    float(x), float(y), float(z)))
    orig = internal_originality(F, sims)
    for p, o in orig.items():
        for k, v in o["components"].items():
            con.execute("INSERT INTO originality VALUES (?,?,?,?,?,?,?,?)",
                        (p, "internal", k, v, None, "percentile within collection (0 = most common, 100 = most unusual)",
                         "medium", "computed"))
        con.execute("INSERT INTO originality VALUES (?,?,?,?,?,?,?,?)",
                    (p, "internal", "composite", o["composite"], o["pattern"],
                     json.dumps(o["raw"]), "medium", "mean of component percentiles"))
    con.execute("INSERT OR REPLACE INTO meta VALUES ('cluster_stats', ?)", (json.dumps(cstats),))
    con.execute("INSERT OR REPLACE INTO meta VALUES ('semantic_model', ?)", (views["semantic"][1],))
    con.commit()
    cnt = Counter(e[2] for e in edges)
    print("edges per view:", dict(cnt), "| clusters:", cstats, "| semantic model:", views["semantic"][1])
    with open(paths.PROCESSED / "similarity_cache.pkl", "wb") as fh:
        pickle.dump({"pids": F["pids"], "sims": sims}, fh)


if __name__ == "__main__":
    run()
