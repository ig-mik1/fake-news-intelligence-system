# Fake News Intelligence System

Fake News Intelligence System (FNIS) is a full-stack misinformation analysis platform that combines transformer-based classification, vector-search evidence retrieval, source credibility scoring, and an analytics dashboard for operational monitoring.

The project is structured as a FastAPI backend plus a Next.js frontend. It supports headline verification, evidence-assisted trust scoring, feedback capture for human review, a live monitoring feed, and dashboard summaries backed by ChromaDB.

## Key Capabilities

- Hybrid verification pipeline that combines:
  - transformer model prediction
  - evidence consensus scoring
  - source credibility scoring
- Evidence retrieval from a ChromaDB vector store
- Scheduled and manual ingestion of news and evidence sources
- Feedback endpoint with rate limiting and duplicate suppression
- Monitoring and dashboard endpoints for frontend analytics
- Modern Next.js dashboard for verification, reporting, and live monitoring

## Architecture Overview

1. Ingestion pulls content from RSS feeds, NewsData, and Reddit/PullPush.
2. New items are normalized and stored in ChromaDB under `data/vector_storage`.
3. The FastAPI service runs:
   - model inference from `models/final_model`
   - evidence retrieval from ChromaDB
   - trust score calculation in the hybrid verifier
4. The Next.js frontend consumes the API for:
   - verification
   - dashboard metrics
   - monitoring stream
   - human feedback submission

## End-to-End Flow (How the App Works)

This is the runtime flow a reader should understand first:

1. Data ingestion runs (startup + every hour) and pulls articles/posts from RSS, NewsData, and Reddit/PullPush.
2. Ingestion writes normalized text and metadata into ChromaDB in `data/vector_storage/`.
3. A user opens the frontend and submits a claim/headline through the Verify page.
4. The frontend calls `POST /api/verify` on FastAPI.
5. The backend pipeline does three things:
  - model inference for fake/real probability
  - evidence retrieval + evidence agreement scoring
  - source trust scoring
6. The hybrid verifier combines those signals into a final trust score and `REAL` or `FAKE` label.
7. The frontend displays the result with evidence summary, confidence, and trust breakdown.
8. Optional user feedback is posted to `POST /api/feedback` for later review.
9. Dashboard and Monitoring pages query summary/live endpoints for operations visibility.

## Tech Stack

### Backend

- Python 3.10
- FastAPI
- Uvicorn
- APScheduler
- ChromaDB
- PyTorch
- Hugging Face Transformers
- Sentence Transformers
- Pandas / NumPy / scikit-learn
- PySpark

### Frontend

- Next.js 16
- React 19
- Tailwind CSS 4
- Framer Motion
- Recharts
- Lucide React

## Repository Structure

```text
api/                         FastAPI app entrypoint and API schemas
  app.py                     Main backend application and routes
  schemas.py                 Request/response models

frontend/                    Next.js web app
  app/                       Route pages (home, verify, dashboard, monitoring)
  components/                Reusable UI components
  lib/api.ts                 Frontend API client wrapper

ingestion/                   External news/evidence collectors
  run_ingestion_layer.py     Orchestrates full ingestion run
  rss_ingestion.py           RSS fetch
  newsdata_ingestion.py      NewsData API fetch
  reddit_ingestion.py        Reddit/PullPush fetch

verification/                Verification and scoring engine
  prediction_service.py      Model inference layer
  evidence_engine.py         Retrieval and evidence processing
  hybrid_verifier.py         Final trust score and decision logic

pipeline/                    Offline data preparation utilities
models/                      Local model artifacts (ignored in Git)
data/                        Runtime data, vector store, feedback (ignored in Git)
logs/                        Runtime logs (ignored in Git)

Dockerfile                   Backend container image
frontend/Dockerfile          Frontend container image
docker-compose.yml           Local full-stack orchestration
```

## Build Process (How This Application Was Built)

The system was developed in layers so each part can be tested independently:

1. Backend foundation
  - Built FastAPI service, request schemas, health checks, and core endpoints.
  - Added scheduler to run ingestion in background.

2. Data ingestion layer
  - Implemented source connectors (RSS, NewsData, Reddit/PullPush).
  - Added normalization, deduplication, and vector-store upsert workflow.

3. Verification engine
  - Added transformer inference service for fake/real prediction.
  - Added evidence retrieval and source credibility logic.
  - Implemented hybrid trust scoring to combine all signals.

4. Frontend application
  - Built Verify, Dashboard, and Monitoring pages in Next.js.
  - Added API client integration and UI components for result display.

5. Operations and deployment
  - Added Dockerfiles and Compose setup for local full-stack run.
  - Added feedback capture and verification logging for iterative improvement.

## What Is Intentionally Not Committed

To keep the repository lightweight and safe, these are intentionally ignored:

- `data/` runtime datasets and ChromaDB files
- `models/` model checkpoints and weights
- `fnis/` local virtual environment
- `logs/*.jsonl` generated runtime logs
- `FNIS_Paper.tex` report/paper source

After cloning, provide your own model artifacts and run ingestion locally to populate vector data.

## Core Services

### Backend API

The backend entrypoint is `api/app.py`. It exposes endpoints for:

- `POST /api/verify`
- `POST /api/feedback`
- `GET /api/dashboard/summary`
- `GET /api/monitoring/latest`
- `GET /api/monitoring`
- `GET /healthz`

It also starts a background scheduler that triggers ingestion every hour.

### Frontend Dashboard

The frontend lives in `frontend/` and provides:

- verification workflow
- dashboard metrics and charts
- live monitoring stream
- command palette driven navigation

### Hybrid Trust Scoring

The verification pipeline uses:

- ML fake-news probability from `verification/prediction_service.py`
- evidence consensus scoring from `verification/hybrid_verifier.py`
- source credibility scoring from `verification/hybrid_verifier.py`

The final trust decision is returned as `REAL` or `FAKE`.

## Prerequisites

Before running locally, ensure you have:

- Python 3.10+
- Node.js 20+
- npm
- Java runtime if you plan to use Spark-related pipeline tooling
- a trained model available at `models/final_model`

GPU acceleration is optional. The prediction service will use CUDA when available and fall back to CPU otherwise.

## Environment Variables

The project reads configuration from `.env`.

### Required

- `NEWSDATA_API_KEY`
  - Required for NewsData ingestion.

### Common Optional Settings

- `FNIS_MODEL_PATH`
- `FNIS_TRUST_THRESHOLD`
- `FNIS_CHROMA_PATH`
- `FNIS_CHROMA_COLLECTION`
- `FNIS_EMBED_MODEL`
- `FNIS_EVIDENCE_TIMEOUT_SECONDS`
- `FNIS_CORS_ORIGINS`
- `FNIS_VERIFY_RATE_LIMIT_PER_MINUTE`
- `FNIS_FEEDBACK_REQUIRE_API_KEY`
- `FNIS_FEEDBACK_API_KEY`
- `FNIS_FEEDBACK_RATE_LIMIT_PER_HOUR`
- `FNIS_FEEDBACK_DUPLICATE_COOLDOWN_SECONDS`
- `FNIS_FEEDBACK_PATH`
- `FNIS_VERIFICATION_LOG_PATH`

If you do not set most `FNIS_*` variables, the application uses sane defaults defined in the source code.

## Local Development Setup

### 1. Create and activate a Python virtual environment

On Windows PowerShell:

```powershell
python -m venv fnis
.\fnis\Scripts\Activate.ps1
```

### 2. Install backend dependencies

```powershell
pip install -r requirements.txt
```

### 3. Start the FastAPI backend

```powershell
uvicorn api.app:app --reload
```

Backend runs at `http://localhost:8000`.

### 4. Start the frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`.

By default, the frontend targets `http://localhost:8000` through `NEXT_PUBLIC_API_URL`.

## Running Ingestion

To populate the vector store manually:

```powershell
python ingestion/run_ingestion_layer.py
```

This script:

- fetches RSS content
- fetches NewsData articles
- fetches Reddit/PullPush evidence
- deduplicates items
- upserts them into ChromaDB

The API also schedules ingestion automatically every hour.

## Docker Usage

To run the backend and frontend together with Docker Compose:

```powershell
docker compose up --build
```

Services:

- frontend: `http://localhost:3000`
- backend: `http://localhost:8000`

The compose file mounts:

- `./data` into the backend container
- `./models/final_model` into the backend container

## API Summary

### `POST /api/verify`

Verifies a news headline and optional body content.

Request body:

```json
{
  "headline": "Sample headline to verify",
  "content": "Optional supporting article body"
}
```

### `POST /api/feedback`

Stores user feedback for model review and retraining workflows.

### `GET /api/dashboard/summary`

Returns dashboard statistics derived from the vector store.

### `GET /api/monitoring/latest`

Returns the latest ingested items for the monitoring dashboard.

### `GET /healthz`

Returns readiness information for:

- model loading
- ChromaDB
- evidence engine

## Data and Logs

Important runtime paths:

- `data/vector_storage/` - ChromaDB persistent store
- `data/feedback/verification_feedback.jsonl` - feedback records
- `logs/verification_events.jsonl` - verification event log

## Notes for Contributors

- Keep the trained model available at `models/final_model`.
- Do not commit secrets or production API keys.
- If the frontend cannot reach the backend, confirm `NEXT_PUBLIC_API_URL` and CORS settings.
- If `/healthz` reports degraded status, check:
  - model path
  - ChromaDB data directory
  - embedding model availability

## Troubleshooting

### Backend starts but verification fails

Check:

- model exists at `models/final_model`
- Python dependencies installed successfully
- `.env` values are present and valid

### Frontend loads but API requests fail

Check:

- backend is running on port `8000`
- `NEXT_PUBLIC_API_URL` points to the correct backend
- CORS includes your frontend origin

### Monitoring or dashboard is empty

This usually means ingestion has not populated the vector store yet. Run:

```powershell
python ingestion/run_ingestion_layer.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Copyright (c) 2026** Mohd Irfan Khan, Syed Fardeen, Mohammed Omer Ali

Department of Computer Science, Lords Institute of Engineering and Technology, Hyderabad, India
