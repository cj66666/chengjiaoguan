from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_claude_md_captures_backend_contract():
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")

    assert "/api/v1" in text
    assert "X-Seller-Id" in text
    assert "Every completed schedule task" in text
    assert "send_message" in text


def test_execution_plan_tracks_all_a_tasks():
    text = (ROOT / "docs" / "EXECUTION_PLAN.md").read_text(encoding="utf-8")

    for task_id in [
        "T05",
        "T06",
        "T07",
        "T08",
        "T09",
        "T10",
        "T11",
        "T12",
        "T13",
        "T14",
        "T15",
        "T18",
        "T19",
    ]:
        assert task_id in text

