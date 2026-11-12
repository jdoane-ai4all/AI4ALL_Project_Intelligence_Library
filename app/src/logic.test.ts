import { describe, expect, it } from "vitest";
import { applyFilters, emptyFilters, parsePrompt, recommend, labels, algorithmsUsed, datasetAvailability } from "./logic";
import type { Project } from "./types";

// Synthetic fixtures only — no real student data in tests.
function mk(id: string, o: Partial<{ ind: string; par: string; alg: string; role: string; tier: string; effort: string; soph: number; py: number; ml: number; total: number; ds: boolean; hold: boolean }>): Project {
  return {
    id, title: `Title ${id}`, title_slide: "", student_description: "", student_type: null,
    summary: { plain: "summary", technical: "", question: "", problem: "", beneficiary: "", domain: "", subdomain: "", inputs: "", outputs: "", results: "" },
    source: { completeness: "complete", confidence: "high", status: o.ds ? "researched" : "extracted", pdf_url: "", text_url: "" },
    terms: {
      industry: [{ id: `industry:${o.ind}`, label: o.ind ?? "Finance & Business", parent: null, level: "confirmed", primary: true }],
      paradigm: [{ id: "paradigm:x", label: o.par ?? "Supervised learning", parent: null, level: "confirmed", primary: false }],
    },
    algorithms: [{ id: "a", label: o.alg ?? "Random forest", original: "", role: o.role ?? "implemented", level: "confirmed" }],
    datasets: o.ds ? [{ id: "d", name: "D", url: "https://example.org/d", relationship: "used", match: "exact" }] : [],
    dataset_clues: [],
    rubric: { total: o.total ?? 20, criteria: {} },
    assessments: {
      difficulty_tier: { overall: { value: 1, label: o.tier ?? "Beginner", rationale: "" } },
      reproduction_effort: { overall: { value: 4, label: o.effort ?? "Moderate", rationale: "" } },
      sophistication: { overall: { value: o.soph ?? 5, label: null, rationale: "" } },
      prerequisites: { python: { value: o.py ?? 1, label: null, rationale: "" }, ml: { value: o.ml ?? 1, label: null, rationale: "" } },
    },
    originality: { internal: { composite: { score: 50, label: "x", rationale: "", confidence: "", method: "" } } },
    precedents: [], tags: [], cluster: null, review: [], audit: [],
    quality_flags: o.hold ? [{ category: "data_leakage", severity: "critical", label: "Label leakage", text: "", acknowledged: false }] : [],
    recommendation: { status: o.hold ? "hold" : "ok", reason: null, reviewer_decision: null },
  } as unknown as Project;
}
const ps = [
  mk("p1", { ind: "Healthcare & Life Sciences", alg: "Random forest", tier: "Beginner", soph: 3, ds: true }),
  mk("p2", { ind: "Finance & Business", alg: "LSTM", tier: "Advanced", soph: 8, py: 3, ml: 3, effort: "High" }),
  mk("p3", { ind: "Healthcare & Life Sciences", alg: "Random forest", role: "proposed", tier: "Intermediate", soph: 5 }),
];

describe("filters", () => {
  it("no filters returns all", () => expect(applyFilters(ps, emptyFilters())).toHaveLength(3));
  it("industry filter", () => expect(applyFilters(ps, { ...emptyFilters(), industry: ["Healthcare & Life Sciences"] }).map((p) => p.id)).toEqual(["p1", "p3"]));
  it("algorithm filter only counts used algorithms, not proposed", () =>
    expect(applyFilters(ps, { ...emptyFilters(), algorithm: ["Random forest"] }).map((p) => p.id)).toEqual(["p1"]));
  it("range filter", () => expect(applyFilters(ps, { ...emptyFilters(), soph: [6, 10] }).map((p) => p.id)).toEqual(["p2"]));
  it("search hits restrict", () => expect(applyFilters(ps, emptyFilters(), new Set(["p3"]))).toHaveLength(1));
});

describe("helpers", () => {
  it("labels and algorithms", () => {
    expect(labels(ps[0], "industry")).toEqual(["Healthcare & Life Sciences"]);
    expect(algorithmsUsed(ps[2])).toEqual([]);
  });
  it("dataset availability", () => {
    expect(datasetAvailability(ps[0])).toBe("Public dataset identified");
    expect(datasetAvailability(ps[1])).toBe("Not yet researched");
  });
});

describe("recommend", () => {
  it("respects interests as a hard constraint and explains reasons", () => {
    const r = recommend(ps, { interests: ["Healthcare & Life Sciences"], paradigms: [], algorithms: [], python: 1, ml: 1, hours: "2-4", wantOriginal: false, needPublicData: true });
    expect(r.map((x) => x.project.id)).toEqual(["p1", "p3"]);
    expect(r[0].reasons.join(" ")).toMatch(/Healthcare/);
  });
  it("penalizes prerequisite gaps", () => {
    const r = recommend(ps, { interests: [], paradigms: [], algorithms: [], python: 1, ml: 1, hours: "2-4", wantOriginal: false, needPublicData: false });
    expect(r[r.length - 1].project.id).toBe("p2");
    expect(r[r.length - 1].cautions.length).toBeGreaterThan(0);
  });
  it("parses free text", () => {
    const g = parsePrompt("I know basic Python and want a climate project, about 5 hours a week", { industries: ["Environmental Science & Climate"], paradigms: [], algorithms: [] });
    expect(g.interests).toEqual(["Environmental Science & Climate"]);
    expect(g.hours).toBe("4-6"); expect(g.python).toBe(1);
    expect(parsePrompt("two hrs per week", { industries: [], paradigms: [], algorithms: [] }).hours).toBe("2-4");
    expect(parsePrompt("6-8 hours weekly", { industries: [], paradigms: [], algorithms: [] }).hours).toBe("6+");
  });
});

describe("methodological holds", () => {
  const held = [...ps, mk("p4", { ind: "Healthcare & Life Sciences", hold: true, ds: true })];
  const g = { interests: ["Healthcare & Life Sciences"], paradigms: [], algorithms: [], python: 1 as const, ml: 1 as const, hours: "2-4" as const, wantOriginal: false, needPublicData: false };
  it("never recommends withheld projects by default", () => expect(recommend(held, g).map((r) => r.project.id)).not.toContain("p4"));
  it("can include them explicitly, with a warning", () => {
    const r = recommend(held, { ...g, includeHeld: true }).find((x) => x.project.id === "p4")!;
    expect(r.cautions[0]).toMatch(/Withheld/);
  });
});
