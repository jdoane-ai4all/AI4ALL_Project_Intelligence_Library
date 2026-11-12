export type Level = "confirmed" | "inferred" | "unknown";

export interface Term {
  id: string; label: string; parent: string | null; level: Level; primary: boolean;
  page?: string | null; quote?: string | null; verified?: number | null;
}
export interface Algorithm {
  id: string; label: string; original: string; role: string; purpose?: string; inputs?: string; outputs?: string;
  result?: string; level: Level; family?: string; difficulty?: number; page?: string; quote?: string; verified?: number | null;
}
export interface Dataset {
  id: string; name: string; url?: string | null; platform?: string; publisher?: string; description?: string;
  modality?: string; access?: string; license?: string; availability?: string; link_status?: string | null;
  relationship: "used" | "mentioned" | "alternative"; match: string; discovery_level?: number; original?: string;
  evidence?: string; confidence?: string; comments?: string;
}
export interface AssessmentCell { value: number | null; label: string | null; rationale: string | null; method?: string; confidence?: string }
export interface Project {
  id: string; title: string; title_slide: string; student_description: string; student_type: string | null;
  summary: { plain: string; technical: string; question: string; problem: string; beneficiary: string; domain: string;
    subdomain: string; inputs: string; outputs: string; results: string };
  source: { completeness: string; confidence: string; status: string; pdf_url: string; text_url: string };
  terms: Record<string, Term[]>;
  algorithms: Algorithm[]; datasets: Dataset[]; dataset_clues: { status: string; clue: string; notes: string }[];
  rubric: { total: number; criteria: Record<string, { score: number; eval_score: number; limiting: string | null; rationale: string; slides: string; evidence: string }> };
  assessments: Record<string, Record<string, AssessmentCell>>;
  originality: Record<string, Record<string, { score: number | null; label: string | null; rationale: string | null; confidence: string; method: string }>>;
  precedents: { title: string; url: string; kind: string; date: string; comparability: string }[];
  tags: string[];
  cluster: { id: number; label: string; x: number; y: number; z: number } | null;
  review: { field: string; reason: string; priority: string }[];
  quality_flags: { category: string; severity: "critical" | "moderate" | "minor"; label: string; text: string; acknowledged: boolean }[];
  recommendation: { status: "hold" | "caution" | "ok"; reason: string | null; reviewer_decision: string | null; reviewer_notes?: string | null };
  audit: { check: string; severity: string; detail: string }[];
}
export interface Edge { source: string; target: string; view: string; weight: number; rank: number; explanation: string; shared: string }
export interface Library {
  meta: Record<string, string>; projects: Project[]; edges: Edge[];
  rubric: { criterion: string; level: number; level_name: string; description: string }[];
  taxonomy: { term_id: string; dimension: string; label: string; parent_id: string | null; attributes: string | null }[];
}
