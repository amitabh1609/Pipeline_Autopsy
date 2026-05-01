"""
TraceBack — Streamlit trace explorer (Phase 4).

Run from repo root:
  streamlit run ui/app.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

from tracer.storage import TraceStorage


def _storage() -> TraceStorage:
    sqlite_path = Path(os.getenv("TRACE_DB_PATH", "data/traces.sqlite"))
    return TraceStorage(sqlite_path=sqlite_path)


def _status_color(status: str) -> str:
    if status == "OK":
        return "#22c55e"
    if status == "ERROR":
        return "#ef4444"
    return "#94a3b8"


def main() -> None:
    st.set_page_config(page_title="TraceBack", layout="wide")
    st.title("TraceBack")
    st.caption("Pipeline traces — colour-coded steps, span payloads, quick human flags.")

    storage = _storage()
    traces = list(storage.list_recent_traces(limit=100))

    if not traces:
        st.info(
            "No traces found. Run the pipeline first, e.g. "
            "`LLM_MODE=mock python3 main.py --document documents/01_clean_invoice.txt`"
        )
        return

    labels = [
        f"{t['document_id']} — {t['trace_id'][:8]}… — {t['status']} — {t['started_at']}"
        for t in traces
    ]
    choice = st.selectbox("Recent trace", options=list(range(len(traces))), format_func=lambda i: labels[i])
    selected = traces[choice]
    trace_id = selected["trace_id"]

    col_doc, col_sum = st.columns(2)
    spans = list(storage.list_spans(trace_id))

    st.subheader("Pipeline steps")
    cols = st.columns(len(spans) if spans else 1)
    for i, span in enumerate(spans):
        name = span.get("name", "?")
        status = span.get("status", "?")
        color = _status_color(status)
        with cols[i] if spans else st.container():
            st.markdown(
                f"<div style='text-align:center'><span style='color:{color};font-size:1.4rem'>●</span>"
                f"<br/><strong>{name}</strong><br/><small>{status}</small></div>",
                unsafe_allow_html=True,
            )

    st.divider()
    for span in spans:
        with st.expander(f"{span.get('name')} — {span.get('status')}", expanded=False):
            st.json({"input": span.get("input_json"), "output": span.get("output_json"), "error": span.get("error")})

    # Lightweight diff: raw inputs from intake vs final summary
    intake_out = next((s.get("output_json") for s in spans if s.get("name") == "intake"), None)
    summ_out = next((s.get("output_json") for s in spans if s.get("name") == "summarization"), None)
    chunks_preview = ""
    if isinstance(intake_out, dict) and intake_out.get("chunks"):
        chunks_preview = "\n\n".join(str(c) for c in intake_out["chunks"][:3])[:4000]
    summary_text = ""
    if isinstance(summ_out, dict) and summ_out.get("summary"):
        summary_text = str(summ_out["summary"])

    with col_doc:
        st.subheader("Source chunks (preview)")
        st.text_area("chunks", value=chunks_preview or "(no intake output)", height=220, disabled=True, label_visibility="collapsed")
    with col_sum:
        st.subheader("Final summary")
        st.text_area("summary", value=summary_text or "(no summary)", height=220, disabled=True, label_visibility="collapsed")

    st.divider()
    st.subheader("Human flag")
    flag_notes = st.text_input("Notes (saved as JSONL alongside traces)", placeholder="e.g. Misclassified as invoice")
    if st.button("Save flag"):
        flags_path = Path(os.getenv("HUMAN_FLAGS_PATH", "data/human_flags.jsonl"))
        flags_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "trace_id": trace_id,
            "document_id": selected.get("document_id"),
            "notes": flag_notes,
            "span_names": [s.get("name") for s in spans],
        }
        with flags_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")
        st.success(f"Appended to {flags_path}")


if __name__ == "__main__":
    main()
