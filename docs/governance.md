# Privacy, Ethics & Data Governance

This library is built from **student-created work**. The default posture is the most restrictive reasonable one.

## What is private and where it lives

| Material | Location | In Git? |
|---|---|---|
| Original workbook (`Project_Type.xlsx`) | `data/private/raw/` | **No** |
| Presentation PDFs and extracted text | `data/private/sources/` | **No** |
| Per-project extractions & research JSON | `data/private/extractions/`, `data/private/research/` | **No** |
| SQLite database, flattened exports, app bundle | `data/processed/`, `app/public/data/` | **No** |
| Code, schema, taxonomy, prompts, docs, aggregate QA reports | repo | Yes |

`.gitignore` excludes all of the above, including any `*.xlsx`, `*.pdf`, `*.sqlite` anywhere in the tree.
`data/private` is created with mode `700`.

## Personal information

- Source text is passed through `src/aipil/sources/redact.py` **before** caching: emails, phone numbers, social
  profile URLs, GitHub account owners, byline names and name-like lines on title/team/closing slides are replaced
  with `[REDACTED]`. The source texts were also largely anonymized upstream (the original grading notes flag
  `possible_redaction`). Redaction is heuristic and is **not** a basis for publication.
- Extraction prompts forbid recording names or personal details; extracted records describe *projects*, not people.
- No demographic data exists in the workbook, and none is inferred. Any future demographic analysis must be
  aggregate-only and never tied to an identifiable individual.
- Assessments evaluate project artifacts; they make no judgement about a student's ability or potential.
  Original rubric scores measure rubric compliance, not holistic quality or merit.

## Backups of private artifacts

The program owner asked (2026-11-06) for the private artifacts to be saved to GitHub because the cloud workspace is
ephemeral. `scripts/private_data.sh backup` pushes extractions, research, QA files, redacted texts, the workbook,
the database and exports (not PDFs) to an orphan `private-data` branch of the **private** repository, and
`restore` brings them back. While that branch exists, the repository must stay private; before any publication of
the code, move the data to a dedicated private repository and delete the branch.

## Reviewed redaction overrides

Names that generic rules cannot catch (first names used as chart or model labels, acknowledgement-slide staff names,
presenter names in footers, personal handles in model-hub/dataset URLs) are redacted through a reviewed override list in
`data/private/redaction_overrides.json`. It stores only **salted SHA-256 hashes** of the terms (never plaintext), scoped
globally or per project; `sources/redact.py` matches tokens (including CamelCase parts such as `<Name>Model`) against it.
Overrides were compiled on 2026-11-06 from extractor notes about personal details left in the sources. Public citation
authors and dataset publishers are not redacted.

## Originals (`_OG`) and redacted versions

At the program owner's request (2026-11-06), every redacted source keeps its untouched original alongside it:
`project-XXX_OG.txt` / `project-XXX_OG.pdf` is the original as downloaded, and the redacted version takes the plain
name (`project-XXX.txt` / `project-XXX.pdf`). All analysis reads only the redacted versions. Both are stored in the
private backup branch, so the originals remain recoverable for authorized internal use.

Personal images are blacked out with true PDF redaction (image content removed, not overlaid) using the reviewed list in
`data/private/image_redactions.json` (`python -m aipil.sources.redact_images`; re-applied automatically after
`make fetch`). First applied to project-186 (team members' personal skin photos; consent not confirmed).

## Streamlit hosting (requested 2026-11-06)

`streamlit/streamlit_app.py` serves the same app with the catalog embedded. The deploy branch `streamlit-app`
(private repo) holds the wrapper, the single-file page and `library.json`. Deploying it puts this private data on
Streamlit Community Cloud (a third-party host): the app must be set to **private**, shared only with named viewers,
and the hosting choice should be confirmed against the organization's data policy. Rebuild with
`scripts/build_streamlit.sh` and push the folder to the branch after data changes.

## Links

- Google Drive links to student presentations are **private student links**. They are kept in the private bundle
  for authorized internal use and are clearly distinguished in the UI from **public dataset links**.
- The app shows Drive links only in the private build. A public build must drop them (see below).

## Access method for sources

Files were fetched by their exact Drive file IDs from the workbook, which only succeeds when the file's existing
sharing settings permit it. No permission was bypassed. Each fetch is recorded in
`data/private/sources/manifest.json` with timestamp, SHA-256, size and status.

## Toward a public catalog (not done; requires approval)

De-identification alone does **not** make publication permissible. A future public catalog would require:

1. Written authorization from the program covering student work reuse (and, where applicable, student/guardian consent).
2. A sanitized export that drops Drive links, student-provided descriptions verbatim, rubric rationales and
   evidence quotes, keeping only derived taxonomy fields, public dataset links and newly written summaries.
3. Human review of every record in the review queue and a manual PII check of all free-text fields.
4. Sign-off recorded in the repository (e.g. `docs/approvals/`).

## Organizational requirements reflected here

- External-facing statistics (e.g. for funder reports) produced from this library must be verified against the
  primary source before publication.
- The library never makes or implies decisions about participant eligibility, acceptance or evaluation.
