import { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph3D from "3d-force-graph";
import type { Library, Project } from "../types";
import { datasetAvailability, internalOriginality, primaryIndustry, readiness, reviewStatus, sophistication, tier, effortScore } from "../logic";
import { colorFor, palette, neutral, type Theme } from "../colors";

type ColorBy = "cluster" | "industry" | "tier" | "student_type" | "data" | "review";
type SizeBy = "uniform" | "sophistication" | "originality" | "rubric" | "effort" | "readiness";
const VIEWS = [
  ["overall", "Overall (blended)"], ["semantic", "Topic (description semantics)"], ["algorithm", "Algorithms"],
  ["industry", "Industry"], ["technical", "Technical approach"], ["dataset", "Shared datasets"], ["skills", "Skill requirements"],
] as const;
const SIZE: Record<SizeBy, { label: string; get: (p: Project) => number | null; max: number; estimated: boolean }> = {
  uniform: { label: "Uniform", get: () => 1, max: 1, estimated: false },
  sophistication: { label: "Technical sophistication (estimated)", get: sophistication, max: 10, estimated: true },
  originality: { label: "Internal originality (computed percentile)", get: internalOriginality, max: 100, estimated: true },
  rubric: { label: "Original rubric total (graded)", get: (p) => p.rubric.total, max: 25, estimated: false },
  effort: { label: "Reproduction effort (estimated)", get: effortScore, max: 15, estimated: true },
  readiness: { label: "Adoption readiness (estimated)", get: readiness, max: 7, estimated: true },
};

// Presets combine connections, color and size to answer a question; any individual change switches to "Custom".
const PRESETS: { id: string; label: string; desc: string; view: string; color: ColorBy; size: SizeBy }[] = [
  { id: "landscape", label: "Project landscape", view: "overall", color: "cluster", size: "sophistication",
    desc: "How the projects group by topic and method. Bigger bubbles = more technically sophisticated." },
  { id: "industry", label: "Did groups stay in their chosen industry?", view: "industry", color: "student_type", size: "readiness",
    desc: "Links join projects whose content is in similar industries; colors show the industry each group chose. Mixed colors within a linked cluster = projects that drifted from their chosen category." },
  { id: "methods", label: "How demanding is each method?", view: "algorithm", color: "tier", size: "sophistication",
    desc: "Links join projects using the same algorithms; color = difficulty tier, size = technical sophistication." },
  { id: "access", label: "What can a new student build?", view: "skills", color: "data", size: "readiness",
    desc: "Links join projects needing similar skills; color = dataset availability, size = adoption readiness." },
  { id: "originality", label: "Where are the distinctive projects?", view: "semantic", color: "industry", size: "originality",
    desc: "Links join projects with similar descriptions; color = primary industry (inferred), size = originality within the collection." },
  { id: "rigor", label: "Review status vs. rubric", view: "technical", color: "review", size: "rubric",
    desc: "Links join projects with similar technical approaches; color = review status, size = original rubric total." },
];
const NEUTRAL = new Set(["Not provided", "Unclassified", "Unknown", "Unclustered"]);

interface GNode { id: string; p: Project; x?: number; y?: number; z?: number; fx?: number; fy?: number; fz?: number; __threeObj?: unknown }
interface GLink { source: string | GNode; target: string | GNode; weight: number; explanation: string }

export default function Constellation({ lib, projects, visible, selected, onSelect, theme }: {
  lib: Library; projects: Project[]; visible: Project[]; selected: string | null; onSelect: (id: string) => void; theme: string;
}) {
  const el = useRef<HTMLDivElement>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const graph = useRef<any>(null);
  const [colorBy, setColorBy] = useState<ColorBy>("cluster");
  const [sizeBy, setSizeBy] = useState<SizeBy>("sophistication");
  const [view, setView] = useState<string>("overall");
  const [showLinks, setShowLinks] = useState(true);
  const [hideFiltered, setHideFiltered] = useState(false);
  const [layout, setLayout] = useState<"embedding" | "force">("embedding");
  const [isolate, setIsolate] = useState<string | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const [hoverLink, setHoverLink] = useState<GLink | null>(null);

  const preset = PRESETS.find((pr) => pr.view === view && pr.color === colorBy && pr.size === sizeBy) ?? null;
  const visibleIds = useMemo(() => new Set(visible.map((p) => p.id)), [visible]);
  const colorKey = (p: Project) =>
    colorBy === "cluster" ? (p.cluster?.label ?? "Unclustered") : colorBy === "industry" ? primaryIndustry(p)
      : colorBy === "tier" ? (tier(p) ?? "Unknown") : colorBy === "data" ? datasetAvailability(p) : colorBy === "review" ? reviewStatus(p) : (p.student_type || "Not provided");
  const legend = useMemo(() => {
    const m = new Map<string, number>();
    projects.forEach((p) => m.set(colorKey(p), (m.get(colorKey(p)) || 0) + 1));
    const fixed = colorBy === "tier" ? ["Beginner", "Intermediate", "Advanced", "Unknown"] : colorBy === "review" ? ["No major issues", "Use with caution", "Withheld for review"] : null;
    // neutral "Not provided"-type groups are gray, listed last, and don't consume a palette color
    const keys = fixed ? fixed.filter((k) => m.has(k))
      : [...m.keys()].sort((a, b) => Number(NEUTRAL.has(a)) - Number(NEUTRAL.has(b)) || m.get(b)! - m.get(a)!);
    let i = 0;
    const t = theme as Theme, pal = palette(t);
    return keys.map((k) => ({ key: k, n: m.get(k)!, color: NEUTRAL.has(k) ? neutral(t) : fixed ? colorFor(k, t) : pal[i++ % pal.length] }));
  }, [projects, colorBy, theme]);
  const colorMap = useMemo(() => new Map(legend.map((l) => [l.key, l.color])), [legend]);

  // Node objects are cached so filter/slider changes only restyle the graph instead of rebuilding it
  // (rebuilding re-initialised the scene, which looked like the network resizing on every slider move).
  const cache = useRef<{ layout: string; map: Map<string, GNode> }>({ layout, map: new Map() });
  const shownKey = useMemo(() => projects
    .filter((p) => !isolate || colorKey(p) === isolate)
    .filter((p) => !hideFiltered || visibleIds.has(p.id))
    .map((p) => p.id).join(","), [projects, isolate, colorBy, hideFiltered, hideFiltered ? visibleIds : null]);
  const nodes = useMemo<GNode[]>(() => {
    if (cache.current.layout !== layout) cache.current = { layout, map: new Map() };
    const byId = new Map(projects.map((p) => [p.id, p]));
    return shownKey.split(",").filter(Boolean).map((id) => {
      const hit = cache.current.map.get(id);
      if (hit) return hit;
      const p = byId.get(id)!, c = p.cluster;
      const pos = c ? { x: c.x * 2.2, y: c.y * 2.2, z: c.z * 2.2 } : {};
      const n: GNode = layout === "embedding" && c ? { id, p, ...pos, fx: pos.x, fy: pos.y, fz: pos.z } : { id, p, ...pos };
      cache.current.map.set(id, n);
      return n;
    });
  }, [shownKey, layout, projects]);

  const links = useMemo<GLink[]>(() => {
    if (!showLinks) return [];
    const ids = new Set(nodes.map((n) => n.id));
    return lib.edges.filter((e) => e.view === view && ids.has(e.source) && ids.has(e.target))
      .map((e) => ({ source: e.source, target: e.target, weight: e.weight, explanation: e.explanation }));
  }, [lib.edges, view, nodes, showLinks]);

  const neighbors = useMemo(() => {
    const m = new Map<string, Set<string>>();
    for (const l of links) {
      const s = typeof l.source === "string" ? l.source : l.source.id, t = typeof l.target === "string" ? l.target : l.target.id;
      if (!m.has(s)) m.set(s, new Set()); if (!m.has(t)) m.set(t, new Set());
      m.get(s)!.add(t); m.get(t)!.add(s);
    }
    return m;
  }, [links]);

  // create graph once
  useEffect(() => {
    if (!el.current) return;
    const g = new (ForceGraph3D as any)(el.current, { controlType: "orbit" })
      .showNavInfo(false)
      .nodeId("id")
      .linkOpacity(0.35)
      .enableNodeDrag(true)
      .cooldownTicks(120);
    graph.current = g;
    (window as unknown as { __atlasGraph?: unknown }).__atlasGraph = g; // exposed for automated UI checks
    const ro = new ResizeObserver(() => g.width(el.current!.clientWidth).height(el.current!.clientHeight));
    ro.observe(el.current);
    return () => { ro.disconnect(); g._destructor?.(); };
  }, []);

  // Styling is split by input so a filter/slider change only recolours nodes. Re-assigning nodeVal (size) makes the
  // 3D library rebuild every sphere, which is what looked like the network resizing on each slider move.
  useEffect(() => {   // static settings + handlers, once
    const g = graph.current; if (!g) return;
    g.nodeRelSize(3).nodeOpacity(0.92).nodeResolution(14)
      .nodeLabel((n: GNode) => tooltip(n.p))
      .linkDirectionalParticleWidth(1.6)
      .linkLabel((l: GLink) => `<div class="tip"><b>${(l.weight * 100).toFixed(0)}% similar</b><br/>${escapeHtml(l.explanation)}</div>`)
      .onNodeHover((n: GNode | null) => { setHover(n ? n.id : null); if (el.current) el.current.style.cursor = n ? "pointer" : "grab"; })
      .onLinkHover((l: GLink | null) => setHoverLink(l))
      .onNodeClick((n: GNode) => { onSelectRef.current(n.id); focusNode(n); })
      .onNodeDragEnd((n: GNode) => { n.fx = n.x; n.fy = n.y; n.fz = n.z; })
      .onBackgroundClick(() => setHover(null));
  }, []);

  useEffect(() => {   // sizes: only when the size metric (or the project set) changes
    const g = graph.current; if (!g) return;
    const S = SIZE[sizeBy];
    // Min-max scaling: whichever metric is chosen, the lowest value maps to MIN_V and the highest to MAX_V.
    const MIN_V = 1, MAX_V = 36, UNIFORM_V = 6;
    const vals = projects.map((p) => S.get(p)).filter((v): v is number => v !== null && v !== undefined);
    const lo = Math.min(...vals), hi = Math.max(...vals);
    g.nodeVal((n: GNode) => {
      if (sizeBy === "uniform") return UNIFORM_V;
      const v = S.get(n.p);
      if (v === null || v === undefined || hi === lo) return MIN_V;
      return MIN_V + (MAX_V - MIN_V) * ((v - lo) / (hi - lo));
    });
  }, [sizeBy, projects]);

  const focus = hover ?? selected;
  useEffect(() => {   // colours: filters, highlighting, legend, theme
    const g = graph.current; if (!g) return;
    const near = focus ? neighbors.get(focus) ?? new Set() : null;
    const dim = (id: string) => (!visibleIds.has(id)) || (near !== null && id !== focus && !near.has(id));
    g.nodeColor((n: GNode) => {
      if (dim(n.id)) return theme === "dark" ? "rgba(168,193,174,0.16)" : "rgba(94,112,101,0.22)";
      return colorMap.get(colorKey(n.p)) ?? "#888";
    });
  }, [visibleIds, focus, neighbors, colorMap, colorBy, theme]);

  useEffect(() => {   // links: hover/selection highlighting and theme
    const g = graph.current; if (!g) return;
    const touches = (l: GLink) => { const s = (l.source as GNode).id ?? l.source, t = (l.target as GNode).id ?? l.target; return !!focus && (s === focus || t === focus); };
    g.linkWidth((l: GLink) => (hoverLink === l ? 2.5 : 0.25 + 2.2 * Math.max(0, l.weight - 0.3)))
      .linkColor((l: GLink) => touches(l) ? (theme === "dark" ? "#FFB200" : "#930059") : (theme === "dark" ? "rgba(172,228,170,0.28)" : "rgba(50,83,61,0.22)"))
      .linkDirectionalParticles((l: GLink) => (touches(l) ? 2 : 0));
  }, [focus, hoverLink, theme]);

  useEffect(() => { graph.current?.backgroundColor(theme === "dark" ? "#191919" : "#FFF8F9"); }, [theme]);

  const fitted = useRef(false);
  useEffect(() => {
    const g = graph.current; if (!g) return;
    g.graphData({ nodes, links });
    if (layout === "force") g.d3ReheatSimulation?.();
    if (!fitted.current && nodes.length) {   // fit the camera once the first real data is in place
      fitted.current = true;
      setTimeout(() => g.zoomToFit(0, 40), 50);
    }
  }, [nodes, links, layout]);

  useEffect(() => { setTimeout(() => graph.current?.zoomToFit(600, 40), 350); }, [isolate, layout]);

  function focusNode(n: GNode) {
    const g = graph.current; if (!g || n.x === undefined) return;
    const d = 140, r = 1 + d / Math.hypot(n.x!, n.y!, n.z!);
    g.cameraPosition({ x: n.x! * r, y: n.y! * r, z: n.z! * r }, n, 900);
  }
  useEffect(() => {
    if (!selected) return;
    const n = (graph.current?.graphData().nodes as GNode[] | undefined)?.find((x) => x.id === selected);
    if (n) focusNode(n);
  }, [selected]);

  return (
    <div className="constellation">
      <div ref={el} className="graph" aria-label="3D project constellation. Use the Explore tab for an accessible list." />
      <div className="hud hud-left">
        <div className="hud-group">
          <label>Preset view</label>
          <select value={preset?.id ?? "custom"} onChange={(e) => { const pr = PRESETS.find((x) => x.id === e.target.value); if (pr) { setView(pr.view); setColorBy(pr.color); setSizeBy(pr.size); setIsolate(null); } }}>
            {PRESETS.map((pr) => <option key={pr.id} value={pr.id}>{pr.label}</option>)}
            <option value="custom" disabled>Custom (your own combination)</option>
          </select>
          <div className="hint-muted">{preset ? preset.desc : "Custom combination — pick a preset to reset."}</div>
        </div>
        <div className="hud-group">
          <label>Color by</label>
          <select value={colorBy} onChange={(e) => { setColorBy(e.target.value as ColorBy); setIsolate(null); }}>
            <option value="cluster">Data-driven cluster</option>
            <option value="industry">Primary industry (inferred)</option>
            <option value="student_type">Group-chosen industry</option>
            <option value="tier">Difficulty tier (estimated)</option>
            <option value="data">Dataset availability</option>
            <option value="review">Review status</option>
          </select>
          <label>Size by</label>
          <select value={sizeBy} onChange={(e) => setSizeBy(e.target.value as SizeBy)}>
            {Object.entries(SIZE).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
          </select>
          {SIZE[sizeBy].estimated && <div className="hint">Size encodes an inferred estimate, not a measured fact.</div>}
        </div>
        <div className="hud-group">
          <label>Connections</label>
          <select value={view} onChange={(e) => setView(e.target.value)}>
            {VIEWS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
          <label className="check"><input type="checkbox" checked={showLinks} onChange={(e) => setShowLinks(e.target.checked)} /> show links ({links.length})</label>
        </div>
        <div className="hud-group">
          <label>Layout</label>
          <div className="seg">
            <button className={layout === "embedding" ? "on" : ""} onClick={() => setLayout("embedding")}>Embedding</button>
            <button className={layout === "force" ? "on" : ""} onClick={() => setLayout("force")}>Force</button>
          </div>
          <label className="check"><input type="checkbox" checked={hideFiltered} onChange={(e) => setHideFiltered(e.target.checked)} /> hide filtered-out</label>
          <div className="row">
            <button onClick={() => graph.current?.zoomToFit(600, 40)}>Recenter</button>
            <button onClick={() => { setIsolate(null); setLayout("embedding"); setHover(null); graph.current?.zoomToFit(600, 40); }}>Reset</button>
          </div>
        </div>
      </div>
      <div className="hud hud-right legend">
        <div className="legend-title">{colorBy === "cluster" ? "Clusters (click to isolate)" : "Legend (click to isolate)"}</div>
        {legend.map((l) => (
          <button key={l.key} className={`legend-item ${isolate === l.key ? "on" : ""}`} onClick={() => setIsolate(isolate === l.key ? null : l.key)}>
            <span className="dot" style={{ background: l.color }} /> <span className="lk">{l.key}</span> <span className="n">{l.n}</span>
          </button>
        ))}
        {isolate && <button className="link" onClick={() => setIsolate(null)}>Show all</button>}
      </div>
      {hoverLink && <div className="hud hud-bottom">{hoverLink.explanation}</div>}
      <div className="hud hud-help">Drag to rotate · scroll to zoom · right-drag to pan · click a node for details</div>
    </div>
  );
}

function escapeHtml(s: string) { return (s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]!)); }
function tooltip(p: Project) {
  const algs = [...new Set(p.algorithms.filter((a) => a.role === "implemented").map((a) => a.label))].slice(0, 3).join(", ");
  return `<div class="tip"><b>${escapeHtml(p.title)}</b><br/><span>${escapeHtml(primaryIndustry(p))} · ${escapeHtml(tier(p) ?? "")}</span>
  <br/><span class="muted">${escapeHtml(algs)}</span><br/><span class="muted">${escapeHtml((p.summary.plain || "").slice(0, 160))}…</span></div>`;
}
