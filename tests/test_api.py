import pytest
from starlette.testclient import TestClient


@pytest.fixture
def api_client(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_MODE", "mock")
    monkeypatch.setenv("TRACE_DB_PATH", str(tmp_path / "tr.sqlite"))
    monkeypatch.setenv("TRACE_JSONL_PATH", str(tmp_path / "tr.jsonl"))
    monkeypatch.setenv("EVAL_DATASET_PATH", str(tmp_path / "eval.jsonl"))
    from api.main import app

    return TestClient(app)


def test_health(api_client: TestClient) -> None:
    r = api_client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_root_redirect(api_client: TestClient) -> None:
    r = api_client.get("/", follow_redirects=False)
    assert r.status_code == 307
    assert r.headers.get("location") == "/docs"


def test_pipeline_run(api_client: TestClient) -> None:
    r = api_client.post(
        "/pipeline/run",
        json={"document_id": "api_test", "text": "Invoice #1\nTotal Due: $50\nPayment Terms: Net 30\n"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "pipeline_result" in body
    pr = body["pipeline_result"]
    assert pr["classification"]["label"] in {"invoice", "support_ticket", "policy_update", "other"}
    assert pr["trace_id"]
    assert pr["summarization"]["summary"]


def test_pipeline_analyze(api_client: TestClient) -> None:
    r = api_client.post(
        "/pipeline/analyze",
        json={"document_id": "api_analyze", "text": "Need help ASAP."},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["diagnosis"]["passed"] is False
    assert "regression" in body
    assert "eval_row" in body
