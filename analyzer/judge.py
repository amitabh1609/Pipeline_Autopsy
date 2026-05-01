import os

from analyzer.models import JudgeResult
from pipeline.models import PipelineResult


def _llm_mode() -> str:
    return os.getenv("LLM_MODE", "mock").strip().lower()


def judge_run(document_text: str, pipeline_result: PipelineResult) -> JudgeResult:
    # Phase 3 keeps this offline-first. OpenAI mode can be swapped in later.
    _ = _llm_mode()
    summary = pipeline_result.summarization.summary.strip()
    label = pipeline_result.classification.label
    confidence = pipeline_result.classification.confidence

    if len(document_text.strip()) < 30:
        return JudgeResult(
            passed=False,
            confidence=0.92,
            reason="Input document is too short to support reliable extraction and summary.",
        )
    if not summary:
        return JudgeResult(
            passed=False,
            confidence=0.95,
            reason="Final summary is empty.",
        )
    if label == "other" and confidence < 0.65:
        return JudgeResult(
            passed=False,
            confidence=0.83,
            reason="Classifier returned low-confidence generic label.",
        )
    if len(pipeline_result.extraction.facts) == 0:
        return JudgeResult(
            passed=False,
            confidence=0.88,
            reason="No extractable facts were produced.",
        )
    return JudgeResult(
        passed=True,
        confidence=0.8,
        reason="Output is coherent and contains usable structured information.",
    )

