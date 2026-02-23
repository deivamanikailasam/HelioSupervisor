# Helio Supervisor — Setup Guide

This guide covers environment setup, dependency installation, provider configuration, and troubleshooting.

---

## 1. Requirements

- **Python 3.10 or newer**
- **pip** and (recommended) a **virtual environment**

### Provider-specific

| Provider   | Requirement |
|-----------|-------------|
| **Ollama** | [Ollama](https://ollama.ai) installed and running (e.g. `ollama serve`); at least one model pulled (e.g. `ollama pull llama3.1`) |
| **OpenAI** | `OPENAI_API_KEY` in `.env` or in the Streamlit sidebar |
| **Google**  | `GOOGLE_API_KEY` in `.env` or in the sidebar; package `langchain-google-genai` (included in `requirements.txt`) |
| **Perplexity** | `PERPLEXITY_API_KEY` in `.env` or in the sidebar |

---

## 2. Virtual environment (recommended)

```bash
cd HelioSupervisor
python -m venv .venv
```

**Activate:**

- **Windows (PowerShell):** `.\.venv\Scripts\Activate.ps1`
- **Windows (cmd):** `.venv\Scripts\activate.bat`
- **macOS/Linux:** `source .venv/bin/activate`

---

## 3. Install dependencies

From the project root (with the venv active):

```bash
pip install -r requirements.txt
```

This installs the LangChain 1.2 stack, Streamlit, Rich, `langchain-google-genai`, and supporting packages.

**RAG (local documents):** For the `rag_search` tool, the stack includes `faiss-cpu`, `sentence-transformers`, `pypdf`, and `langchain-text-splitters`. In the **Web UI**, RAG is opt-in per run: before sending a message, attach a document (saved to `memory/docs/`), and/or select documents or folders from the “RAG for this run” expander. If you do none of these, RAG is not used for that run. When scope is set, a scoped in-memory index is built from the selected paths. You can also add `.md`, `.txt`, or `.pdf` files directly under `memory/docs/` (including subfolders) and select them in the UI. If RAG dependencies are missing, the tool falls back to simple keyword matching over the selected docs.

### Clean reinstall (PowerShell)

To purge the pip cache and reinstall from `requirements.txt`:

```powershell
.\scripts\reinstall.ps1
```

---

## 4. Environment file

Create `.env` from the example (do not commit `.env`):

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

Edit `.env` and set at least:

- `LLM_PROVIDER` — one of `openai`, `ollama`, `google`, `perplexity`
- `LLM_MODEL` — e.g. `gpt-4o-mini`, `llama3.1`
- For cloud providers: the corresponding API key variable (see [CONFIGURATION.md](CONFIGURATION.md)).

---

## 5. Run the application

### Web UI (Streamlit)

```bash
streamlit run app/ui.py
```

Or from repo root so the `app` package resolves correctly:

```bash
python -m streamlit run app/ui.py
```

The UI opens in the browser (default: http://localhost:8501). Use the sidebar to choose provider, model, temperature, and (optionally) API keys.

### CLI

```bash
python -m app.cli
```

Ensure you run from the **project root** so that `app` is importable. The CLI uses `.env` for provider and API keys; there is no UI for keys in the CLI.

---

## 6. Verifying providers

- **Ollama:** `curl http://localhost:11434/api/tags` should return a list of models. The Streamlit UI also fetches this list for the model dropdown.
- **OpenAI:** Set `OPENAI_API_KEY` and choose provider “OpenAI” and a model (e.g. `gpt-4o-mini`). Send a simple message in the UI or CLI.
- **Google:** Set `GOOGLE_API_KEY`, choose provider “Google” and a model (e.g. `gemini-1.5-pro`). Send a message.
- **Perplexity:** Set `PERPLEXITY_API_KEY`, choose provider “Perplexity” and a model. Send a message.

---

## 7. Troubleshooting

### Import errors when running `app/ui.py` or `app/cli.py`

- Run from the **repository root** (the directory that contains `app/` and `requirements.txt`).
- Use `python -m app.cli` or `streamlit run app/ui.py` so the `app` package is on the path.

### SSL / certificate errors (e.g. on Windows)

The app sets `SSL_CERT_FILE` and `REQUESTS_CA_BUNDLE` to `certifi.where()` so HTTPS (e.g. `web_fetch`) uses the certifi bundle. If you still see certificate errors, check that `certifi` is installed and that no other env vars override these.

### Ollama “connection refused”

- Start Ollama: run `ollama serve` or start the Ollama app.
- Ensure nothing else is using port 11434.

### Google provider: “No module named 'langchain_google_genai'”

Install the Google GenAI integration:

```bash
pip install langchain-google-genai
```

It is already listed in `requirements.txt`; if you use a minimal install, add it explicitly.

### CLI: “No module named 'rich'”

Install Rich (used for terminal formatting):

```bash
pip install rich
```

It is included in `requirements.txt`.

### Empty or wrong model list in Streamlit for Ollama

The UI calls `http://localhost:11434/api/tags`. If Ollama is not running or is unreachable, the dropdown falls back to a default list. Start Ollama and refresh the page.

---

## 8. Next steps

- [CONFIGURATION.md](CONFIGURATION.md) — All environment variables and behaviour options.
- [ARCHITECTURE.md](ARCHITECTURE.md) — How the supervisor, tools, and memory fit together.
