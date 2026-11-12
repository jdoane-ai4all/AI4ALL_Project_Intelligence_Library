import { useMemo, useState } from "react";
import type { Project } from "../types";
import { algorithmsUsed, CRITERIA, datasetAvailability, effort, externalOriginality, internalOriginality, labels, primaryIndustry, readiness, sophistication, tier } from "../logic";
import { Badge, Meter } from "./ui";

const SORTS: Record<string, [string, (p: Project) => number | string]> = {
  relevance: ["Relevance", () => 0],
  title: ["Title", (p) => p.title.toLowerCase()],
  soph: ["Technical sophistication", (p) => -(sophistication(p) ?? -1)],
  orig: ["Internal originality", (p) => -(internalOriginality(p) ?? -1)],
  rubric: ["Rubric total", (p) => -p.rubric.total],
  effort: ["Lowest reproduction effort", (p) => p.assessments.reproduction_effort?.overall?.value ?? 99],
  ready: ["Adoption readiness", (p) => -(readiness(p) ?? -1)],
  id: ["Project ID", (p) => p.id],
};

export default function Explorer({ projects, onSelect, scores }: { projects: Project[]; onSelect: (id: string) => void; scores: Map<string, number> | null }) {
  const [sort, setSort] = useState("relevance");
  const [mode, setMode] = useState<"grid" | "table">("grid");
  const [compare, setCompare] = useState<string[]>([]);
  // Relevance = search score when a query is typed; without a query it falls back to sophistication.
  const key = (p: Project): number | string =>
    sort === "relevance" ? (scores ? -(scores.get(p.id) ?? 0) : -(sophistication(p) ?? -1)) : SORTS[sort][1](p);
  const sorted = useMemo(() => [...projects].sort((a, b) => {
    const x = key(a), y = key(b); return x < y ? -1 : x > y ? 1 : 0;
  }), [projects, sort, scores]);
  const toggleCmp = (id: string) => setCompare((c) => (c.includes(id) ? c.filter((x) => x !== id) : c.length >= 4 ? c : [...c, id]));
  const cmp = compare.map((id) => projects.find((p) => p.id === id)).filter(Boolean) as Project[];

  return (
    <div className="explorer">
      <div className="toolbar">
        <span className="muted">{projects.length} projects{sort === "relevance" && !scores ? " · type in the search box to rank by relevance" : ""}</span>
        <label>Sort <select value={sort} onChange={(e) => setSort(e.target.value)}>{Object.entries(SORTS).map(([k, [l]]) => <option key={k} value={k}>{l}</option>)}</select></label>
        <div className="seg"><button className={mode === "grid" ? "on" : ""} onClick={() => setMode("grid")}>Cards</button><button className={mode === "table" ? "on" : ""} onClick={() => setMode("table")}>Table</button></div>
        {compare.length > 0 && <span className="muted">Comparing {compare.length}/4 <button className="link" onClick={() => setCompare([])}>clear</button></span>}
      </div>
      {cmp.length >= 2 && <Compare ps={cmp} onSelect={onSelect} />}
      {mode === "grid" ? (
        <div className="grid">
          {sorted.map((p) => (
            <article key={p.id} className="card" tabIndex={0} onClick={() => onSelect(p.id)} onKeyDown={(e) => e.key === "Enter" && onSelect(p.id)}>
              <div className="card-top">
                <span className="pid">{p.id}</span>
                <span className="row">{p.recommendation?.status !== "ok" && <span className={`rflag rf-${p.recommendation.status}`} title={p.recommendation.reason ?? ""}>{p.recommendation.status === "hold" ? "⚠ withheld" : "caution"}</span>}
                <Badge kind={tier(p) ?? ""}>{tier(p) ?? "—"}</Badge></span>
              </div>
              <h3>{p.title}</h3>
              <p className="muted clamp">{p.summary.plain}</p>
              <div className="chips">
                <span className="chip ind">{primaryIndustry(p)}</span>
                {algorithmsUsed(p).slice(0, 3).map((a) => <span key={a} className="chip">{a}</span>)}
              </div>
              <div className="card-metrics">
                <Meter label="Sophistication" v={sophistication(p)} max={10} est />
                <Meter label="Originality" v={internalOriginality(p)} max={100} est />
                <Meter label="Rubric" v={p.rubric.total} max={25} />
              </div>
              <div className="card-foot">
                <span className="muted small">{effort(p) ?? "?"} effort · {datasetAvailability(p)}</span>
                <label className="check small" onClick={(e) => e.stopPropagation()}>
                  <input type="checkbox" checked={compare.includes(p.id)} onChange={() => toggleCmp(p.id)} /> compare
                </label>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th></th><th>ID</th><th>Title</th><th>Industry</th><th>Algorithms used</th><th>Tier</th><th>Effort</th><th>Soph.</th><th>Orig.</th><th>Rubric</th><th>Data</th></tr></thead>
            <tbody>
              {sorted.map((p) => (
                <tr key={p.id} onClick={() => onSelect(p.id)} tabIndex={0} onKeyDown={(e) => e.key === "Enter" && onSelect(p.id)}>
                  <td onClick={(e) => e.stopPropagation()}><input type="checkbox" aria-label={`compare ${p.title}`} checked={compare.includes(p.id)} onChange={() => toggleCmp(p.id)} /></td>
                  <td className="mono">{p.id}</td><td>{p.title}</td><td>{primaryIndustry(p)}</td>
                  <td>{algorithmsUsed(p).join(", ")}</td><td>{tier(p)}</td><td>{effort(p)}</td>
                  <td>{sophistication(p)?.toFixed(1)}</td><td>{internalOriginality(p)?.toFixed(0)}</td><td>{p.rubric.total}</td>
                  <td className="small">{datasetAvailability(p)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Compare({ ps, onSelect }: { ps: Project[]; onSelect: (id: string) => void }) {
  const rows: [string, (p: Project) => string][] = [
    ["Industry", (p) => labels(p, "industry", { leafOnly: true }).join(", ")],
    ["Paradigms", (p) => labels(p, "paradigm").join(", ")],
    ["Tasks", (p) => labels(p, "task").join(", ")],
    ["Algorithms used", (p) => algorithmsUsed(p).join(", ")],
    ["Modalities", (p) => labels(p, "modality").join(", ")],
    ["Datasets", (p) => p.datasets.filter((d) => d.relationship === "used").map((d) => d.name).join("; ") || datasetAvailability(p)],
    ["Difficulty tier (est.)", (p) => tier(p) ?? "—"],
    ["Sophistication (est.)", (p) => sophistication(p)?.toFixed(1) ?? "—"],
    ["Reproduction effort (est.)", (p) => effort(p) ?? "—"],
    ["Internal originality", (p) => `${internalOriginality(p)?.toFixed(0) ?? "—"} · ${p.originality.internal?.composite?.label ?? ""}`],
    ["External originality", (p) => externalOriginality(p) ?? "not researched"],
    ...CRITERIA.map((c) => [`Rubric: ${c}`, (p: Project) => String(p.rubric.criteria[c]?.score ?? "—")] as [string, (p: Project) => string]),
    ["Rubric total", (p) => String(p.rubric.total)],
  ];
  return (
    <section className="compare">
      <h3>Side-by-side comparison</h3>
      <div className="table-wrap">
        <table className="table">
          <thead><tr><th></th>{ps.map((p) => <th key={p.id}><button className="link" onClick={() => onSelect(p.id)}>{p.title}</button></th>)}</tr></thead>
          <tbody>{rows.map(([l, f]) => <tr key={l}><th>{l}</th>{ps.map((p) => <td key={p.id}>{f(p)}</td>)}</tr>)}</tbody>
        </table>
      </div>
    </section>
  );
}
