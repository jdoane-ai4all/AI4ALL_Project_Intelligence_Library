import { useEffect, useRef } from "react";
import type { Library, Project } from "../types";
import { CRITERIA, internalOriginality, labels, sophistication, tier } from "../logic";
import { Badge, Level, Meter } from "./ui";

const ROLE_ORDER = ["implemented", "baseline", "compared", "considered", "proposed", "unclear"];
const ORIG_LABELS: Record<string, string> = {
  established: "Established approach", distinctive_application: "Standard techniques, distinctive application",
  unusual_combination: "Unusual combination of established methods", potentially_novel: "Potentially novel — requires verification",
  not_assessed: "Not assessed — precedent search did not run",
};

export default function Detail({ p, lib, byId, onClose, onSelect }: {
  p: Project; lib: Library; byId: Map<string, Project>; onClose: () => void; onSelect: (id: string) => void;
}) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => { ref.current?.focus(); ref.current?.scrollTo(0, 0); }, [p.id]);
  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k); return () => window.removeEventListener("keydown", k);
  }, [onClose]);
  const a = p.assessments;
  const related = lib.edges.filter((e) => e.view === "overall" && (e.source === p.id || e.target === p.id))
    .sort((x, y) => y.weight - x.weight).slice(0, 8)
    .map((e) => ({ e, other: byId.get(e.source === p.id ? e.target : e.source)! })).filter((r) => r.other);
  const crossView = lib.edges.filter((e) => e.view !== "overall" && (e.source === p.id || e.target === p.id))
    .sort((x, y) => y.weight - x.weight);
  const io = p.originality.internal || {};
  const eo = p.originality.external || {};
  const algs = [...p.algorithms].sort((x, y) => ROLE_ORDER.indexOf(x.role) - ROLE_ORDER.indexOf(y.role));

  return (
    <aside className="detail" ref={ref} tabIndex={-1} aria-label={`Project profile: ${p.title}`}>
      <div className="detail-head">
        <div>
          <div className="muted mono small">{p.id} · group-chosen industry: {p.student_type || "Not provided"}</div>
          <h2>{p.title}</h2>
          {p.title_slide && p.title_slide.toLowerCase() !== p.title.toLowerCase() && <div className="muted small">Title slide: {p.title_slide}</div>}
        </div>
        <button className="ghost close" onClick={onClose} aria-label="Close">✕</button>
      </div>

      {p.recommendation?.status !== "ok" && (
        <div className={`qbanner q-${p.recommendation.status}`} role="note">
          <b>{p.recommendation.status === "hold" ? "Withheld — not recommended as a model example" : "Use with caution"}</b>
          {p.recommendation.reviewer_decision && <span className="small"> · program reviewer: {p.recommendation.reviewer_decision}</span>}
          {p.recommendation.reviewer_notes && <p className="small reviewer-note"><b>Reviewer note.</b> {p.recommendation.reviewer_notes}</p>}
          <ul>{p.quality_flags.filter((q) => q.severity !== "minor").map((q, i) => (
            <li key={i}><span className={`pill sev-${q.severity}`}>{q.severity}</span> {q.label}{q.acknowledged ? " (acknowledged by the team)" : ""}
              <details><summary className="small">details</summary><span className="small">{q.text}</span></details></li>))}</ul>
          <div className="small muted">Flags describe the presentation materials, not the students, and do not change the original grades.</div>
        </div>)}
      <div className="kpis">
        <Meter label="Sophistication" v={sophistication(p)} max={10} est />
        <Meter label="Originality (internal)" v={internalOriginality(p)} max={100} est />
        <Meter label="Readiness" v={a.adoption_readiness?.overall?.value} max={7} est />
        <Meter label="Rubric total" v={p.rubric.total} max={25} />
        <div className="kpi-tags">
          <Badge kind={tier(p) ?? ""}>{tier(p) ?? "—"}</Badge>
          <span className="chip">{a.reproduction_effort?.overall?.label ?? "?"} effort</span>
          <span className="chip">{p.source.confidence} confidence</span>
        </div>
      </div>
      <p className="small muted">* Estimated using the documented framework (Method tab). Rubric scores are the original grades, unchanged.</p>

      <Section title="Summary">
        <p>{p.summary.plain}</p>
        {p.summary.question && <p><b>Research question.</b> {p.summary.question}</p>}
        <details><summary>Technical summary</summary><p>{p.summary.technical}</p>
          {p.summary.results && <p><b>Reported results.</b> {p.summary.results}</p>}</details>
        <details><summary>Student-provided description</summary><p className="quote">{p.student_description}</p></details>
        <dl className="kv">
          {p.summary.problem && <><dt>Problem</dt><dd>{p.summary.problem}</dd></>}
          {p.summary.beneficiary && <><dt>Beneficiary</dt><dd>{p.summary.beneficiary}</dd></>}
          {p.summary.inputs && <><dt>Inputs</dt><dd>{p.summary.inputs}</dd></>}
          {p.summary.outputs && <><dt>Outputs</dt><dd>{p.summary.outputs}</dd></>}
        </dl>
      </Section>

      <Section title="Classification" note="● confirmed in source · ◐ inferred">
        {(["industry", "paradigm", "task", "modality", "method", "tool"] as const).map((d) => (p.terms[d]?.length ? (
          <div key={d} className="tagrow"><span className="tagdim">{d === "method" ? "techniques" : d}</span>
            {p.terms[d].filter((t) => d !== "industry" || t.parent || !p.terms[d].some((x) => x.parent === t.id)).map((t) => (
              <span key={t.id} className={`chip ${t.primary ? "primary" : ""}`} title={t.quote ? `p${t.page}: “${t.quote}”` : t.level}>
                <Level level={t.level} /> {t.label}</span>))}
          </div>) : null))}
      </Section>

      <Section title="Algorithms & models">
        <table className="table compact">
          <thead><tr><th>Model</th><th>Role</th><th>Purpose / output</th><th>Reported result</th></tr></thead>
          <tbody>{algs.map((x, i) => (
            <tr key={i}><td><Level level={x.level} /> <b>{x.label}</b>{x.original && x.original !== x.label && <div className="muted small">“{x.original}”</div>}</td>
              <td><span className={`role r-${x.role}`}>{x.role}</span></td>
              <td className="small">{x.purpose}{x.outputs && <div className="muted">→ {x.outputs}</div>}</td>
              <td className="small">{x.result ?? "—"}{x.page && <div className="muted">p.{x.page}</div>}</td></tr>))}</tbody>
        </table>
      </Section>

      <Section title="Datasets">
        {p.datasets.length === 0 && p.dataset_clues.filter((c) => c.status === "extracted").length > 0 && (
          <p className="muted small">Dataset research has not yet been run for this project. References found in the source:</p>)}
        {p.datasets.length === 0 && p.dataset_clues.filter((c) => c.status === "extracted").map((c, i) => {
          const d = safeJson(c.clue); return <div key={i} className="ds pending"><b>{d.name_guess || d.original_reference}</b> <span className="muted small">({c.notes})</span>
            {d.url_in_source && <div className="small mono break">{d.url_in_source} <span className="muted">(as written in source; not yet verified)</span></div>}</div>;
        })}
        {p.datasets.map((d) => (
          <div key={d.id + d.relationship} className={`ds m-${d.match}`}>
            <div><b>{d.name}</b> <span className={`pill m-${d.match}`}>{d.relationship === "alternative" ? "alternative" : `${d.match} match`}</span>
              {d.relationship === "mentioned" && <span className="pill">mentioned only</span>}</div>
            {d.url && <div className="small"><a href={d.url} target="_blank" rel="noreferrer noopener">{d.url}</a> <span className="muted">· public dataset link · {d.link_status ?? "not checked"}</span></div>}
            <div className="small muted">{[d.platform, d.publisher, d.modality, d.access, d.license && `license: ${d.license}`].filter(Boolean).join(" · ")}</div>
            {d.evidence && <div className="small">Evidence: {d.evidence}</div>}
          </div>))}
        {p.dataset_clues.filter((c) => c.status === "unresolved").map((c, i) => <div key={i} className="ds unresolved small">Unresolved: {c.clue} <span className="muted">{c.notes}</span></div>)}
      </Section>

      <Section title="Difficulty, effort & prerequisites" note="estimated">
        <p><Badge kind={tier(p) ?? ""}>{tier(p)}</Badge> <span className="small">{a.difficulty_tier?.overall?.rationale}</span></p>
        <div className="two">
          <div><h4>Prerequisites (1–3)</h4>{["python", "math_stats", "ml", "domain"].map((k) => (
            <Row key={k} k={k.replace("_", " & ")} v={a.prerequisites?.[k]?.value} max={3} why={a.prerequisites?.[k]?.rationale} />))}
            <div className="small muted">Minimum hardware: {a.prerequisites?.hardware?.label?.replace(/_/g, " ")}</div></div>
          <div><h4>Reproduction effort: {a.reproduction_effort?.overall?.label}</h4>
            <div className="small muted">{a.reproduction_effort?.overall?.rationale}</div>
            {["data_access", "data_preparation", "implementation", "compute", "dependencies"].map((k) => (
              <Row key={k} k={k.replace("_", " ")} v={a.reproduction_effort?.[k]?.value} max={3} why={a.reproduction_effort?.[k]?.rationale} />))}</div>
        </div>
        <details><summary>Technical sophistication components</summary>
          {Object.entries(a.sophistication || {}).filter(([k]) => k !== "overall").map(([k, v]) => <Row key={k} k={k.replace(/_/g, " ")} v={v.value} max={3} why={v.rationale} />)}
        </details>
        <details><summary>Adoption readiness ({a.adoption_readiness?.overall?.label})</summary>
          <ul className="checklist">{Object.entries(a.adoption_readiness || {}).filter(([k]) => k !== "overall").map(([k, v]) => <li key={k} className={v.value ? "yes" : "no"}>{k.replace(/_/g, " ")}</li>)}</ul>
        </details>
        {Object.keys(a.extension_ideas || {}).length > 0 && <details><summary>Extension ideas (from the project's next steps)</summary>
          <ul>{Object.values(a.extension_ideas).map((v, i) => <li key={i}>{v.label}</li>)}</ul></details>}
      </Section>

      <Section title="Originality" note="two separate measures">
        <div className="two">
          <div><h4>Within this collection</h4>
            <p><b>{io.composite?.score?.toFixed(0) ?? "—"}</b>/100 percentile · {io.composite?.label}</p>
            {["semantic_isolation", "algorithm_rarity", "domain_rarity", "combination_rarity"].map((k) => <Row key={k} k={k.replace("_", " ")} v={io[k]?.score} max={100} />)}
          </div>
          <div><h4>Against external precedents</h4>
            {eo.classification ? <><p><b>{ORIG_LABELS[eo.classification.label ?? ""] ?? eo.classification.label}</b> <span className="muted small">({eo.classification.confidence} confidence)</span></p>
              <p className="small">{eo.classification.rationale}</p>
              {["problem", "application_domain", "algorithmic", "data", "integration"].map((k) => <Row key={k} k={k.replace("_", " ")} v={eo[k]?.score} max={5} why={eo[k]?.rationale ?? undefined} />)}
              <p className="small muted">Absence of found precedents is not proof of novelty.</p></>
              : <p className="muted small">External precedent research not yet available for this project.</p>}
          </div>
        </div>
        {p.precedents.length > 0 && <><h4>Comparable external work</h4><ul className="small">{p.precedents.map((x, i) => (
          <li key={i}>{x.url ? <a href={x.url} target="_blank" rel="noreferrer noopener">{x.title}</a> : x.title} <span className="muted">({x.kind}{x.date ? `, ${x.date}` : ""})</span> — {x.comparability}</li>))}</ul></>}
      </Section>

      <Section title="Original rubric evaluation" note="authoritative grades — unchanged">
        <table className="table compact">
          <tbody>{CRITERIA.map((c) => { const r = p.rubric.criteria[c]; return (
            <tr key={c}><th>{c}</th><td className="mono">{r?.score}/5{r && r.eval_score !== r.score && <span className="warn" title="Scores sheet and rationale sheet disagree"> ⚠ {r.eval_score}</span>}</td>
              <td className="small"><details><summary>{(r?.rationale || "").slice(0, 110)}{(r?.rationale || "").length > 110 ? "…" : ""}</summary>
                <p>{r?.rationale}</p><p className="muted">Slides cited: {r?.slides} {r?.limiting && <>· limiting factors: {r.limiting}</>}</p><p className="quote">{r?.evidence}</p></details></td></tr>); })}
            <tr><th>Total</th><td className="mono"><b>{p.rubric.total}</b>/25</td><td /></tr></tbody>
        </table>
      </Section>

      <Section title="Related projects">
        {related.length === 0 && <p className="muted small">No strong neighbors.</p>}
        {related.map(({ e, other }) => (
          <button key={other.id} className="related" onClick={() => onSelect(other.id)}>
            <span><b>{other.title}</b> <span className="muted small">{(e.weight * 100).toFixed(0)}%</span></span>
            <span className="small muted">{e.explanation}</span></button>))}
        {crossView.length > 0 && <details><summary>Connections by specific dimension ({crossView.length})</summary>
          {crossView.slice(0, 14).map((e, i) => { const o = byId.get(e.source === p.id ? e.target : e.source); return o ? (
            <button key={i} className="related" onClick={() => onSelect(o.id)}><span><span className="pill">{e.view}</span> {o.title}</span><span className="small muted">{e.explanation}</span></button>) : null; })}
        </details>}
      </Section>

      <Section title="Sources & quality">
        {p.recommendation?.status === "ok" && p.recommendation.reviewer_decision && (
          <p className="small"><b>Program review:</b> {p.recommendation.reviewer_decision}{p.recommendation.reviewer_notes ? ` — ${p.recommendation.reviewer_notes}` : ""}</p>)}
        <p className="small">Source completeness: <b>{p.source.completeness}</b> · extraction confidence: <b>{p.source.confidence}</b> · status: {p.source.status}</p>
        <p className="small"><a href={p.source.pdf_url} target="_blank" rel="noreferrer noopener">Original presentation (private student file)</a> · <a href={p.source.text_url} target="_blank" rel="noreferrer noopener">Extracted text (private)</a></p>
        {p.audit.length > 0 && <ul className="small warnlist">{p.audit.map((x, i) => <li key={i}>Data audit: {x.detail}</li>)}</ul>}
        {p.review.length > 0 && <details><summary>Open review items ({p.review.length})</summary>
          <ul className="small">{p.review.map((r, i) => <li key={i}><span className="pill">{r.field}</span> {r.reason}</li>)}</ul></details>}
        {p.tags.length > 0 && <div className="chips">{p.tags.map((t) => <span key={t} className="chip small">{t}</span>)}</div>}
      </Section>
    </aside>
  );
}

function Section({ title, note, children }: { title: string; note?: string; children: React.ReactNode }) {
  return <section className="dsec"><h3>{title} {note && <span className="muted small">· {note}</span>}</h3>{children}</section>;
}
function Row({ k, v, max, why }: { k: string; v: number | null | undefined; max: number; why?: string | null }) {
  return <div className="row-m" title={why ?? ""}><span className="rk">{k}</span><div className="meter-bar"><div className="meter-fill est" style={{ width: `${v == null ? 0 : (v / max) * 100}%` }} /></div><span className="mono small">{v == null ? "—" : Number.isInteger(v) ? v : v.toFixed(0)}</span>{why && <span className="why small muted">{why}</span>}</div>;
}
function safeJson(s: string) { try { return JSON.parse(s); } catch { return { original_reference: s }; } }
export { labels };
