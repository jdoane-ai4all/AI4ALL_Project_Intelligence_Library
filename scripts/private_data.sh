#!/usr/bin/env bash
# Back up / restore the private data artifacts to/from the `private-data` branch of the PRIVATE GitHub repo.
# The branch is orphaned (no shared history with main). PDFs are excluded: they are re-downloadable with `make fetch`.
#
#   scripts/private_data.sh backup    # copy artifacts -> branch, commit, push
#   scripts/private_data.sh restore   # fetch branch -> copy artifacts back into data/
#
# WARNING: the branch contains student work. Never make this repository public while the branch exists.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BRANCH=private-data
WT="$(mktemp -d)"
PATHS=(data/private/raw data/private/redaction_overrides.json data/private/image_redactions.json data/private/sources/text data/private/sources/manifest.json data/private/extractions
       data/private/research data/private/qa data/processed/aipil.sqlite data/processed/library.json
       data/processed/projects_flat.csv data/processed/projects_flat.json data/processed/flagged_projects_review.xlsx
       data/processed/qa_report_private.md data/processed/research_report_private.md)
# Image-redacted PDFs: include both the _OG original and the redacted version (owner's convention).
for og in data/private/sources/pdf/*_OG.pdf; do
  [ -e "$og" ] && PATHS+=("$og" "${og%_OG.pdf}.pdf")
done
cleanup() { git -C "$ROOT" worktree remove --force "$WT" 2>/dev/null || rm -rf "$WT"; }
trap cleanup EXIT
cd "$ROOT"
case "${1:-}" in
  backup)
    if git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
      git fetch -q origin "$BRANCH"
      git worktree add -q --detach "$WT" "origin/$BRANCH"
    else
      git worktree add -q --detach "$WT"
      (cd "$WT" && git checkout -q --orphan "$BRANCH" && git rm -rq --cached . \
        && find . -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +)
    fi
    for p in "${PATHS[@]}"; do
      [ -e "$p" ] || continue
      mkdir -p "$WT/$(dirname "$p")"; rm -rf "${WT:?}/$p"; cp -a "$p" "$WT/$p"
    done
    printf '%s\n' "# PRIVATE DATA - student work. Do not make this repository public." \
      "Artifacts for the AI Project Intelligence Library (main branch). Restore with scripts/private_data.sh restore." \
      "Original PDFs are not stored here; re-download them with make fetch." > "$WT/README.md"
    (cd "$WT" && git add -A -f . && if git diff --cached --quiet; then echo "no changes"; else
      git commit -q -m "Private data snapshot $(date -u +%Y-%m-%dT%H:%MZ)"; fi)
    (cd "$WT" && git push -q origin "HEAD:refs/heads/$BRANCH")
    echo "backed up to origin/$BRANCH"
    ;;
  restore)
    git fetch -q origin "$BRANCH"
    git worktree add -q --detach "$WT" "origin/$BRANCH"
    for p in "${PATHS[@]}"; do
      [ -e "$WT/$p" ] || continue
      mkdir -p "$(dirname "$p")"; rm -rf "$p"; cp -a "$WT/$p" "$p"
    done
    if [ -d "$WT/data/private/sources/pdf" ]; then   # redacted PDFs and their _OG originals
      mkdir -p data/private/sources/pdf && cp -a "$WT/data/private/sources/pdf/." data/private/sources/pdf/
    fi
    chmod 700 data/private
    echo "restored from origin/$BRANCH"
    ;;
  *) echo "usage: $0 backup|restore"; exit 1 ;;
esac
