"""Deterministic link validation for dataset URLs found during research.

Records HTTP status and a coarse status label. 401/403/429 and login redirects are
recorded as 'restricted_or_blocked' — NOT broken — since many portals block automated
clients or require sign-in. Results cached in data/private/research/link_checks.json.
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests

from aipil import paths

UA = {"User-Agent": "Mozilla/5.0 (compatible; aipil-linkcheck/0.1; research catalog validation)"}


KAGGLE_DS = re.compile(r"kaggle\.com/datasets/([^/?#]+)/([^/?#]+)", re.I)


def kaggle_meta(url: str) -> dict | None:
    """Kaggle's public dataset-view endpoint (no auth) confirms existence and returns title/license/creator."""
    m = KAGGLE_DS.search(url)
    if not m:
        return None
    try:
        r = requests.get(f"https://www.kaggle.com/api/v1/datasets/view/{m.group(1)}/{m.group(2)}", headers=UA, timeout=25)
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return {"kaggle_api_status": r.status_code}
    j = r.json()
    return {"kaggle_api_status": 200, "title": j.get("titleNullable"), "license": j.get("licenseNameNullable"),
            "creator": j.get("creatorNameNullable"), "bytes": j.get("totalBytesNullable"),
            "last_updated": j.get("lastUpdated"), "subtitle": j.get("subtitleNullable")}


def check(url: str) -> dict:
    out = {"checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    km = kaggle_meta(url)
    if km is not None:
        out["kaggle"] = km
        if km.get("kaggle_api_status") == 200:
            out.update(http_code=200, final_url=url, status="ok")
            return out
    try:
        # GET (not HEAD): several portals, including Kaggle, answer HEAD with 404/405.
        r = requests.get(url, headers=UA, timeout=25, allow_redirects=True, stream=True)
        code = r.status_code
        out.update(http_code=code, final_url=r.url)
        login = any(k in r.url.lower() for k in ("login", "signin", "sign-in", "auth"))
        if 200 <= code < 300:
            out["status"] = "ok_login_redirect" if login else "ok"
        elif code in (401, 403, 429, 999):
            out["status"] = "restricted_or_blocked"
        elif code in (404, 410):
            out["status"] = "not_found"
        else:
            out["status"] = f"http_{code}"
    except requests.RequestException as e:
        out.update(http_code=None, status="error", error=str(e)[:200])
    return out


def run(force: bool = False):
    paths.RESEARCH.mkdir(parents=True, exist_ok=True)
    cache_f = paths.RESEARCH / "link_checks.json"
    cache = json.loads(cache_f.read_text()) if cache_f.exists() else {}
    urls = set()
    for f in paths.RESEARCH.glob("project-*.json"):
        for d in json.loads(f.read_text()).get("datasets", []):
            if d.get("canonical_url"):
                urls.add(d["canonical_url"])
    todo = sorted(u for u in urls if force or u not in cache)
    with ThreadPoolExecutor(8) as ex:
        for u, res in zip(todo, ex.map(check, todo)):
            cache[u] = res
    cache_f.write_text(json.dumps(cache, indent=1, sort_keys=True))
    from collections import Counter
    print(f"checked {len(todo)} new URLs; status counts:", Counter(v["status"] for v in cache.values() if v and v.get("status")))


if __name__ == "__main__":
    import sys
    run(force="--force" in sys.argv)
