import { useState } from "react";
import type { Library } from "../types";

// Shown when the app has no bundled data (e.g. on GitHub Pages, which is public). The viewer opens their own private
// library.json; it is read in this browser only and never uploaded anywhere.
export function parseLibrary(text: string): Library {
  const lib = JSON.parse(text) as Library;
  if (!lib || !Array.isArray(lib.projects) || !Array.isArray(lib.edges) || !Array.isArray(lib.rubric)) {
    throw new Error("This doesn't look like an atlas data bundle (expected projects, edges and rubric).");
  }
  return lib;
}

export default function DataLoader({ onLoad }: { onLoad: (lib: Library) => void }) {
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);

  const read = async (f: File | undefined) => {
    if (!f) return;
    setBusy(true); setErr(null);
    try { onLoad(parseLibrary(await f.text())); }
    catch (e) { setErr(e instanceof Error ? e.message : String(e)); setBusy(false); }
  };

  return (
    <div className="loader">
      <div className="loader-card">
        <div className="loader-art" aria-hidden style={{ backgroundImage: "url(./brand/dither-plum.png)" }} />
        <div className="loader-brand"><img className="ai4all-logo" src="./brand/ai4all-pill.png" alt="AI4ALL" width="96" height="30" />
          <span className="brand-title">AI Project Atlas</span></div>
        <h1>Open your data bundle</h1>
        <p>This page contains only the app. The project data is private student work, so it is not published here.
          Open your copy of <code>library.json</code> to explore it.</p>
        <label className={`drop ${drag ? "over" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); read(e.dataTransfer.files[0]); }}>
          <input type="file" accept=".json,application/json" onChange={(e) => read(e.target.files?.[0])} />
          <span className="drop-main">{busy ? "Loading…" : "Choose library.json"}</span>
          <span className="muted small">or drag it here</span>
        </label>
        {err && <p className="loader-err" role="alert">{err}</p>}
        <p className="muted small">🔒 The file is read in this browser only. Nothing is uploaded, stored or sent anywhere;
          closing the tab clears it.</p>
        <p className="muted small">Need the file? Ask the program owner, or generate it with <code>make export</code>
          (<code>data/processed/library.json</code>).</p>
      </div>
    </div>
  );
}
