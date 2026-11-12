"""AI Project Atlas on Streamlit.

Serves the React/three.js app (built as one self-contained page) with the catalog data embedded.
Deploy folder layout (assembled by scripts/build_streamlit.sh):
    streamlit_app.py   atlas.html   library.json   favicon.png   requirements.txt   .streamlit/config.toml
PRIVATE: library.json contains student work. Deploy only as a private app shared with named viewers.
"""
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

HERE = Path(__file__).parent
st.set_page_config(page_title="AI Project Atlas · AI4ALL",
                   page_icon=str(HERE / "favicon.png") if (HERE / "favicon.png").exists() else None, layout="wide")
st.markdown("""<style>
  .block-container {padding: 0 0.5rem 0 0.5rem; max-width: 100%;}
  header[data-testid="stHeader"] {height: 0; visibility: hidden;}
  #MainMenu, footer {visibility: hidden;}
  /* make the embedded app fill the browser window */
  div[data-testid="stIFrame"], iframe {height: calc(100vh - 4px) !important; width: 100% !important;}
  div[data-testid="stAppViewBlockContainer"], .block-container {padding-top: 0 !important; padding-bottom: 0 !important;}
  div[data-testid="stVerticalBlock"] {gap: 0 !important;}
</style>""", unsafe_allow_html=True)


@st.cache_data(show_spinner="Loading the atlas…")
def page() -> str:
    html = (HERE / "atlas.html").read_text(encoding="utf-8")
    data = (HERE / "library.json").read_text(encoding="utf-8")
    json.loads(data)  # fail fast on a corrupt bundle
    inject = "<script>window.__AIPIL_LIBRARY__=" + data.replace("</", "<\\/") + ";</script>"
    return html.replace("<head>", "<head>" + inject, 1)


components.html(page(), height=900, scrolling=False)  # CSS above stretches it to the full window height
