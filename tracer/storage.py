from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from tracer.models import Span, Trace


def _dt_to_iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), default=str)


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS traces (
  trace_id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  status TEXT NOT NULL,
  attributes_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS spans (
  span_id TEXT PRIMARY KEY,
  trace_id TEXT NOT NULL,
  parent_span_id TEXT,
  name TEXT NOT NULL,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  status TEXT NOT NULL,
  error TEXT,
  attributes_json TEXT NOT NULL,
  input_json TEXT,
  output_json TEXT,
  FOREIGN KEY(trace_id) REFERENCES traces(trace_id)
);

CREATE INDEX IF NOT EXISTS idx_spans_trace_id ON spans(trace_id);
"""


@dataclass(frozen=True)
class TraceStorage:
    sqlite_path: Path
    jsonl_path: Optional[Path] = None

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.sqlite_path))
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def ensure_schema(self) -> None:
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)

    def upsert_trace(self, trace: Trace) -> None:
        self.ensure_schema()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO traces(trace_id, document_id, started_at, ended_at, status, attributes_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(trace_id) DO UPDATE SET
                  ended_at=excluded.ended_at,
                  status=excluded.status,
                  attributes_json=excluded.attributes_json
                """,
                (
                    trace.trace_id,
                    trace.document_id,
                    _dt_to_iso(trace.started_at),
                    _dt_to_iso(trace.ended_at),
                    trace.status,
                    _json_dumps(trace.attributes),
                ),
            )

        if self.jsonl_path:
            self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"type": "trace", **trace.model_dump()}
            with self.jsonl_path.open("a", encoding="utf-8") as f:
                f.write(_json_dumps(payload) + "\n")

    def upsert_span(self, span: Span) -> None:
        self.ensure_schema()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO spans(span_id, trace_id, parent_span_id, name, started_at, ended_at, status, error,
                                 attributes_json, input_json, output_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(span_id) DO UPDATE SET
                  ended_at=excluded.ended_at,
                  status=excluded.status,
                  error=excluded.error,
                  attributes_json=excluded.attributes_json,
                  input_json=excluded.input_json,
                  output_json=excluded.output_json
                """,
                (
                    span.span_id,
                    span.trace_id,
                    span.parent_span_id,
                    span.name,
                    _dt_to_iso(span.started_at),
                    _dt_to_iso(span.ended_at),
                    span.status,
                    span.error,
                    _json_dumps(span.attributes),
                    _json_dumps(span.input) if span.input is not None else None,
                    _json_dumps(span.output) if span.output is not None else None,
                ),
            )

        if self.jsonl_path:
            self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"type": "span", **span.model_dump()}
            with self.jsonl_path.open("a", encoding="utf-8") as f:
                f.write(_json_dumps(payload) + "\n")

    def list_spans(self, trace_id: str) -> Iterable[Dict[str, Any]]:
        self.ensure_schema()
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT span_id, trace_id, parent_span_id, name, started_at, ended_at, status, error,
                       attributes_json, input_json, output_json
                FROM spans
                WHERE trace_id = ?
                ORDER BY started_at ASC
                """,
                (trace_id,),
            )
            cols = [c[0] for c in cur.description]
            for row in cur.fetchall():
                item = dict(zip(cols, row))
                for key in ["attributes_json", "input_json", "output_json"]:
                    if item.get(key):
                        item[key] = json.loads(item[key])
                yield item

    def list_recent_traces(self, *, limit: int = 50) -> Iterable[Dict[str, Any]]:
        self.ensure_schema()
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT trace_id, document_id, started_at, ended_at, status, attributes_json
                FROM traces
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            cols = [c[0] for c in cur.description]
            for row in cur.fetchall():
                item = dict(zip(cols, row))
                if item.get("attributes_json"):
                    item["attributes_json"] = json.loads(item["attributes_json"])
                yield item
