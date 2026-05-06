# CV Analyzer AI

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?style=flat&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat&logo=typescript&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-gpt--4o--mini-412991?style=flat&logo=openai&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat&logo=redis&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=flat&logo=mysql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white)

An AI-powered CV screening and ranking tool built for recruiters.

Upload one or more CVs alongside a job description and get a structured, bias-reduced ranking in seconds. CVs are anonymized before evaluation so the model scores candidates on skills and experience — not on names, contact details, or demographic signals. Results are persisted in a searchable bank for future use.

---

## Screenshots

<!-- Add screenshots here -->

---

## Key Features

🤖 **AI-powered candidate ranking**
Each CV is scored across four weighted dimensions — technical skills, experience, education, and soft skills — using GPT-4o mini. Scores are normalized to a 0–100 scale and sorted into tiers: `bajo`, `medio`, `alto`, `excelente`.

📄 **Multi-format CV support**
Accepts PDF (up to 3 pages), DOCX, and images (JPG, PNG, WEBP). PDFs are parsed with pdfplumber; DOCX with python-docx; images are transcribed via the OpenAI Vision API at `detail: high`.

🔒 **Bias reduction via anonymization**
Before every LLM call, a regex pipeline strips emails, phone numbers (Argentine and international formats), LinkedIn/GitHub URLs, age references, and name-like title lines. Filenames are replaced with neutral labels (`candidate_a`, `candidate_b`, …) so the model evaluates skills — not identity.

⚡ **Async processing with Celery + Redis**
`/analyze` and `/match-job` return HTTP 202 with a `job_id` immediately. The heavy work (LLM ranking, DB persistence) runs in a Celery worker. The frontend polls `GET /jobs/{job_id}` every 2 seconds and stops automatically on completion or failure.

🏆 **Tiebreaker system for close scores**
When two or more candidates land within 5 points of the top score, a tiebreaker banner appears. The recruiter answers LLM-generated questions about hiring priorities, and the ranking is recalculated accordingly.

⭐ **Feedback and rating per analysis**
After reviewing results, recruiters can leave a 1–5 star rating. Ratings are stored per analysis in the database and can be used to track evaluation quality over time.

🗄️ **Persistent CV bank with semantic search**
Every uploaded CV is ingested into a persistent bank. On `/match-job`, a job description is embedded and compared against all stored CVs via ChromaDB semantic search — no CVs need to be uploaded again. Bank candidates receive a recency factor that slightly down-weights older profiles.

🛡️ **Security-first file handling**
Every file is validated against its magic bytes independent of its extension, capped at 5 MB, and PDFs are rejected beyond 3 pages. Input lengths are enforced server-side. Error responses never leak internal details.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **API** | FastAPI 0.136, Python 3.11+ |
| **Task queue** | Celery 5.3.6, Redis 7 |
| **AI** | OpenAI API — gpt-4o-mini (configurable) |
| **Database** | MySQL 8.0, SQLAlchemy 2.0, aiomysql |
| **Migrations** | Alembic |
| **Vector store** | ChromaDB (local, file-based) |
| **CV parsing** | pdfplumber, python-docx, OpenAI Vision API |
| **Frontend** | React 18, TypeScript, Vite |
| **Styling** | Tailwind CSS |
| **State / data** | TanStack Query (React Query) |
| **Routing** | React Router v6 |
| **Infrastructure** | Docker Compose |

---

## Architecture Overview

A request to `/analyze` or `/match-job` hits FastAPI, which extracts text from uploaded files synchronously (fast, fails early, keeps binary data out of the queue) and immediately enqueues a Celery task, returning HTTP 202 with a `job_id`. The Celery worker picks up the task and runs the full pipeline: anonymization → OpenAI ranking call → recency factor application → persistence to MySQL and ChromaDB. The frontend polls `GET /jobs/{job_id}` every two seconds until the status becomes `completed` or `failed`.

Anonymization is a mandatory step that runs before every LLM call in both the `/analyze` and `/match-job` flows. Filenames are replaced with opaque labels and a regex pipeline removes all PII from the CV text. After the LLM returns scores, real filenames are restored from an in-memory map, and contact information is attached from MySQL — the model never sees personal data at any point.

---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- Python 3.11+
- Node.js 18+
- An [OpenAI API key](https://platform.openai.com/account/api-keys)

### Setup

**1. Clone the repository**

```bash
git clone https://github.com/matiasbocco/CV-Annalyzer-AI.git
cd CV-Annalyzer-AI
```

**2. Configure environment variables**

```bash
cp .env.example .env
```

Open `.env` and set `OPENAI_API_KEY`. The other variables have working defaults for local development.

**3. Install backend dependencies**

```bash
pip install -r requirements.txt
```

**4. Install frontend dependencies**

```bash
cd web && npm install && cd ..
```

**5. Start the database and Redis**

```bash
docker compose up -d db redis
```

Wait a few seconds for MySQL to finish its initial setup.

**6. Run database migrations**

```bash
alembic upgrade head
```

**7. Start the three services** (each in a separate terminal)

```bash
# Terminal 1 — Celery worker
celery -A core.celery_app worker --loglevel=info --concurrency=2

# Terminal 2 — FastAPI
uvicorn core.main:app --reload

# Terminal 3 — Frontend
cd web && npm run dev
```

**8. Open the app**

```
http://localhost:5173
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | **Yes** | — | Your OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Model used for ranking, extraction, and tiebreaker |
| `DATABASE_URL` | No | `mysql+aiomysql://cvuser:cvpass@localhost:3306/cv_analyzer` | MySQL connection string |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection string (broker and result backend) |

---

## Project Structure

```
CV-Annalyzer-AI/
│
├── core/                        # FastAPI application and backend logic
│   ├── main.py                  # All API endpoints and request handling
│   ├── config.py                # Settings loaded from environment variables
│   ├── celery_app.py            # Celery instance and configuration
│   ├── tasks.py                 # Async task pipelines (analyze, match-job)
│   │
│   ├── services/
│   │   ├── file_extraction_service.py   # PDF / DOCX / image text extraction
│   │   ├── anonymization_service.py     # PII stripping and label mapping
│   │   ├── llm_service.py               # OpenAI ranking prompt and client
│   │   ├── contact_service.py           # Contact info extraction via LLM
│   │   ├── cv_bank_service.py           # CV ingestion and deduplication
│   │   ├── vector_service.py            # ChromaDB operations
│   │   ├── embedding_service.py         # Text embedding generation
│   │   ├── tiebreaker_service.py        # Cluster detection and score adjustment
│   │   ├── category_service.py          # Job category classification
│   │   ├── recency_service.py           # Recency factor computation
│   │   └── ttl_service.py               # CV expiry logic
│   │
│   ├── db/
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   └── database.py          # Async and sync engine setup
│   │
│   ├── models/
│   │   ├── response.py          # Pydantic response schemas
│   │   └── tiebreaker.py        # Tiebreaker-specific schemas
│   │
│   └── tests/
│       ├── test_anonymization.py    # 17 unit tests for the PII pipeline
│       ├── test_file_extraction.py  # File parsing and format validation
│       └── test_validation.py       # Input size and limit enforcement
│
├── alembic/                     # Database migration scripts (7 versions)
├── docker-compose.yml           # core, celery_worker, redis, mysql services
├── requirements.txt
├── .env.example
│
└── web/                         # Vite + React frontend
    └── src/
        ├── pages/
        │   ├── AnalyzePage.tsx  # CV upload, async polling, results, tiebreaker
        │   ├── MatchPage.tsx    # Bank search by job description
        │   └── UploadPage.tsx   # Two-step candidate self-upload flow
        │
        └── components/
            ├── CandidateCard.tsx    # Full candidate result card with contact info
            ├── RankingTable.tsx     # Summary ranking table
            ├── TiebreakerFlow.tsx   # Multi-phase tiebreaker UI
            ├── StarRating.tsx       # 1–5 star feedback widget
            ├── NavBar.tsx           # Top navigation
            └── LoadingScreen.tsx    # Spinner for synchronous waits
```

---

## Design Decisions

**FastAPI over Flask or Django**
FastAPI is async-native, which fits a workload dominated by I/O — database queries, OpenAI API calls, and file reads. Pydantic provides request validation and serialization without extra configuration, and automatic OpenAPI docs make the API self-documenting.

**GPT-4o mini as the default model**
GPT-4o mini handles structured extraction tasks — ranking, contact parsing, tiebreaker question generation — with results comparable to larger models at a fraction of the cost. The model is configurable via `OPENAI_MODEL` for use cases where a more capable model is preferred.

**Celery + Redis for async processing**
An LLM call over a batch of CVs takes 10–30 seconds. Holding an HTTP connection open for that duration is a poor user experience and wastes server resources under load. Celery offloads the work to a background worker; the frontend polls a lightweight status endpoint until results are ready.

**Anonymization as a prerequisite to LLM evaluation**
Stripping PII before ranking is not only a privacy measure — it directly improves fairness. A model that sees a name, nationality signal, or LinkedIn profile URL may weight those signals even when instructed not to. Regex-based scrubbing is deterministic and runs at zero additional API cost, unlike a pre-processing LLM pass.

**Single entry point for file extraction**
All formats flow through `extract_text_from_bytes(raw, filename)`, which performs magic byte validation independent of the file extension before dispatching to the appropriate parser. This keeps format-specific code isolated, makes the validation layer easy to test, and ensures the same size and integrity checks apply regardless of format.

---

## Notes

- The application is optimized for desktop use.
- No authentication is implemented. It is intended for local or internal demo use.
- ChromaDB data persists locally in `./chroma_db/`. Delete this directory to reset the vector store.
- Running `python -m core.scripts.rebuild_chroma` re-indexes all active CVs from MySQL if the vector store falls out of sync.

---

## Author

**Matias Juan Bocco**
[github.com/matiasbocco](https://github.com/matiasbocco)
