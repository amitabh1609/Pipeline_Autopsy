from typing import Literal, Optional

from pydantic import BaseModel, Field


FailureType = Literal[
    "Extraction Hallucination",
    "Misclassification",
    "Propagation Error",
    "Context Loss",
]


class JudgeResult(BaseModel):
    passed: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str


class DiagnosisReport(BaseModel):
    document_id: str
    trace_id: Optional[str] = None
    passed: bool
    failing_step: Optional[str] = None
    failure_type: Optional[FailureType] = None
    judge_confidence: float
    judge_reason: str

