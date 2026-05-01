"""TraceBack HTTP API — run pipeline and optional diagnosis."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI
from pydantic import BaseModel, Field
from starlette.responses import RedirectResponse

from analyzer.service import get_regression_summary, run_diagnosis
from pipeline.runner import run_pipeline

app = FastAPI(title="TraceBack", version="0.1.0")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Opening the server root in a browser lands on interactive API docs."""
    return RedirectResponse(url="/docs")


class PipelineRunRequest(BaseModel):
    document_id: str = Field(..., min_length=1)
    text: str = Field(..., description="Raw document body")


class PipelineRunResponse(BaseModel):
    pipeline_result: Dict[str, Any]


class AnalyzeResponse(BaseModel):
    pipeline_result: Dict[str, Any]
    diagnosis: Dict[str, Any]
    eval_row: Dict[str, Any]
    regression: Dict[str, float]


@app.post("/pipeline/run", response_model=PipelineRunResponse)
def post_run(body: PipelineRunRequest) -> PipelineRunResponse:
    result = run_pipeline(document_id=body.document_id, text=body.text)
    return PipelineRunResponse(pipeline_result=result.model_dump())


@app.post("/pipeline/analyze", response_model=AnalyzeResponse)
def post_analyze(body: PipelineRunRequest) -> AnalyzeResponse:
    result = run_pipeline(document_id=body.document_id, text=body.text)
    diagnosis, eval_row = run_diagnosis(
        document_id=body.document_id,
        document_text=body.text,
        pipeline_result=result,
    )
    return AnalyzeResponse(
        pipeline_result=result.model_dump(),
        diagnosis=diagnosis.model_dump(),
        eval_row=eval_row or {},
        regression=get_regression_summary(),
    )


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}
