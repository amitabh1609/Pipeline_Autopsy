import json
from pathlib import Path

from analyzer.service import get_regression_summary, run_diagnosis
from pipeline.runner import run_pipeline


def test_diagnosis_pass_case(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LLM_MODE", "mock")
    monkeypatch.setenv("TRACE_DB_PATH", str(tmp_path / "traces.sqlite"))
    monkeypatch.setenv("TRACE_JSONL_PATH", str(tmp_path / "traces.jsonl"))
    monkeypatch.setenv("EVAL_DATASET_PATH", str(tmp_path / "eval.jsonl"))

    text = "Invoice #INV-1\nVendor: ACME\nTotal Due: $500\nPayment Terms: Net 30\n"
    result = run_pipeline(document_id="pass_case", text=text)
    diagnosis, eval_row = run_diagnosis(
        document_id="pass_case",
        document_text=text,
        pipeline_result=result,
    )

    assert diagnosis.passed is True
    assert diagnosis.failure_type is None
    assert eval_row == {}
    summary = get_regression_summary()
    assert summary["total"] == 0.0


def test_diagnosis_failure_appends_eval(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LLM_MODE", "mock")
    monkeypatch.setenv("TRACE_DB_PATH", str(tmp_path / "traces.sqlite"))
    monkeypatch.setenv("TRACE_JSONL_PATH", str(tmp_path / "traces.jsonl"))
    eval_path = tmp_path / "eval.jsonl"
    monkeypatch.setenv("EVAL_DATASET_PATH", str(eval_path))

    text = "ASAP."
    result = run_pipeline(document_id="fail_case", text=text)
    diagnosis, eval_row = run_diagnosis(
        document_id="fail_case",
        document_text=text,
        pipeline_result=result,
    )

    assert diagnosis.passed is False
    assert diagnosis.failure_type == "Context Loss"
    assert eval_row["document_id"] == "fail_case"
    lines = [json.loads(ln) for ln in eval_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    summary = get_regression_summary()
    assert summary["total"] == 1.0
    assert summary["failed"] == 1.0
    assert summary["pass_rate"] == 0.0

