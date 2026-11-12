from aipil.classification import assess
from aipil.extraction.schema import norm_text, quote_found
from aipil.sources.redact import redact


def test_redacts_contact_details():
    txt = "=== PAGE 001 ===\nMy Project\nby: Jane Q Doe, John Roe\nContact jane@example.org or 555-123-4567\n" \
          "github.com/janedoe/cool-repo\n=== PAGE 002 ===\nRandom Forest Results\n"
    out, n = redact(txt)
    assert "Jane" not in out and "jane@" not in out and "555-123" not in out and "janedoe" not in out
    assert "github.com/[REDACTED]/cool-repo" in out
    assert "Random Forest Results" in out  # slide content outside name contexts is preserved
    assert n >= 4


def test_content_pages_keep_title_case_lines():
    txt = "=== PAGE 001 ===\nT\n=== PAGE 002 ===\nx\n=== PAGE 003 ===\nLabrador Retriever\n"
    out, _ = redact(txt)
    assert "Labrador Retriever" in out


def test_quote_matching_tolerates_whitespace():
    src = norm_text("We used   the Kaggle\nHistorical Bitcoin dataset")
    assert quote_found("used the Kaggle Historical Bitcoin", src)
    assert not quote_found("used the UCI dataset", src)


def test_sophistication_composite():
    assert assess.sophistication({k: 3 for k in "abcdef"}) == 10.0
    assert assess.sophistication({k: 0 for k in "abcdef"}) == 0.0


def test_difficulty_tiers():
    assert assess.difficulty_tier({"python": 1, "math_stats": 1, "ml": 1, "domain": 3}, 1)[0] == "Beginner"
    assert assess.difficulty_tier({"python": 2, "math_stats": 2, "ml": 2, "domain": 1}, 2)[0] == "Intermediate"
    assert assess.difficulty_tier({"python": 2, "math_stats": 2, "ml": 3, "domain": 1}, 3)[0] == "Advanced"


def test_reproduction_bands():
    assert assess.reproduction_band({"a": 0, "b": 1, "c": 1, "d": 0, "e": 0})[1] == "Low"
    assert assess.reproduction_band({"a": 3, "b": 3, "c": 3, "d": 3, "e": 3})[1] == "Very high"


def test_contact_rows_paths_and_handles():
    txt = ("=== PAGE 001 ===\nT\n=== PAGE 002 ===\nx\n=== PAGE 009 ===\nAlex Smith Linkedin GitHub\nJo Kim LUnkedin GitHvo\n"
           "https://huggingface.co/spaces/someuser/app-backend\nhuggingface.co/google-bert/bert-base\nPS C:\\Users\\someone\\Desktop>\n"
           "kaggle.com/code/studenthandle/notebook\nkaggle.com/datasets/publisher/data\nOur GitHub Repository\n")
    out, _ = redact(txt)
    for bad in ["Alex", "Kim", "someuser", "someone", "studenthandle"]:
        assert bad not in out
    assert "kaggle.com/datasets/publisher/data" in out  # public dataset publishers are kept
    assert "Our GitHub Repository" in out


def test_knowledge_only_originality_is_not_loaded():
    from aipil.database.build import search_performed
    assert not search_performed({"precedents": [], "external_originality": {"search_coverage": "NO_SEARCH: budget exhausted"}})
    assert not search_performed({"precedents": [], "external_originality": {"search_coverage": "background knowledge only"}})
    assert search_performed({"precedents": [{"title": "x"}], "external_originality": {"search_coverage": "q1"}})
    assert search_performed({"precedents": [], "external_originality": {"search_coverage": "queries: churn kaggle"}})


def _ex(tools=(), methods=(), algs=(), soph=None, paradigms=()):
    tag = lambda t: {"term": t, "evidence_level": "confirmed"}  # noqa: E731
    return {"tools": [tag(t) for t in tools], "methods": [tag(m) for m in methods], "paradigms": [tag(p) for p in paradigms],
            "algorithms": [{"canonical": a, "role": r} for a, r in algs],
            "sophistication": {k: {"score": v} for k, v in (soph or {}).items()}}


def test_python_level_criteria():
    assert assess.python_level(_ex(tools=["pandas", "scikit_learn"], algs=[("random_forest", "implemented")]))[0] == 1
    assert assess.python_level(_ex(tools=["streamlit"], algs=[("random_forest", "implemented")]))[0] == 2
    assert assess.python_level(_ex(algs=[("llm", "implemented")]))[0] == 2
    lv, hits = assess.python_level(_ex(tools=["pytorch"], algs=[("lstm", "implemented")]))
    assert lv == 3 and "trains_deep_model" in hits
    # a proposed (not run) deep model does not raise the level
    assert assess.python_level(_ex(tools=["pytorch"], algs=[("lstm", "proposed")]))[0] == 1
    assert assess.python_level(_ex(soph={"engineering": 3}))[0] == 3


def test_image_redaction_keeps_original_and_removes_image(tmp_path, monkeypatch):
    import json
    import pymupdf
    from aipil import paths
    from aipil.sources import redact_images as ri
    pdf_dir = tmp_path / "pdf"
    pdf_dir.mkdir()
    monkeypatch.setattr(paths, "PDF_DIR", pdf_dir)
    doc = pymupdf.open()
    page = doc.new_page()
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 20, 20), False)
    pix.set_rect(pix.irect, (200, 120, 90))
    page.insert_image(pymupdf.Rect(50, 50, 150, 150), pixmap=pix)
    page.insert_text((50, 200), "keep this caption")
    doc.save(pdf_dir / "project-999.pdf")
    xref = pymupdf.open(pdf_dir / "project-999.pdf")[0].get_image_info(xrefs=True)[0]["xref"]
    r = ri.redact_pdf("project-999", [{"page": 1, "xref": xref, "reason": "test"}])
    assert r["items"][0]["image_removed"]
    red, og = pymupdf.open(pdf_dir / "project-999.pdf"), pymupdf.open(pdf_dir / "project-999_OG.pdf")
    assert red[0].get_image_info() == [] and len(og[0].get_image_info()) == 1
    assert "keep this caption" in red[0].get_text()


def test_clean_for_ui_placeholders():
    from aipil.export.exports import clean_for_ui
    r = clean_for_ui({"student_type": "No data submitted", "x": "nan", "license": "unknown", "level": "unknown",
                      "ok": "Finance & Business", "n": float("nan"), "l": ["", "a"]})
    assert r["student_type"] is None and r["x"] is None and r["license"] is None and r["n"] is None
    assert r["level"] == "unknown" and r["ok"] == "Finance & Business" and r["l"] == [None, "a"]
