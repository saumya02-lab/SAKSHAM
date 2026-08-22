# SAKSHAM - Multi-Agent AI Business Assistant

A web-based multi-agent AI assistant that coordinates specialized AI agents (Research, Coding, Email/Writing) under a Supervisor to handle complex tasks with citations, tool usage, and memory.

## How is SAKSHAM different from a normal chatbot?

A normal chatbot is one API call with one prompt. SAKSHAM is architecturally different:

| Feature | Normal Chatbot | SAKSHAM |
|---------|---------------|---------|
| Agent routing | None — single prompt | Supervisor classifies intent, picks specialist agent(s) |
| Model per task | Same model for everything | Different model + temperature per agent role |
| Tool usage | None | Web search, calculator, document RAG — results fed into prompt |
| Multi-agent chaining | Not possible | "Research X then email about it" runs two agents sequentially |
| Long-term memory | None | Learns your preferences, applies them in every future response |
| Transparency | Black box | Shows which agent was chosen, why, and which model is running |

When using **Ollama**, each agent can run a genuinely different local model (e.g. `deepseek-coder` for coding, `llama3` for research, `mistral` for writing). When using **OpenAI/Gemini**, each agent gets a tuned temperature (low for code accuracy, high for creative writing) and optionally a different model via environment variables.

## Quick Start

### Prerequisites
- Docker Desktop (includes Docker Compose)
- An LLM API key (OpenAI, Gemini, or local Ollama)

### 1. Configure environment

`.env` is **required** — `docker compose` fails to start without it.

macOS / Linux:
```bash
cp .env.example .env
```

Windows (PowerShell):
```powershell
Copy-Item .env.example .env
```

Then edit `.env` and set `LLM_PROVIDER` plus the matching key:

| Provider | Set these |
|----------|-----------|
| `openai` | `OPENAI_API_KEY=sk-...` |
| `gemini` | `GOOGLE_API_KEY=...` |
| `ollama` | `OLLAMA_BASE_URL=http://host.docker.internal:11434` |

> **Two gotchas:** never put a comment on the same line as a value
> (`LLM_PROVIDER=openai  # ...` makes the value invalid), and leave the
> `DATABASE_URL` / `CHROMA_URL` hostnames as the compose service names
> (`postgres`, `chroma`) — not `localhost`.

### 2. Run
```bash
docker compose up --build
```

First build takes a few minutes. Wait for `Application startup complete`
from the `api` service before using the UI.

### 3. Access
- **Frontend:** http://localhost:3000
- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## Architecture

```
Frontend (Next.js) --> Backend (FastAPI) --> Agent Orchestrator
                                            |-- Supervisor (routes)
                                            |-- Research Agent (RAG + web search)
                                            |-- Coding Agent
                                            +-- Email/Writing Agent

Data: PostgreSQL + Redis + ChromaDB
```

## Features (MVP)

- **JWT Authentication** - Register, login, protected routes
- **Streaming Chat** - SSE-based token streaming with markdown/code rendering
- **3 Specialized Agents** - Research (with citations), Coding, Email/Writing
- **Supervisor Auto-Routing** - Hybrid rule + LLM routing
- **Multi-Agent Handoff** - Compound requests across agents
- **Document Upload + RAG** - PDF/TXT/DOCX ingestion with cited answers
- **Conversation Memory & History** - Persistent, per-user
- **Long-Term Memory** - Learns stated facts/preferences and applies them to
  future replies; viewable and erasable in Settings
- **Semantic Document Search** - Search your uploaded files from the sidebar
- **Tool Calling** - Web search, calculator, document retrieval
- **Stop & Regenerate** - Interrupt a reply or ask for a fresh one
- **Dark / Light / System Theme** - Toggle in the header, persisted per device
- **Settings** - Profile, model choice, default agent, theme, memory
- **Audit Log** - Key action tracking
- **Dockerized** - One-command deployment

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js, React, TypeScript, Tailwind CSS |
| Backend | FastAPI (Python) |
| Orchestration | LangChain |
| LLMs | OpenAI / Gemini / Ollama |
| Vector DB | ChromaDB |
| Database | PostgreSQL |
| Cache | Redis |
| Auth | JWT |
| Deploy | Docker Compose |

## Project Structure

```
nexus/
├── docker-compose.yml
├── .env.example
├── frontend/           # Next.js app
│   ├── app/
│   ├── components/
│   └── lib/
├── backend/            # FastAPI
│   ├── app/
│   │   ├── api/        # Routes
│   │   ├── agents/     # Supervisor, Research, Coding, Email
│   │   ├── orchestration/
│   │   ├── rag/        # Ingest, retrieve
│   │   ├── tools/      # Web search, calculator
│   │   ├── models/     # DB models & schemas
│   │   └── core/       # Auth, config, database
│   └── Dockerfile
└── docs/
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/auth/register | Register |
| POST | /api/auth/login | Login |
| GET | /api/auth/me | Current user |
| POST | /api/chat | Chat (SSE stream) |
| GET | /api/conversations | List conversations |
| GET | /api/conversations/:id | Get conversation |
| DELETE | /api/conversations/:id | Delete conversation |
| POST | /api/documents | Upload document |
| GET | /api/documents | List documents |
| DELETE | /api/documents/:id | Delete document |
| GET | /api/agents | List agents |
| POST | /api/search | Semantic search over your documents |
| GET | /api/memory | List memories |
| DELETE | /api/memory/:id | Delete one memory |
| DELETE | /api/memory | Clear all memory |
| GET/PATCH | /api/settings | User settings |
| GET | /api/audit | Audit logs |

## Tests

Backend (routing accuracy, memory extraction, chunking, calculator):

```bash
docker compose run --rm api pytest -q -s
```

Or locally, from `backend/`:

```bash
pip install -r requirements.txt
pytest -q -s
```

`tests/test_routing.py` scores the supervisor against a 30-prompt labelled set
and prints the measured accuracy (PRD PO-1 requires >=90%).

Frontend typecheck and production build, from `frontend/`:

```bash
npm install
npx tsc --noEmit
npm run build
```

## License

MIT
