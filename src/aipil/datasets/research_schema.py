"""Schema + validator for dataset/precedent research outputs (prompts/research_v1.md)."""
from __future__ import annotations

import json
import sys
from typing import Literal, Optional

from pydantic import BaseModel, field_validator

from aipil import paths


class DatasetCandidate(BaseModel):
    name: str
    canonical_url: Optional[str] = None
    platform: Optional[str] = None
    publisher: Optional[str] = None
    description: Optional[str] = None
    modality: Optional[str] = None
    access_requirements: Optional[str] = None
    license: Optional[str] = None
    availability_status: Literal["available", "restricted", "unavailable", "unknown"] = "unknown"
    relationship: Literal["used", "mentioned", "alternative"]
    match_level: Literal["exact", "probable", "possible", "alternative"]
    discovery_level: int
    original_reference: Optional[str] = None
    evidence: str
    confidence: Literal["high", "medium", "low"]
    comments: Optional[str] = None

    @field_validator("canonical_url")
    @classmethod
    def _url(cls, v):
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("canonical_url must be http(s)")
        return v

    @field_validator("discovery_level")
    @classmethod
    def _lvl(cls, v):
        if v not in (1, 2, 3, 4):
            raise ValueError("discovery_level must be 1-4")
        return v


class Unresolved(BaseModel):
    clue: str
    notes: Optional[str] = None


class Precedent(BaseModel):
    title: str
    url: Optional[str] = None
    kind: Optional[str] = None
    date: Optional[str] = None
    comparability: str


class Dim(BaseModel):
    score: int
    rationale: str


class ExternalOriginality(BaseModel):
    classification: Literal["established", "distinctive_application", "unusual_combination", "potentially_novel"]
    rationale: str
    confidence: Literal["high", "medium", "low"]
    search_coverage: str
    dimensions: dict[str, Dim]

    @field_validator("dimensions")
    @classmethod
    def _dims(cls, v):
        want = {"problem", "application_domain", "algorithmic", "data", "integration"}
        if set(v) != want:
            raise ValueError(f"dimensions must be exactly {sorted(want)}")
        for k, d in v.items():
            if not 1 <= d.score <= 5:
                raise ValueError(f"{k} score must be 1-5")
        return v


class Research(BaseModel):
    project_id: str
    prompt_version: str = "research_v1.1"
    researched_at: str
    datasets: list[DatasetCandidate]
    unresolved: list[Unresolved] = []
    precedents: list[Precedent] = []
    external_originality: ExternalOriginality


def main(argv=None):
    args = argv if argv is not None else sys.argv[1:]
    files = sorted(paths.RESEARCH.glob("project-*.json")) if args == ["all"] else \
        [paths.RESEARCH / f"{a}.json" for a in args]
    bad = 0
    for f in files:
        try:
            r = Research.model_validate(json.loads(f.read_text()))
            probs = []
            if r.project_id != f.stem:
                probs.append("project_id does not match filename")
            if any(d.relationship == "used" and d.match_level == "alternative" for d in r.datasets):
                probs.append("a dataset cannot be both 'used' and an 'alternative'")
            if not r.datasets and not r.unresolved:
                probs.append("no datasets and no unresolved entries")
        except Exception as e:  # noqa: BLE001
            probs = [str(e)[:500]]
        print(f"{f.stem}: {'OK' if not probs else probs}")
        bad += bool(probs)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
