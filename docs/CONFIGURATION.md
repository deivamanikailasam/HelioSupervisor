# Helio Supervisor — Configuration Reference

All behaviour is driven by environment variables loaded from `.env` in the project root (via `python-dotenv` in `app/config.py`). The Streamlit UI can override **API keys** and **provider/model/temperature** per session; the CLI uses only `.env` and defaults.

---

## 1. LLM provider and model

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LLM_PROVIDER` | string | `openai` | One of: `openai`, `ollama`, `google`, `perplexity` (case-insensitive). |
| `LLM_MODEL` | string | `gpt-4o-mini` | Default model for OpenAI and Ollama. For Google/Perplexity, see below. |
| `LLM_TEMPERATURE` | float | `0.1` | Sampling temperature (0.0–1.0). |
| `MAX_TOKENS` | int | `8192` | Maximum tokens per LLM response. |
| `OLLAMA_NUM_CTX` | int | `4096` | Context window size for Ollama. |
| `GOOGLE_MODEL` | string | `gemini-1.5-pro` | Model used when `LLM_PROVIDER=google`. |
| `PERPLEXITY_MODEL` | string | `llama-3.1-sonar-small-128k-online` | Model used when `LLM_PROVIDER=perplexity`. |

---

## 2. API keys

Set in `.env` (or in the Streamlit sidebar; sidebar values override `.env` for that run).

| Variable | Used when | Description |
|----------|-----------|-------------|
| `OPENAI_API_KEY` | `LLM_PROVIDER=openai` | OpenAI API key (e.g. `sk-...`). |
| `GOOGLE_API_KEY` | `LLM_PROVIDER=google` | Google AI (Gemini) API key (e.g. `AIza...`). |
| `PERPLEXITY_API_KEY` | `LLM_PROVIDER=perplexity` | Perplexity API key (e.g. `pplx-...`). |

- **Ollama** does not use API keys.
- If the UI supplies keys, they are passed into `run_supervisor(..., api_keys=...)` and the corresponding env vars are temporarily unset so tools and the agent use only the UI keys.

---

## 3. Agent and tool behaviour

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `RECURSION_LIMIT` | int | `50` | Maximum agent steps (tool calls + responses) per turn. |
| `MEMORY_RECENT_TURNS` | int | `6` | Number of recent conversation turns loaded from `memory/conversations.jsonl` into context. |
| `PLAN_MAX_STEPS` | int | `10` | Maximum steps allowed in the `plan_tasks` tool. |
| `WEB_FETCH_MAX_CHARS` | int | `8000` | Maximum characters returned by `web_fetch` from a single URL. |
| `WEB_FETCH_TIMEOUT` | float | `10.0` | Timeout in seconds for `web_fetch` HTTP requests. |
| `CODE_EXEC_TIMEOUT` | int | `10` | Timeout in seconds for `code_exec` subprocess. |
| `SUMMARIZE_MAX_WORDS` | int | `2000` | Default max words for the `summarize_text` tool. |
| `SUMMARIZE_CRITIQUE_MAX_WORDS` | int | `2000` | Max words for the optional self-critique summary. |
| `RAG_DOCS_DIR` | string | `memory/docs` | Path (relative to project root) where RAG documents are stored; uploads and selections use this. |
| `RAG_INDEX_DIR` | string | `memory/rag_faiss` | Path (relative to project root) for persisted FAISS index (when using global index). |
| `RAG_CHUNK_SIZE` | int | `800` | Character size for document chunks (RAG). |
| `RAG_CHUNK_OVERLAP` | int | `100` | Overlap between consecutive chunks (RAG). |
| `RAG_TOP_K` | int | `5` | Default number of top chunks returned by `rag_search`. |
| `RAG_EMBEDDING_MODEL` | string | `BAAI/bge-base-en-v1.5` | Embedding model for RAG; BGE gives best retrieval quality. Use `sentence-transformers/all-MiniLM-L6-v2` for a smaller/faster model. |
| `RAG_EMBEDDING_DEVICE` | string | `cpu` | Device for embedding model (e.g. `cpu`, `cuda`). |
| `RAG_ALLOWED_EXTENSIONS` | string | `md,txt,pdf` | Comma-separated file extensions (without leading dot) for RAG documents. |
| `RAG_NAIVE_CHUNK_MAX_CHARS` | int | `0` | Max characters per chunk in naive keyword fallback; `0` = use `RAG_CHUNK_SIZE * 2`. |

---

## 4. Paths (hardcoded in config)

Configured in `app/config.py` (not overridable via env in the current version):

- **Log directory:** `BASE_DIR / "logs"` — created at import; reserved for future logging.
- **Memory directory:** `BASE_DIR / "memory"` — holds `conversations.jsonl` and agent-written `*.md` notes.
- **RAG docs directory:** `BASE_DIR / "memory" / "docs"` — place `.md`, `.txt`, or `.pdf` files here for local RAG. The UI can attach files (saved here) and list documents/folders for selection. RAG runs only when the user attaches a file or selects documents/folders for that run; no global index is used in the UI flow (scoped in-memory index per run).

`BASE_DIR` is the parent of the `app/` package (the repository root).

---

## 5. RAG (opt-in per run)

In the **Web UI**, RAG is used only when the user, before sending a message, does at least one of:

- **Attach document(s):** Upload one or more `.md`, `.txt`, or `.pdf` files; they are saved to `memory/docs/` and used as the RAG scope for that run.
- **Select documents:** Choose one or more files from the “Select documents from memory/docs/” multiselect (includes files in subfolders).
- **Select folder(s):** Choose one or more folders (e.g. “(Root — all docs)” to use everything in `memory/docs/`); all documents inside are included in the scope.

If none of these are done, RAG is not used for that run and the `rag_search` tool returns a message asking the user to attach or select documents. The CLI does not pass `rag_scope`, so RAG is not used when running from the CLI unless you extend it to accept scope.

**RAG mode (Streamlit UI):**

- **Answer only from documents (offline):** When this checkbox is on, the agent may not use `web_fetch`; it answers strictly from the selected documents. Use for document-only Q&A without internet.
- **Off (default):** The agent can use both the selected documents and the internet (`web_fetch`) when answering.

**Anti-hallucination:** When RAG is used, the agent is instructed to base answers only on the retrieved chunks, to say when something is not in the document(s), and not to invent content.

---

## 6. Human-in-the-loop and self-critique

- **Human approval:** When enabled (default in the UI: “Approve all actions” unchecked), the supervisor will ask the user for explicit approval before using `code_exec`, `web_fetch`, or `write_note`. This is controlled by the UI checkbox and passed as `require_human_approval` to `run_supervisor()`; there is no env var for it.
- **Self-critique:** When “Allow self-critique summary” is checked in the UI (or `include_critique=True` in the CLI), the app runs a summarization step after each response and stores it; length is capped by `SUMMARIZE_CRITIQUE_MAX_WORDS`.

---

## 7. Reducing memory usage (Streamlit)

If the Streamlit UI uses too much RAM:

- **Chat history cap:** The UI keeps only the last 40 messages in session state (`MAX_CHAT_HISTORY_MESSAGES` in `app/ui.py`). Use **Clear conversation** in the sidebar to free memory during long sessions.
- **RAG:** Each run with RAG builds an in-memory FAISS index for the selected scope; it is cleared and garbage-collected after the run. To reduce peak RAM: attach or select fewer/smaller documents, or avoid using RAG when not needed.
- **Embeddings:** The RAG embedding model (default `BAAI/bge-base-en-v1.5`) is loaded once and kept in memory. Use `RAG_EMBEDDING_DEVICE=cpu` in `.env` to avoid GPU memory; for a smaller model set `RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2`.
- **Streamlit config:** `.streamlit/config.toml` sets `headless = true`, `fastReruns = true`, and a 200 MB upload limit to reduce overhead.

---

## 8. Example `.env` snippets

**OpenAI only:**

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.1
OPENAI_API_KEY=sk-...
```

**Ollama (local):**

```env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1
OLLAMA_NUM_CTX=4096
```

**Google Gemini:**

```env
LLM_PROVIDER=google
GOOGLE_MODEL=gemini-1.5-pro
GOOGLE_API_KEY=AIza...
```

**Stricter limits (optional):**

```env
RECURSION_LIMIT=25
CODE_EXEC_TIMEOUT=5
WEB_FETCH_MAX_CHARS=5000
MEMORY_RECENT_TURNS=4
```

---

## 9. Where configuration is read

- **`app/config.py`:** Loads `.env` once at import; defines `LLMConfig` and `AppConfig` dataclasses and the singleton `config`. All other modules use `from .config import config` (or `from app.config import config`).
- **Streamlit UI:** Reads provider, model, temperature, and API keys from the sidebar and passes them to `run_supervisor()`; these override the defaults derived from `.env` for that session only.
- **CLI:** Uses only `.env` (via `config`) and does not accept API keys on the command line.

For a concise table of all variables, see the [Configuration](#configuration) section in the main [README](../README.md).
