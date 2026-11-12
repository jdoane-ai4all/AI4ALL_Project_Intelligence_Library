"""Retrieve linked presentation sources into the private cache, with a manifest.

Access method: the workbook's Google Drive links are shared by link. Files are fetched
with Drive's download endpoint using the exact file IDs in the workbook, which only
succeeds for files whose sharing settings already permit it; nothing is circumvented.
A failed or permission-denied fetch is recorded as such (never treated as analyzed).
The original Drive connector can be used as a fallback for files that fail.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from aipil import paths
from aipil.ingestion.workbook import now
from aipil.sources.redact import redact

DL = "https://drive.google.com/uc?export=download&id={id}"
UA = {"User-Agent": "aipil-source-fetcher/0.1"}


def _fetch(fid: str) -> tuple[int, bytes, str]:
    r = requests.get(DL.format(id=fid), headers=UA, timeout=60)
    return r.status_code, r.content, r.headers.get("content-type", "")


def _retrieve_one(pid: str, kind: str, fid: str | None, url: str | None, force: bool) -> dict:
    rec = dict(doc_id=f"{pid}:{kind}", project_id=pid, kind=kind, drive_file_id=fid, url=url,
               access_status="missing_link", retrieved_at=None, sha256=None, n_bytes=None, n_pages=None,
               n_chars=None, redactions=None, error=None)
    if not fid:
        return rec
    target = (paths.TEXT_DIR / f"{pid}.txt") if kind == "text" else (paths.PDF_DIR / f"{pid}.pdf")
    if target.exists() and not force:
        prev = _manifest().get(rec["doc_id"])
        if prev and prev.get("access_status") == "retrieved":
            return prev
    for attempt in range(4):
        try:
            code, body, ctype = _fetch(fid)
            break
        except requests.RequestException as e:  # network retry with backoff
            if attempt == 3:
                rec.update(access_status="failed", error=str(e)[:300])
                return rec
            time.sleep(2 ** (attempt + 1))
    rec["retrieved_at"] = now()
    if code != 200 or ("text/html" in ctype and kind == "pdf") or (kind == "text" and body[:15].lower().startswith(b"<!doctype html")):
        rec.update(access_status="failed", error=f"http {code} {ctype}")
        return rec
    rec["sha256"] = hashlib.sha256(body).hexdigest()
    rec["n_bytes"] = len(body)
    if kind == "text":
        txt = body.decode("utf-8", errors="replace")
        red, n = redact(txt, pid)
        # Owner's convention: keep the untouched original as <pid>_OG.txt; the redacted text takes <pid>.txt.
        (paths.TEXT_DIR / f"{pid}_OG.txt").write_text(txt)
        target.write_text(red)
        rec.update(n_chars=len(red), redactions=n, n_pages=txt.count("=== PAGE "))
    else:
        if not body.startswith(b"%PDF"):
            rec.update(access_status="failed", error="not a PDF payload")
            return rec
        target.write_bytes(body)
        try:
            import pdfplumber
            with pdfplumber.open(target) as pdf:
                rec["n_pages"] = len(pdf.pages)
        except Exception as e:  # noqa: BLE001
            rec["error"] = f"page count failed: {e}"[:200]
    rec["access_status"] = "retrieved"
    return rec


def _manifest() -> dict:
    if paths.MANIFEST.exists():
        return json.loads(paths.MANIFEST.read_text())
    return {}


def fetch_all(kinds=("text", "pdf"), limit=None, force=False, workers=4):
    paths.TEXT_DIR.mkdir(parents=True, exist_ok=True)
    paths.PDF_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(paths.DB_PATH)
    rows = con.execute("SELECT project_id, text_drive_id, text_url, pdf_drive_id, pdf_url FROM projects ORDER BY project_id").fetchall()
    if limit:
        rows = rows[:limit]
    jobs = []
    for pid, tid, turl, did, durl in rows:
        if "text" in kinds:
            jobs.append((pid, "text", tid, turl))
        if "pdf" in kinds:
            jobs.append((pid, "pdf", did, durl))
    manifest = _manifest()
    with ThreadPoolExecutor(workers) as ex:
        for rec in ex.map(lambda j: _retrieve_one(*j, force), jobs):
            manifest[rec["doc_id"]] = rec
    paths.MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True))
    cols = ["doc_id", "project_id", "kind", "drive_file_id", "url", "access_status", "retrieved_at", "sha256",
            "n_bytes", "n_pages", "n_chars", "redactions", "error"]
    con.executemany(f"INSERT OR REPLACE INTO source_documents ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                    [tuple(r.get(c) for c in cols) for r in manifest.values()])
    con.commit()
    from collections import Counter
    print(Counter((r["kind"], r["access_status"]) for r in manifest.values()))
    if "pdf" in kinds:  # fetching restores original PDFs; re-apply reviewed image redactions
        from aipil.sources.redact_images import run as redact_images
        redact_images()
