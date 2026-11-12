import { useEffect, useMemo, useState } from "react";
import MiniSearch from "minisearch";
import type { Library, Project } from "./types";
import { applyFilters, emptyFilters, type Filters, labels, algorithmsUsed } from "./logic";
import Constellation from "./components/Constellation";
import Explorer from "./components/Explorer";
import Detail from "./components/Detail";
import Guide from "./components/Guide";
import Insights from "./components/Insights";
import About from "./components/About";
import FilterPanel from "./components/FilterPanel";

type Tab = "atlas" | "explore" | "guide" | "insights" | "about";
const TABS: [Tab, string][] = [["atlas", "Constellation"], ["explore", "Explore"], ["guide", "Find a project"], ["insights", "Insights"], ["about", "Method"]];

function hasWebGL() {
  try {
    const c = document.createElement("canvas");
    return !!(window.WebGLRenderingContext && (c.getContext("webgl2") || c.getContext("webgl")));
  } catch { return false; }
}

export default function App({ lib }: { lib: Library }) {
  const extracted = useMemo(() => lib.projects.filter((p) => p.summary?.plain), [lib]);
  const heldCount = useMemo(() => extracted.filter((p) => p.recommendation?.status === "hold").length, [extracted]);
  const [showHeld, setShowHeld] = useState(false);
  // Projects withheld after methodological review are hidden everywhere unless the header switch is on.
  const projects = useMemo(() => (showHeld ? extracted : extracted.filter((p) => p.recommendation?.status !== "hold")), [extracted, showHeld]);
  const byId = useMemo(() => new Map(lib.projects.map((p) => [p.id, p])), [lib]);
  const webgl = useMemo(hasWebGL, []);
  const [tab, setTab] = useState<Tab>(() => (location.hash.slice(1) as Tab) || (webgl ? "atlas" : "explore"));
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [selected, setSelected] = useState<string | null>(null);
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    try { return (localStorage.getItem("atlas-theme") as "dark" | "light") || "dark"; } catch { return "dark"; }
  });
  const [showFilters, setShowFilters] = useState(true);

  useEffect(() => { if (location.hash.slice(1) !== tab) location.hash = tab; }, [tab]);
  useEffect(() => {
    const on = () => { const h = location.hash.slice(1) as Tab; if (TABS.some(([k]) => k === h)) setTab(h); };
    window.addEventListener("hashchange", on); return () => window.removeEventListener("hashchange", on);
  }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem("atlas-theme", theme); } catch { /* storage unavailable */ }
  }, [theme]);

  const search = useMemo(() => {
    const ms = new MiniSearch<{ id: string; title: string; text: string; tags: string; tech: string }>({
      fields: ["title", "text", "tags", "tech"], storeFields: ["id"],
      searchOptions: { boost: { title: 6, tags: 2, tech: 1.5 }, prefix: true, fuzzy: 0.15 },
    });
    ms.addAll(projects.map((p) => ({
      id: p.id, title: p.title,
      text: [p.summary.plain, p.summary.technical, p.summary.question, p.student_description].join(" "),
      tags: p.tags.join(" "),
      tech: [...algorithmsUsed(p), ...labels(p, "industry"), ...labels(p, "task"), ...labels(p, "modality"), ...labels(p, "paradigm")].join(" "),
    })));
    return ms;
  }, [projects]);

  const results = useMemo(() => (filters.q.trim() ? search.search(filters.q) : null), [filters.q, search]);
  const hits = useMemo(() => (results ? new Set(results.map((r) => r.id as string)) : null), [results]);
  const scores = useMemo(() => (results ? new Map(results.map((r) => [r.id as string, r.score])) : null), [results]);
  const visible = useMemo(() => applyFilters(projects, filters, hits), [projects, filters, hits]);
  const sel = selected ? byId.get(selected) ?? null : null;
  const pending = lib.projects.length - extracted.length;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <img className="ai4all-logo" src="./brand/ai4all-pill.png" alt="AI4ALL" width="96" height="30" />
          <div>
            <div className="brand-title-row">
              <span className="brand-title">AI Project Atlas</span>
              <label className="switch" title="Projects with a critical methodological issue, withheld by the program reviewer">
                <input type="checkbox" role="switch" checked={showHeld} onChange={(e) => setShowHeld(e.target.checked)} />
                <span className="track" aria-hidden><span className="knob" /></span> Show withheld ({heldCount})
              </label>
            </div>
            <div className="brand-sub">{projects.length} student AI/ML projects{!showHeld && heldCount ? ` (${heldCount} withheld)` : ""} · evidence-grounded library · AI4ALL Ignite</div>
          </div>
        </div>
        <nav className="tabs" role="tablist">
          {TABS.map(([k, l]) => (
            <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</button>
          ))}
        </nav>
        <div className="top-actions">
          <input className="search" type="search" placeholder="Search projects, methods, domains…" aria-label="Search"
            value={filters.q} onChange={(e) => setFilters({ ...filters, q: e.target.value })} />
          <button className="ghost" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} aria-label="Toggle theme">
            {theme === "dark" ? "☀" : "☾"}
          </button>
        </div>
      </header>
      {pending > 0 && <div className="banner">{pending} project(s) are still awaiting extraction and are not shown.</div>}
      <div className={`body ${tab === "atlas" || tab === "explore" ? "with-filters" : ""} ${showFilters ? "" : "filters-hidden"}`}>
        {(tab === "atlas" || tab === "explore") && (
          <FilterPanel all={projects} visible={visible} filters={filters} setFilters={setFilters}
            open={showFilters} toggle={() => setShowFilters(!showFilters)} />
        )}
        <main className="main">
          {tab === "atlas" && (webgl
            ? <Constellation lib={lib} projects={projects} visible={visible} selected={selected} onSelect={setSelected} theme={theme} />
            : <div className="notice">3D view needs WebGL, which is unavailable here. Use <button className="link" onClick={() => setTab("explore")}>Explore</button> for the full catalog.</div>)}
          {tab === "explore" && <Explorer projects={visible} onSelect={setSelected} scores={scores} />}
          {tab === "guide" && <Guide projects={projects} onSelect={setSelected} includeHeld={showHeld} />}
          {tab === "insights" && <Insights projects={projects} lib={lib} onSelect={setSelected} />}
          {tab === "about" && <About lib={lib} />}
        </main>
        {sel && <Detail p={sel} lib={lib} byId={byId} onClose={() => setSelected(null)} onSelect={setSelected} />}
      </div>
    </div>
  );
}
