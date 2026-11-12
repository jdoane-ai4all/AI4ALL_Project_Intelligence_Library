"""Typed schema for per-project structured extractions (prompt v1).

An extraction is produced by an LLM reader following prompts/extraction_v1.md, saved as
data/private/extractions/<project_id>.json, and validated here before loading. Validation
covers: JSON schema, taxonomy membership, enum values, and verbatim grounding of every
evidence quote against the cached source text.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field, field_validator

from aipil import paths

EvidenceLevel = Literal["confirmed", "inferred", "unknown"]
Role = Literal["implemented", "baseline", "compared", "considered", "proposed", "unclear"]
DatasetRel = Literal["used", "mentioned", "alternative"]


class Evidence(BaseModel):
    page: Optional[str] = Field(None, description="Slide/page number(s), e.g. '4' or '4-5'")
    quote: Optional[str] = Field(None, description="Short verbatim excerpt from the source (<= 300 chars)")
    source: Literal["text", "pdf_visual", "workbook", "inference"] = "text"


class Tag(BaseModel):
    term: str
    evidence_level: EvidenceLevel
    primary: bool = False
    original_term: Optional[str] = None
    evidence: Optional[Evidence] = None


class Algorithm(BaseModel):
    original_name: str
    canonical: str
    role: Role
    purpose: Optional[str] = None
    inputs: Optional[str] = None
    outputs: Optional[str] = None
    reported_result: Optional[str] = None
    evidence_level: EvidenceLevel
    evidence: Optional[Evidence] = None


class DatasetRef(BaseModel):
    original_reference: str
    name_guess: Optional[str] = None
    url_in_source: Optional[str] = None
    description: Optional[str] = None
    modality: Optional[str] = None
    relationship: DatasetRel
    evidence: Optional[Evidence] = None


class Scored(BaseModel):
    score: int
    rationale: str


class Summary(BaseModel):
    plain_language: str
    technical: str
    research_question: Optional[str] = None
    problem: Optional[str] = None
    primary_beneficiary: Optional[str] = None
    application_domain: Optional[str] = None
    subdomain: Optional[str] = None
    inputs: Optional[str] = None
    outputs: Optional[str] = None
    results: Optional[str] = None


class Extraction(BaseModel):
    project_id: str
    prompt_version: str = "extraction_v1.1"
    sources_used: list[str]
    source_completeness: Literal["complete", "partial", "poor"]
    source_notes: Optional[str] = None
    summary: Summary
    industries: list[Tag]
    paradigms: list[Tag]
    tasks: list[Tag]
    modalities: list[Tag]
    methods: list[Tag] = []
    tools: list[Tag] = []
    algorithms: list[Algorithm]
    datasets: list[DatasetRef] = []
    sophistication: dict[str, Scored]
    prerequisites: dict[str, Scored]
    hardware: Literal["laptop_cpu", "free_cloud_gpu", "dedicated_gpu", "unknown"]
    reproduction: dict[str, Scored]
    adoption_readiness: dict[str, bool]
    extension_ideas: list[str] = []
    team_suitability: Literal["individual", "team", "either"] = "either"
    search_tags: list[str] = []
    uncertainties: list[str] = []
    review_flags: list[str] = []
    overall_confidence: Literal["high", "medium", "low"]

    @field_validator("project_id")
    @classmethod
    def _pid(cls, v):
        if not re.match(r"^project-\d{3}$", v):
            raise ValueError("bad project_id")
        return v


@lru_cache
def taxonomy() -> dict:
    return yaml.safe_load((paths.CONFIG / "taxonomy.yaml").read_text())


@lru_cache
def assessment_cfg() -> dict:
    return yaml.safe_load((paths.CONFIG / "assessment.yaml").read_text())


def term_set(dim: str) -> set[str]:
    return set(taxonomy()["dimensions"][dim]["terms"])


_WS = re.compile(r"[\s\\]+")
_GLYPHS = re.compile(r"[\ue000-\uf8ff•●○▪■□◦‣∙·»«➢➤✓✔→]")


def norm_text(s: str) -> str:
    s = s.replace("ﬁ", "fi").replace("ﬂ", "fl").replace("ﬀ", "ff").replace("ﬃ", "ffi").replace("ﬄ", "ffl")
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-")
    s = _GLYPHS.sub(" ", s)
    return _WS.sub(" ", s).strip().lower()


def quote_found(quote: str, source_norm: str) -> bool:
    q = norm_text(quote).strip(" .…\"'")
    if not q:
        return False
    if q in source_norm:
        return True
    # tolerate ellipses joining fragments: every fragment of >= 12 chars must be present
    frags = [f.strip(" .\"'") for f in re.split(r"\.\.\.|…", q)]
    frags = [f for f in frags if len(f) >= 12]
    return bool(frags) and all(f in source_norm for f in frags)


def validate_extraction(data: dict, source_text: str | None) -> tuple[Extraction | None, list[str], dict]:
    """Return (model, problems, grounding_stats)."""
    problems: list[str] = []
    try:
        ex = Extraction.model_validate(data)
    except Exception as e:  # noqa: BLE001
        return None, [f"schema: {e}"], {}
    for dim, items in [("industry", ex.industries), ("paradigm", ex.paradigms), ("task", ex.tasks),
                       ("modality", ex.modalities), ("method", ex.methods), ("tool", ex.tools)]:
        allowed = term_set(dim)
        for t in items:
            if t.term not in allowed and not t.term.startswith("new:"):
                problems.append(f"{dim}: unknown term '{t.term}' (use taxonomy slug or 'new:<slug>')")
    algs = term_set("algorithm")
    for a in ex.algorithms:
        if a.canonical not in algs and not a.canonical.startswith("new:"):
            problems.append(f"algorithm: unknown canonical '{a.canonical}'")
    cfg = assessment_cfg()
    for block, key in [("sophistication", ex.sophistication), ("reproduction_effort", ex.reproduction)]:
        want = set(cfg[block]["components"])
        if set(key) != want:
            problems.append(f"{block}: components {sorted(key)} != {sorted(want)}")
        for k, v in key.items():
            if not 0 <= v.score <= 3:
                problems.append(f"{block}.{k}: score {v.score} out of 0-3")
    want = set(cfg["prerequisites"]["components"])
    if set(ex.prerequisites) != want:
        problems.append(f"prerequisites: components {sorted(ex.prerequisites)} != {sorted(want)}")
    for k, v in ex.prerequisites.items():
        if not 1 <= v.score <= 3:
            problems.append(f"prerequisites.{k}: score {v.score} out of 1-3")
    if set(ex.adoption_readiness) != set(cfg["adoption_readiness"]["criteria"]):
        problems.append("adoption_readiness: criteria mismatch")
    for d in ex.datasets:
        if d.relationship == "used" and not d.evidence:
            problems.append(f"dataset '{d.original_reference[:40]}': 'used' datasets need evidence (page/quote)")
    if not any(t.primary for t in ex.industries):
        problems.append("industries: no primary industry marked")

    # Grounding: confirmed claims need a quote that appears verbatim in the source.
    stats = {"quotes": 0, "verified": 0, "confirmed_without_quote": 0}
    src = norm_text(source_text) if source_text else ""
    unverified = []
    for label, ev, level in _iter_evidence(ex):
        if ev and ev.quote and ev.source == "text":
            stats["quotes"] += 1
            if src and quote_found(ev.quote, src):
                stats["verified"] += 1
            else:
                unverified.append(f"{label}: quote not found verbatim: {ev.quote[:80]!r}")
        elif level == "confirmed" and not (ev and (ev.quote or ev.source == "pdf_visual")):
            stats["confirmed_without_quote"] += 1
    problems += unverified
    return ex, problems, stats


def _iter_evidence(ex: Extraction):
    for dim, items in [("industry", ex.industries), ("paradigm", ex.paradigms), ("task", ex.tasks),
                       ("modality", ex.modalities), ("method", ex.methods), ("tool", ex.tools)]:
        for t in items:
            yield f"{dim}:{t.term}", t.evidence, t.evidence_level
    for a in ex.algorithms:
        yield f"algorithm:{a.canonical}", a.evidence, a.evidence_level
    for d in ex.datasets:
        yield f"dataset:{d.original_reference[:30]}", d.evidence, "confirmed"


def load_source_text(pid: str) -> str | None:
    p = paths.TEXT_DIR / f"{pid}.txt"
    return p.read_text() if p.exists() else None


def main(argv=None):
    """CLI: python -m aipil.extraction.schema project-002 [project-003 ...]  (or 'all')."""
    import json
    import sys
    args = argv if argv is not None else sys.argv[1:]
    files = sorted(paths.EXTRACTIONS.glob("project-*.json")) if args == ["all"] else \
        [paths.EXTRACTIONS / f"{a}.json" for a in args]
    bad = 0
    for f in files:
        if not f.exists():
            print(f"{f.stem}: MISSING")
            bad += 1
            continue
        try:
            data = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            print(f"{f.stem}: INVALID JSON {e}")
            bad += 1
            continue
        _, probs, st = validate_extraction(data, load_source_text(f.stem))
        status = "OK" if not probs else f"{len(probs)} problem(s)"
        print(f"{f.stem}: {status}  quotes verified {st.get('verified', 0)}/{st.get('quotes', 0)}")
        for p in probs:
            print("   -", p)
        bad += bool(probs)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
