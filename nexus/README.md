# Nexus — Multi-Agent AI Business Assistant

A web-based multi-agent AI assistant that coordinates specialized AI agents (Research, Coding, Email/Writing) under a Supervisor to handle complex tasks with citations, tool usage, and memory.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- An LLM API key (OpenAI, Gemini, or local Ollama)

### 1. Configure environment
```bash
cp .env.example .env
# Edit .env with your API keys
```

### 2. Run
```bash
docker compose up --build
```

### 3. Access
- **Frontend:** http://localhost:3000
- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## Architecture

```
Frontend (Next.js) → Backend (FastAPI) → Agent Orchestrator
                                         ├─ Supervisor (routes)
                                         ├─ Research Agent (RAG + web search)
                                         ├─ Coding Agent
                                         └─ Email/Writing Agent
                                     
Data: PostgreSQL + Redis + ChromaDB
```

## Features (MVP)

- **JWT Authentication** — Register, login, protected routes
- **Streaming Chat** — SSE-based token streaming with markdown/code rendering
- **3 Specialized Agents** — Research (with citations), Coding, Email/Writing
- **Supervisor Auto-Routing** — Hybrid rule + LLM routing
- **Multi-Agent Handoff** — Compound requests across agents
- **Document Upload + RAG** — PDF/TXT/DOCX ingestion with cited answers
- **Conversation Memory & History** — Persistent, per-user
- **Tool Calling** — Web search, calculator, document retrieval
- **Settings** — Profile, model choice, theme
- **Audit Log** — Key action tracking
- **Dockerized** — One-command deployment

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
| POST | `/api/auth/register` | Register |
| POST | `/api/auth/login` | Login |
| GET | `/api/auth/me` | Current user |
| POST | `/api/chat` | Chat (SSE stream) |
| GET | `/api/conversations` | List conversations |
| GET | `/api/conversations/:id` | Get conversation |
| DELETE | `/api/conversations/:id` | Delete conversation |
| POST | `/api/documents` | Upload document |
| GET | `/api/documents` | List documents |
| DELETE | `/api/documents/:id` | Delete document |
| GET | `/api/agents` | List agents |
| GET | `/api/memory` | List memories |
| DELETE | `/api/memory/:id` | Delete memory |
| GET/PATCH | `/api/settings` | User settings |
| GET | `/api/audit` | Audit logs |

## License

MIT
