"""Deterministic Level-1 dataset resolution.

For every dataset reference whose URL is written in the student's source, verify the URL in
code (HTTP + Kaggle's public dataset metadata endpoint) instead of spending LLM/web-search
effort. Output: data/private/research/level1/<pid>.json — a partial research record that the
LLM research step (prompts/research_v1.md) copies and extends with Level 2-4 work and
external precedents.

Matching rule: a URL given in the source that currently resolves is an `exact` match for the
reference it was attached to (discovery level 1). Unresolvable URLs are kept as `unresolved`
clues with the HTTP outcome, never silently dropped.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

from aipil import paths
from aipil.datasets.linkcheck import check

PLATFORMS = {"kaggle.com": "Kaggle", "archive.ics.uci.edu": "UCI Machine Learning Repository", "huggingface.co": "Hugging Face",
             "data.gov": "Data.gov", "catalog.data.gov": "Data.gov", "openml.org": "OpenML", "physionet.org": "PhysioNet",
             "github.com": "GitHub", "zenodo.org": "Zenodo", "worldbank.org": "World Bank", "cdc.gov": "CDC",
             "noaa.gov": "NOAA", "nasa.gov": "NASA", "census.gov": "U.S. Census Bureau", "data.cityofchicago.org": "City of Chicago"}


def clean_url(u: str) -> str | None:
    if not u or "[REDACTED]" in u:
        return None
    u = re.sub(r"\s+", "", u.strip()).rstrip(".,;)")
    if not u.startswith("http"):
        u = "https://" + u
    p = urlparse(u)
    if not p.netloc or "." not in p.netloc:
        return None
    # Kaggle: drop query strings (?select=file.csv) and trailing sub-pages to get the dataset landing page
    if "kaggle.com" in p.netloc:
        m = re.search(r"(kaggle\.com/datasets/[^/?#]+/[^/?#]+)", u)
        if m:
            return "https://www." + m.group(1)
    return u


def platform_of(url: str) -> str:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    for k, v in PLATFORMS.items():
        if host == k or host.endswith("." + k) or host.endswith(k):
            return v
    return host


def resolve_all() -> dict:
    out_dir = paths.RESEARCH / "level1"
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_f = paths.RESEARCH / "link_checks.json"
    cache = json.loads(cache_f.read_text()) if cache_f.exists() else {}
    stats = {"refs_with_url": 0, "resolved": 0, "unresolved": 0, "projects": 0}
    for f in sorted(paths.EXTRACTIONS.glob("project-*.json")):
        ex = json.loads(f.read_text())
        rec = {"project_id": ex["project_id"], "datasets": [], "unresolved": [],
               "resolved_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        for d in ex.get("datasets", []):
            url = clean_url(d.get("url_in_source") or "")
            if not url:
                continue
            stats["refs_with_url"] += 1
            if url not in cache:
                cache[url] = check(url)
            c = cache[url]
            kg = c.get("kaggle") or {}
            page = (d.get("evidence") or {}).get("page")
            if c.get("status") in ("ok", "ok_login_redirect", "restricted_or_blocked"):
                stats["resolved"] += 1
                rec["datasets"].append({
                    "name": kg.get("title") or d.get("name_guess") or d["original_reference"],
                    "canonical_url": url, "platform": platform_of(url), "publisher": kg.get("creator"),
                    "description": kg.get("subtitle") or d.get("description"), "modality": d.get("modality"),
                    "access_requirements": "free Kaggle account" if "kaggle" in url else
                    ("may require sign-in or block automated access" if c["status"] != "ok" else "public page"),
                    "license": kg.get("license") or "unknown",
                    "availability_status": "available" if c["status"] == "ok" else "restricted",
                    "relationship": d["relationship"], "match_level": "exact", "discovery_level": 1,
                    "original_reference": d["original_reference"],
                    "evidence": f"URL given in source{f' (p.{page})' if page else ''}; verified by code: "
                                f"{c['status']}" + (f", Kaggle title '{kg.get('title')}'" if kg.get("title") else ""),
                    "confidence": "high" if c["status"] == "ok" else "medium",
                    "comments": "resolved deterministically (src/aipil/datasets/resolve_urls.py)"})
            else:
                stats["unresolved"] += 1
                rec["unresolved"].append({"clue": f"{d['original_reference']} — URL in source: {url}",
                                          "notes": f"URL did not resolve ({c.get('status')}, HTTP {c.get('http_code')})"})
        if rec["datasets"] or rec["unresolved"]:
            stats["projects"] += 1
        (out_dir / f"{ex['project_id']}.json").write_text(json.dumps(rec, indent=1))
    cache_f.write_text(json.dumps(cache, indent=1, sort_keys=True))
    print(stats)
    return stats


if __name__ == "__main__":
    resolve_all()
