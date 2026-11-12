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
# Streamlit serves atlas.html inside an iframe, where relative ./brand/*.png paths can't resolve:
# inline the brand images (logo, loader art, icons) as data URIs so the AI4ALL branding renders.
python3 - "$OUT/atlas.html" "$ROOT/app/public/brand" <<'PY'
import base64, re, sys
from pathlib import Path
html_path, brand = Path(sys.argv[1]), Path(sys.argv[2])
def inline(m):
    f = brand / m.group(2)
    return "data:image/png;base64," + base64.b64encode(f.read_bytes()).decode() if f.is_file() else m.group(0)
html, n = re.subn(r"(\./|/)?brand/([A-Za-z0-9_-]+\.png)", inline, html_path.read_text(encoding="utf-8"))
html_path.write_text(html, encoding="utf-8")
left = re.findall(r"brand/[A-Za-z0-9_-]+\.png", html)
print(f"Inlined {n - len(left)} brand image reference(s)" + (f"; unresolved: {sorted(set(left))}" if left else ""))
PY
cp "$ROOT/app/public/brand/favicon.png" "$OUT/favicon.png"
cp "$ROOT/data/processed/library.json" "$OUT/library.json"
echo "Streamlit deploy folder ready: $OUT"
