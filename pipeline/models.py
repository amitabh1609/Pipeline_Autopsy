from typing import List

from pydantic import BaseModel, Field


class IntakeInput(BaseModel):
    document_id: str = Field(..., description="Unique document identifier")
    text: str = Field(..., description="Raw document text")
    chunk_size: int = Field(default=800, ge=100, le=4000)
    overlap: int = Field(default=100, ge=0, le=500)


class IntakeOutput(BaseModel):
    document_id: str
    chunks: List[str]
    chunk_count: int


class ExtractionInput(BaseModel):
    document_id: str
    chunks: List[str]


class ExtractionOutput(BaseModel):
    document_id: str
    entities: List[str]
    facts: List[str]
    raw_model_output: str


class ClassificationInput(BaseModel):
    document_id: str
    chunks: List[str]
    entities: List[str]
    facts: List[str]


class ClassificationOutput(BaseModel):
    document_id: str
    label: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str


class SummarizationInput(BaseModel):
    document_id: str
    chunks: List[str]
    entities: List[str]
    facts: List[str]
    label: str
    rationale: str


class SummarizationOutput(BaseModel):
    document_id: str
    summary: str


class PipelineResult(BaseModel):
    intake: IntakeOutput
    extraction: ExtractionOutput
    classification: ClassificationOutput
    summarization: SummarizationOutput

