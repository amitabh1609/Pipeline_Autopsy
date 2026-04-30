import json
from pathlib import Path

from pipeline.runner import run_pipeline
from tracer.storage import TraceStorage


def test_trace_writes_four_spans_in_mock_mode(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LLM_MODE", "mock")
    db_path = tmp_path / "traces.sqlite"
    jsonl_path = tmp_path / "traces.jsonl"
    monkeypatch.setenv("TRACE_DB_PATH", str(db_path))
    monkeypatch.setenv("TRACE_JSONL_PATH", str(jsonl_path))

    result = run_pipeline(document_id="trace_test", text="Invoice #123\nTotal Due: $10\n")
    assert result.classification.label in {"invoice", "other"}

    storage = TraceStorage(sqlite_path=db_path)
    trace_events = [
        json.loads(ln)
        for ln in jsonl_path.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    traces = [e for e in trace_events if e.get("type") == "trace"]
    assert traces
    trace_id = traces[-1]["trace_id"]

    spans = list(storage.list_spans(trace_id))
    assert [s["name"] for s in spans] == ["intake", "extraction", "classification", "summarization"]
    assert all(s["status"] in {"OK", "ERROR"} for s in spans)
