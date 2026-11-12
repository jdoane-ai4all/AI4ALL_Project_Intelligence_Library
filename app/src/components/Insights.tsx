import { useMemo } from "react";
import type { Library, Project } from "../types";
import { algorithmsUsed, datasetAvailability, facetCounts, internalOriginality, labels, primaryIndustry, sophistication, tier, TIERS } from "../logic";

export default function Insights({ projects, lib, onSelect }: { projects: Project[]; lib: Library; onSelect: (id: string) => void }) {
  const ind = useMemo(() => facetCounts(projects, (p) => labels(p, "industry", { topOnly: true })), [projects]);
  const algs = useMemo(() => facetCounts(projects, algorithmsUsed).slice(0, 15), [projects]);
  const tasks = useMemo(() => facetCounts(projects, (p) => labels(p, "task")).slice(0, 12), [projects]);
  const data = useMemo(() => facetCounts(projects, (p) => [datasetAvailability(p)]), [projects]);
  const tiers = useMemo(() => TIERS.map((t) => [t, projects.filter((p) => tier(p) === t).length] as [string, number]), [projects]);
  const distinctive = useMemo(() => [...projects].filter((p) => internalOriginality(p) !== null).sort((a, b) => internalOriginality(b)! - internalOriginality(a)!).slice(0, 8), [projects]);
  const cs = (() => { try { return JSON.parse(lib.meta.cluster_stats || "{}"); } catch { return {}; } })();

  return (
    <div className="insights">
      <p className="muted">Descriptive, exploratory views of the catalog. Estimated constructs (sophistication, tier, originality) come from the documented framework; rubric totals are the original grades. See <code>reports/research_report.md</code> for the full analysis with caveats.</p>
      <div className="ins-grid">
        <Card title="Industries (multi-label)"><Bars rows={ind} /></Card>
        <Card title="Most-used algorithms (implemented/compared)"><Bars rows={algs} /></Card>
        <Card title="Task types"><Bars rows={tasks} /></Card>
        <Card title="Difficulty tier (estimated)"><Bars rows={tiers} /></Card>
        <Card title="Dataset availability"><Bars rows={data} /></Card>
        <Card title="Sophistication (est.) vs. original rubric total">
          <Scatter ps={projects} x={(p) => sophistication(p)} y={(p) => p.rubric.total} xl="sophistication (0–10, est.)" yl="rubric total (5–25)" xmax={10} ymin={5} ymax={25} onSelect={onSelect} />
        </Card>
        <Card title="Most distinctive within the collection">
          <div className="rank-list small">{distinctive.map((p, i) => (
            <div key={p.id} className="rank-row"><span className="rank-n mono">{i + 1}.</span>
              <div><button className="link" onClick={() => onSelect(p.id)}>{p.title}</button>
                <div className="muted">percentile {internalOriginality(p)?.toFixed(0)} · {p.originality.internal?.composite?.label}</div></div></div>))}</div>
        </Card>
        <Card title="Clustering diagnostics">
          <p className="small">k = {cs.k} clusters (Ward linkage, chosen by silhouette). Silhouette {cs.silhouette}; bootstrap stability ARI {cs.bootstrap_ari_mean} ± {cs.bootstrap_ari_sd}. Semantic model: {lib.meta.semantic_model}.</p>
          <p className="small muted">Clusters are labeled by their most over-represented taxonomy terms. Moderate silhouette values are typical for short project descriptions — treat cluster boundaries as soft.</p>
          <Bars rows={facetCounts(projects, (p) => [p.cluster?.label ?? "—"])} />
        </Card>
        <Card title="Primary industry × difficulty tier">
          <Heat rows={ind.map(([k]) => k)} cols={TIERS} get={(r, c) => projects.filter((p) => primaryIndustry(p) === r && tier(p) === c).length} />
          <p className="small muted">Rows sorted by total projects; industries with no primary-industry projects are omitted.</p>
        </Card>
      </div>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) { return <section className="icard"><h3>{title}</h3>{children}</section>; }
function Bars({ rows }: { rows: [string, number][] }) {
  const max = Math.max(1, ...rows.map((r) => r[1]));
  return <div className="bars">{rows.map(([k, n]) => <div key={k} className="bar-row"><span className="bl" title={k}>{k}</span><div className="bar"><div style={{ width: `${(n / max) * 100}%` }} /></div><span className="mono small">{n}</span></div>)}</div>;
}
function Scatter({ ps, x, y, xl, yl, xmax, ymin, ymax, onSelect }: { ps: Project[]; x: (p: Project) => number | null; y: (p: Project) => number | null; xl: string; yl: string; xmax: number; ymin: number; ymax: number; onSelect: (id: string) => void }) {
  const W = 360, H = 220, P = 30;
  const pts = ps.map((p) => ({ p, x: x(p), y: y(p) })).filter((d) => d.x !== null && d.y !== null) as { p: Project; x: number; y: number }[];
  const jitter = (id: string) => ((parseInt(id.slice(-3), 10) * 37) % 11 - 5) / 10;
  // ordinary least-squares fit y = a + b x (descriptive only)
  const n = pts.length, mx = pts.reduce((s, d) => s + d.x, 0) / n, my = pts.reduce((s, d) => s + d.y, 0) / n;
  const b = pts.reduce((s, d) => s + (d.x - mx) * (d.y - my), 0) / Math.max(1e-9, pts.reduce((s, d) => s + (d.x - mx) ** 2, 0));
  const a = my - b * mx;
  const sx = (x: number) => P + (x / xmax) * (W - P - 12), sy = (y: number) => H - P - ((y - ymin) / (ymax - ymin)) * (H - P - 12);
  const xs = pts.map((d) => d.x), x0 = Math.min(...xs), x1 = Math.max(...xs);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="scatter" role="img" aria-label={`${yl} by ${xl}`}>
      <line x1={P} y1={H - P} x2={W - 8} y2={H - P} className="axis" /><line x1={P} y1={8} x2={P} y2={H - P} className="axis" />
      <text x={W / 2} y={H - 6} className="axl">{xl}</text><text x={10} y={H / 2} className="axl" transform={`rotate(-90 10 ${H / 2})`}>{yl}</text>
      {pts.map(({ p, x: px, y: py }) => (
        <circle key={p.id} cx={sx(px)} cy={sy(py + jitter(p.id))} r={3.2} className="pt" onClick={() => onSelect(p.id)}>
          <title>{p.title} — {px.toFixed(1)}, {py}</title></circle>))}
      {n > 2 && <line x1={sx(x0)} y1={sy(a + b * x0)} x2={sx(x1)} y2={sy(a + b * x1)} className="fit" />}
      {n > 2 && <text x={W - 12} y={14} className="axl fit-l" textAnchor="end">best fit: rubric ≈ {a.toFixed(1)} + {b.toFixed(2)} × sophistication</text>}
    </svg>
  );
}
function Heat({ rows: allRows, cols, get }: { rows: string[]; cols: string[]; get: (r: string, c: string) => number }) {
  const total = (r: string) => cols.reduce((a, c) => a + get(r, c), 0);
  const rows = allRows.filter((r) => total(r) > 0).sort((a, b) => total(b) - total(a));
  const max = Math.max(1, ...rows.flatMap((r) => cols.map((c) => get(r, c))));
  return <table className="heat small"><thead><tr><th />{cols.map((c) => <th key={c}>{c}</th>)}<th>Total</th></tr></thead>
    <tbody>{rows.map((r) => <tr key={r}><th>{r}</th>{cols.map((c) => { const v = get(r, c); return <td key={c} style={{ background: `color-mix(in srgb, var(--accent) ${Math.round(v / max * 85)}%, transparent)`, color: v / max > 0.55 ? "var(--on-accent)" : undefined }}>{v || ""}</td>; })}<td className="mono muted">{total(r)}</td></tr>)}</tbody></table>;
}
