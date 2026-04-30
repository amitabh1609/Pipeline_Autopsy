from pipeline.runner import run_pipeline


INVOICE_SAMPLE = """
Invoice #INV-1001
Date: 2026-04-10
Vendor: Northwind Supplies
Customer: Blue Harbor Retail
Items: 3 office chairs ($120 each), 2 desks ($310 each)
Subtotal: $980
Tax: $98
Total Due: $1,078
Payment Terms: Net 30
""".strip()

SHORT_SAMPLE = "Need this handled ASAP."


def test_pipeline_runs_invoice_in_mock_mode(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "mock")
    result = run_pipeline(
        document_id="invoice_test",
        text=INVOICE_SAMPLE,
    )

    assert result.intake.chunk_count >= 1
    assert isinstance(result.extraction.entities, list)
    assert isinstance(result.extraction.facts, list)
    assert result.classification.label in {
        "invoice",
        "support_ticket",
        "policy_update",
        "legal_notice",
        "medical_note",
        "research_note",
        "other",
    }
    assert 0.0 <= result.classification.confidence <= 1.0
    assert len(result.summarization.summary) > 0


def test_pipeline_handles_very_short_document(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "mock")
    result = run_pipeline(
        document_id="short_test",
        text=SHORT_SAMPLE,
    )

    assert result.intake.chunk_count == 1
    assert result.classification.label == "other"
    assert "insufficient signals" in result.classification.rationale.lower()

