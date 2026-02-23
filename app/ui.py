# app/ui.py
from __future__ import annotations
import sys
from pathlib import Path
from typing import List, Dict, Any

# Allow running as script: streamlit run app/ui.py or python app/ui.py
if __name__ == "__main__" or __package__ is None:
    _root = Path(__file__).resolve().parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import streamlit as st

try:
    from . import __version__
    from .supervisor import run_supervisor
    from .config import config
    from . import rag
except ImportError:
    from app import __version__
    from app.supervisor import run_supervisor
    from app.config import config
    from app import rag

# Limit in-session chat history to control RAM (Streamlit holds full list in session state)
MAX_CHAT_HISTORY_MESSAGES = 40

# Provider and model options (defaults from .env)
PROVIDERS = ["ollama", "openai", "google", "perplexity"]

OPENAI_MODELS = [
    "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo",
    "o1", "o1-mini",
]
GOOGLE_MODELS = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.0-pro"]
PERPLEXITY_MODELS = [
    "llama-3.1-sonar-small-128k-online",
    "llama-3.1-sonar-large-128k-online",
    "sonar",
    "sonar-pro",
]


def _default_provider() -> str:
    p = (config.llm.provider or "openai").lower()
    return p if p in PROVIDERS else "openai"


def _default_model_for_provider(provider: str) -> str:
    """Default model for this provider; use .env only when it matches the provider."""
    if provider == "google":
        return config.google_model or "gemini-1.5-pro"
    if provider == "perplexity":
        return config.perplexity_model or PERPLEXITY_MODELS[0]
    if provider == "ollama":
        return config.llm.model if _default_provider() == "ollama" else "llama3.1"
    # openai
    return config.llm.model if _default_provider() == "openai" else "gpt-4o-mini"


def _ollama_models() -> List[str]:
    """Return list of Ollama model names from local API, with fallback."""
    try:
        import httpx
        r = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        r.raise_for_status()
        data = r.json()
        names = [m.get("name", "").split(":")[0] for m in data.get("models", []) if m.get("name")]
        return sorted(set(names)) if names else _ollama_models_fallback()
    except Exception:
        return _ollama_models_fallback()


def _ollama_models_fallback() -> List[str]:
    default = config.llm.model or "llama3.1"
    extra = ["llama3.1", "llama3.2", "llama3.2-vision", "codellama", "mistral", "phi", "qwen2"]
    if default not in extra:
        return [default] + extra
    return extra


def _models_for_provider(provider: str) -> List[str]:
    if provider == "ollama":
        return _ollama_models()
    if provider == "openai":
        return OPENAI_MODELS
    if provider == "google":
        return GOOGLE_MODELS
    if provider == "perplexity":
        return PERPLEXITY_MODELS
    return []

st.set_page_config(
    page_title="Helio Supervisor",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom chat layout: avatar + bubble via columns (marker class for CSS targeting)
HELIO_AVATAR_USER = "👤"
HELIO_AVATAR_ASSISTANT = "🤖"


def _render_chat_row(role: str, content: str, tools_used: list | None = None, self_critique: str | None = None, show_critique: bool = True) -> None:
    """Render one chat message as avatar column + bubble column."""
    avatar = HELIO_AVATAR_USER if role == "user" else HELIO_AVATAR_ASSISTANT
    col_avatar, col_msg = st.columns([0.6, 9.4])
    with col_avatar:
        st.markdown(f'<div class="helio-avatar-wrap"><span class="helio-avatar">{avatar}</span><span class="helio-chat-avatar-col" aria-hidden="true"></span></div>', unsafe_allow_html=True)
    with col_msg:
        st.markdown('<div class="helio-bubble">', unsafe_allow_html=True)
        st.markdown(content)
        if role == "assistant":
            tools_label = ", ".join(tools_used) if tools_used else "(none)"
            st.caption(f"Tools used: {tools_label}")
        if role == "assistant" and show_critique and self_critique:
            with st.expander("Self-critique / summary"):
                st.markdown(self_critique)
        st.markdown("</div>", unsafe_allow_html=True)


# Custom styles: custom chat rows (avatar column + bubble column)
st.markdown("""
<style>
    /* Main container */
    .main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 900px; }

    /* Marker for targeting (hidden) */
    .helio-chat-avatar-col { display: none !important; }

    /* Avatar column: fixed width, top-aligned with bubble */
    [data-testid="column"]:has(.helio-chat-avatar-col) {
        min-width: 2.5rem !important;
        max-width: 2.5rem !important;
        padding: 0 !important;
        vertical-align: top;
    }
    .helio-avatar-wrap {
        display: flex;
        align-items: flex-start;
        justify-content: flex-start;
        padding-top: 0.6rem;
        line-height: 1.2;
    }
    .helio-avatar {
        font-size: 1.75rem;
        width: 2.25rem;
        height: 2.25rem;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        border-radius: 10px;
        background: var(--background-secondary, rgba(128,128,128,0.15));
        border: 1px solid var(--default-border-color, rgba(0,0,0,0.08));
    }

    /* Bubble column: message content */
    [data-testid="column"]:has(.helio-chat-avatar-col) + [data-testid="column"] {
        padding: 1rem 1.2rem !important;
        border-radius: 14px;
        background-color: var(--background-secondary, rgba(0,0,0,0.04));
        border: 1px solid var(--default-border-color, rgba(0,0,0,0.08));
        margin-bottom: 1rem;
    }
    [data-testid="column"]:has(.helio-chat-avatar-col) + [data-testid="column"] p {
        margin: 0 0 0.5em 0;
    }
    [data-testid="column"]:has(.helio-chat-avatar-col) + [data-testid="column"] p:last-child {
        margin-bottom: 0;
    }
    [data-testid="column"]:has(.helio-chat-avatar-col) + [data-testid="column"] [data-testid="stCaptionContainer"] {
        margin-top: 0.5rem;
        padding-top: 0.35rem;
        border-top: 1px solid var(--default-border-color, rgba(0,0,0,0.06));
    }
    [data-testid="column"]:has(.helio-chat-avatar-col) + [data-testid="column"] [data-testid="stExpander"] {
        margin-top: 0.6rem;
    }
    [data-testid="column"]:has(.helio-chat-avatar-col) + [data-testid="column"] [data-testid="stExpander"] details {
        border-radius: 10px;
        border: 1px solid var(--default-border-color, rgba(0,0,0,0.08));
        padding: 0.4rem 0.6rem;
    }

    /* Sidebar */
    .sidebar .stCheckbox { margin-bottom: 0.5rem; }
    .sidebar .stSlider { margin-top: 0.25rem; }

    /* Headers */
    h1 { font-size: 1.6rem; margin-bottom: 0.25rem; }
    .app-caption { color: var(--text-color-secondary, #666); font-size: 0.9rem; margin-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)

if "chat_history" not in st.session_state:
    st.session_state.chat_history: List[Dict[str, Any]] = []
if "rag_attached_paths" not in st.session_state:
    st.session_state.rag_attached_paths: List[str] = []
if "rag_selected_docs" not in st.session_state:
    st.session_state.rag_selected_docs: List[str] = []
if "rag_selected_folders" not in st.session_state:
    st.session_state.rag_selected_folders: List[str] = []
if "rag_saved_upload_names" not in st.session_state:
    st.session_state.rag_saved_upload_names: set[str] = set()

# ----- Sidebar: settings and global toggles -----
with st.sidebar:
    st.subheader("Model")
    provider_options = PROVIDERS
    default_provider = _default_provider()
    provider_index = provider_options.index(default_provider) if default_provider in provider_options else 0
    selected_provider = st.selectbox(
        "Provider",
        options=provider_options,
        index=provider_index,
        format_func=lambda x: x.capitalize(),
        help="LLM provider (default from .env: LLM_PROVIDER).",
    )
    model_options = _models_for_provider(selected_provider)
    default_model = _default_model_for_provider(selected_provider)
    if not model_options:
        model_options = [default_model]
    if default_model not in model_options:
        model_options = [default_model] + [m for m in model_options if m != default_model]
    model_index = model_options.index(default_model) if default_model in model_options else 0
    selected_model = st.selectbox(
        "Model",
        options=model_options,
        index=model_index,
        help="Model for this provider (default from .env: LLM_MODEL / GOOGLE_MODEL / PERPLEXITY_MODEL).",
    )
    temperature = st.slider(
        "Temperature",
        0.0,
        1.0,
        float(config.llm.temperature) if getattr(config.llm, "temperature", None) is not None else 0.2,
        0.05,
    )

    st.divider()
    st.subheader("API keys")
    st.caption("Used instead of .env. Leave empty for Ollama.")
    api_key_openai = st.text_input(
        "OpenAI",
        type="password",
        placeholder="sk-...",
        key="api_key_openai",
        help="Required when provider is OpenAI.",
    )
    api_key_google = st.text_input(
        "Google",
        type="password",
        placeholder="AIza...",
        key="api_key_google",
        help="Required when provider is Google.",
    )
    api_key_perplexity = st.text_input(
        "Perplexity",
        type="password",
        placeholder="pplx-...",
        key="api_key_perplexity",
        help="Required when provider is Perplexity.",
    )
    api_keys = {
        "openai": (api_key_openai or "").strip() or None,
        "google": (api_key_google or "").strip() or None,
        "perplexity": (api_key_perplexity or "").strip() or None,
    }

    st.divider()
    st.subheader("Behaviour")
    # Global toggle: always include self-critique when enabled (no per-turn prompt)
    allow_self_critique = st.checkbox(
        "Allow self-critique summary",
        value=False,
        help="After each response, generate a short self-critique/summary. When off, no critique is requested.",
    )
    # Toggle: approve all actions by default vs require user approval
    approve_all_actions = st.checkbox(
        "Approve all actions by default",
        value=False,
        help="When on, the agent will not ask for confirmation before running code_exec, write_note, or web_fetch. When off, it will ask for your approval.",
    )
    # Whether to show the critique in the UI when present
    show_hitl_hints = st.checkbox(
        "Show self-critique / guidance in chat",
        value=True,
        help="When a self-critique is available, show it in an expander below the response.",
    )

    st.divider()
    st.caption("Tools: plan_tasks, web_fetch, code_exec, write_note, summarize_text, rag_search")
    st.caption("RAG runs only when you attach a file or select docs/folders in the chat area.")
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

    st.divider()
    st.caption(f"Helio Supervisor **v{__version__}**")

# ----- Main area -----
st.title("Helio Supervisor")
st.markdown(
    f'<p class="app-caption">Local hierarchical supervisor ({selected_provider.capitalize()}). Plan, fetch, run code, write notes — with optional self-critique and human-in-the-loop.</p>',
    unsafe_allow_html=True,
)

# ----- RAG: attach docs, select docs/folders (opt-in per run) -----
with st.expander("RAG for this run — attach or select documents", expanded=False):
    st.caption("If you do none of these, RAG will not be used. Attached files are saved to memory/docs/.")
    rag_documents_only = st.checkbox(
        "Answer only from documents (offline)",
        value=False,
        key="rag_documents_only",
        help="When on: agent uses only the selected documents (no web_fetch). When off: agent can use internet + documents.",
    )
    uploaded = st.file_uploader(
        "Attach document (.md, .txt, .pdf)",
        type=["md", "txt", "pdf"],
        accept_multiple_files=True,
        key="rag_uploader",
        help="Uploaded files are saved to memory/docs/ and used only for this run.",
    )
    if uploaded:
        for f in uploaded:
            if f is not None and f.name and f.name not in st.session_state.rag_saved_upload_names:
                try:
                    rel = rag.save_uploaded_to_docs(f.getvalue(), f.name)
                    st.session_state.rag_saved_upload_names.add(f.name)
                    if rel not in st.session_state.rag_attached_paths:
                        st.session_state.rag_attached_paths.append(rel)
                except Exception as e:
                    st.warning(f"Could not save {f.name}: {e}")
        if st.session_state.rag_attached_paths:
            st.caption(f"Attached: {', '.join(st.session_state.rag_attached_paths)}")

    doc_folders = rag.list_docs_and_folders()
    file_options = [x["path"] for x in doc_folders["files"]]
    folder_options = [x["path"] for x in doc_folders["folders"]]

    if file_options:
        selected_docs = st.multiselect(
            "Select documents from memory/docs/",
            options=file_options,
            default=st.session_state.rag_selected_docs,
            key="rag_docs_select",
            help="RAG will search only these documents for this run.",
        )
        st.session_state.rag_selected_docs = selected_docs
    else:
        st.caption("No .md / .txt / .pdf files in memory/docs/ yet.")
        st.session_state.rag_selected_docs = []

    if folder_options:
        folder_display = {x["path"]: x["name"] for x in doc_folders["folders"]}
        selected_folders = st.multiselect(
            "Select folder(s) — use all docs inside",
            options=folder_options,
            default=st.session_state.rag_selected_folders,
            format_func=lambda p: folder_display.get(p, p),
            key="rag_folders_select",
            help="RAG will use every document inside the selected folders.",
        )
        st.session_state.rag_selected_folders = selected_folders
    else:
        st.session_state.rag_selected_folders = []

user_input = st.chat_input("Describe your goal or task...")

chat_container = st.container()
with chat_container:
    for msg in st.session_state.chat_history:
        _render_chat_row(
            role=msg["role"],
            content=msg["content"],
            tools_used=msg.get("tools_used"),
            self_critique=msg.get("self_critique"),
            show_critique=show_hitl_hints,
        )

if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    if len(st.session_state.chat_history) > MAX_CHAT_HISTORY_MESSAGES:
        st.session_state.chat_history = st.session_state.chat_history[-MAX_CHAT_HISTORY_MESSAGES:]
    _render_chat_row(role="user", content=user_input, tools_used=None, self_critique=None, show_critique=False)

    # RAG scope: attached + selected docs + all files in selected folders
    rag_scope: List[str] = list(st.session_state.rag_attached_paths)
    rag_scope.extend(st.session_state.rag_selected_docs)
    if st.session_state.rag_selected_folders:
        rag_scope.extend(rag.expand_rag_scope(st.session_state.rag_selected_folders))
    rag_scope = sorted(set(rag_scope)) if rag_scope else None
    if not rag_scope:
        rag_scope = None

    result = run_supervisor(
        user_input,
        chat_history=[
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.chat_history
        ],
        include_critique=allow_self_critique,
        require_human_approval=not approve_all_actions,
        llm_provider=selected_provider,
        llm_model=selected_model,
        api_keys=api_keys,
        rag_scope=rag_scope,
        rag_documents_only=rag_documents_only,
    )

    output = result["output"]
    tools_used = result.get("tools_used") or []
    critique = result.get("self_critique")

    assistant_entry: Dict[str, Any] = {
        "role": "assistant",
        "content": output,
        "tools_used": tools_used,
    }
    if critique:
        assistant_entry["self_critique"] = critique

    _render_chat_row(
        role="assistant",
        content=output,
        tools_used=tools_used,
        self_critique=critique,
        show_critique=show_hitl_hints,
    )
    st.session_state.chat_history.append(assistant_entry)
    if len(st.session_state.chat_history) > MAX_CHAT_HISTORY_MESSAGES:
        st.session_state.chat_history = st.session_state.chat_history[-MAX_CHAT_HISTORY_MESSAGES:]
    # Clear attached paths and saved names so next run doesn't reuse them unless user re-uploads or selects them
    st.session_state.rag_attached_paths = []
    st.session_state.rag_saved_upload_names = set()