import os
from pathlib import Path

from analyzer.judge import judge_run
from analyzer.models import DiagnosisReport
from analyzer.root_cause import diagnose_failure
from eval.regression import regression_snapshot
from eval.storage import append_eval_case
from pipeline.models import PipelineResult
from tracer.storage import TraceStorage


def run_diagnosis(
    *,
    document_id: str,
    document_text: str,
    pipeline_result: PipelineResult,
) -> tuple[DiagnosisReport, dict]:
    trace_id = pipeline_result.trace_id
    spans = []
    if trace_id:
        db_path = Path(os.getenv("TRACE_DB_PATH", "data/traces.sqlite"))
        spans = list(TraceStorage(sqlite_path=db_path).list_spans(trace_id))

    judge_result = judge_run(document_text=document_text, pipeline_result=pipeline_result)
    diagnosis = diagnose_failure(
        document_id=document_id,
        trace_id=trace_id,
        document_text=document_text,
        spans=spans,
        pipeline_result=pipeline_result,
        judge_result=judge_result,
    )

    eval_row = {}
    if not diagnosis.passed:
        eval_path = Path(os.getenv("EVAL_DATASET_PATH", "eval/failure_dataset.jsonl"))
        eval_row = append_eval_case(
            output_path=eval_path,
            document_text=document_text,
            pipeline_result=pipeline_result,
            diagnosis=diagnosis,
        )
    return diagnosis, eval_row


def get_regression_summary() -> dict:
    eval_path = Path(os.getenv("EVAL_DATASET_PATH", "eval/failure_dataset.jsonl"))
    return regression_snapshot(eval_path)

