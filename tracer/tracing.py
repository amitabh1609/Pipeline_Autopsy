from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, Optional

from pydantic import BaseModel

from tracer.models import Span, Trace
from tracer.storage import TraceStorage


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_dict(value: Any) -> Optional[Dict[str, Any]]:
    if value is None:
        return None
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return {"value": str(value)}


def _default_storage() -> TraceStorage:
    sqlite_path = Path(os.getenv("TRACE_DB_PATH", "data/traces.sqlite"))
    jsonl_path_env = os.getenv("TRACE_JSONL_PATH", "data/traces.jsonl")
    jsonl_path = Path(jsonl_path_env) if jsonl_path_env else None
    return TraceStorage(sqlite_path=sqlite_path, jsonl_path=jsonl_path)


class PipelineTracer:
    def __init__(self, storage: Optional[TraceStorage] = None):
        self.storage = storage or _default_storage()

    def start_trace(self, *, document_id: str, attributes: Optional[Dict[str, Any]] = None) -> Trace:
        trace = Trace(document_id=document_id, attributes=attributes or {})
        self.storage.upsert_trace(trace)
        return trace

    def end_trace(self, trace: Trace, *, status: str) -> Trace:
        trace.ended_at = _utcnow()
        trace.status = status
        self.storage.upsert_trace(trace)
        return trace

    @contextmanager
    def span(
        self,
        *,
        trace: Trace,
        name: str,
        step_input: Any,
        attributes: Optional[Dict[str, Any]] = None,
        parent_span_id: Optional[str] = None,
    ) -> Generator[Span, None, None]:
        span = Span(
            trace_id=trace.trace_id,
            parent_span_id=parent_span_id,
            name=name,
            input=_as_dict(step_input),
            attributes=attributes or {},
        )
        self.storage.upsert_span(span)
        try:
            yield span
            span.status = "OK"
        except Exception as exc:
            span.status = "ERROR"
            span.error = str(exc)
            raise
        finally:
            span.ended_at = _utcnow()
            self.storage.upsert_span(span)

    def set_span_output(self, span: Span, step_output: Any) -> None:
        span.output = _as_dict(step_output)
        self.storage.upsert_span(span)
