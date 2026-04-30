from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Trace(BaseModel):
    trace_id: str = Field(default_factory=lambda: uuid4().hex)
    document_id: str
    started_at: datetime = Field(default_factory=_utcnow)
    ended_at: Optional[datetime] = None
    status: str = Field(default="IN_PROGRESS")
    attributes: Dict[str, Any] = Field(default_factory=dict)


class Span(BaseModel):
    trace_id: str
    span_id: str = Field(default_factory=lambda: uuid4().hex)
    parent_span_id: Optional[str] = None
    name: str
    started_at: datetime = Field(default_factory=_utcnow)
    ended_at: Optional[datetime] = None
    status: str = Field(default="IN_PROGRESS")
    error: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    input: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
