import json
from pathlib import Path

import pytest

from eval.analytics import (
    count_field,
    dataset_overview,
    failures_per_day,
    load_eval_rows,
    recent_failures,
)


def test_analytics_empty(tmp_path: Path):
    p = tmp_path / "empty.jsonl"
    assert load_eval_rows(p) == []
    assert dataset_overview([])["total_rows"] == 0


def test_analytics_aggregates(tmp_path: Path):
    p = tmp_path / "eval.jsonl"
    rows_data = [
        {
            "timestamp": "2026-05-01T10:00:00+00:00",
            "document_id": "a",
            "passed": False,
            "failing_step": "extraction",
            "failure_type": "Extraction Hallucination",
            "judge_confidence": 0.9,
            "judge_reason": "x",
        },
        {
            "timestamp": "2026-05-02T11:00:00+00:00",
            "document_id": "b",
            "passed": False,
            "failing_step": "classification",
            "failure_type": "Misclassification",
            "judge_confidence": 0.8,
            "judge_reason": "y",
        },
    ]
    p.write_text("\n".join(json.dumps(r, ensure_ascii=True) for r in rows_data), encoding="utf-8")
    loaded = load_eval_rows(p)
    assert len(loaded) == 2
    ov = dataset_overview(loaded)
    assert ov["failure_rows"] == 2
    assert ov["avg_judge_confidence_on_failures"] == pytest.approx(0.85)
    ft = count_field(loaded, "failure_type")
    assert ft["Extraction Hallucination"] == 1
    assert ft["Misclassification"] == 1
    by_day = failures_per_day(loaded)
    assert by_day["2026-05-01"] == 1
    assert by_day["2026-05-02"] == 1
    recent = recent_failures(loaded, limit=10)
    assert len(recent) == 2
