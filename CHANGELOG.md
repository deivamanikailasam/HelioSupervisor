# Changelog

All notable changes to Helio Supervisor are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2025-02-23

### Added

- **RAG mode toggle (Streamlit):** In the "RAG for this run" expander, checkbox **"Answer only from documents (offline)"**. When on, the agent may not use `web_fetch` and answers strictly from the selected documents; when off, the agent can use both documents and the internet.
- **RAG anti-hallucination:** When RAG is used, the agent is instructed to base answers only on retrieved chunks, to say when something is not in the document(s), and not to invent content.
- **Best-in-class RAG embeddings:** Default embedding model is now `BAAI/bge-base-en-v1.5` (BGE); uses `HuggingFaceBgeEmbeddings` when the model name contains `bge`. Override via `RAG_EMBEDDING_MODEL` in `.env`.
- **PDF extraction fallback:** PDF text extraction tries **pypdf** first, then **PyMuPDF** (`pymupdf`) when pypdf fails or returns empty text (e.g. many web/Medium PDFs). Added `pymupdf>=1.24.0` to `requirements.txt`.
- **Streamlit config:** `.streamlit/config.toml` for lower memory use (headless, fastReruns, 200 MB upload limit).
- **Chat history cap:** In-session chat history limited to the last 40 messages (`MAX_CHAT_HISTORY_MESSAGES`) to control Streamlit RAM; "Clear conversation" resets it.
- **RAG fallback when no similar chunks:** For generic queries (e.g. "summarize", "what is this about?"), if similarity or keyword search returns no chunks, the search now returns the first chunks from the document so the agent has content to summarize.
- **Clearer RAG tool message:** When selected document(s) yield no text (e.g. image-only PDF), the tool returns a helpful message suggesting text-based PDF, pymupdf, or .txt/.md.
- **This changelog** and version documentation.

### Changed

- **RAG_EMBEDDING_MODEL** default is `BAAI/bge-base-en-v1.5` (was `sentence-transformers/all-MiniLM-L6-v2`). Set in `.env` and `.env.example`.
- **Supervisor system prompt** is built with `rag_scope` and `rag_documents_only`: when RAG is used, anti-hallucination and (optionally) documents-only instructions are added; when documents-only is on, `web_fetch` is omitted from the tool list.
- **create_supervisor_graph** and **run_supervisor** accept `rag_scope` and `rag_documents_only`; tools list is restricted when RAG documents-only is enabled.
- **CONFIGURATION.md:** RAG mode, anti-hallucination, and "Reducing memory usage" section updated; default embedding and RAG_EMBEDDING_MODEL documented.

### Fixed

- **RAG not used when documents selected:** Added explicit hint in the user message when `rag_scope` is set so the agent uses `rag_search`; made `set_rag_scope` defensive (empty scope, try/except with warning) so scope is set correctly.
- **Tools used not shown in UI:** Tools-used line is always shown for assistant messages (shows "(none)" when no tools used); improved extraction of tool names from messages (`_tool_name_from_tool_call` supports both `name` and `tool` keys).
- **"No relevant chunks" for summarize/overview:** When semantic or keyword search returns no chunks, RAG now returns the first N chunks from the document so the agent can summarize.
- **PDFs not yielding text:** Two-stage extraction (pypdf then pymupdf) so more PDFs produce text for RAG.
- **Streamlit high RAM:** Chat history cap, `gc.collect()` after clearing RAG scope, and `.streamlit/config.toml` to reduce memory use.

---

## [1.0.0] - Initial release

### Features

- Multi-provider LLM support (OpenAI, Ollama, Google, Perplexity).
- Six tools: `plan_tasks`, `web_fetch`, `code_exec`, `write_note`, `summarize_text`, `rag_search`.
- Optional RAG over `memory/docs/` (attach/select documents or folders in UI; scoped in-memory FAISS index per run).
- Optional human-in-the-loop approval and self-critique.
- Streamlit web UI and Rich CLI.
- Persistent conversation memory and agent-written notes.

---

[1.1.0]: https://github.com/your-org/HelioSupervisor/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/your-org/HelioSupervisor/releases/tag/v1.0.0

*(Replace `your-org/HelioSupervisor` with your repo URL when publishing.)*
