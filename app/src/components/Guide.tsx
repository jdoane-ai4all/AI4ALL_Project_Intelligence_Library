import { useMemo, useState } from "react";
import type { Project } from "../types";
import { algorithmsUsed, availableHours, datasetAvailability, effort, facetCounts, type GuideInput, HOURS_BANDS, type HoursBand, labels, parsePrompt, PROGRAM_WEEKS, recommend, tier } from "../logic";
import { Badge } from "./ui";

const DEFAULT: GuideInput = { interests: [], paradigms: [], algorithms: [], python: 1, ml: 1, hours: "2-4", wantOriginal: false, needPublicData: true, includeHeld: false };
const EXAMPLES = [
  "I'm interested in climate change, know basic Python, and can spend about 3 hours a week on a supervised learning project.",
  "I'm technically advanced, have 6+ hours a week, and want an original deep learning project in healthcare.",
  "I want to use random forests on finance data with 4-5 hours a week.",
];

export default function Guide({ projects, onSelect, includeHeld }: { projects: Project[]; onSelect: (id: string) => void; includeHeld: boolean }) {
  const [g, setG] = useState<GuideInput>(DEFAULT);
  const [text, setText] = useState("");
  const vocab = useMemo(() => ({
    industries: facetCounts(projects, (p) => labels(p, "industry")).map(([k]) => k),
    paradigms: facetCounts(projects, (p) => labels(p, "paradigm")).map(([k]) => k),
    algorithms: facetCounts(projects, algorithmsUsed).map(([k]) => k),
  }), [projects]);
  const recs = useMemo(() => recommend(projects, { ...g, includeHeld }, 8), [projects, g, includeHeld]);

  const applyText = (t: string) => { setText(t); setG({ ...DEFAULT, ...parsePrompt(t, vocab) }); };
  const toggle = (k: "interests" | "paradigms" | "algorithms", v: string) =>
    setG({ ...g, [k]: g[k].includes(v) ? g[k].filter((x) => x !== v) : [...g[k], v] });

  return (
    <div className="guide">
      <section className="guide-form">
        <h2>Find a project to build</h2>
        <p className="muted">Recommendations are retrieved from this catalog and ranked with a transparent scoring rule — every reason shown is a fact from the project record.</p>
        <textarea rows={2} value={text} placeholder="Describe what you want, e.g. “I know basic Python and want a two-week healthcare classification project”"
          onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), applyText(text))} aria-label="Describe your goal" />
        <div className="row"><button onClick={() => applyText(text)}>Interpret</button>
          {EXAMPLES.map((x, i) => <button key={i} className="link small" onClick={() => applyText(x)}>Example {i + 1}</button>)}</div>
        <div className="guide-grid">
          <Pick title="Interests (industry)" opts={vocab.industries} sel={g.interests} on={(v) => toggle("interests", v)} />
          <Pick title="ML paradigm" opts={vocab.paradigms} sel={g.paradigms} on={(v) => toggle("paradigms", v)} />
          <Pick title="Algorithms" opts={vocab.algorithms} sel={g.algorithms} on={(v) => toggle("algorithms", v)} />
          <div className="facet form-grid">
            <label>Python level <select value={g.python} onChange={(e) => setG({ ...g, python: Number(e.target.value) as 1 | 2 | 3 })}><option value={1}>Basic</option><option value={2}>Comfortable</option><option value={3}>Strong</option></select></label>
            <label>ML level <select value={g.ml} onChange={(e) => setG({ ...g, ml: Number(e.target.value) as 1 | 2 | 3 })}><option value={1}>New to ML</option><option value={2}>Some ML</option><option value={3}>Deep learning experience</option></select></label>
            <label>Time available <select value={g.hours} onChange={(e) => setG({ ...g, hours: e.target.value as HoursBand })}>
              {(Object.keys(HOURS_BANDS) as HoursBand[]).map((h) => <option key={h} value={h}>{HOURS_BANDS[h].label}</option>)}</select></label>
            <div className="small muted form-note">≈ {availableHours(g.hours)} hours over ~{PROGRAM_WEEKS} working weeks of the 13-week program (proposal by week 7, build weeks 8–11, present week 12).</div>
            <label className="check"><input type="checkbox" checked={g.needPublicData} onChange={(e) => setG({ ...g, needPublicData: e.target.checked })} /> need an accessible public dataset</label>
            <label className="check"><input type="checkbox" checked={g.wantOriginal} onChange={(e) => setG({ ...g, wantOriginal: e.target.checked })} /> favor distinctive projects</label>
          </div>
        </div>
      </section>
      <section className="guide-results">
        {recs.length === 0 && <p className="notice">No project in the catalog matches those interests. Try removing an interest filter.</p>}
        {recs.map((r, i) => {
          const p = r.project;
          const ds = p.datasets.filter((d) => d.relationship === "used" && d.url);
          const alts = p.datasets.filter((d) => d.relationship === "alternative" && d.url);
          return (
            <article key={p.id} className="rec">
              <div className="rec-head"><span className="rank">{i + 1}</span>
                <div><button className="link h" onClick={() => onSelect(p.id)}>{p.title}</button>
                  <div className="muted small">{labels(p, "industry", { leafOnly: true }).join(" · ")}</div></div>
                <Badge kind={tier(p) ?? ""}>{tier(p)}</Badge></div>
              <p className="small">{p.summary.plain}</p>
              <div className="two small">
                <div><b>Why it fits</b><ul>{r.reasons.map((x, j) => <li key={j}>{x}</li>)}</ul>
                  {r.cautions.length > 0 && <><b>Watch out</b><ul className="cautions">{r.cautions.map((x, j) => <li key={j}>{x}</li>)}</ul></>}</div>
                <div>
                  <div><b>Algorithms used:</b> {algorithmsUsed(p).join(", ") || "—"}</div>
                  <div><b>Background:</b> Python {p.assessments.prerequisites?.python?.value}/3, math {p.assessments.prerequisites?.math_stats?.value}/3, ML {p.assessments.prerequisites?.ml?.value}/3</div>
                  <div><b>Comparable build:</b> {effort(p)} effort — {p.assessments.reproduction_effort?.overall?.rationale}</div>
                  <div><b>Data:</b> {ds.length ? ds.map((d) => <a key={d.id} href={d.url!} target="_blank" rel="noreferrer noopener">{d.name}</a>).reduce((a: React.ReactNode[], x, j) => (j ? [...a, ", ", x] : [x]), []) : datasetAvailability(p)}
                    {alts.length > 0 && <> · alternative: {alts.map((d) => d.name).join(", ")}</>}</div>
                  <div className="muted">Open the profile for related alternatives.</div>
                </div>
              </div>
            </article>
          );
        })}
      </section>
    </div>
  );
}

function Pick({ title, opts, sel, on }: { title: string; opts: string[]; sel: string[]; on: (v: string) => void }) {
  const [all, setAll] = useState(false);
  const shown = all ? opts : opts.slice(0, 10);
  return (
    <fieldset className="facet"><legend>{title}</legend>
      <div className="chips">{shown.map((o) => <button key={o} className={`chip toggle ${sel.includes(o) ? "on" : ""}`} aria-pressed={sel.includes(o)} onClick={() => on(o)}>{o}</button>)}</div>
      {opts.length > 10 && <button className="link small" onClick={() => setAll(!all)}>{all ? "fewer" : `all ${opts.length}`}</button>}
    </fieldset>
  );
}
