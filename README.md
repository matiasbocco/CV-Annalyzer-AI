# CV-Annalyzer-AI

AI tool that ranks CVs against a job description using LLMs. Returns scores, strengths, skill gaps, and recommendations. Supports a CV bank with semantic search via embeddings.

## Stack

| Layer | Tech |
|---|---|
| Backend API | Python · FastAPI · OpenAI GPT-4o mini |
| Database | MySQL · SQLAlchemy (async) · Alembic |
| Vector DB | ChromaDB (embeddings + similarity search) |
| Frontend | React · TypeScript · Vite · Tailwind CSS v3 |
| State / fetching | TanStack Query · Axios |

## Running locally

You need **two terminals** — backend and frontend run separately.

### Terminal 1 — Backend

```bash
# from project root
uvicorn core.main:app --reload
```

Runs on `http://localhost:8000`.  
Legacy HTML test pages are at `/static/test.html`, `/static/upload.html`, `/static/match.html`.

### Terminal 2 — Frontend (React)

```bash
cd web
npm run dev
```

Runs on `http://localhost:5173`.  
The backend must be running for the frontend to connect.

## First-time setup

### Backend

```bash
python -m venv venv
./venv/Scripts/pip install -r requirements.txt   # Windows
# source venv/bin/activate && pip install -r requirements.txt  # macOS/Linux
alembic upgrade head
```

Requires a `.env` file (or environment variables) with:
- `DATABASE_URL` — async MySQL URL (`mysql+aiomysql://...`)
- `OPENAI_API_KEY`

### Frontend

```bash
cd web
npm install
```

## Author

Matias Bocco · Universidad Católica de Córdoba
