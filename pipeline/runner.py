from pipeline.logging_utils import configure_logger, log_step
from pipeline.models import (
    ClassificationInput,
    ExtractionInput,
    IntakeInput,
    PipelineResult,
    SummarizationInput,
)
from pipeline.steps import (
    classification_step,
    extraction_step,
    intake_step,
    summarization_step,
)
from tracer.tracing import PipelineTracer


def run_pipeline(document_id: str, text: str) -> PipelineResult:
    logger = configure_logger()
    tracer = PipelineTracer()
    trace = tracer.start_trace(
        document_id=document_id,
        attributes={"component": "pipeline", "version": "phase1"},
    )

    intake_input = IntakeInput(document_id=document_id, text=text)
    try:
        with tracer.span(trace=trace, name="intake", step_input=intake_input) as span:
            intake_output = intake_step(intake_input)
            tracer.set_span_output(span, intake_output)
        log_step(
            logger=logger,
            step_name="intake",
            step_input=intake_input,
            step_output=intake_output,
            success=True,
        )
    except Exception as exc:  # pragma: no cover - defensive logging path
        tracer.end_trace(trace, status="ERROR")
        log_step(
            logger=logger,
            step_name="intake",
            step_input=intake_input,
            success=False,
            error=str(exc),
        )
        raise

    extraction_input = ExtractionInput(
        document_id=document_id,
        chunks=intake_output.chunks,
    )
    try:
        with tracer.span(trace=trace, name="extraction", step_input=extraction_input) as span:
            extraction_output = extraction_step(extraction_input)
            tracer.set_span_output(span, extraction_output)
        log_step(
            logger=logger,
            step_name="extraction",
            step_input=extraction_input,
            step_output=extraction_output,
            success=True,
        )
    except Exception as exc:  # pragma: no cover
        tracer.end_trace(trace, status="ERROR")
        log_step(
            logger=logger,
            step_name="extraction",
            step_input=extraction_input,
            success=False,
            error=str(exc),
        )
        raise

    classification_input = ClassificationInput(
        document_id=document_id,
        chunks=intake_output.chunks,
        entities=extraction_output.entities,
        facts=extraction_output.facts,
    )
    try:
        with tracer.span(trace=trace, name="classification", step_input=classification_input) as span:
            classification_output = classification_step(classification_input)
            tracer.set_span_output(span, classification_output)
        log_step(
            logger=logger,
            step_name="classification",
            step_input=classification_input,
            step_output=classification_output,
            success=True,
        )
    except Exception as exc:  # pragma: no cover
        tracer.end_trace(trace, status="ERROR")
        log_step(
            logger=logger,
            step_name="classification",
            step_input=classification_input,
            success=False,
            error=str(exc),
        )
        raise

    summarization_input = SummarizationInput(
        document_id=document_id,
        chunks=intake_output.chunks,
        entities=extraction_output.entities,
        facts=extraction_output.facts,
        label=classification_output.label,
        rationale=classification_output.rationale,
    )
    try:
        with tracer.span(trace=trace, name="summarization", step_input=summarization_input) as span:
            summarization_output = summarization_step(summarization_input)
            tracer.set_span_output(span, summarization_output)
        log_step(
            logger=logger,
            step_name="summarization",
            step_input=summarization_input,
            step_output=summarization_output,
            success=True,
        )
    except Exception as exc:  # pragma: no cover
        tracer.end_trace(trace, status="ERROR")
        log_step(
            logger=logger,
            step_name="summarization",
            step_input=summarization_input,
            success=False,
            error=str(exc),
        )
        raise

    tracer.end_trace(trace, status="OK")
    return PipelineResult(
        intake=intake_output,
        extraction=extraction_output,
        classification=classification_output,
        summarization=summarization_output,
    )

