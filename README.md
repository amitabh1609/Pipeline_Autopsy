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
├── render.yaml
├── fly.toml
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

## Hosting (cloud)

Containers listen on **`PORT`** when the platform sets it (`scripts/start-api.sh`, `scripts/start-ui.sh`). Local Compose still uses **8000** / **8501**.

**Important:** On managed hosts, **SQLite files are usually ephemeral** unless you add a **persistent disk** or external DB. API and UI each run separate containers on dual-service setups, so **traces are not shared** between them unless you redesign storage.

### Option A — Render first (recommended path)

These steps assume the repo is on GitHub with **`render.yaml`** at the root (`Failure_Forensics`).

1. Create a [Render](https://render.com) account and connect **GitHub** when asked.
2. Click **New +** → **Blueprint**.
3. Pick this repository. Render should detect **`render.yaml`** automatically (confirm the path is repo root).
4. Click **Apply** / **Create blueprint**. Wait for **two** web services to provision: **`traceback-api`** and **`traceback-ui`** (first build can take several minutes).
5. When both show **Live**, open:
   - **API docs:** your API hostname plus **`/docs`** (or **`/health`** for a quick check).
   - **UI:** the Streamlit service URL (no path needed).
6. **OpenAI (optional):** In the Render dashboard, open **each** service → **Environment** → add **`OPENAI_API_KEY`** with your key. Set **`LLM_MODE`** to **`openai`** on **both** services when you want live LLM calls. Leave **`mock`** for zero-cost demos (pipeline uses offline heuristics).
7. **Redeploy** each service after changing env vars (Render usually offers **Manual Deploy**).

**Note:** SQLite **`data/`** lives inside each container separately unless you add Render disks. API traces and UI traces **do not match** across the two URLs unless you change storage (fine for demos).

**Pricing:** Docker web services may require a **paid** instance type on Render—check their current plans before relying on a free tier.

**If both URLs fail or spin forever:** merge the latest repo (includes `healthCheckPath` fixes for Streamlit), then **Manual Deploy** both services. In the dashboard open **Logs** — look for build errors or crash loops. **Cold starts** on free/low tiers can take **30–60s** after sleep—refresh once. Confirm each service shows **Live**, not **Build failed** / **Deploy failed**. Test raw endpoints: **`…/health`** (API) and **`/_stcore/health`** (UI). Ensure GitHub’s **default branch** matches what Render deploys (push `render.yaml` to that branch).

### Option B — Fly.io (API only in `fly.toml`)

1. Install the [Fly CLI](https://fly.io/docs/hubs/cli/) and log in: `fly auth login`.
2. Edit **`fly.toml`** and set **`app`** to a unique app name (or run `fly apps create <name>` and match it here).
3. From the repo root: `fly launch --no-deploy` (review region/machine) or `fly deploy` if the app already exists.
4. Set secrets:  
   `fly secrets set OPENAI_API_KEY=sk-...`  
   `fly secrets set LLM_MODE=openai`
5. Hit `https://<your-app>.fly.dev/docs`.

Deploy Streamlit separately with another Fly app whose Docker command is **`start-ui.sh`**, or run the UI locally against the hosted API (would require wiring the UI to HTTP instead of in-process imports — not implemented yet).

### Option C — Single VPS (simplest shared disk)

Rent any small Linux VM, install Docker, clone the repo, add `.env`, run **`docker compose up -d`**. **data/** and **eval/** stay on the VM disk so API and UI share traces.

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
