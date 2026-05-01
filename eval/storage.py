import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from analyzer.models import DiagnosisReport
from pipeline.models import PipelineResult


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_eval_case(
    *,
    output_path: Path,
    document_text: str,
    pipeline_result: PipelineResult,
    diagnosis: DiagnosisReport,
) -> Dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload: Dict[str, Any] = {
        "timestamp": _utcnow_iso(),
        "document_id": diagnosis.document_id,
        "trace_id": diagnosis.trace_id,
        "passed": diagnosis.passed,
        "failing_step": diagnosis.failing_step,
        "failure_type": diagnosis.failure_type,
        "judge_confidence": diagnosis.judge_confidence,
        "judge_reason": diagnosis.judge_reason,
        "document_text": document_text,
        "classification_label": pipeline_result.classification.label,
        "summary": pipeline_result.summarization.summary,
    }
    with output_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")
    return payload

