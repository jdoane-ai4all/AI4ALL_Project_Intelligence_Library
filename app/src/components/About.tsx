import type { Library } from "../types";

export default function About({ lib }: { lib: Library }) {
  const crit = [...new Set(lib.rubric.map((r) => r.criterion))];
  return (
    <div className="about prose">
      <h2>How this atlas was built</h2>
      <p>Each project record was extracted from the student's presentation text (and slide images where needed) with an evidence-grounded schema: every confirmed classification carries a page reference and a verbatim quote that is automatically checked against the source. <b>Confirmed</b> (●) means explicitly stated; <b>inferred</b> (◐) means reasonably derived but not stated.</p>
      <h3>Separate constructs — never mixed</h3>
      <ul>
        <li><b>Original rubric scores</b> — the authoritative historical grades on five criteria ({crit.join(", ")}). They measure rubric compliance, not holistic quality. They are displayed unchanged.</li>
        <li><b>Technical sophistication</b> (0–10, estimated) — mean of six anchored components (algorithmic complexity, data processing, methodological breadth, validation rigor, engineering, mathematical depth), rated for what the project <i>demonstrated</i>.</li>
        <li><b>Difficulty tier</b> (estimated) — background a new student needs for a comparable project, derived by a fixed rule from prerequisite ratings and the most advanced algorithm used.</li>
        <li><b>Reproduction effort</b> (estimated) — sum of five 0–3 components (data access, preparation, implementation, compute, dependencies) mapped to bands. A sophisticated project with clean data can be easier to reproduce than a simple one with hard-to-get data.</li>
        <li><b>Internal originality</b> (computed) — percentile within this collection: semantic isolation, algorithm rarity, domain rarity and method–domain combination rarity.</li>
        <li><b>External originality</b> (researched) — classification against precedents found by web search. Absence of results is not proof of novelty.</li>
      </ul>
      <h3>Similarity & clusters</h3>
      <p>Connections are sparse nearest-neighbor edges computed separately for topic semantics, algorithms, industry, technical approach, shared datasets and skill profile, plus a blended view. Every edge carries a generated explanation of what is shared. Clusters come from Ward clustering on a blended representation; their labels are the most over-represented taxonomy terms and boundaries should be read as soft.</p>
      <h3>Privacy</h3>
      <p>This build contains private student work and links to private student files. It must not be published. Dataset links are public resources; presentation links are private student files.</p>
      <p className="muted small">Schema {lib.meta.schema_version} · taxonomy {lib.meta.taxonomy_version} · pipeline {lib.meta.pipeline_version} · built {lib.meta.built_at}</p>
    </div>
  );
}
