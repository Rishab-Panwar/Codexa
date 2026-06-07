<div align="center">

<img src="docs/logo.svg" width="92" alt="Codexa logo" />

# Codexa

**Chat with any codebase** — semantic code search with grounded, cited answers.

</div>

> [!TIP]
> Index any public GitHub repo, then ask questions and get answers grounded in the **actual code** with `file:line` citations.
> Powered by **semantic RAG** (Vertex AI embeddings + FAISS — not keyword/hash matching), a **LangGraph** agent pipeline (retrieval → memory → mentor), per-repo **conversation memory**, and **real-time token streaming**.
> Built to make any unfamiliar codebase explorable in plain English.

<div align="center">

[![Follow @Rishab-Panwar](https://img.shields.io/github/followers/Rishab-Panwar?style=social)](https://github.com/Rishab-Panwar) &nbsp; Follow **[@Rishab-Panwar](https://github.com/Rishab-Panwar)** on GitHub.

</div>

<div align="center">

![Python](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=next.js&logoColor=white)
![LLM](https://img.shields.io/badge/LLM-Groq%20Llama--3.1-F55036)
![Embeddings](https://img.shields.io/badge/embeddings-Vertex%20AI-4285F4?logo=googlecloud&logoColor=white)
![Vector](https://img.shields.io/badge/vector-FAISS-0064FF)
![License](https://img.shields.io/github/license/Rishab-Panwar/Codexa?color=brightgreen)
![Stars](https://img.shields.io/github/stars/Rishab-Panwar/Codexa)

</div>

---

## ✨ Features

- **Index any public GitHub repo** — paste a URL; Codexa clones, parses, and embeds it.
- **Semantic code retrieval (RAG)** — dense vector search over the codebase using **real semantic embeddings** (Vertex AI), *not* keyword/hash matching.
- **Grounded answers with citations** — every answer is built from retrieved snippets and cites exact `file:line` locations, reducing hallucination.
- **Conversational memory** — per-repo chat history; follow-ups like *"refactor it"* or *"what about that file?"* resolve against earlier turns.
- **Real-time streaming** — answers stream token-by-token over SSE (first words in ~1–2s).
- **Code-aware parsing** — tree-sitter extracts functions/classes across ~18 languages; docs/config files (README, YAML, Dockerfile…) are indexed too.
- **Dependency graph** — builds and visualizes the import graph of the repo.
- **File explorer** — browse the indexed file tree and preview files.
- **Eval dashboard** — live analytics: query count, p95 latency, agent utilization, per-repo stats, recent queries.
- **Multiple embedding backends** — Vertex AI (default, semantic), fastembed (local ONNX, semantic), or hash (lexical fallback) — switchable via one env var.
- **Pluggable LLM** — Groq (Llama-3.1-8B) by default via an OpenAI-compatible client; swap providers with env vars.

---

## 🧠 How it works

```
                    ┌─────────────── Indexing ───────────────┐
GitHub URL ─► git clone --depth 1 ─► tree-sitter parse ─► embed chunks (Vertex)
                                          │                        │
                                   functions + docs          FAISS index (cosine)
                                          │                        │
                                   import graph (JSON)        persisted to disk

                    ┌─────────────── Querying ───────────────┐
Question ─► embed (Vertex) ─► FAISS top-k ─► lexical rerank ─► context block
        + recent chat turns ───────────────────────────────────────┐
                                                                     ▼
                                          Groq LLM ─► streamed answer + file:line citations
```

- **Embeddings:** Vertex AI `text-embedding-004` (768-dim) — true semantic vectors. Indexing is parallelized with token-aware batching + retry/backoff.
- **Vector store:** FAISS (`IndexFlatIP`, cosine on normalized vectors), held in memory and persisted to disk.
- **Retrieval:** dense FAISS search + a lightweight lexical (token-overlap) rerank → a small hybrid.
- **Generation:** Groq streams a grounded answer; context is capped per-snippet to keep latency predictable.

---

## 🤖 Agent architecture

Codexa is built on a **LangGraph** multi-agent orchestrator. The production path runs a fast, low-latency subset (**Retrieval → Mentor**, with **Memory** threading prior turns); the full graph is available for deeper, multi-step reasoning.

### Production pipeline (fast mode)

```mermaid
flowchart LR
    Q([User question]) --> MEM[Memory Agent<br/>recent turns]
    Q --> R[Retrieval Agent<br/>embed → FAISS → rerank]
    R --> CTX[Code context + citations]
    MEM --> M[Coding Mentor]
    CTX --> M
    M --> A([Streamed answer + citations])
```

### Full multi-agent orchestrator (LangGraph)

```mermaid
flowchart TD
    START([Question]) --> P[Planner Agent<br/>break into steps]
    P --> D{Dispatcher<br/>route each step}
    D -->|retrieval| R[Retrieval Agent]
    D -->|analyst| AN[Repo Analyst Agent<br/>architecture + graph]
    D -->|mentor| ME[Coding Mentor Agent]
    D -->|memory| MM[Memory Agent]
    D -->|all steps done| V[Validator<br/>refine answer]
    R --> D
    AN --> D
    ME --> D
    MM --> D
    V --> FIN([Final answer + citations])
```

**Agents**

| Agent | Role |
|---|---|
| **Retrieval** | Embeds the query, searches FAISS, reranks, returns grounded snippets + citations |
| **Coding Mentor** | Generates the final answer/code from retrieved context, senior-engineer style |
| **Memory** | Threads recent conversation turns so follow-ups resolve correctly |
| **Planner** *(full mode)* | Breaks a question into steps and routes them to agents |
| **Repo Analyst** *(full mode)* | Answers architecture questions using the import graph |
| **Validator** *(full mode)* | Reviews and refines the draft answer |

> The fast pipeline makes **1 retrieval + 1 LLM call**; the full orchestrator trades latency for deeper reasoning.

---

## 🛠️ Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js (React), Tailwind CSS, SSE streaming |
| Backend | FastAPI (async, Python 3.11+) |
| LLM | Groq — Llama-3.1-8B-instant (via `langchain-openai`) |
| Embeddings | Vertex AI `text-embedding-004` (fastembed / hash fallbacks) |
| Vector store | FAISS (`faiss-cpu`) |
| Parsing | tree-sitter (`tree-sitter-languages`) |
| Orchestration | LangGraph |
| Graphs | NetworkX (import dependency graph) |
| Metrics | Prometheus |
| Infra | Docker Compose, Caddy (reverse proxy + auto-TLS), GCP Compute Engine, Cloudflare DNS |
| CI | GitHub Actions (ruff, pytest, docker build; Next.js lint + build) |

---

## 📁 Project structure

```
codexa/
├── codexa/                     # FastAPI backend
│   ├── app/                    # app factory, DI, security
│   ├── controllers/            # API routes (analyze, ask, files, repos, dependencies, eval…)
│   ├── services/
│   │   ├── agents/             # LangGraph orchestrator + agents
│   │   ├── ingestion/          # git clone loader
│   │   ├── parsing/            # tree-sitter AST parser
│   │   ├── retrieval/          # embedders (vertex/fastembed/hash) + FAISS retriever + indexing
│   │   ├── qa/                 # answer service (retrieve → rerank → context)
│   │   ├── dependency/         # import graph builder
│   │   ├── memory/ state/      # conversational + repo state stores
│   ├── observability/          # Prometheus metrics + session tracker
│   └── utils/                  # config, logging
├── codexa-ui/                  # Next.js frontend
│   ├── app/                    # landing, workspace, eval pages
│   └── components/             # Layout (TopBar/drawers), Chat, Sidebar, Panels
├── infra/                      # Caddy config + env files (gitignored secrets)
├── docker-compose.yml
└── Dockerfile
```

---

## 🚀 Local development

**Prerequisites:** Python 3.11, Node 20, and either a Vertex AI project (semantic, default) or set `CODEXA_EMBEDDING_PROVIDER=fastembed` for fully local embeddings.

**Backend**
```bash
uv venv .venv --python 3.12 && .venv/Scripts/activate   # or python -m venv
uv pip install -r requirements.txt
uv run uvicorn codexa.app.main:app --reload --port 8000
```

**Frontend**
```bash
cd codexa-ui
npm install
npm run dev   # http://localhost:3000
```

### Configuration (`.env`)
```bash
# Embedding: vertex (semantic, default) | fastembed (local semantic) | hash (lexical)
CODEXA_EMBEDDING_PROVIDER=vertex
GOOGLE_CLOUD_PROJECT=your-gcp-project
GOOGLE_CLOUD_LOCATION=us-central1

# LLM
CODEXA_LLM_PROVIDER=groq
CODEXA_LLM_MODEL=llama-3.1-8b-instant
GROQ_API_KEY=your-groq-key

# CORS + storage
CODEXA_ALLOWED_ORIGINS=http://localhost:3000
CODEXA_INDEX_DIR=.codexa/indexes
CODEXA_STATE_DIR=.codexa/state

# Frontend → backend (build-time)
NEXT_PUBLIC_API_URL=http://localhost:8000
```
> Vertex AI uses Application Default Credentials (`gcloud auth application-default login` locally; the VM's service account in production). No API key needed for embeddings.

---

## ☁️ Deployment

Containerized and deployed with **Docker Compose** on a **GCP Compute Engine** VM:

- **Caddy** reverse-proxies `app.domain` → frontend and `api.domain` → backend with automatic HTTPS.
- **Cloudflare** DNS points a reserved **static IP** at the VM.
- **Vertex AI** auth comes from the VM's **service account** (metadata server) — no key files in the container.

```bash
git pull
docker-compose up -d --build
```

---

## 🗺️ Roadmap

- Incremental re-indexing on git changes (diff + Merkle-tree change detection)
- Per-user isolation + authentication (multi-tenant)
- Externalized state (managed vector DB + Postgres) for horizontal scaling
- Indexing via a job queue (Celery) with dedicated workers
- Branch selection (currently indexes the default branch only)
