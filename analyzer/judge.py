import json
import os
from pathlib import Path
from typing import TypeVar

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from analyzer.models import JudgeResult
from pipeline.models import PipelineResult

try:
    load_dotenv(dotenv_path=Path.cwd() / ".env")
except OSError:
    pass

MODEL_NAME = "gpt-4o-mini"
T = TypeVar("T", bound=BaseModel)


def _llm_mode() -> str:
    return os.getenv("LLM_MODE", "mock").strip().lower()


def _require_openai_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise EnvironmentError("OPENAI_API_KEY not found in environment or .env file.")


def _invoke_structured(prompt: str, output_model: type[T]) -> T:
    _require_openai_key()
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0)
    structured_llm = llm.with_structured_output(output_model)
    return structured_llm.invoke(prompt)


def _heuristic_judge(document_text: str, pipeline_result: PipelineResult) -> JudgeResult:
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


def _llm_judge(document_text: str, pipeline_result: PipelineResult) -> JudgeResult:
    doc_preview = document_text.strip()
    if len(doc_preview) > 12_000:
        doc_preview = doc_preview[:12_000] + "\n\n[…truncated for judge context…]"

    class Verdict(BaseModel):
        passed: bool = Field(description="True if summary and structured outputs fit the document.")
        confidence: float = Field(ge=0.0, le=1.0, description="Certainty in this verdict.")
        reason: str = Field(description="Short justification referencing contradictions or gaps if failed.")

    payload = {
        "classification": pipeline_result.classification.model_dump(),
        "extraction": {
            "entities": pipeline_result.extraction.entities,
            "facts": pipeline_result.extraction.facts,
        },
        "summary": pipeline_result.summarization.summary,
    }

    prompt = f"""
You are an evaluator for a multi-step document pipeline (extract → classify → summarize).
Decide if the final outputs are acceptable for the given document: no major hallucinations,
misclassification that contradicts obvious document intent, empty or misleading summary, or missing critical facts.

Return strict JSON matching the schema: passed (bool), confidence (0-1), reason (brief).

Document text:
{doc_preview}

Pipeline outputs (JSON):
{json.dumps(payload, ensure_ascii=True)}
""".strip()

    verdict = _invoke_structured(prompt, Verdict)
    return JudgeResult(
        passed=verdict.passed,
        confidence=min(1.0, max(0.0, verdict.confidence)),
        reason=verdict.reason.strip(),
    )


def judge_run(document_text: str, pipeline_result: PipelineResult) -> JudgeResult:
    if _llm_mode() != "openai":
        return _heuristic_judge(document_text, pipeline_result)

    summary = pipeline_result.summarization.summary.strip()
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

    return _llm_judge(document_text, pipeline_result)
