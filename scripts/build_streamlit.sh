#!/usr/bin/env bash
# Assemble the Streamlit deploy folder (data/processed/streamlit_deploy/, git-ignored) from the current build.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/data/processed/streamlit_deploy"
(cd "$ROOT/app" && npm run -s build:single)
rm -rf "$OUT" && mkdir -p "$OUT/.streamlit"
cp "$ROOT/streamlit/streamlit_app.py" "$ROOT/streamlit/requirements.txt" "$OUT/"
cp "$ROOT/streamlit/.streamlit/config.toml" "$OUT/.streamlit/"
cp "$ROOT/app/dist-single/index.html" "$OUT/atlas.html"
cp "$ROOT/app/public/brand/favicon.png" "$OUT/favicon.png"
cp "$ROOT/data/processed/library.json" "$OUT/library.json"
echo "Streamlit deploy folder ready: $OUT"
