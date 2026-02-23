# app/config.py
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env once at startup
load_dotenv(BASE_DIR / ".env")


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


@dataclass
class LLMConfig:
    provider: str = field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "openai").lower()
    )
    model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))
    temperature: float = field(
        default_factory=lambda: _env_float("LLM_TEMPERATURE", 0.1)
    )
    max_tokens: int = field(default_factory=lambda: _env_int("MAX_TOKENS", 8192))
    num_ctx: int = field(default_factory=lambda: _env_int("OLLAMA_NUM_CTX", 4096))


@dataclass
class AppConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    enable_human_approval: bool = True
    log_dir: Path = BASE_DIR / "logs"
    memory_dir: Path = BASE_DIR / "memory"
    recursion_limit: int = field(default_factory=lambda: _env_int("RECURSION_LIMIT", 50))
    summarize_max_words: int = field(default_factory=lambda: _env_int("SUMMARIZE_MAX_WORDS", 2000))
    summarize_critique_max_words: int = field(
        default_factory=lambda: _env_int("SUMMARIZE_CRITIQUE_MAX_WORDS", 2000)
    )
    plan_max_steps: int = field(default_factory=lambda: _env_int("PLAN_MAX_STEPS", 10))
    web_fetch_max_chars: int = field(default_factory=lambda: _env_int("WEB_FETCH_MAX_CHARS", 8000))
    web_fetch_timeout: float = field(
        default_factory=lambda: _env_float("WEB_FETCH_TIMEOUT", 10.0)
    )
    code_exec_timeout: int = field(default_factory=lambda: _env_int("CODE_EXEC_TIMEOUT", 10))
    memory_recent_turns: int = field(
        default_factory=lambda: _env_int("MEMORY_RECENT_TURNS", 6)
    )
    # RAG: local documents and index paths, limits, embedding (all from .env)
    _rag_docs_subdir: str = field(default_factory=lambda: os.getenv("RAG_DOCS_DIR", "memory/docs"))
    _rag_index_subdir: str = field(default_factory=lambda: os.getenv("RAG_INDEX_DIR", "memory/rag_faiss"))

    @property
    def docs_dir(self) -> Path:
        return BASE_DIR / self._rag_docs_subdir

    @property
    def rag_index_dir(self) -> Path:
        return BASE_DIR / self._rag_index_subdir

    rag_chunk_size: int = field(default_factory=lambda: _env_int("RAG_CHUNK_SIZE", 800))
    rag_chunk_overlap: int = field(default_factory=lambda: _env_int("RAG_CHUNK_OVERLAP", 100))
    rag_top_k: int = field(default_factory=lambda: _env_int("RAG_TOP_K", 5))
    rag_embedding_model: str = field(
        default_factory=lambda: os.getenv("RAG_EMBEDDING_MODEL", "BAAI/bge-base-en-v1.5")
    )
    rag_embedding_device: str = field(
        default_factory=lambda: os.getenv("RAG_EMBEDDING_DEVICE", "cpu")
    )
    rag_allowed_extensions: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            f".{x.strip().lstrip('.')}" for x in os.getenv("RAG_ALLOWED_EXTENSIONS", "md,txt,pdf").split(",") if x.strip()
        ) or (".md", ".txt", ".pdf")
    )
    rag_naive_chunk_max_chars: int = field(
        default_factory=lambda: _env_int("RAG_NAIVE_CHUNK_MAX_CHARS", 0)
    )  # 0 = use rag_chunk_size * 2

    @property
    def openai_api_key(self) -> str | None:
        return os.getenv("OPENAI_API_KEY") or None

    @property
    def google_api_key(self) -> str | None:
        return os.getenv("GOOGLE_API_KEY") or None

    @property
    def perplexity_api_key(self) -> str | None:
        return os.getenv("PERPLEXITY_API_KEY") or None

    @property
    def google_model(self) -> str:
        return os.getenv("GOOGLE_MODEL", "gemini-1.5-pro")

    @property
    def perplexity_model(self) -> str:
        return os.getenv("PERPLEXITY_MODEL", "llama-3.1-sonar-small-128k-online")

config = AppConfig()
config.log_dir.mkdir(parents=True, exist_ok=True)
config.memory_dir.mkdir(parents=True, exist_ok=True)
