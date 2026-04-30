import json
import os
import re
from pathlib import Path
from typing import List, TypeVar

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from pipeline.models import (
    ClassificationInput,
    ClassificationOutput,
    ExtractionInput,
    ExtractionOutput,
    IntakeInput,
    IntakeOutput,
    SummarizationInput,
    SummarizationOutput,
)

try:
    load_dotenv(dotenv_path=Path.cwd() / ".env")
except OSError:
    # Some environments may block/timeout reading .env; env vars can still be supplied by shell.
    pass

MODEL_NAME = "gpt-4o-mini"
T = TypeVar("T", bound=BaseModel)


def _require_openai_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise EnvironmentError("OPENAI_API_KEY not found in environment or .env file.")


def _llm_mode() -> str:
    return os.getenv("LLM_MODE", "mock").strip().lower()


def _chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    cleaned = text.strip()
    if not cleaned:
        return []

    if overlap >= chunk_size:
        overlap = max(0, chunk_size - 1)

    chunks: List[str] = []
    start = 0
    while start < len(cleaned):
        end = start + chunk_size
        chunks.append(cleaned[start:end])
        if end >= len(cleaned):
            break
        start = end - overlap
    return chunks


def intake_step(step_input: IntakeInput) -> IntakeOutput:
    chunks = _chunk_text(step_input.text, step_input.chunk_size, step_input.overlap)
    return IntakeOutput(
        document_id=step_input.document_id,
        chunks=chunks,
        chunk_count=len(chunks),
    )


def _invoke_structured(prompt: str, output_model: type[T]) -> T:
    _require_openai_key()
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0)
    structured_llm = llm.with_structured_output(output_model)
    return structured_llm.invoke(prompt)


def _extract_mock(chunks: List[str]) -> tuple[List[str], List[str]]:
    combined = "\n".join(chunks)
    entities = sorted(
        {
            token.strip(".,:;!?()[]{}\"'")
            for token in re.findall(r"\b[A-Z][A-Za-z0-9_-]{2,}\b", combined)
        }
    )
    facts = [line.strip("- ").strip() for line in combined.splitlines() if line.strip()]
    return entities[:20], facts[:20]


def _classify_mock(chunks: List[str], entities: List[str], facts: List[str]) -> tuple[str, float, str]:
    text = " ".join(chunks).lower()
    if any(k in text for k in ["invoice", "total due", "payment terms", "tax"]):
        return "invoice", 0.93, "Detected financial terms consistent with invoice documents."
    if any(k in text for k in ["ticket", "issue", "priority", "crash", "support"]):
        return "support_ticket", 0.9, "Detected incident/support language and ticket structure."
    if any(k in text for k in ["policy", "compliance", "guideline"]):
        return "policy_update", 0.82, "Detected policy/compliance-oriented language."
    if len(facts) <= 2 or len(" ".join(facts)) < 80:
        return "other", 0.55, "Very short context; insufficient signals for stronger classification."
    if len(entities) <= 1:
        return "other", 0.6, "Sparse entity extraction indicates ambiguous document type."
    return "research_note", 0.72, "Defaulted to general informational category."


def _summarize_mock(
    *,
    label: str,
    rationale: str,
    entities: List[str],
    facts: List[str],
) -> str:
    top_entities = ", ".join(entities[:5]) if entities else "none"
    top_facts = "; ".join(facts[:3]) if facts else "no explicit facts extracted"
    return (
        f"Document classified as '{label}'. "
        f"Key entities: {top_entities}. "
        f"Main points: {top_facts}. "
        f"Classifier rationale: {rationale}"
    )


def extraction_step(step_input: ExtractionInput) -> ExtractionOutput:
    if _llm_mode() != "openai":
        entities, facts = _extract_mock(step_input.chunks)
        return ExtractionOutput(
            document_id=step_input.document_id,
            entities=entities,
            facts=facts,
            raw_model_output=json.dumps(
                {"mode": "mock", "entities_count": len(entities), "facts_count": len(facts)},
                ensure_ascii=True,
            ),
        )

    prompt = f"""
You are an information extraction assistant.
Extract key entities and factual statements from the document chunks below.
Return concise results and avoid inventing details.

Document ID: {step_input.document_id}
Chunks:
{json.dumps(step_input.chunks, ensure_ascii=True)}
""".strip()

    class ExtractionPayload(BaseModel):
        entities: List[str]
        facts: List[str]

    model_output = _invoke_structured(prompt, ExtractionPayload)
    return ExtractionOutput(
        document_id=step_input.document_id,
        entities=model_output.entities,
        facts=model_output.facts,
        raw_model_output=model_output.model_dump_json(),
    )


def classification_step(step_input: ClassificationInput) -> ClassificationOutput:
    if _llm_mode() != "openai":
        label, confidence, rationale = _classify_mock(
            step_input.chunks, step_input.entities, step_input.facts
        )
        return ClassificationOutput(
            document_id=step_input.document_id,
            label=label,
            confidence=confidence,
            rationale=rationale,
        )

    prompt = f"""
Classify this document into a practical business category.
Examples: invoice, support_ticket, policy_update, legal_notice, medical_note, research_note, other.
Use provided chunks, entities, and facts.

Document ID: {step_input.document_id}
Chunks: {json.dumps(step_input.chunks, ensure_ascii=True)}
Entities: {json.dumps(step_input.entities, ensure_ascii=True)}
Facts: {json.dumps(step_input.facts, ensure_ascii=True)}
""".strip()

    class ClassificationPayload(BaseModel):
        label: str
        confidence: float
        rationale: str

    model_output = _invoke_structured(prompt, ClassificationPayload)
    clamped_confidence = min(1.0, max(0.0, model_output.confidence))
    return ClassificationOutput(
        document_id=step_input.document_id,
        label=model_output.label.strip().lower().replace(" ", "_"),
        confidence=clamped_confidence,
        rationale=model_output.rationale,
    )


def summarization_step(step_input: SummarizationInput) -> SummarizationOutput:
    if _llm_mode() != "openai":
        return SummarizationOutput(
            document_id=step_input.document_id,
            summary=_summarize_mock(
                label=step_input.label,
                rationale=step_input.rationale,
                entities=step_input.entities,
                facts=step_input.facts,
            ),
        )

    prompt = f"""
Create a clear summary of this document.
Highlight the most critical points, keep it under 120 words, and avoid speculation.

Document ID: {step_input.document_id}
Class: {step_input.label}
Classification rationale: {step_input.rationale}
Entities: {json.dumps(step_input.entities, ensure_ascii=True)}
Facts: {json.dumps(step_input.facts, ensure_ascii=True)}
Chunks: {json.dumps(step_input.chunks, ensure_ascii=True)}
""".strip()

    class SummaryPayload(BaseModel):
        summary: str

    model_output = _invoke_structured(prompt, SummaryPayload)
    return SummarizationOutput(
        document_id=step_input.document_id,
        summary=model_output.summary.strip(),
    )

