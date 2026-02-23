# Helio Supervisor

**Version:** defined in [VERSION](VERSION) (used for app and GitHub release tags). See [CHANGELOG.md](CHANGELOG.md) for history.

A **local hierarchical supervisor agent** for goal-oriented workflows. It plans tasks, fetches web content, runs code snippets, writes notes, and summarizes text—with optional **human-in-the-loop** approval and **self-critique** summaries.

---

## Features

- **Multi-provider LLM support**: OpenAI, Ollama (local), Google (Gemini), Perplexity
- **Six built-in tools**: `plan_tasks`, `web_fetch`, `code_exec`, `write_note`, `summarize_text`, `rag_search`
- **Optional RAG (local documents)**: In the Web UI, attach a document and/or select documents or folders from `memory/docs/`; RAG runs only for that run. **RAG mode toggle:** answer only from documents (offline) or use internet + documents. **Anti-hallucination:** answers are grounded in retrieved chunks; the agent says when something is not in the document(s).
- **Optional human approval** for risky actions (code execution, web fetch, writing notes)
- **Optional self-critique**: short summary of the agent’s answer after each turn
- **Persistent conversation memory** (JSONL) and **notes** written to disk
- **Two interfaces**: Streamlit web UI and Rich-based CLI
- **Best-in-class RAG embeddings**: Default `BAAI/bge-base-en-v1.5` (set `RAG_EMBEDDING_MODEL` in `.env`). PDF extraction: pypdf then PyMuPDF. **Streamlit**: Chat history cap (40 messages), `.streamlit/config.toml`, "Tools used" shown for every reply.

---

## Quick start

### Prerequisites

- **Python 3.10+**
- For **Ollama**: [Ollama](https://ollama.ai) running locally (e.g. `ollama serve`)
- For **OpenAI / Google / Perplexity**: corresponding API keys (set in `.env` or in the UI)

### 1. Clone and install

```bash
git clone <your-repo-url>
cd HelioSupervisor
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure environment

Copy the example env and set at least the provider and (if needed) API keys:

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

Edit `.env`:

- **LLM_PROVIDER**: `openai` | `ollama` | `google` | `perplexity`
- **LLM_MODEL**: e.g. `gpt-4o-mini`, `llama3.1`
- For cloud providers, set **OPENAI_API_KEY**, **GOOGLE_API_KEY**, or **PERPLEXITY_API_KEY**

See [Configuration](#configuration) and [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for all options.

### 3. Run the app

**Web UI (recommended):**

```bash
streamlit run app/ui.py
```

**CLI:**

```bash
python -m app.cli
```

Type your goal or task; type `exit` or `quit` to leave the CLI.

---

## Project layout

```
HelioSupervisor/
├── app/
│   ├── config.py      # Env-based config (paths, limits, API keys, RAG)
│   ├── types.py       # Pydantic schemas for tool inputs
│   ├── llm.py         # LLM factory (OpenAI, Ollama, Google, Perplexity)
│   ├── memory.py      # Conversation persistence (conversations.jsonl)
│   ├── rag.py         # RAG: scoped search over memory/docs/ (FAISS + local embeddings)
│   ├── tools.py       # LangChain tools (plan, fetch, code_exec, note, summarize, rag_search)
│   ├── supervisor.py  # Supervisor agent graph and run_supervisor()
│   ├── ui.py          # Streamlit web UI (attach/select docs for RAG)
│   └── cli.py         # Rich CLI loop
├── memory/            # Runtime: conversations.jsonl + agent-written *.md notes
│   └── docs/          # RAG documents (.md, .txt, .pdf); UI uploads saved here
├── logs/              # Created at startup (for future use)
├── scripts/
│   └── reinstall.ps1  # Pip cache purge + reinstall from requirements.txt
├── docs/              # Detailed documentation
├── .streamlit/
│   └── config.toml    # Streamlit server/browser options (e.g. lower RAM)
├── .env               # Local config (not committed; copy from .env.example)
├── .env.example       # Example env template
├── VERSION            # Single source of truth for version (app + GitHub release tags)
├── CHANGELOG.md       # Version history and changes
├── requirements.txt
└── README.md
```

---

## Configuration

| Variable | Description | Default |
|----------|-------------|--------|
| **LLM** | | |
| `LLM_PROVIDER` | `openai` \| `ollama` \| `google` \| `perplexity` | `openai` |
| `LLM_MODEL` | Model name for OpenAI/Ollama | `gpt-4o-mini` |
| `LLM_TEMPERATURE` | Sampling temperature | `0.1` |
| `MAX_TOKENS` | Max tokens per response | `8192` |
| `GOOGLE_MODEL` | Model when provider is Google | `gemini-1.5-pro` |
| `PERPLEXITY_MODEL` | Model when provider is Perplexity | `llama-3.1-sonar-small-128k-online` |
| `OLLAMA_NUM_CTX` | Context size for Ollama | `4096` |
| **API keys** | Set in `.env` or in Streamlit sidebar | — |
| `OPENAI_API_KEY` | For OpenAI | — |
| `GOOGLE_API_KEY` | For Google Gemini | — |
| `PERPLEXITY_API_KEY` | For Perplexity | — |
| **Behaviour** | | |
| `RECURSION_LIMIT` | Max agent steps per turn | `50` |
| `MEMORY_RECENT_TURNS` | Recent turns loaded into context | `6` |
| `PLAN_MAX_STEPS` | Max steps in plan_tasks | `10` |
| `WEB_FETCH_MAX_CHARS` | Max characters from web_fetch | `8000` |
| `WEB_FETCH_TIMEOUT` | Timeout (seconds) for web_fetch | `10` |
| `CODE_EXEC_TIMEOUT` | Timeout (seconds) for code_exec | `10` |
| `SUMMARIZE_MAX_WORDS` | Max words for summarize_text | `2000` |
| `SUMMARIZE_CRITIQUE_MAX_WORDS` | Max words for self-critique | `2000` |
| **RAG** | | |
| `RAG_DOCS_DIR` | Path to RAG documents (relative to project root) | `memory/docs` |
| `RAG_INDEX_DIR` | Path for FAISS index (relative to project root) | `memory/rag_faiss` |
| `RAG_CHUNK_SIZE` | Chunk size for RAG | `800` |
| `RAG_CHUNK_OVERLAP` | Chunk overlap for RAG | `100` |
| `RAG_TOP_K` | Default top-k chunks returned by rag_search | `5` |
| `RAG_EMBEDDING_MODEL` | RAG embedding model (default: BGE for best quality) | `BAAI/bge-base-en-v1.5` |
| `RAG_EMBEDDING_DEVICE` | Device for embeddings (`cpu` or `cuda`) | `cpu` |
| `RAG_ALLOWED_EXTENSIONS` | Allowed file types for RAG (comma-separated) | `md,txt,pdf` |
| `RAG_NAIVE_CHUNK_MAX_CHARS` | Max chars per chunk in keyword fallback; `0` = chunk_size×2 | `0` |

**Note:** In the Streamlit UI, API keys entered in the sidebar override `.env` for that session.

---

## Tools

| Tool | Description |
|------|-------------|
| **plan_tasks** | Breaks a high-level goal into an ordered step-by-step plan. |
| **web_fetch** | Fetches raw HTML/text from a URL (GET, no JavaScript). |
| **code_exec** | Runs short Python snippets in a subprocess; use `print()` for output. |
| **write_note** | Writes a note to `memory/<title>.md`. |
| **summarize_text** | Summarizes text with configurable max word count. |
| **rag_search** | Searches selected/attached documents (in `memory/docs/`) for relevant chunks; only used when you attach a file or select documents/folders in the UI. |

When **human approval** is enabled (default in UI: “Approve all actions” off), the agent will ask for confirmation before using `code_exec`, `web_fetch`, or `write_note`. **RAG** is opt-in per run: attach a document and/or select documents or folders in the "RAG for this run" expander; use **"Answer only from documents (offline)"** to forbid web fetch. When RAG is used, the agent is instructed not to hallucinate.

---

## Memory and data

- **Conversations**: Appended to `memory/conversations.jsonl` (role, content, timestamp).
- **Notes**: Created by the agent in `memory/*.md` via `write_note`.
- **RAG documents**: Stored in `memory/docs/` (path configurable via `RAG_DOCS_DIR`). In the Web UI you can attach files (saved there), or select existing documents/folders; RAG runs only when at least one is chosen for that run.
- **Context**: The supervisor loads the last `MEMORY_RECENT_TURNS` turns from disk and merges with the current chat when using the UI.

---

## Scripts

- **`scripts/reinstall.ps1`** (PowerShell, run from repo root): purges pip cache and installs from `requirements.txt` with pinned versions.

---

## Documentation

- **[docs/SETUP.md](docs/SETUP.md)** — Detailed setup (venv, dependencies, providers, troubleshooting).
- **[docs/CONFIGURATION.md](docs/CONFIGURATION.md)** — All environment variables and behaviour options.
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — Data flow, modules, and design.
- **[CHANGELOG.md](CHANGELOG.md)** — Version history and list of changes per release.

---

## License

See repository license file.
