"""Black out personal images in source PDFs (true redaction: image content is removed, not just covered).

Config (private): data/private/image_redactions.json
    {"project-186": [{"page": 6, "xref": 27, "reason": "team members' personal skin photos"}]}

Naming convention (program owner's request, 2026-11-06): the untouched original is kept as
<pid>_OG.pdf and the redacted version takes the original name <pid>.pdf. Both are private and both are
included in the private-data backup. Idempotent: safe to re-run after `make fetch`, which restores originals.

    python -m aipil.sources.redact_images
"""
from __future__ import annotations

import hashlib
import json
import shutil

import pymupdf

from aipil import paths

CONFIG = paths.PRIVATE / "image_redactions.json"


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def redact_pdf(pid: str, items: list[dict]) -> dict:
    target = paths.PDF_DIR / f"{pid}.pdf"
    og = paths.PDF_DIR / f"{pid}_OG.pdf"
    if not og.exists():
        shutil.copy2(target, og)                   # first run: preserve the original under the _OG name
    elif target.exists() and _sha(target) != _sha(og) and target.stat().st_mtime > og.stat().st_mtime:
        # target already redacted from this OG; re-run anyway from the OG for determinism
        pass
    doc = pymupdf.open(og)
    done = []
    for it in items:
        page = doc[it["page"] - 1]
        rects = [pymupdf.Rect(info["bbox"]) for info in page.get_image_info(xrefs=True) if info["xref"] == it["xref"]]
        if not rects and it.get("bbox"):
            rects = [pymupdf.Rect(it["bbox"])]
        for r in rects:
            page.add_redact_annot(r, fill=(0, 0, 0))
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_REMOVE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,
                              text=pymupdf.PDF_REDACT_TEXT_NONE)
        done.append({"page": it["page"], "xref": it["xref"], "boxes": len(rects), "rects": [list(r) for r in rects],
                     "reason": it.get("reason")})
    tmp = target.with_suffix(".tmp.pdf")
    doc.save(tmp, garbage=4, deflate=True)
    doc.close()
    tmp.replace(target)
    check = pymupdf.open(target)   # verify on the saved file: no image may intersect a redacted box
    for d in done:
        pg = check[d["page"] - 1]
        d["image_removed"] = not any(pymupdf.Rect(i["bbox"]).intersects(pymupdf.Rect(r))
                                     for i in pg.get_image_info() for r in d["rects"])
    check.close()
    return {"pid": pid, "original": og.name, "redacted": target.name, "items": done}


def run():
    if not CONFIG.exists():
        print("no image redaction config")
        return []
    cfg = json.loads(CONFIG.read_text())
    out = [redact_pdf(pid, items) for pid, items in cfg.items() if not pid.startswith("_")]
    manifest = json.loads(paths.MANIFEST.read_text()) if paths.MANIFEST.exists() else {}
    for r in out:
        rec = manifest.get(f"{r['pid']}:pdf", {})
        rec.update(image_redactions=r["items"], original_file=r["original"])
        manifest[f"{r['pid']}:pdf"] = rec
    paths.MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True))
    for r in out:
        print(r)
    return out


if __name__ == "__main__":
    run()
