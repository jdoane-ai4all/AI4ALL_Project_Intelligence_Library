import { useState } from "react";
import type { Project } from "../types";
import { algorithmsUsed, datasetAvailability, effort, emptyFilters, EFFORT, facetCounts, type Filters, labels, reviewStatus, tier, TIERS } from "../logic";

type ListKey = "industry" | "paradigm" | "algorithm" | "task" | "modality" | "tier" | "effort" | "data" | "review";
const FACETS: { key: ListKey; label: string; get: (p: Project) => string[]; order?: string[] }[] = [
  { key: "review", label: "Review status", get: (p) => [reviewStatus(p)], order: ["No major issues", "Use with caution", "Withheld for review"] },
  { key: "industry", label: "Industry", get: (p) => labels(p, "industry", { topOnly: true }) },
  { key: "paradigm", label: "ML paradigm", get: (p) => labels(p, "paradigm") },
  { key: "algorithm", label: "Algorithm (used)", get: algorithmsUsed },
  { key: "task", label: "Task", get: (p) => labels(p, "task") },
  { key: "modality", label: "Data modality", get: (p) => labels(p, "modality") },
  { key: "tier", label: "Difficulty tier (est.)", get: (p) => [tier(p) ?? ""], order: TIERS },
  { key: "effort", label: "Reproduction effort (est.)", get: (p) => [effort(p) ?? ""], order: EFFORT },
  { key: "data", label: "Dataset availability", get: (p) => [datasetAvailability(p)] },
];

export default function FilterPanel({ all, visible, filters, setFilters, open, toggle }: {
  all: Project[]; visible: Project[]; filters: Filters; setFilters: (f: Filters) => void; open: boolean; toggle: () => void;
}) {
  const active = FACETS.reduce((n, f) => n + filters[f.key].length, 0) +
    (filters.soph.join() !== "0,10" ? 1 : 0) + (filters.orig.join() !== "0,100" ? 1 : 0) + (filters.rubric.join() !== "5,25" ? 1 : 0);
  return (
    <aside className={`filters ${open ? "" : "collapsed"}`} aria-label="Filters">
      <div className="filters-head">
        <button className="ghost" onClick={toggle} aria-expanded={open}>{open ? "⟨ Filters" : "⟩"}</button>
        {open && <span className="count">{visible.length} / {all.length} shown</span>}
        {open && active > 0 && <button className="link" onClick={() => setFilters({ ...emptyFilters(), q: filters.q })}>Clear ({active})</button>}
      </div>
      {open && (
        <div className="filters-body">
          <Range label="Technical sophistication (est., 0–10)" min={0} max={10} step={0.5} val={filters.soph} set={(v) => setFilters({ ...filters, soph: v })} />
          <Range label="Internal originality (percentile)" min={0} max={100} step={5} val={filters.orig} set={(v) => setFilters({ ...filters, orig: v })} />
          <Range label="Original rubric total (5–25)" min={5} max={25} step={1} val={filters.rubric} set={(v) => setFilters({ ...filters, rubric: v })} />
          {FACETS.map((f) => <Facet key={f.key} f={f} all={all} filters={filters} setFilters={setFilters} />)}
        </div>
      )}
    </aside>
  );
}

function Facet({ f, all, filters, setFilters }: { f: (typeof FACETS)[number]; all: Project[]; filters: Filters; setFilters: (f: Filters) => void }) {
  const [more, setMore] = useState(false);
  let counts = facetCounts(all, f.get).filter(([k]) => k);
  if (f.order) counts = f.order.map((k) => counts.find((c) => c[0] === k)).filter(Boolean) as [string, number][];
  const sel = filters[f.key];
  const TOP = 3;
  const shown = more ? counts : counts.filter(([k], i) => i < TOP || sel.includes(k));
  const toggle = (k: string) => setFilters({ ...filters, [f.key]: sel.includes(k) ? sel.filter((x) => x !== k) : [...sel, k] });
  return (
    <fieldset className="facet">
      <legend>{f.label}</legend>
      {shown.map(([k, n]) => (
        <label key={k} className={`facet-row ${sel.includes(k) ? "on" : ""}`}>
          <input type="checkbox" checked={sel.includes(k)} onChange={() => toggle(k)} />
          <span className="fl">{k}</span><span className="n">{n}</span>
        </label>
      ))}
      {counts.length > TOP && <button className="link small" onClick={() => setMore(!more)}>{more ? "show fewer" : `+${counts.length - shown.length} more`}</button>}
    </fieldset>
  );
}

function Range({ label, min, max, step, val, set }: { label: string; min: number; max: number; step: number; val: [number, number]; set: (v: [number, number]) => void }) {
  const lo = (val[0] - min) / (max - min) * 100, hi = (val[1] - min) / (max - min) * 100;
  return (
    <fieldset className="facet range-facet">
      <legend>{label}</legend>
      <div className="range-vals"><span className="mono">{val[0]}</span><span className="mono">{val[1]}</span></div>
      <div className="dual" style={{ ["--lo" as string]: `${lo}%`, ["--hi" as string]: `${hi}%` }}>
        <input type="range" aria-label={`${label} minimum`} min={min} max={max} step={step} value={val[0]} onChange={(e) => set([Math.min(Number(e.target.value), val[1]), val[1]])} />
        <input type="range" aria-label={`${label} maximum`} min={min} max={max} step={step} value={val[1]} onChange={(e) => set([val[0], Math.max(Number(e.target.value), val[0])])} />
      </div>
    </fieldset>
  );
}
