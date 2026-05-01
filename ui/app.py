"""
TraceBack — Streamlit console (Phases 4–5).

Run from repo root:
  streamlit run ui/app.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Streamlit executes this file with `ui/` on sys.path — repo packages live one level up.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pandas as pd
import streamlit as st

from analyzer.service import get_regression_summary, run_diagnosis
from eval.analytics import (
    count_field,
    dataset_overview,
    failures_per_day,
    load_eval_rows,
    load_human_flags,
    recent_failures,
)
from pipeline.runner import run_pipeline
from tracer.storage import TraceStorage

_SAMPLE_FILES: dict[str, str] = {
    "invoice": "01_clean_invoice.txt",
    "support": "02_clean_support_ticket.txt",
    "ambiguous": "03_ambiguous_text.txt",
    "short": "05_missing_context_short.txt",
}


def _read_sample(key: str) -> str:
    root = Path(__file__).resolve().parents[1]
    path = root / "documents" / _SAMPLE_FILES[key]
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return f"[could not read {path}]"


def _html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _classification_detail_panel(output: dict) -> str:
    label = _html_escape(str(output.get("label") or "—"))
    conf = output.get("confidence")
    try:
        conf_s = f"{float(conf):.0%}" if conf is not None else "—"
    except (TypeError, ValueError):
        conf_s = "—"
    rationale = str(output.get("rationale") or "")
    if len(rationale) > 240:
        rationale = rationale[:240] + "…"
    rationale = _html_escape(rationale)
    return (
        f"<div class='tb-step-detail tb-step-detail--classification'>"
        f"<dl><dt>Label</dt><dd><strong>{label}</strong></dd>"
        f"<dt>Confidence</dt><dd class='tb-mono'>{_html_escape(conf_s)}</dd>"
        f"<dt>Rationale</dt><dd>{rationale or '—'}</dd></dl></div>"
    )


def _summarization_detail_panel(output: dict) -> str:
    summary = str(output.get("summary") or "")
    if len(summary) > 320:
        summary = summary[:320] + "…"
    summary = _html_escape(summary)
    return (
        f"<div class='tb-step-detail tb-step-detail--summarization'>"
        f"<dl><dt>Summary preview</dt><dd>{summary or '—'}</dd></dl></div>"
    )


def _step_card_class(step_name: str) -> str:
    base = "tb-step"
    key = (step_name or "").strip().lower()
    accent = {
        "intake": "tb-step--intake",
        "extraction": "tb-step--extraction",
        "classification": "tb-step--classification",
        "summarization": "tb-step--summarization",
    }.get(key, "tb-step--default")
    return f"{base} {accent}"


def _inject_styles() -> None:
    st.markdown(
        """
<style>
    .tb-hero-shell {
        padding: 1.15rem 1.35rem 1.25rem;
        border-radius: 16px;
        background: linear-gradient(135deg,
            rgba(99,102,241,0.22) 0%,
            rgba(236,72,153,0.12) 45%,
            rgba(34,211,238,0.14) 100%);
        border: 1px solid rgba(148,163,184,0.28);
        box-shadow: 0 12px 40px rgba(15,23,42,0.35);
    }
    .tb-hero-kicker {
        margin: 0;
        font-size: 0.72rem;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        background: linear-gradient(90deg,#c4b5fd,#67e8f9,#f472b6);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        font-weight: 700;
    }
    .tb-hero-title {
        margin: 0.35rem 0 0 0;
        font-size: clamp(1.45rem, 2.5vw, 1.85rem);
        font-weight: 700;
        letter-spacing: -0.03em;
        line-height: 1.2;
    }
    .tb-hero-sub {
        margin: 0.65rem 0 0 0;
        opacity: 0.78;
        font-size: 0.96rem;
        max-width: 46rem;
        line-height: 1.45;
    }
    .tb-step {
        text-align: center;
        padding: 14px 10px;
        border-radius: 14px;
        background: rgba(15,23,42,0.45);
        border: 1px solid rgba(148, 163, 184, 0.22);
        min-height: 92px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .tb-step:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 28px rgba(0,0,0,0.25);
    }
    .tb-step--intake { border-top: 4px solid #a78bfa; box-shadow: inset 0 1px 0 rgba(167,139,250,0.25); }
    .tb-step--extraction { border-top: 4px solid #22d3ee; box-shadow: inset 0 1px 0 rgba(34,211,238,0.25); }
    .tb-step--classification { border-top: 4px solid #fbbf24; box-shadow: inset 0 1px 0 rgba(251,191,36,0.25); }
    .tb-step--summarization { border-top: 4px solid #fb7185; box-shadow: inset 0 1px 0 rgba(251,113,133,0.25); }
    .tb-step--default { border-top: 4px solid #94a3b8; }
    .tb-step-detail {
        margin-top: 11px;
        padding: 10px 12px;
        border-radius: 12px;
        text-align: left;
        font-size: 0.84rem;
        line-height: 1.45;
    }
    .tb-step-detail--classification {
        background: rgba(251,191,36,0.09);
        border: 1px solid rgba(251,191,36,0.35);
        box-shadow: 0 6px 18px rgba(245,158,11,0.08);
    }
    .tb-step-detail--summarization {
        background: rgba(251,113,133,0.09);
        border: 1px solid rgba(251,113,133,0.35);
        box-shadow: 0 6px 18px rgba(244,63,94,0.08);
    }
    .tb-step-detail dt {
        margin: 0.35rem 0 0.1rem 0;
        font-size: 0.65rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        opacity: 0.55;
        font-weight: 700;
    }
    .tb-step-detail dd {
        margin: 0 0 0.15rem 0;
        padding: 0;
    }
    .tb-step-detail .tb-mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, monospace; font-size: 0.8rem; }
    .tb-step-dot { font-size: 1.15rem; line-height: 1; filter: drop-shadow(0 0 6px currentColor); }
    .tb-step-name {
        margin-top: 6px;
        font-weight: 600;
        font-size: 0.88rem;
    }
    .tb-step-status {
        margin-top: 4px;
        opacity: 0.65;
        font-size: 0.76rem;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
    }
    .tb-panel-title {
        font-size: 0.78rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        opacity: 0.55;
        margin-bottom: 0.35rem;
        font-weight: 600;
    }
    .tb-chip-label {
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
        padding: 0.25rem 0.5rem;
        border-radius: 8px;
        display: inline-block;
    }
    .tb-chip-violet { color:#ddd6fe; background:rgba(139,92,246,0.35); border:1px solid rgba(167,139,250,0.45); }
    .tb-chip-cyan { color:#cffafe; background:rgba(6,182,212,0.35); border:1px solid rgba(34,211,238,0.45); }
    .tb-chip-amber { color:#fef3c7; background:rgba(245,158,11,0.35); border:1px solid rgba(251,191,36,0.5); }
    .tb-chip-rose { color:#ffe4e6; background:rgba(244,63,94,0.35); border:1px solid rgba(251,113,133,0.45); }
    .tb-verdict {
        display: inline-block;
        padding: 0.35rem 1rem;
        border-radius: 999px;
        font-weight: 800;
        letter-spacing: 0.06em;
        font-size: 0.85rem;
        margin: 0.35rem 0 0.75rem 0;
    }
    .tb-verdict--pass {
        color: #bbf7d0;
        background: linear-gradient(135deg, rgba(34,197,94,0.35), rgba(16,185,129,0.25));
        border: 1px solid rgba(74,222,128,0.55);
        box-shadow: 0 0 24px rgba(74,222,128,0.2);
    }
    .tb-verdict--fail {
        color: #fecaca;
        background: linear-gradient(135deg, rgba(239,68,68,0.4), rgba(244,63,94,0.25));
        border: 1px solid rgba(248,113,113,0.55);
        box-shadow: 0 0 24px rgba(248,113,113,0.2);
    }
    div[data-testid="stExpander"] details summary { font-weight: 600; }
    div[data-testid="stButton"] > button[kind="primary"] {
        background: linear-gradient(135deg,#6366f1 0%,#8b5cf6 40%,#db2777 100%) !important;
        border: none !important;
        color: #fafafa !important;
        font-weight: 700 !important;
        box-shadow: 0 6px 22px rgba(99,102,241,0.45) !important;
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover {
        box-shadow: 0 8px 28px rgba(219,39,119,0.45) !important;
        filter: brightness(1.06);
    }
    div[data-testid="stButton"] > button[kind="secondary"] {
        border: 1px solid rgba(45,212,191,0.55) !important;
        color: #5eead4 !important;
        background: rgba(13,148,136,0.15) !important;
        font-weight: 600 !important;
    }
    div[data-testid="stDownloadButton"] > button {
        background: linear-gradient(135deg,rgba(34,211,238,0.35),rgba(99,102,241,0.35)) !important;
        border: 1px solid rgba(34,211,238,0.45) !important;
        color: #ecfeff !important;
        font-weight: 600 !important;
    }
</style>
""",
        unsafe_allow_html=True,
    )


def _storage() -> TraceStorage:
    sqlite_path = Path(os.getenv("TRACE_DB_PATH", "data/traces.sqlite"))
    return TraceStorage(sqlite_path=sqlite_path)


def _status_color(status: str) -> str:
    if status == "OK":
        return "#4ade80"
    if status == "ERROR":
        return "#f87171"
    return "#94a3b8"


def _hero() -> None:
    st.markdown(
        '<div class="tb-hero-shell">'
        '<p class="tb-hero-kicker">TraceBack</p>'
        '<p class="tb-hero-title">Observability & root-cause for multi-step AI pipelines</p>'
        '<p class="tb-hero-sub">Trace every step, judge outputs, walk backward to the failing span, '
        "capture regressions, and watch failure trends in one place.</p>"
        "</div>",
        unsafe_allow_html=True,
    )


def _sidebar() -> None:
    with st.sidebar:
        st.markdown("### Controls")
        r1, r2 = st.columns(2)
        with r1:
            if st.button("Refresh data", type="primary", use_container_width=True, help="Reload eval JSONL cache"):
                st.cache_data.clear()
                st.rerun()
        with r2:
            if st.button("Reset form", type="secondary", use_container_width=True, help="Clear sample fields & cached rows"):
                for _k in ("tb_run_doc", "tb_doc_id", "tb_flag_notes"):
                    st.session_state.pop(_k, None)
                st.cache_data.clear()
                st.rerun()
        st.markdown("##### Environment")
        st.caption("Resolved from env vars.")
        st.code(
            f"TRACE_DB\n{os.getenv('TRACE_DB_PATH', 'data/traces.sqlite')}\n\n"
            f"EVAL_DATASET\n{os.getenv('EVAL_DATASET_PATH', 'eval/failure_dataset.jsonl')}\n\n"
            f"LLM_MODE\n{os.getenv('LLM_MODE', 'mock').strip() or 'mock'}",
            language="text",
        )


@st.cache_data
def _cached_eval_rows(path_str: str) -> list:
    return load_eval_rows(Path(path_str))


@st.cache_data
def _cached_human_flags(path_str: str) -> list:
    return load_human_flags(Path(path_str))


def _render_trace_explorer() -> None:
    storage = _storage()
    traces = list(storage.list_recent_traces(limit=100))

    if not traces:
        st.info(
            "No traces yet. Open **Run & diagnose**, paste a document, or run "
            "`LLM_MODE=mock python3 main.py --document documents/01_clean_invoice.txt`"
        )
        return

    labels = [
        f"{t['document_id']}  ·  {t['trace_id'][:8]}…  ·  {t['status']}  ·  {t['started_at']}"
        for t in traces
    ]
    choice = st.selectbox(
        "Select trace",
        options=list(range(len(traces))),
        format_func=lambda i: labels[i],
        label_visibility="collapsed",
    )
    selected = traces[choice]
    trace_id = selected["trace_id"]

    spans = list(storage.list_spans(trace_id))
    st.markdown('<p class="tb-panel-title">Pipeline</p>', unsafe_allow_html=True)
    step_cols = st.columns(len(spans) if spans else 1)
    for i, span in enumerate(spans):
        name = span.get("name", "?")
        status = span.get("status", "?")
        color = _status_color(status)
        cell = step_cols[i] if spans else st.container()
        card = _step_card_class(name)
        out_json = span.get("output_json")
        with cell:
            st.markdown(
                f"<div class='{card}'><div class='tb-step-dot' style='color:{color}'>●</div>"
                f"<div class='tb-step-name'>{name}</div>"
                f"<div class='tb-step-status'>{status}</div></div>",
                unsafe_allow_html=True,
            )
            if isinstance(out_json, dict):
                if name == "classification":
                    st.markdown(_classification_detail_panel(out_json), unsafe_allow_html=True)
                elif name == "summarization":
                    st.markdown(_summarization_detail_panel(out_json), unsafe_allow_html=True)

    trace_blob = json.dumps({"trace": selected, "spans": spans}, default=str, indent=2)
    act1, act2, act3 = st.columns([1, 1, 2])
    with act1:
        st.download_button(
            label="Download trace JSON",
            data=trace_blob,
            file_name=f"{trace_id[:12]}_trace.json",
            mime="application/json",
            use_container_width=True,
            key=f"tb_dl_trace_{trace_id}",
        )
    with act2:
        if st.button("Quick tip", type="secondary", use_container_width=True, key=f"tb_tip_{trace_id}"):
            st.toast("Failure analytics highlights taxonomy drift — cross-check with flags you save here.")
    with act3:
        st.caption(f"`trace_id` **{trace_id}** · document **{selected.get('document_id')}**")

    st.divider()
    for span in spans:
        with st.expander(f"{span.get('name')} · {span.get('status')}", expanded=False):
            st.json({"input": span.get("input_json"), "output": span.get("output_json"), "error": span.get("error")})

    intake_out = next((s.get("output_json") for s in spans if s.get("name") == "intake"), None)
    summ_out = next((s.get("output_json") for s in spans if s.get("name") == "summarization"), None)
    chunks_preview = ""
    if isinstance(intake_out, dict) and intake_out.get("chunks"):
        chunks_preview = "\n\n".join(str(c) for c in intake_out["chunks"][:3])[:4000]
    summary_text = ""
    if isinstance(summ_out, dict) and summ_out.get("summary"):
        summary_text = str(summ_out["summary"])

    left, right = st.columns(2)
    with left:
        st.markdown('<p class="tb-panel-title">Chunk preview</p>', unsafe_allow_html=True)
        st.text_area(
            "chunks_preview",
            value=chunks_preview or "(no intake output)",
            height=240,
            disabled=True,
            label_visibility="collapsed",
        )
    with right:
        st.markdown('<p class="tb-panel-title">Final summary</p>', unsafe_allow_html=True)
        st.text_area(
            "summary_preview",
            value=summary_text or "(no summary)",
            height=240,
            disabled=True,
            label_visibility="collapsed",
        )

    st.divider()
    st.markdown('<p class="tb-panel-title">Human flag</p>', unsafe_allow_html=True)
    st.text_input(
        "Notes",
        placeholder="e.g. Wrong taxonomy — should be support_ticket",
        label_visibility="collapsed",
        key="tb_flag_notes",
    )
    bf1, bf2 = st.columns(2)
    with bf1:
        if st.button("Save flag", type="primary", use_container_width=True):
            flags_path = Path(os.getenv("HUMAN_FLAGS_PATH", "data/human_flags.jsonl"))
            flags_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "trace_id": trace_id,
                "document_id": selected.get("document_id"),
                "notes": st.session_state.get("tb_flag_notes", ""),
                "span_names": [s.get("name") for s in spans],
            }
            with flags_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=True) + "\n")
            st.success(f"Saved → `{flags_path}`")
    with bf2:
        if st.button("Clear notes", type="secondary", use_container_width=True):
            st.session_state.tb_flag_notes = ""
            st.rerun()


def _render_run_diagnose() -> None:
    st.caption(
        "Judge uses **heuristics** in mock mode and **gpt-4o-mini** when `LLM_MODE=openai` "
        "(after cheap checks for empty / too-short input)."
    )

    st.markdown('<p class="tb-panel-title">Quick samples</p>', unsafe_allow_html=True)
    qs = st.columns(4)
    quick = [
        ("invoice", "tb-chip-violet", "Invoice"),
        ("support", "tb-chip-cyan", "Support ticket"),
        ("ambiguous", "tb-chip-amber", "Ambiguous"),
        ("short", "tb-chip-rose", "Short / edge"),
    ]
    for col, (sample_key, chip_cls, title) in zip(qs, quick):
        with col:
            st.markdown(f"<span class='tb-chip-label {chip_cls}'>{title}</span>", unsafe_allow_html=True)
            if st.button("Load sample", key=f"qs_{sample_key}", use_container_width=True):
                st.session_state.tb_run_doc = _read_sample(sample_key)
                st.rerun()

    with st.form("run_pipeline_form"):
        doc_id = st.text_input("Document id", key="tb_doc_id")
        doc_text = st.text_area("Document", height=260, key="tb_run_doc", placeholder="Paste document body…")
        do_diagnose = st.checkbox("Run diagnosis & capture failures to eval dataset", value=True)
        row_btn = st.columns(2)
        with row_btn[0]:
            run_btn = st.form_submit_button("Run pipeline", type="primary", use_container_width=True)
        with row_btn[1]:
            clr_btn = st.form_submit_button("Clear document", type="secondary", use_container_width=True)

    if clr_btn:
        st.session_state.tb_run_doc = ""
        st.rerun()

    if not run_btn:
        return

    doc_text = str(st.session_state.get("tb_run_doc", ""))
    doc_id_val = str(st.session_state.get("tb_doc_id", "ui_run")).strip()

    if not doc_text.strip():
        st.warning("Add document text first.")
        return

    with st.spinner("Executing pipeline…"):
        result = run_pipeline(document_id=doc_id_val, text=doc_text)

    st.success(f"Finished · `trace_id={result.trace_id}`")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Classification", result.classification.label)
    with m2:
        st.metric("Confidence", f"{result.classification.confidence:.0%}")
    with m3:
        st.metric("Entities", len(result.extraction.entities))
    with m4:
        st.metric("Facts", len(result.extraction.facts))

    st.text_area("Summary", value=result.summarization.summary, height=160, label_visibility="collapsed")

    if do_diagnose:
        with st.spinner("Judging & diagnosing…"):
            diagnosis, eval_row = run_diagnosis(
                document_id=doc_id_val,
                document_text=doc_text,
                pipeline_result=result,
            )
        if diagnosis.passed:
            st.markdown('<div class="tb-verdict tb-verdict--pass">PASS</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="tb-verdict tb-verdict--fail">FAIL</div>', unsafe_allow_html=True)
        st.markdown(
            f"Confidence **{diagnosis.judge_confidence:.2f}** · {diagnosis.judge_reason}",
        )
        if not diagnosis.passed:
            c_a, c_b = st.columns(2)
            with c_a:
                st.metric("Failing step", diagnosis.failing_step or "—")
            with c_b:
                st.metric("Failure type", diagnosis.failure_type or "—")
            if eval_row:
                with st.expander("Captured eval row"):
                    st.json(eval_row)
        reg = get_regression_summary()
        st.caption(
            f"Regression file · rows: **{int(reg['total'])}** · failed flag: **{int(reg['failed'])}** · "
            f"pass_rate field: **{reg['pass_rate']:.0%}** (dataset semantics)"
        )


def _render_failure_analytics() -> None:
    path = Path(os.getenv("EVAL_DATASET_PATH", "eval/failure_dataset.jsonl"))
    flags_path = Path(os.getenv("HUMAN_FLAGS_PATH", "data/human_flags.jsonl"))

    top_act = st.columns([1, 3])
    with top_act[0]:
        if st.button("Reload analytics", type="primary", use_container_width=True, key="tb_an_reload"):
            st.cache_data.clear()
            st.rerun()
    with top_act[1]:
        st.caption(f"Dataset: **`{path}`**")

    rows = _cached_eval_rows(str(path.resolve()))
    overview = dataset_overview(rows)
    flags = _cached_human_flags(str(flags_path.resolve()))

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Dataset rows", overview["total_rows"])
    with k2:
        st.metric("Failure rows", overview["failure_rows"])
    with k3:
        st.metric("Unique docs", overview["unique_documents"])
    with k4:
        avg = overview["avg_judge_confidence_on_failures"]
        st.metric("Avg judge conf. (failures)", f"{avg:.2f}" if avg is not None else "—")

    if overview["total_rows"] == 0:
        st.info(
            f"No rows at `{path}`. Failures are appended when diagnosis fails "
            "(CLI `--analyze` or **Run & diagnose** with diagnosis enabled)."
        )
        return

    ft_counts = count_field(rows, "failure_type")
    fs_counts = count_field(rows, "failing_step")
    daily = failures_per_day(rows)

    ch_left, ch_right = st.columns(2)
    with ch_left:
        st.markdown("##### Failure taxonomy")
        if ft_counts:
            df_ft = pd.DataFrame({"type": list(ft_counts.keys()), "count": list(ft_counts.values())})
            df_ft = df_ft.set_index("type")
            st.bar_chart(df_ft, color="#818cf8")
        else:
            st.caption("No failure-type breakdown.")
    with ch_right:
        st.markdown("##### Failing step")
        if fs_counts:
            df_fs = pd.DataFrame({"step": list(fs_counts.keys()), "count": list(fs_counts.values())})
            df_fs = df_fs.set_index("step")
            st.bar_chart(df_fs, color="#34d399")
        else:
            st.caption("No failing-step breakdown.")

    st.markdown("##### Failures over time (UTC date)")
    if daily and set(daily.keys()) != {"unknown"}:
        df_day = pd.DataFrame({"date": list(daily.keys()), "failures": list(daily.values())})
        df_day = df_day.set_index("date")
        st.area_chart(df_day, color="#f472b6")
    else:
        st.caption("No dated failures yet (timestamps missing or sparse).")

    st.markdown("##### Recent failures")
    slim = recent_failures(rows, limit=40)
    if slim:
        df_slim = pd.DataFrame(slim)
        st.dataframe(df_slim, use_container_width=True, hide_index=True)
        st.download_button(
            "Export failures CSV",
            df_slim.to_csv(index=False).encode("utf-8"),
            file_name="traceback_recent_failures.csv",
            mime="text/csv",
            use_container_width=True,
            key="tb_dl_fail_csv",
        )
    else:
        st.caption("No failure rows to list.")

    st.divider()
    st.markdown("##### Human flags")
    st.caption(f"`{flags_path}` · **{len(flags)}** entries")
    if flags:
        tail = flags[-30:]
        df_f = pd.DataFrame(tail)
        st.dataframe(df_f, use_container_width=True, hide_index=True)
        st.download_button(
            "Export flags CSV",
            df_f.to_csv(index=False).encode("utf-8"),
            file_name="traceback_human_flags.csv",
            mime="text/csv",
            use_container_width=True,
            key="tb_dl_flags_csv",
        )
    else:
        st.caption("No flags saved yet — use **Explore traces** to append notes.")


def main() -> None:
    st.set_page_config(
        page_title="TraceBack",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    if "tb_doc_id" not in st.session_state:
        st.session_state.tb_doc_id = "ui_run"
    if "tb_run_doc" not in st.session_state:
        st.session_state.tb_run_doc = ""
    if "tb_flag_notes" not in st.session_state:
        st.session_state.tb_flag_notes = ""

    _inject_styles()
    _sidebar()
    _hero()
    st.divider()

    tab_explore, tab_run, tab_analytics = st.tabs(["Explore traces", "Run & diagnose", "Failure analytics"])

    with tab_explore:
        _render_trace_explorer()

    with tab_run:
        _render_run_diagnose()

    with tab_analytics:
        _render_failure_analytics()


if __name__ == "__main__":
    main()
