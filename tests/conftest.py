import pandas as pd
import pytest

from aipil.ingestion.workbook import CRITERIA, TOTAL_COL, Workbook


@pytest.fixture
def synthetic_workbook():
    """Small synthetic workbook mirroring the real structure (no real student data)."""
    rows = []
    for i, scores in [(2, [5, 4, 3, 4, 5]), (3, [3, 3, 3, 3, 3]), (5, [5, 5, 4, 5, 5])]:
        r = {"project_id": f"project-{i:03d}", **dict(zip(CRITERIA, scores)), TOTAL_COL: sum(scores),
             "Title from title slide": f"Title {i}", "PDF Link": f"https://drive.google.com/file/d/PDF{i}/view",
             "Extracted Text": f"https://drive.google.com/file/d/TXT{i}/view",
             "Student-Provided Project Name": f"Title {i}", "Student-Provided Project Description": "desc",
             "Student-Provided Project Type": "Finance & Business"}
        rows.append(r)
    scores = pd.DataFrame(rows)
    rat = pd.DataFrame([{"project_id": r["project_id"], "Criterion": c, "Score": r[c], "Limiting factors": None,
                         "Rationale": "ok", "Slides cited": "1", "Evidence": "p1: x"} for r in rows for c in CRITERIA])
    rubric = pd.DataFrame({"Criteria": CRITERIA, "5\nExceeds Requirements": ["a"] * 5,
                           "4\nAt Times Exceeds Requirements": ["b"] * 5, "3\nMeets\nRequirement": ["c"] * 5,
                           "2\nBeginning to Meet Requirements": ["d"] * 5, "1\nNeeds Major Improvement": ["e"] * 5})
    return Workbook(scores=scores, rationale=rat, rubric=rubric)
