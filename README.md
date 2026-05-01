# failure-forensics

Observability and root-cause diagnosis tool for multi-step AI pipelines.

This repository now includes **Phase 1**: a typed 4-step document pipeline with extraction, classification, and summarization that can run in offline mock mode or OpenAI mode.

## Current Structure

```text
failure-forensics/
├── pipeline/
├── tracer/
├── analyzer/
├── ui/
├── api/
├── eval/
├── data/
├── documents/
├── docker/
├── main.py
├── requirements.txt
└── README.md
```

## Phase 1 Implemented

1. Intake: load and chunk document text
2. Extraction: extract entities and facts with LLM
3. Classification: classify document category
4. Summarization: produce a concise final summary

Each step accepts and returns **typed Pydantic models** and the runner executes steps sequentially.

## Setup

1. Create and activate a virtual environment (Python 3.11+ recommended).
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Configure `.env`:
   - `LLM_MODE=mock` (default, no API usage/cost)
   - `OPENAI_API_KEY=your_key_here` (only required when `LLM_MODE=openai`)

## Run

```bash
# No-cost local run (default)
python3 main.py --document documents/01_clean_invoice.txt
```

To use OpenAI later:

```bash
LLM_MODE=openai python3 main.py --document documents/01_clean_invoice.txt
```

## Smoke Tests (no API cost)

```bash
# install deps once
pip install -r requirements.txt

# run local zero-cost validation suite
make smoke
```

## Tracing (Phase 2)

Every pipeline run now writes a trace with one span per step to:
- SQLite: `data/traces.sqlite` (configurable via `TRACE_DB_PATH`)
- JSONL: `data/traces.jsonl` (configurable via `TRACE_JSONL_PATH`)

This works in both `LLM_MODE=mock` and `LLM_MODE=openai`.

## Analyzer (Phase 3)

Run end-to-end with diagnosis:

```bash
python3 main.py --document documents/03_ambiguous_text.txt --analyze
```

Analyzer output includes:
- judge pass/fail and rationale
- inferred failing step via backward span walk
- failure taxonomy label
- failure case capture to `eval/failure_dataset.jsonl` (failures only)
- regression snapshot (`total`, `failed`, `pass_rate`)

## Logging Behavior

Each step emits one JSON log entry with:
- step name
- typed input payload
- typed output payload (when successful)
- success/failure flag
- error message (when failed)

## Sample Documents

The `documents/` folder includes at least 5 examples:
- clean invoice
- clean support ticket
- ambiguous text
- contradictory information
- very short/missing context input
