"""Aggregate stats from the eval / failure JSONL dataset (Phase 5)."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


def load_eval_rows(dataset_path: Path) -> List[Dict[str, Any]]:
    if not dataset_path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in dataset_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def load_human_flags(flags_path: Path) -> List[Dict[str, Any]]:
    if not flags_path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in flags_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def failure_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [r for r in rows if not r.get("passed", True)]


def dataset_overview(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    fails = failure_rows(rows)
    doc_ids = {r.get("document_id") for r in rows if r.get("document_id")}
    confidences = [float(r["judge_confidence"]) for r in fails if r.get("judge_confidence") is not None]
    avg_conf = sum(confidences) / len(confidences) if confidences else None
    return {
        "total_rows": len(rows),
        "failure_rows": len(fails),
        "unique_documents": len(doc_ids),
        "avg_judge_confidence_on_failures": avg_conf,
    }


def count_field(rows: List[Dict[str, Any]], field: str, *, subset_failures_only: bool = True) -> Dict[str, int]:
    source = failure_rows(rows) if subset_failures_only else rows
    ctr: Counter[str] = Counter()
    for r in source:
        raw = r.get(field)
        key = "(unknown)" if raw is None or raw == "" else str(raw)
        ctr[key] += 1
    return dict(ctr.most_common())


def failures_per_day(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    ctr: Counter[str] = Counter()
    for r in failure_rows(rows):
        ts = r.get("timestamp") or ""
        day = ts[:10] if isinstance(ts, str) and len(ts) >= 10 else "unknown"
        ctr[day] += 1
    return dict(sorted(ctr.items()))


def recent_failures(rows: List[Dict[str, Any]], *, limit: int = 25) -> List[Dict[str, Any]]:
    fails = failure_rows(rows)
    fails_sorted = sorted(fails, key=lambda r: str(r.get("timestamp") or ""), reverse=True)
    slim: List[Dict[str, Any]] = []
    for r in fails_sorted[:limit]:
        reason = str(r.get("judge_reason") or "")
        slim.append(
            {
                "timestamp": r.get("timestamp"),
                "document_id": r.get("document_id"),
                "failure_type": r.get("failure_type"),
                "failing_step": r.get("failing_step"),
                "classification_label": r.get("classification_label"),
                "judge_confidence": r.get("judge_confidence"),
                "judge_reason": (reason[:120] + "…") if len(reason) > 120 else reason or None,
            }
        )
    return slim
