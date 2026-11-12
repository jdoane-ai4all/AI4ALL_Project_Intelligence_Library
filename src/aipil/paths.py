"""Central path configuration. All private material lives under data/private (git-ignored)."""
from pathlib import Path
import os

ROOT = Path(os.environ.get("AIPIL_ROOT", Path(__file__).resolve().parents[2]))
CONFIG = ROOT / "config"
DATA = ROOT / "data"
PRIVATE = DATA / "private"
RAW_WORKBOOK = Path(os.environ.get("AIPIL_WORKBOOK", PRIVATE / "raw" / "Project_Type.xlsx"))
SOURCES = PRIVATE / "sources"
TEXT_DIR = SOURCES / "text"
PDF_DIR = SOURCES / "pdf"
MANIFEST = SOURCES / "manifest.json"
EXTRACTIONS = PRIVATE / "extractions"
RESEARCH = PRIVATE / "research"
PROCESSED = DATA / "processed"
DB_PATH = Path(os.environ.get("AIPIL_DB", PROCESSED / "aipil.sqlite"))
REPORTS = ROOT / "reports"
