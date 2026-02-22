# Helio Supervisor — Architecture

This document describes the high-level design, data flow, and main components of the Helio Supervisor application.

---

## 1. Overview

Helio Supervisor is a **hierarchical agent** that uses a single LLM with tools to accomplish user goals. The agent (supervisor) decides which tools to call and in what order; it can plan, fetch web content, run Python code, write notes to disk, and summarize text. Optional **human-in-the-loop** approval and **self-critique** summaries are supported.

**Stack:**

- **LangChain 1.2** and **LangGraph** for the agent (e.g. `create_agent` with tools and system prompt).
- **Streamlit** for the web UI; **Rich** for the CLI.
- **Pydantic** for tool input schemas; **python-dotenv** for configuration.

---

## 2. Module roles

| Module | Role |
|--------|------|
| **config.py** | Loads `.env`, exposes `AppConfig` and `LLMConfig` (paths, limits, API key properties). Creates `logs/` and `memory/` at import. |
| **types.py** | Pydantic models for tool arguments: `PlanTaskInput`, `WebFetchInput`, `CodeExecInput`, `NoteInput`, `SummarizeInput`. |
| **llm.py** | Builds the chat LLM by provider (OpenAI, Ollama, Google, Perplexity). Supports UI-supplied API keys via a context variable; when set, env keys are not used. |
| **memory.py** | `MemoryStore`: appends conversation turns to `memory/conversations.jsonl` and loads recent turns for context. |
| **tools.py** | LangChain `@tool` implementations: `plan_tasks`, `web_fetch`, `code_exec`, `write_note`, `summarize_text`. All use `get_base_llm()` so they respect the current provider and API keys. |
| **supervisor.py** | Builds the supervisor system prompt and tool list; creates the agent graph with `create_agent()`; implements `run_supervisor()` (history loading, invoke, memory append, optional self-critique). |
| **ui.py** | Streamlit app: sidebar (provider, model, temperature, API keys, approval/critique toggles), chat input, and chat history with custom styling. |
| **cli.py** | Rich-based loop: prompt user, call `run_supervisor()`, print tools used and Markdown output; “exit”/“quit” to stop. |

---

## 3. Data flow

1. **User input** is submitted via the Streamlit UI or the CLI.
2. **UI or CLI** calls `run_supervisor(user_input, chat_history=..., api_keys=..., include_critique=..., require_human_approval=...)`.
3. **run_supervisor** (in `supervisor.py`):
   - Optionally sets a context variable for API keys and temporarily removes API key env vars so tools use only the provided keys.
   - Loads recent turns from `memory_store` (from `conversations.jsonl`) and merges with any in-memory `chat_history` (e.g. from the UI).
   - Appends the new user message to the message list.
   - Builds the agent graph with `create_supervisor_graph(...)` (LLM + tools + system prompt).
   - Invokes the graph with `graph.invoke({"messages": history_msgs}, config={"recursion_limit": ...})`.
   - Extracts the last AI message as the response and the list of tools used.
   - Appends the user turn and assistant turn to `memory_store`.
   - If `include_critique` is True, runs `summarize_text_tool` on the request + answer and appends the critique to memory; adds it to the returned dict.
   - Restores env vars and returns `{output, tools_used, self_critique?}`.
4. **Agent execution:** The LLM receives the message history and can call tools. When human approval is required, the agent is instructed to ask the user before using `code_exec`, `web_fetch`, or `write_note`; the actual “approve/deny” step is conversational (user replies in chat).
5. **Tools** use `get_base_llm()` (so they see the same provider/keys as the supervisor), read timeouts/limits from `config`, and write notes to `config.memory_dir`.
6. **UI** appends the assistant reply (and optional critique) to `st.session_state.chat_history` and re-renders. **CLI** prints the reply and optional critique, then appends to a local `chat_history` list for the next turn (CLI does not persist history to disk between restarts; persistence is via `memory_store` in `run_supervisor`).

---

## 4. Persistence

- **Conversations:** Every user and assistant message (and optional self-critique block) is appended to `memory/conversations.jsonl` as one JSON object per line (role, content, timestamp).
- **Notes:** The `write_note` tool writes files to `memory/<safe_title>.md`.
- **Logs:** The `logs/` directory is created by config; no application code currently writes log files there (reserved for future use).

---

## 5. Agent and tools

The supervisor is a single **LangChain 1.2 agent** (created with `create_agent`) that has:

- A **system prompt** (from `get_supervisor_system_prompt(require_human_approval)`): describes the role, tool use, and whether to ask for approval before risky actions.
- **Tools** from `get_supervisor_tools()`: `plan_tasks_tool`, `web_fetch_tool`, `code_exec_tool`, `write_note_tool`, `summarize_text_tool`.

The same LLM instance (from `get_base_llm()`) is used for the agent and for tool-internal LLM calls (e.g. `plan_tasks`, `summarize_text`), so provider and API keys stay consistent.

---

## 6. API keys and context

When the UI (or any caller) passes `api_keys` to `run_supervisor()`:

1. The keys are stored in a **context variable** (`_api_keys_ctx` in `llm.py`).
2. The env vars `OPENAI_API_KEY`, `GOOGLE_API_KEY`, and `PERPLEXITY_API_KEY` are **temporarily removed** from `os.environ` for the duration of the run.
3. `get_base_llm()` (used by the agent and by tools) reads keys from the context when present, so all LLM calls use the UI-supplied keys and never fall back to `.env` during that run.
4. After the run, the original env vars are restored.

This keeps UI sessions isolated from `.env` when the user enters keys in the sidebar.

---

## 7. Entry points

| Entry | Command | Notes |
|-------|---------|--------|
| **Web UI** | `streamlit run app/ui.py` | Run from repo root. UI adds root to `sys.path` when run as script. |
| **CLI** | `python -m app.cli` | Run from repo root. Uses `.env` only. |

There is no `pyproject.toml` or console script entry points; the app is intended to be run from the repository root with the above commands.

---

## 8. Dependencies (conceptual)

```
ui.py / cli.py
    → supervisor.run_supervisor()
        → supervisor.create_supervisor_graph()
            → llm.get_base_llm(), tools.get_supervisor_tools()
        → memory_store.load_recent(), memory_store.append()
        → tools.summarize_text_tool (if include_critique)
    → config.config
tools.py
    → llm.get_base_llm(), config, types
llm.py
    → config
memory.py
    → config
supervisor.py
    → config, llm, tools, types, memory
```

All modules that need configuration or the LLM depend on `config` and/or `llm`; tools and supervisor are the central orchestration layer.
