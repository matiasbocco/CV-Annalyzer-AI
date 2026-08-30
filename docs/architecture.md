# Architecture

## Request Flow

The sequence below covers the `/analyze` endpoint. The `/match-job` flow is identical except step 4 performs a ChromaDB vector search instead of processing uploaded files.

```mermaid
flowchart TD
    Browser["Browser\n(React SPA)"]
    FastAPI["FastAPI\ncore/main.py"]
    Redis["Redis\nBroker + Result Backend"]
    Celery["Celery Worker\ncore/tasks.py"]
    OpenAI["OpenAI API\nGPT-4o mini\ntext-embedding-3-small"]
    ChromaDB["ChromaDB\nVector Store"]
    MySQL["MySQL 8.0\nPersistence"]

    Browser -->|"POST /analyze\n(files + job description)"| FastAPI
    FastAPI -->|"Extract text from files\nValidate + anonymize"| FastAPI
    FastAPI -->|"Enqueue task"| Redis
    FastAPI -->|"HTTP 202\n{ job_id }"| Browser
    Browser -->|"GET /jobs/{job_id}\n(poll every 2s)"| FastAPI
    FastAPI -->|"Read job status"| Redis
    Redis -->|"Consume task"| Celery
    Celery -->|"Anonymized CV text\nRanking prompt"| OpenAI
    Celery -->|"Embed job description\nSemantic search"| ChromaDB
    ChromaDB -->|"Top-N matching CVs"| Celery
    OpenAI -->|"Structured ranking\nContact extraction"| Celery
    Celery -->|"Persist Analysis\n+ CVs + scores"| MySQL
    Celery -->|"Write result"| Redis
    FastAPI -->|"completed result"| Browser
```

---

## Anonymization Pipeline

Anonymization is a mandatory step that runs before every LLM call. It is not configurable.

```mermaid
flowchart LR
    Raw["Raw CV text\n+ real filename"]
    Regex["Regex pipeline\nStrip: emails, phones,\nLinkedIn, GitHub, URLs,\nage references, name-like\ntitle lines"]
    Label["Replace filename\nwith opaque label\ncandidate_a, candidate_b …"]
    LLM["OpenAI\nRanking call"]
    Restore["Restore real filenames\nfrom in-memory map"]
    Contact["Attach contact info\nfrom MySQL\n(never sent to LLM)"]
    Output["Ranked candidates\nwith contact info"]

    Raw --> Regex --> Label --> LLM --> Restore --> Contact --> Output
```

---

## Database Schema

```mermaid
erDiagram
    organizations {
        uuid id PK
        string name
    }

    users {
        uuid id PK
        string email
        string hashed_password
        string role
        string first_name
        string last_name
        bool is_active
        uuid organization_id FK
        datetime created_at
    }

    cvs {
        uuid id PK
        string filename
        text extracted_text
        string text_hash
        json contact_info
        datetime contact_extracted_at
        bool is_expired
        datetime last_seen_at
        int times_matched
        datetime created_at
    }

    analyses {
        uuid id PK
        uuid user_id FK
        text job_description
        string job_category FK
        json ranking
        string status
        int file_count
        datetime created_at
        datetime expires_at
    }

    cv_analyses {
        uuid id PK
        uuid analysis_id FK
        uuid cv_id FK
        float score
        string nivel
        json detailed_scores
        string source
    }

    feedback {
        uuid id PK
        uuid analysis_id FK
        int rating
        datetime created_at
    }

    tiebreaker_sessions {
        uuid id PK
        uuid analysis_id FK
        json questions
        json answers
        string status
        datetime created_at
    }

    job_categories {
        string slug PK
        string label
    }

    organizations ||--o{ users : "has"
    users ||--o{ analyses : "runs"
    analyses ||--o{ cv_analyses : "contains"
    cvs ||--o{ cv_analyses : "appears in"
    analyses }o--|| job_categories : "classified as"
    analyses ||--o| feedback : "has"
    analyses ||--o| tiebreaker_sessions : "may have"
```

---

## CV Bank Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Active : CV uploaded / ingested
    Active --> Active : Re-uploaded (last_seen_at reset)
    Active --> Degraded : Age > 90 days\n(recency_factor = 0.7)
    Degraded --> Expired : Age > 120 days\n(recency_factor = 0.0,\nis_expired = true)
    Expired --> Active : Re-uploaded\n(contact_extracted_at reset)
    Expired --> [*] : Admin cleanup
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Scores in `cv_analyses`, not on `cvs` | The same CV can score differently across different job descriptions; a junction table captures context-dependent results |
| Anonymization before every LLM call | Regex-based PII stripping is deterministic, zero additional API cost, and prevents the model from weighting demographic signals |
| CV TTL + recency factor | Hard deletion would lose candidate data; soft expiry with score degradation surfaces fresh candidates first while preserving history |
| Celery `--pool=solo` on Windows | Windows does not support the `prefork` multiprocessing start method that Celery uses by default on Linux/macOS |
| Refresh token in httpOnly cookie | Keeps the long-lived token out of JavaScript; access tokens are stored only in memory (not localStorage) to limit XSS exposure |
| Text extracted before enqueueing | Binary file data stays in the web process; the task queue only carries plain text, keeping message sizes small and parsing errors synchronous |
