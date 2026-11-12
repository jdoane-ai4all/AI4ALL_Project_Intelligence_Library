import type { ReactNode } from "react";

export function Badge({ kind, children }: { kind: string; children: ReactNode }) {
  return <span className={`badge b-${kind.toLowerCase().replace(/\s+/g, "-")}`}>{children}</span>;
}

/** A horizontal meter. `est` marks inferred/estimated metrics with a hatched fill and an asterisk. */
export function Meter({ label, v, max, est }: { label: string; v: number | null | undefined; max: number; est?: boolean }) {
  const pct = v === null || v === undefined ? 0 : Math.max(0, Math.min(100, (v / max) * 100));
  return (
    <div className="meter" title={est ? `${label}: estimated/inferred metric` : label}>
      <div className="meter-l"><span>{label}{est ? "*" : ""}</span><span className="mono">{v === null || v === undefined ? "—" : Number.isInteger(v) ? v : v.toFixed(1)}</span></div>
      <div className="meter-bar"><div className={`meter-fill ${est ? "est" : ""}`} style={{ width: `${pct}%` }} /></div>
    </div>
  );
}

export function Level({ level }: { level: string }) {
  return <span className={`lvl lvl-${level}`} title={level === "confirmed" ? "Explicitly stated in the source" : level === "inferred" ? "Reasonably inferred, not explicitly stated" : "Unknown"}>{level === "confirmed" ? "●" : level === "inferred" ? "◐" : "○"}</span>;
}
