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
├── scripts/
├── data/
├── documents/
├── docker/
├── Dockerfile
├── docker-compose.yml
├── main.py
├── requirements.txt
├── .env.example
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
3. Configure secrets (never commit keys):
   - Copy `.env.example` to `.env`
   - Set `LLM_MODE=mock` (default, no API usage/cost) or `LLM_MODE=openai`
   - Set `OPENAI_API_KEY` only when using `LLM_MODE=openai`

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

GitHub Actions runs the same suite on every push/PR to `main`.

## FastAPI

```bash
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

- `GET /health` — liveness
- `POST /pipeline/run` — JSON body `{ "document_id", "text" }`
- `POST /pipeline/analyze` — run pipeline plus judge/diagnosis/regression snapshot
- `GET /` redirects to `/docs` (Swagger).

## Streamlit UI

```bash
streamlit run ui/app.py
```

Explore traces, run/diagnose pipelines, and open the **Failure analytics** tab (aggregates `eval/failure_dataset.jsonl`). Theme lives under `.streamlit/config.toml`.

## Docker

```bash
make docker-build   # or: docker compose build
make docker-up      # or: docker compose up
```

- **API:** http://localhost:8000/docs  
- **UI:** http://localhost:8501  

Compose passes `LLM_MODE` and `OPENAI_API_KEY` from your environment or a local `.env` file next to `docker-compose.yml`. Mounts keep `data/` and `eval/` on the host.

## Demo document bulk generator (Phase 6)

Creates synthetic `.txt` files under `documents/generated/` (gitignored):

```bash
make demo-docs
# or: python3 scripts/generate_demo_docs.py --count 50 --out documents/generated
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

## Failure analytics (Phase 5)

The Streamlit **Failure analytics** tab charts failure taxonomy, failing steps, and timelines from `eval/failure_dataset.jsonl`. Failures are appended when diagnosis marks a run as failed (CLI `--analyze` or UI).

## Sample Documents

The `documents/` folder includes at least 5 examples:
- clean invoice
- clean support ticket
- ambiguous text
- contradictory information
- very short/missing context input
