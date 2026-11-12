// Pure, testable logic: derived fields, filtering, sorting, recommendation scoring.
import type { Project } from "./types";

export const CRITERIA = ["Project Description", "Algorithm", "Essential Question", "Next Steps", "Citations"];
export const TIERS = ["Beginner", "Intermediate", "Advanced"];
export const EFFORT = ["Low", "Moderate", "High", "Very high"];

const ok = (l: string) => l === "confirmed" || l === "inferred";

export function labels(p: Project, dim: string, opts: { topOnly?: boolean; leafOnly?: boolean } = {}): string[] {
  const items = (p.terms[dim] || []).filter((t) => ok(t.level));
  const f = items.filter((t) => (opts.topOnly ? !t.parent : opts.leafOnly ? !!t.parent || !items.some((x) => x.parent === t.id) : true));
  return [...new Set(f.map((t) => t.label))].sort();
}
export const algorithmsUsed = (p: Project) =>
  [...new Set(p.algorithms.filter((a) => ["implemented", "baseline", "compared"].includes(a.role)).map((a) => a.label))].sort();

export const tier = (p: Project) => p.assessments.difficulty_tier?.overall?.label ?? null;
export const effort = (p: Project) => p.assessments.reproduction_effort?.overall?.label ?? null;
export const effortScore = (p: Project) => p.assessments.reproduction_effort?.overall?.value ?? null;
export const sophistication = (p: Project) => p.assessments.sophistication?.overall?.value ?? null;
export const readiness = (p: Project) => p.assessments.adoption_readiness?.overall?.value ?? null;
export const internalOriginality = (p: Project) => p.originality.internal?.composite?.score ?? null;
export const externalOriginality = (p: Project) => p.originality.external?.classification?.label ?? null;
export const prereq = (p: Project, k: string) => p.assessments.prerequisites?.[k]?.value ?? null;
export const primaryIndustry = (p: Project) => {
  const items = p.terms.industry || [];
  const prim = items.find((t) => t.primary);
  const top = prim ? (prim.parent ? items.find((t) => t.id === prim.parent)?.label ?? prim.parent : prim.label) : items.find((t) => !t.parent)?.label;
  return top ?? p.student_type ?? "Unclassified";
};
export const REVIEW_STATUS: Record<string, string> = { hold: "Withheld for review", caution: "Use with caution", ok: "No major issues" };
export const reviewStatus = (p: Project) => REVIEW_STATUS[p.recommendation?.status ?? "ok"];

export function datasetAvailability(p: Project): "Public dataset identified" | "Alternative only" | "Unresolved" | "Not yet researched" {
  const used = p.datasets.filter((d) => d.relationship === "used" && ["exact", "probable"].includes(d.match) && d.url);
  if (used.length) return "Public dataset identified";
  if (p.datasets.some((d) => d.relationship === "alternative" && d.url)) return "Alternative only";
  if (p.source.status === "researched") return "Unresolved";
  return "Not yet researched";
}

export interface Filters {
  q: string;
  industry: string[]; paradigm: string[]; algorithm: string[]; task: string[]; modality: string[];
  tier: string[]; effort: string[]; data: string[]; review: string[];
  soph: [number, number]; orig: [number, number]; rubric: [number, number];
}
export const emptyFilters = (): Filters => ({
  q: "", industry: [], paradigm: [], algorithm: [], task: [], modality: [], tier: [], effort: [], data: [], review: [],
  soph: [0, 10], orig: [0, 100], rubric: [5, 25],
});

const anyOf = (sel: string[], vals: string[]) => sel.length === 0 || sel.some((s) => vals.includes(s));
const inRange = (v: number | null, [a, b]: [number, number], full: [number, number]) =>
  (a === full[0] && b === full[1]) || (v !== null && v >= a && v <= b);

export function applyFilters(ps: Project[], f: Filters, searchHits?: Set<string> | null): Project[] {
  return ps.filter((p) =>
    (!searchHits || searchHits.has(p.id)) &&
    anyOf(f.industry, labels(p, "industry")) &&
    anyOf(f.paradigm, labels(p, "paradigm")) &&
    anyOf(f.algorithm, algorithmsUsed(p)) &&
    anyOf(f.task, labels(p, "task")) &&
    anyOf(f.modality, labels(p, "modality")) &&
    anyOf(f.tier, [tier(p) ?? ""]) &&
    anyOf(f.effort, [effort(p) ?? ""]) &&
    anyOf(f.data, [datasetAvailability(p)]) &&
    anyOf(f.review, [reviewStatus(p)]) &&
    inRange(sophistication(p), f.soph, [0, 10]) &&
    inRange(internalOriginality(p), f.orig, [0, 100]) &&
    inRange(p.rubric.total, f.rubric, [5, 25]),
  );
}

export function facetCounts(ps: Project[], get: (p: Project) => string[]): [string, number][] {
  const m = new Map<string, number>();
  for (const p of ps) for (const v of new Set(get(p))) m.set(v, (m.get(v) || 0) + 1);
  return [...m.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
}

// ---------------------------------------------------------------- guided discovery
export interface GuideInput {
  interests: string[];          // industry labels (top-level or subdomain)
  paradigms: string[];          // paradigm labels
  algorithms: string[];         // algorithm labels
  python: 1 | 2 | 3;            // student's python level
  ml: 1 | 2 | 3;                // student's ML level
  hours: HoursBand;             // time available per week
  wantOriginal: boolean;
  needPublicData: boolean;
  includeHeld?: boolean;        // projects withheld after methodological review are excluded unless explicitly included
}
// Program calendar: 13 weeks, of which ~9 are working weeks (familiarization/proposal through build).
export type HoursBand = "2-4" | "4-6" | "6+";
export const PROGRAM_WEEKS = 9;
export const HOURS_BANDS: Record<HoursBand, { label: string; perWeek: number }> = {
  "2-4": { label: "2–4 hrs/week", perWeek: 3 }, "4-6": { label: "4–6 hrs/week", perWeek: 5 }, "6+": { label: "6+ hrs/week", perWeek: 7 },
};
export const EFFORT_HOURS: Record<string, number> = { Low: 12, Moderate: 25, High: 45, "Very high": 70 };
export const availableHours = (h: HoursBand) => HOURS_BANDS[h].perWeek * PROGRAM_WEEKS;

export interface Rec { project: Project; score: number; reasons: string[]; cautions: string[] }


/** Transparent, retrieval-grounded scoring over the actual catalog. Every point awarded has a stated reason. */
export function recommend(ps: Project[], g: GuideInput, n = 8): Rec[] {
  const recs: Rec[] = [];
  for (const p of ps) {
    if (!p.summary?.plain) continue;
    const st = p.recommendation?.status ?? "ok";
    if (st === "hold" && !g.includeHeld) continue;
    let s = 0; const reasons: string[] = []; const cautions: string[] = [];
    const ind = labels(p, "industry");
    const hitInd = g.interests.filter((i) => ind.includes(i));
    if (g.interests.length) {
      if (hitInd.length) { s += 4; reasons.push(`Matches your interest in ${hitInd.join(", ")}`); }
      else continue; // interests are a hard constraint when given
    }
    const par = labels(p, "paradigm");
    const hitPar = g.paradigms.filter((x) => par.includes(x));
    if (g.paradigms.length) {
      if (hitPar.length) { s += 3; reasons.push(`Uses ${hitPar.join(", ").toLowerCase()}`); } else s -= 2;
    }
    const algs = algorithmsUsed(p);
    const hitAlg = g.algorithms.filter((x) => algs.includes(x));
    if (g.algorithms.length) {
      if (hitAlg.length) { s += 3; reasons.push(`Actually implements ${hitAlg.join(", ")}`); } else s -= 2;
    }
    const py = prereq(p, "python") ?? 2, ml = prereq(p, "ml") ?? 2;
    const gap = Math.max(0, py - g.python) + Math.max(0, ml - g.ml);
    if (gap === 0) { s += 2; reasons.push("Prerequisites fit your current Python/ML background"); }
    else { s -= 1.5 * gap; cautions.push(`Expects more background than you listed (Python ${py}/3, ML ${ml}/3)`); }
    const e = effort(p);
    if (e) {
      const need = EFFORT_HOURS[e] ?? 40, have = availableHours(g.hours);
      if (need <= have) { s += 2; reasons.push(`${e} effort (~${need} hrs) fits ${HOURS_BANDS[g.hours].label} over the program (~${have} hrs)`); }
      else { s -= Math.min(3, (need - have) / 10); cautions.push(`${e} effort (~${need} hrs) likely exceeds ${HOURS_BANDS[g.hours].label} (~${have} hrs); consider a team`); }
    }
    const avail = datasetAvailability(p);
    if (avail === "Public dataset identified") { s += 1.5; reasons.push("Has a verified public dataset link"); }
    else if (g.needPublicData) { s -= 3; cautions.push(`Dataset: ${avail.toLowerCase()}`); }
    const io = internalOriginality(p);
    if (g.wantOriginal && io !== null) { s += (io - 50) / 20; if (io >= 70) reasons.push(`Distinctive within this collection (originality percentile ${Math.round(io)})`); }
    const issues = (p.quality_flags ?? []).filter((q) => q.severity !== "minor");
    if (st === "hold") { s -= 10; cautions.unshift(`Withheld: ${issues[0]?.label ?? "methodological issue"} — not a model example`); }
    else if (st === "caution") {
      s -= 1;
      const note = p.recommendation?.reviewer_notes;
      cautions.unshift(note ? `Reviewer note: ${note}` : `Review note: ${issues.map((q) => q.label).slice(0, 2).join("; ")}`);
    }
    recs.push({ project: p, score: Math.round(s * 10) / 10, reasons, cautions });
  }
  return recs.sort((a, b) => b.score - a.score).slice(0, n);
}

/** Lightweight free-text parser mapping a prompt to guide inputs using the catalog's own vocabulary. */
export function parsePrompt(text: string, vocab: { industries: string[]; paradigms: string[]; algorithms: string[] }): Partial<GuideInput> {
  const t = text.toLowerCase();
  const syn: Record<string, string[]> = {
    "Environmental Science & Climate": ["climate", "environment", "weather", "wildfire", "flood", "pollution"],
    "Healthcare & Life Sciences": ["health", "medical", "medicine", "disease", "clinical", "hospital"],
    "Finance & Business": ["finance", "stock", "trading", "business", "bank", "crypto", "credit"],
    "Manufacturing & Infrastructure": ["manufacturing", "factory", "industrial", "infrastructure", "bridge"],
    "Entertainment & Media": ["music", "movie", "film", "game", "media", "entertainment"],
    "Sports": ["sport", "basketball", "football", "soccer", "nba"],
    "Education": ["education", "student", "school", "learning outcomes"],
    "Cybersecurity": ["security", "phishing", "fraud", "spam", "cyber"],
    "Agriculture & Food": ["agriculture", "crop", "farm", "food"],
  };
  const interests = vocab.industries.filter((i) => t.includes(i.toLowerCase()) || (syn[i] || []).some((w) => t.includes(w)));
  const paradigms = vocab.paradigms.filter((p) => t.includes(p.toLowerCase().split(" ")[0]) && t.includes(p.toLowerCase().split(" ").slice(-1)[0]));
  const algorithms = vocab.algorithms.filter((a) => t.includes(a.toLowerCase()));
  const words: Record<string, number> = { one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, ten: 10 };
  const hr = t.match(/(\d+|one|two|three|four|five|six|seven|eight|ten)(?:\s*(?:-|to)\s*(\d+))?\s*(?:hours|hrs|hr|h)\b/);
  const out: Partial<GuideInput> = { interests, paradigms, algorithms };
  if (hr) {
    const n = Number(hr[2] ?? hr[1]) || words[hr[1]] || 3;
    out.hours = n >= 6 ? "6+" : n >= 4 ? "4-6" : "2-4";
  }
  if (/basic python|beginner|new to|just started/.test(t)) { out.python = 1; out.ml = 1; }
  else if (/advanced|experienced|deep learning experience/.test(t)) { out.python = 3; out.ml = 3; }
  if (/original|unusual|unique|novel/.test(t)) out.wantOriginal = true;
  return out;
}
