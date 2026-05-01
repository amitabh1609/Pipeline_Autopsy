from typing import Any, Dict, Iterable, Optional

from analyzer.models import DiagnosisReport, FailureType, JudgeResult
from pipeline.models import PipelineResult


def _infer_failure_type(
    *,
    failing_step: str,
    document_text: str,
    pipeline_result: PipelineResult,
) -> FailureType:
    if len(document_text.strip()) < 30 or pipeline_result.intake.chunk_count == 0:
        return "Context Loss"
    if failing_step == "extraction":
        return "Extraction Hallucination"
    if failing_step == "classification":
        return "Misclassification"
    return "Propagation Error"


def _detect_failing_step(
    *,
    spans: Iterable[Dict[str, Any]],
    document_text: str,
    pipeline_result: PipelineResult,
) -> Optional[str]:
    ordered = list(spans)
    for span in reversed(ordered):
        if span.get("status") == "ERROR":
            return span.get("name")

    # Heuristic fallback when all spans are OK but final judged result is poor.
    if len(document_text.strip()) < 30:
        return "intake"
    if len(pipeline_result.extraction.facts) == 0:
        return "extraction"
    if pipeline_result.classification.label == "other" and pipeline_result.classification.confidence < 0.65:
        return "classification"
    if len(pipeline_result.summarization.summary.strip()) == 0:
        return "summarization"
    return None


def diagnose_failure(
    *,
    document_id: str,
    trace_id: Optional[str],
    document_text: str,
    spans: Iterable[Dict[str, Any]],
    pipeline_result: PipelineResult,
    judge_result: JudgeResult,
) -> DiagnosisReport:
    if judge_result.passed:
        return DiagnosisReport(
            document_id=document_id,
            trace_id=trace_id,
            passed=True,
            judge_confidence=judge_result.confidence,
            judge_reason=judge_result.reason,
        )

    failing_step = _detect_failing_step(
        spans=spans,
        document_text=document_text,
        pipeline_result=pipeline_result,
    )
    failure_type = _infer_failure_type(
        failing_step=failing_step or "summarization",
        document_text=document_text,
        pipeline_result=pipeline_result,
    )
    return DiagnosisReport(
        document_id=document_id,
        trace_id=trace_id,
        passed=False,
        failing_step=failing_step,
        failure_type=failure_type,
        judge_confidence=judge_result.confidence,
        judge_reason=judge_result.reason,
    )

