# app/llm.py
import contextvars
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
from .config import config

ProviderType = Literal["ollama", "openai", "google", "perplexity"]

# API keys from UI (set by run_supervisor so tools use the same keys)
_api_keys_ctx: contextvars.ContextVar[dict | None] = contextvars.ContextVar("api_keys", default=None)


def get_base_llm(
    provider: ProviderType | None = None,
    model: str | None = None,
    api_keys: dict | None = None,
) -> BaseChatModel:
    """
    Return a chat LLM according to provider. API keys come from api_keys dict
    (or from context if not passed); .env is not used for keys.
    """
    provider = (provider or config.llm.provider).lower()
    if model is None:
        model = _model_for_provider(provider)
    keys = api_keys if api_keys is not None else _api_keys_ctx.get()
    use_ui_keys = keys is not None  # UI or run_supervisor set context
    keys = keys or {}

    def _key(name: str) -> str | None:
        v = keys.get(name)
        return (v or None) if (v and str(v).strip()) else None

    def _openai_key() -> str | None:
        if use_ui_keys:
            k = _key("openai")
            return k if k else "__UI_NO_KEY__"  # prevent .env fallback
        return config.openai_api_key

    def _google_key() -> str:
        if use_ui_keys:
            k = _key("google")
            return k if k else "__UI_NO_KEY__"
        return config.google_api_key or ""

    def _perplexity_key() -> str:
        if use_ui_keys:
            k = _key("perplexity")
            return k if k else "__UI_NO_KEY__"
        return config.perplexity_api_key or ""

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        kwargs = {
            "model": model,
            "temperature": config.llm.temperature,
            "max_tokens": config.llm.max_tokens,
        }
        key = _openai_key()
        if key and key != "__UI_NO_KEY__":
            kwargs["api_key"] = key
        elif key == "__UI_NO_KEY__":
            kwargs["api_key"] = key  # force no .env
        return ChatOpenAI(**kwargs)

    if provider == "ollama":
        from langchain_community.chat_models import ChatOllama

        return ChatOllama(
            model=model,
            temperature=config.llm.temperature,
            num_ctx=config.llm.num_ctx,
        )
    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=config.llm.temperature,
            google_api_key=_google_key(),
        )
    if provider == "perplexity":
        from langchain_community.chat_models import ChatPerplexity
        return ChatPerplexity(
            model=model,
            temperature=config.llm.temperature,
            perplexity_api_key=_perplexity_key(),
        )

    raise ValueError(f"Unsupported provider: {provider}")


def _model_for_provider(provider: str) -> str:
    """Return the default model name for the given provider from config."""
    if provider == "google":
        return config.google_model
    if provider == "perplexity":
        return config.perplexity_model
    return config.llm.model

def simple_chat(query: str, system_prompt: str | None = None) -> str:
    llm = get_base_llm()
    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=query))
    resp = llm.invoke(messages)
    return resp.content
