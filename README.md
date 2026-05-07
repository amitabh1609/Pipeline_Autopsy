# Pipeline Autopsy

**Pipeline Autopsy** is an observability and intelligent diagnosis tool built for multi-step AI pipelines. It answers a question that every AI engineer eventually runs into: *when a pipeline fails, which step broke, and why?*

Instead of digging through raw logs and guessing, Pipeline Autopsy traces every step of the pipeline automatically, runs a built-in AI judge to evaluate the output, and produces a structured diagnosis that tells you exactly where things went wrong and how often.

---

## What Problem Does This Solve

Modern AI applications are not a single model call. They are pipelines: a document goes in, gets chunked, entities get extracted, it gets classified, summarized, and a final result comes out. When something in that chain fails or produces a bad result, it is nearly impossible to tell which step caused it just by looking at the final output.

Pipeline Autopsy gives every pipeline run a full trace, records the input and output of each step, and when you run the analyzer it walks backward through the trace to pinpoint the exact step that failed. It also categorizes the failure and builds a historical dataset over time so you can spot patterns.

---

## Key Features

**End-to-End Pipeline Tracing**
Every pipeline run is recorded span by span into both a SQLite database and a JSONL file. You get a complete history of what went in and what came out at each stage, for every run.

**Intelligent Failure Diagnosis**
The built-in judge evaluates the final output and, if it fails, walks backward through the trace to find the root cause. Each failure gets a taxonomy label so you can group and analyze failure types over time.

**Interactive Dashboard**
A Streamlit web interface lets you browse traces, trigger new pipeline runs, and explore a Failure Analytics tab that charts failure trends, problematic steps, and timelines from the accumulated dataset.

**REST API**
A FastAPI backend exposes endpoints to run pipelines and retrieve diagnoses programmatically. The API is fully documented via Swagger at `/docs`.

**Zero-Cost Local Mode**
The entire system runs offline with `LLM_MODE=mock` using heuristics instead of API calls. You can explore, test, and demo the full feature set without spending a cent on any external service.

**Docker Ready**
One command spins up the API and the UI in separate containers. Cloud deployment configs for Render and Fly.io are included in the repo.

---

## Tech Stack

Python 3.11, FastAPI, Streamlit, Pydantic, SQLite, Docker, GitHub Actions, OpenAI API (optional)

---

## The Pipeline

When a document is submitted, it moves through four sequential steps:

1. **Intake** — the document text is loaded and chunked into processable pieces
2. **Extraction** — entities and key facts are pulled out using an LLM
3. **Classification** — the document is assigned a category based on its content
4. **Summarization** — a concise final summary is produced

Each step accepts and returns strongly typed Pydantic models, so there is no ambiguity about what data flows between stages.

---

## Getting Started

**Step 1.** Create and activate a Python virtual environment (Python 3.11 or higher recommended).

**Step 2.** Install dependencies:

```bash
pip install -r requirements.txt
```

**Step 3.** Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Set `LLM_MODE=mock` to run fully offline at zero cost. Set `LLM_MODE=openai` and add your `OPENAI_API_KEY` to use real LLM calls.

**Step 4.** Run the pipeline on a sample document:

```bash
python3 main.py --document documents/01_clean_invoice.txt
```

To run with diagnosis enabled:

```bash
python3 main.py --document documents/03_ambiguous_text.txt --analyze
```

---

## Running the UI

```bash
streamlit run ui/app.py
```

Open your browser and explore traces, run pipelines, and view failure analytics all in one place.

---

## Running the API

```bash
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Visit `http://127.0.0.1:8000/docs` for the interactive Swagger documentation.

The two main endpoints are:

`POST /pipeline/run` — submit a document and get a structured pipeline result

`POST /pipeline/analyze` — run the pipeline and return a full diagnosis with judge output and regression snapshot

---

## Running with Docker

```bash
make docker-build
make docker-up
```

The API will be available at `http://localhost:8000/docs` and the UI at `http://localhost:8501`.

---

## Tests

```bash
make smoke
```

This runs the full local validation suite with no API calls and no cost. The same suite runs automatically on every push to `main` via GitHub Actions.

---

## Cloud Deployment

The repo includes ready-to-use configuration files for two hosting platforms.

**Render** (recommended): Connect your GitHub repo, select Blueprint, and Render will detect `render.yaml` and provision both the API and UI services automatically. Set `OPENAI_API_KEY` and `LLM_MODE` in the Render dashboard environment settings if you want live LLM calls.

**Fly.io**: Use the included `fly.toml` to deploy the API. Run `fly secrets set OPENAI_API_KEY=sk-...` to configure credentials, then `fly deploy`.

**Single VPS**: Clone the repo on any Linux server with Docker installed, add your `.env` file, and run `docker compose up -d`. This is the simplest setup because both services share the same disk, so traces are consistent between the API and UI.

---

## Sample Documents

The `documents/` folder includes five example inputs to get you started right away: a clean invoice, a clean support ticket, an ambiguous text, a document with contradictory information, and a very short input with missing context. These cover a range of scenarios from clean runs to guaranteed failures, which is useful for testing the analyzer.

You can also generate a large batch of synthetic documents:

```bash
make demo-docs
```

---

## Author

Built by **Amitabh Choudhury**
