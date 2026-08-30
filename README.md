# CV Analyzer AI

> AI-powered CV screening and ranking tool for recruiters

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-latest-009688?style=flat&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React%20%2B%20TypeScript-18-61DAFB?style=flat&logo=react&logoColor=black)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?style=flat&logo=openai&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)

CV Analyzer AI is a full-stack application that automates the initial CV screening stage for recruiters. Upload a set of CVs alongside a job description and receive a scored, structured ranking within seconds. Every CV is anonymized before evaluation to reduce demographic bias, and all results are persisted in a searchable candidate bank for future searches. The project is built as a portfolio piece demonstrating modern AI engineering patterns — async task queues, RAG, semantic search, and role-based access control — in a production-style architecture.

---

## Features

- **Multi-CV ranking** — scores each candidate across four dimensions (technical skills, experience, education, soft skills) using GPT-4o mini; normalized to 0–100 and grouped into tiers
- **RAG-powered CV bank** — every ingested CV is embedded and stored in ChromaDB; `/match-job` runs semantic search over the full bank without requiring a re-upload
- **Mandatory anonymization** — PII (names, emails, phone numbers, LinkedIn/GitHub URLs, age references) is stripped before every LLM call so the model evaluates skills, not identity
- **Async processing** — `/analyze` and `/match-job` return HTTP 202 immediately; the heavy pipeline runs in a Celery worker and the frontend polls for completion
- **Tiebreaker flow** — when top candidates score within 5 points of each other, the recruiter answers LLM-generated priority questions and the ranking is recalculated
- **JWT authentication with RBAC** — access tokens in memory, refresh tokens in httpOnly cookies (7-day TTL); Admin and Recruiter roles with separate route guards
- **Admin panel** — user management (create, activate/deactivate, reset password), per-user metrics, and OpenAI cost estimation
- **Analysis history** — all analyses are stored with a configurable TTL; recruiters can browse past results with full candidate cards and contact info
- **Multi-language support** — the ranking prompt instructs the model to respond in the language of the job description
- **Contact extraction** — a dedicated LLM pass extracts structured contact info (name, email, phone, LinkedIn, availability) from each CV after scoring

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Backend | Python 3.12, FastAPI | Async REST API |
| AI / LLM | OpenAI GPT-4o mini | CV ranking, contact extraction, tiebreaker questions |
| Embeddings | OpenAI text-embedding-3-small | Semantic vector generation |
| Vector DB | ChromaDB | CV bank similarity search |
| Task Queue | Celery + Redis | Async background processing |
| Database | MySQL 8.0 + SQLAlchemy 2.0 | Persistent storage |
| Migrations | Alembic | Schema versioning |
| Frontend | React 18 + TypeScript + Vite | Single-page application |
| State | TanStack Query | Server state and polling |
| Styling | Tailwind CSS | UI |
| Auth | JWT + bcrypt | Authentication and authorization |
| Infrastructure | Docker Compose | Local service orchestration |

---

## Architecture

The system follows a producer-consumer pattern. A request to `/analyze` hits FastAPI, which extracts text from the uploaded files synchronously (fails fast, keeps binary data out of the queue), then enqueues a Celery task and returns HTTP 202 with a `job_id`. The Celery worker runs the full pipeline: anonymization → LLM ranking → recency factor application → persistence to MySQL and ChromaDB. The frontend polls `GET /jobs/{job_id}` every two seconds and stops when the status becomes `completed` or `failed`.

SEE THE FULL FLOW AND DATABASE SCHEMA IN [docs/architecture.md](docs/architecture.md).

**Key design decisions:**

- Scores are stored in a `cv_analyses` junction table (not on the CV row) because the same CV can rank differently across different job descriptions
- Anonymization runs before every LLM call — it is a mandatory step in both the analyze and match-job pipelines, not an option
- CV bank entries expire after 4 months; the recency factor begins degrading at month 3 (1.0 → 0.7 → 0.0) to down-weight stale candidates without deleting their data
- Celery is configured with `--pool=solo` on Windows (prefork spawning is not supported on Windows)

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker Desktop (for MySQL and Redis)
- An OpenAI API key

### Installation

**1. Clone the repository**

```bash
git clone https://github.com/matiasbocco/CV-Annalyzer-AI.git
cd CV-Annalyzer-AI
```

**2. Configure environment variables**

```bash
cp .env.example .env
```

Open `.env` and set `OPENAI_API_KEY`. All other variables have working defaults for local development.

**3. Start the database and Redis**

```bash
docker compose up -d db redis
```

Wait a few seconds for MySQL to complete its initial setup before proceeding.

**4. Create a virtual environment and install dependencies**

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

**5. Apply database migrations**

```bash
alembic upgrade head
```

**6. Seed reference data and the default admin user**

```bash
python -m core.scripts.seed_categories
python -m core.scripts.seed_admin
```

The seed script prints the admin credentials to the console.

**7. Start the three services** (each in a separate terminal)

```bash
# Terminal 1 — FastAPI
uvicorn core.main:app --reload

# Terminal 2 — Celery worker
celery -A core.celery_app worker --loglevel=info --pool=solo

# Terminal 3 — Frontend
cd web && npm install && npm run dev
```

**8. Open the app**

```
http://localhost:5173
```

Log in with the admin credentials from step 6.

---

## Project Structure

```
cv-analyzer-ai/
├── core/                  # FastAPI backend
│   ├── routers/           # API endpoints (auth, admin, protected routes)
│   ├── services/          # Business logic (LLM, embeddings, CV bank, anonymization, etc.)
│   ├── db/                # SQLAlchemy models and async database setup
│   ├── tasks.py           # Celery async task pipelines (analyze, match-job)
│   └── scripts/           # Seed and utility scripts
├── web/                   # React frontend
│   └── src/
│       ├── pages/         # Route-level components (Analyze, Match, Upload, History, Admin)
│       ├── components/    # Reusable UI components (CandidateCard, NavBar, etc.)
│       └── api/           # Axios client, TanStack Query hooks, and TypeScript types
├── alembic/               # Database migration versions
├── test_cvs/              # Sample CVs for local testing
└── docker-compose.yml     # Service orchestration (MySQL, Redis)
```

---

## Key Concepts

**RAG (Retrieval-Augmented Generation)**
The CV bank implements a retrieval-augmented pattern: when a recruiter searches by job description, the query is embedded and used to retrieve the most semantically similar CVs from ChromaDB before passing them to the LLM. This means the model only evaluates relevant candidates rather than the entire database.

**Semantic search**
Each CV's text is converted to a dense vector using `text-embedding-3-small`. ChromaDB stores these vectors and retrieves the closest matches by cosine similarity, enabling search by meaning rather than keyword overlap.

**Algorithmic fairness via anonymization**
Before every LLM evaluation, a regex pipeline removes all personally identifiable information — full names (detected as title-case lines), email addresses, phone numbers, LinkedIn and GitHub URLs, and age references. Filenames are replaced with neutral labels (`candidate_a`, `candidate_b`, …). The model scores only the professional content of the CV.

**Async producer-consumer architecture**
FastAPI acts as the producer: it validates input, enqueues a task to Redis, and returns immediately. Celery acts as the consumer: it picks up the task, runs the expensive LLM pipeline, and writes results to MySQL and Redis. The frontend polls a lightweight status endpoint until the job is done. This pattern decouples request latency from processing time and makes the system horizontally scalable at the worker layer.

---

## Author

**Matias Bocco** — Systems Engineering Student, Universidad Católica de Córdoba, Argentina

[github.com/matiasbocco](https://github.com/matiasbocco)

---

## Notes

- The application is optimized for desktop use (768px+).
- ChromaDB data persists locally in `./chroma_db/`. Delete this directory to reset the vector store.
- Run `python -m core.scripts.rebuild_chroma` to re-sync the vector store with MySQL if they drift out of alignment.
- On Windows, Celery requires `--pool=solo` due to prefork multiprocessing limitations. This is already set as the default in `core/celery_app.py`.

---

## License

MIT
