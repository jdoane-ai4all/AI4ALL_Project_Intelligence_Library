import sqlite3

from aipil.ingestion.workbook import (drive_id, import_workbook, init_db, parse_rubric, validate)


def test_clean_workbook_has_no_errors(synthetic_workbook):
    rep = validate(synthetic_workbook)
    assert rep.errors == []
    assert rep.stats["n_unique_projects"] == 3
    assert rep.stats["id_gaps"] == ["project-004"]  # gaps are reported as info, never relabeled


def test_total_mismatch_detected(synthetic_workbook):
    synthetic_workbook.scores.loc[0, "Strict total (scored criteria)"] = 99
    assert any(f.check_name == "total_mismatch" for f in validate(synthetic_workbook).errors)


def test_out_of_range_and_sheet_mismatch(synthetic_workbook):
    synthetic_workbook.scores.loc[1, "Algorithm"] = 7
    synthetic_workbook.rationale.loc[0, "Score"] = 1
    names = {f.check_name for f in validate(synthetic_workbook).errors}
    assert {"score_out_of_range", "score_sheet_mismatch"} <= names


def test_missing_rationale_rows(synthetic_workbook):
    synthetic_workbook.rationale = synthetic_workbook.rationale.iloc[1:]
    assert any(f.check_name == "rationale_count" for f in validate(synthetic_workbook).errors)


def test_duplicate_ids(synthetic_workbook):
    import pandas as pd
    wb = synthetic_workbook
    wb.scores = pd.concat([wb.scores, wb.scores.iloc[[0]]], ignore_index=True)
    assert any(f.check_name == "duplicate_project_id" for f in validate(wb).errors)


def test_rubric_parsing(synthetic_workbook):
    rows = parse_rubric(synthetic_workbook.rubric)
    assert len(rows) == 25
    assert {r["level"] for r in rows} == {1, 2, 3, 4, 5}
    assert any(r["level_name"] == "Meets Requirement" for r in rows)


def test_drive_id():
    assert drive_id("https://drive.google.com/file/d/AbC_1-2/view?usp=drivesdk") == "AbC_1-2"
    assert drive_id(None) is None


def test_import_preserves_scores(synthetic_workbook):
    con = sqlite3.connect(":memory:")
    init_db(con)
    rep = validate(synthetic_workbook)
    import_workbook(synthetic_workbook, con, rep)
    assert con.execute("select count(*) from projects").fetchone()[0] == 3
    assert con.execute("select count(*) from raw_scores").fetchone()[0] == 3
    assert con.execute("select count(*) from rubric_evaluations").fetchone()[0] == 15
    got = con.execute("select score from rubric_scores where project_id='project-002' and criterion='Essential Question'").fetchone()[0]
    assert got == 3
    # Idempotent re-import
    import_workbook(synthetic_workbook, con, rep)
    assert con.execute("select count(*) from rubric_scores").fetchone()[0] == 15


def test_rebuild_is_idempotent_with_foreign_keys(tmp_path, monkeypatch, synthetic_workbook):
    """Regression: rebuilding derived tables must not violate FK constraints when data already exists."""
    import json
    from aipil import paths
    from aipil.database import build as b
    db = tmp_path / "t.sqlite"
    monkeypatch.setattr(paths, "DB_PATH", db)
    monkeypatch.setattr(paths, "EXTRACTIONS", tmp_path / "ex")
    monkeypatch.setattr(paths, "RESEARCH", tmp_path / "res")
    (tmp_path / "ex").mkdir()
    con = sqlite3.connect(db)
    init_db(con)
    import_workbook(synthetic_workbook, con, validate(synthetic_workbook))
    con.execute("PRAGMA foreign_keys = ON")
    b.load_taxonomy(con)
    con.execute("INSERT INTO project_terms VALUES ('project-002','industry:finance','industry','confirmed',NULL,NULL,1)")
    con.commit()
    con.close()
    b.build()
    b.build()
