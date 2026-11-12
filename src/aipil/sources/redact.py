"""Best-effort removal of personal identifiers from extracted presentation text.

Student names, emails, phone numbers, social-profile handles and GitHub owners are
removed before text is cached for analysis. This is defence in depth: the cached text
still lives only under data/private/ and is never committed. Redaction is heuristic and
is NOT a basis for publication (see docs/governance.md).
"""
from __future__ import annotations

import re

TOKEN = "[REDACTED]"

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)")
PROFILE = re.compile(r"(https?://)?(www\.)?(linkedin\.com/in|instagram\.com|twitter\.com|x\.com|facebook\.com)/[\w.\-/%]+", re.I)
GITHUB_OWNER = re.compile(r"(github\.com/)([A-Za-z0-9-]+)(?=/|\b)", re.I)
# Only Spaces (hosted apps, typically the students' own) are redacted; model/dataset/paper paths name public publishers.
HF_OWNER = re.compile(r"(huggingface\.co/spaces/)([A-Za-z0-9_.-]+)(?=/)", re.I)
KAGGLE_USER = re.compile(r"(kaggle\.com/code/)([A-Za-z0-9_-]+)(?=/|\b)", re.I)
USER_PATH = re.compile(r"((?:\\Users\\)|(?:/Users/)|(?:/home/))([^\\/\s>]+)", re.I)
# Contact rows such as "<Name> LinkedIn GitHub" (OCR often mangles the labels: "LUnkedin", "GitHvo").
CONTACT_LINE = re.compile(r"l\w{0,2}n\w{0,2}k\w{0,2}d\w{0,2}n|git\s?h\w{1,2}\b", re.I)
BYLINE = re.compile(r"^\s*(by|presented by|created by|authors?|team members?|team|group members?|members?)\s*[:\-–]\s*(.*)$", re.I)

# Words that frequently appear capitalized on slides but are not names.
_NON_NAME = set("""
ai ml data model models project projects learning machine deep neural network networks analysis prediction predicting
detection classification regression random forest decision tree trees using the and of for with in on to a an our
ignite ai4all research question questions conclusion results result introduction overview future work next steps
thank you thanks team meet about us agenda demo dataset datasets sources references citations bias impact impacts
algorithm algorithms evaluation training testing feature features engineering methodology method methods approach
health healthcare finance stock market price prices disease detection image images text system systems app
""".split())
_NAME_TOKEN = re.compile(r"^[A-Z][a-z'’\-]+\.?$|^[A-Z]\.$")


def looks_like_name_line(line: str) -> bool:
    toks = [t for t in re.split(r"[\s,&]+", line.strip()) if t and t.lower() not in {"and", "&"}]
    if not 2 <= len(toks) <= 12:
        return False
    if any(t.lower().strip(".") in _NON_NAME for t in toks):
        return False
    return all(_NAME_TOKEN.match(t) for t in toks)


def _load_overrides():
    """Reviewed per-project name/handle overrides, stored privately as salted hashes (never plaintext)."""
    import hashlib
    import json
    from aipil import paths
    f = paths.PRIVATE / "redaction_overrides.json"
    if not f.exists():
        return None
    o = json.loads(f.read_text())
    return o["salt"], o["terms"], hashlib


_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
_CAMEL = re.compile(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])")


def apply_overrides(text: str, project_id: str | None) -> tuple[str, int]:
    ov = _load_overrides()
    if not ov:
        return text, 0
    salt, terms, hashlib = ov
    wanted = set(terms.get("global", [])) | set(terms.get(project_id or "", []))
    if not wanted:
        return text, 0
    hit = lambda w: hashlib.sha256((salt + w.lower()).encode()).hexdigest() in wanted  # noqa: E731
    n = 0

    def fix(m):
        nonlocal n
        tok = m.group(0)
        if hit(tok):
            n += 1
            return TOKEN
        parts = _CAMEL.findall(tok)  # e.g. "AngelModel" -> Angel + Model
        if len(parts) > 1 and any(hit(p) for p in parts):
            n += 1
            return "".join(TOKEN if hit(p) else p for p in parts)
        return tok
    return _TOKEN.sub(fix, text), n


def redact(text: str, project_id: str | None = None) -> tuple[str, int]:
    n = 0
    text, n = apply_overrides(text, project_id)

    def sub(pattern, repl, s):
        nonlocal n
        s2, k = pattern.subn(repl, s)
        n += k
        return s2

    text = sub(EMAIL, TOKEN, text)
    text = sub(PHONE, TOKEN, text)
    text = sub(PROFILE, TOKEN, text)
    text = sub(GITHUB_OWNER, lambda m: m.group(1) + TOKEN, text)
    text = sub(HF_OWNER, lambda m: m.group(1) + TOKEN, text)
    text = sub(KAGGLE_USER, lambda m: m.group(1) + TOKEN, text)
    text = sub(USER_PATH, lambda m: m.group(1) + TOKEN, text)

    out_lines = []
    pages = re.split(r"(?m)^(?==== PAGE )", text)
    for pi, page in enumerate(pages):
        lines = page.split("\n")
        low = page.lower()
        # Name-like lines are only redacted where names are expected: the title slide,
        # team/about pages, and closing slides. Elsewhere Title Case lines are slide content.
        team_page = (pi <= 1) or bool(re.search(r"meet (the|our) team|about (us|the team)|team members|our team|"
                                                  r"presented by|thank you|questions\?", low))
        in_byline = 0
        for line in lines:
            m = BYLINE.match(line)
            if m:
                rest = m.group(2).strip()
                out_lines.append(f"{m.group(1)}: {TOKEN}" if rest else f"{m.group(1)}:")
                n += 1 if rest else 0
                in_byline = 6
                continue
            if in_byline and line.strip():
                if looks_like_name_line(line) or _all_caps_name(line):
                    out_lines.append(TOKEN)
                    n += 1
                    in_byline -= 1
                    continue
                in_byline = 0
            if _is_contact_row(line):
                out_lines.append(TOKEN)
                n += 1
                continue
            if team_page and looks_like_name_line(line):
                out_lines.append(TOKEN)
                n += 1
                continue
            out_lines.append(line)
    return "\n".join(out_lines), n


def _all_caps_name(line: str) -> bool:
    toks = line.split()
    return 1 <= len(toks) <= 3 and all(t.isalpha() and t.isupper() and len(t) > 1 for t in toks) \
        and not any(t.lower() in _NON_NAME for t in toks)


_CONTACT_OK = {"github", "link", "repository", "repo", "code", "our", "the", "on", "available", "project", "see", "view"}


def _is_contact_row(line: str) -> bool:
    """A short line with a LinkedIn/GitHub label plus capitalized non-technical words is treated as a contact row."""
    if not CONTACT_LINE.search(line) or "github.com" in line.lower() and TOKEN in line:
        return False
    rest = [t for t in re.split(r"[\s|,•·]+", CONTACT_LINE.sub(" ", line)) if t]
    if len(rest) > 8:
        return False
    caps = [t for t in rest if t[:1].isupper() and t.lower().strip(":") not in _CONTACT_OK and t.lower() not in _NON_NAME]
    return bool(caps) or bool(re.search(r"l\w{0,2}n\w{0,2}k\w{0,2}d\w{0,2}n", line, re.I))
