# Helio Supervisor

A **local hierarchical supervisor agent** for goal-oriented workflows. It plans tasks, fetches web content, runs code snippets, writes notes, and summarizes text—with optional **human-in-the-loop** approval and **self-critique** summaries.

---

## Features

- **Multi-provider LLM support**: OpenAI, Ollama (local), Google (Gemini), Perplexity
- **Five built-in tools**: `plan_tasks`, `web_fetch`, `code_exec`, `write_note`, `summarize_text`
- **Optional human approval** for risky actions (code execution, web fetch, writing notes)
- **Optional self-critique**: short summary of the agent’s answer after each turn
- **Persistent conversation memory** (JSONL) and **notes** written to disk
- **Two interfaces**: Streamlit web UI and Rich-based CLI

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
│   ├── config.py      # Env-based config (paths, limits, API key props)
│   ├── types.py       # Pydantic schemas for tool inputs
│   ├── llm.py         # LLM factory (OpenAI, Ollama, Google, Perplexity)
│   ├── memory.py      # Conversation persistence (conversations.jsonl)
│   ├── tools.py       # LangChain tools (plan, fetch, code_exec, note, summarize)
│   ├── supervisor.py  # Supervisor agent graph and run_supervisor()
│   ├── ui.py          # Streamlit web UI
│   └── cli.py         # Rich CLI loop
├── memory/            # Runtime: conversations.jsonl + agent-written *.md notes
├── logs/              # Created at startup (for future use)
├── scripts/
│   └── reinstall.ps1  # Pip cache purge + reinstall from requirements.txt
├── docs/              # Detailed documentation
├── .env               # Local config (not committed; copy from .env.example)
├── .env.example       # Example env template
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

When **human approval** is enabled (default in UI: “Approve all actions” off), the agent will ask for confirmation before using `code_exec`, `web_fetch`, or `write_note`.

---

## Memory and data

- **Conversations**: Appended to `memory/conversations.jsonl` (role, content, timestamp).
- **Notes**: Created by the agent in `memory/*.md` via `write_note`.
- **Context**: The supervisor loads the last `MEMORY_RECENT_TURNS` turns from disk and merges with the current chat when using the UI.

---

## Scripts

- **`scripts/reinstall.ps1`** (PowerShell, run from repo root): purges pip cache and installs from `requirements.txt` with pinned versions.

---

## Documentation

- **[docs/SETUP.md](docs/SETUP.md)** — Detailed setup (venv, dependencies, providers, troubleshooting).
- **[docs/CONFIGURATION.md](docs/CONFIGURATION.md)** — All environment variables and behaviour options.
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — Data flow, modules, and design.

---

## License

See repository license file.
