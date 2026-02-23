# app/rag.py — Minimal RAG: local docs in memory/docs/, FAISS + HuggingFace embeddings, rag_search
from __future__ import annotations

import contextvars
import os
from pathlib import Path
from typing import Callable, List

from .config import config

# Lazy imports so RAG deps are optional until rag_search is used
_embeddings = None
_vector_store = None

# Per-run scope: when set, rag_search_tool uses this instead of global index. None = RAG not used this run.
_rag_search_fn_ctx: contextvars.ContextVar[Callable[[str, int], List[str]] | None] = contextvars.ContextVar(
    "rag_search_fn", default=None
)


def _get_docs_dir() -> Path:
    config.docs_dir.mkdir(parents=True, exist_ok=True)
    return config.docs_dir


def _load_document_text(path: Path) -> str | None:
    """Load a single file as plain text. Supports extensions from RAG_ALLOWED_EXTENSIONS (default .md, .txt, .pdf)."""
    try:
        if path.suffix.lower() not in config.rag_allowed_extensions:
            return None
        if path.suffix.lower() == ".pdf":
            text = _extract_pdf_text(path)
            return text.strip() or None
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def _extract_pdf_text(path: Path) -> str:
    """Extract text from a PDF; try pypdf first, then PyMuPDF if available (better for many PDFs)."""
    # 1) pypdf (already in requirements)
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        parts = []
        for p in reader.pages:
            t = p.extract_text()
            if t and t.strip():
                parts.append(t.strip())
        if parts:
            return "\n".join(parts)
    except Exception:
        pass
    # 2) PyMuPDF fallback (often extracts text when pypdf fails or returns empty)
    try:
        import pymupdf
        doc = pymupdf.open(path)
        try:
            parts = [page.get_text().strip() for page in doc if page.get_text().strip()]
            return "\n".join(parts) if parts else ""
        finally:
            doc.close()
    except ImportError:
        pass
    except Exception:
        pass
    return ""


def _load_documents_from_docs_dir() -> List[tuple[str, dict]]:
    """Load all .md, .txt, .pdf from config.docs_dir. Returns list of (page_content, metadata)."""
    docs_dir = _get_docs_dir()
    out: List[tuple[str, dict]] = []
    for path in sorted(docs_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in config.rag_allowed_extensions:
            continue
        text = _load_document_text(path)
        if not (text and text.strip()):
            continue
        rel = path.relative_to(docs_dir)
        out.append((text.strip(), {"source": str(rel).replace("\\", "/")}))
    return out


def _load_documents_from_paths(relative_paths: List[str]) -> List[tuple[str, dict]]:
    """Load only .md/.txt/.pdf at the given paths (relative to docs_dir). Paths use forward slashes."""
    docs_dir = _get_docs_dir()
    out: List[tuple[str, dict]] = []
    for rel_str in relative_paths:
        rel_str = rel_str.replace("\\", "/").strip()
        if not rel_str:
            continue
        path = docs_dir / rel_str
        if not path.exists():
            continue
        if path.is_file():
            if path.suffix.lower() not in config.rag_allowed_extensions:
                continue
            text = _load_document_text(path)
            if text and text.strip():
                out.append((text.strip(), {"source": rel_str}))
        else:
            for p in sorted(path.rglob("*")):
                if not p.is_file() or p.suffix.lower() not in config.rag_allowed_extensions:
                    continue
                text = _load_document_text(p)
                if text and text.strip():
                    rel = p.relative_to(docs_dir)
                    out.append((text.strip(), {"source": str(rel).replace("\\", "/")}))
    return out


def expand_rag_scope(paths: List[str]) -> List[str]:
    """Expand a list of paths (files and/or folders, relative to docs_dir) to a list of file paths. '.' = root (all docs)."""
    docs_dir = _get_docs_dir()
    out: List[str] = []
    for rel_str in paths:
        rel_str = rel_str.replace("\\", "/").strip()
        if rel_str in ("", "."):
            for p in docs_dir.rglob("*"):
                if p.is_file() and p.suffix.lower() in config.rag_allowed_extensions:
                    r = p.relative_to(docs_dir)
                    out.append(str(r).replace("\\", "/"))
            continue
        path = docs_dir / rel_str
        if not path.exists():
            continue
        if path.is_file() and path.suffix.lower() in config.rag_allowed_extensions:
            out.append(rel_str)
        elif path.is_dir():
            for p in path.rglob("*"):
                if p.is_file() and p.suffix.lower() in config.rag_allowed_extensions:
                    r = p.relative_to(docs_dir)
                    out.append(str(r).replace("\\", "/"))
    return sorted(set(out))


def list_docs_and_folders() -> dict:
    """List all documents and subfolders under memory/docs for UI dropdowns. Paths use forward slashes."""
    docs_dir = _get_docs_dir()
    files: List[dict] = []
    folders: List[dict] = [{"path": ".", "name": "(Root — all docs)"}]
    for path in sorted(docs_dir.rglob("*")):
        rel = path.relative_to(docs_dir)
        rel_str = str(rel).replace("\\", "/")
        if path.is_file() and path.suffix.lower() in config.rag_allowed_extensions:
            files.append({"path": rel_str, "name": rel_str})
        elif path.is_dir():
            folders.append({"path": rel_str, "name": rel_str + "/"})
    return {"files": files, "folders": folders}


def save_uploaded_to_docs(file_bytes: bytes, filename: str) -> str:
    """Save an uploaded file to memory/docs/. Returns relative path (forward slashes). Overwrites if same name."""
    docs_dir = _get_docs_dir()
    safe = "".join(c for c in filename if c.isalnum() or c in (".", "-", "_")).strip() or "uploaded"
    if not any(safe.lower().endswith(ext) for ext in config.rag_allowed_extensions):
        safe = safe + (".txt" if ".txt" in config.rag_allowed_extensions else config.rag_allowed_extensions[0])
    path = docs_dir / safe
    path.write_bytes(file_bytes)
    return str(path.relative_to(docs_dir)).replace("\\", "/")


def build_scoped_search(scope_file_paths: List[str]) -> Callable[[str, int], List[str]]:
    """Build an in-memory FAISS search over only the given file paths (relative to docs_dir). Returns (query, top_k) -> chunks."""
    if not scope_file_paths:
        def _empty(_q: str, _k: int) -> List[str]:
            return []
        return _empty

    raw = _load_documents_from_paths(scope_file_paths)
    if not raw:
        def _empty2(_q: str, _k: int) -> List[str]:
            return []
        return _empty2

    try:
        from langchain_community.vectorstores import FAISS
        from langchain_core.documents import Document

        docs = [Document(page_content=c, metadata=m) for c, m in raw]
        splitter = _get_text_splitter()
        chunks = splitter.split_documents(docs)
        if not chunks:
            def _empty3(_q: str, _k: int) -> List[str]:
                return []
            return _empty3
        embeddings = _get_embeddings()
        store = FAISS.from_documents(chunks, embeddings)
        chunk_texts = [d.page_content for d in chunks]

        def _search(query: str, top_k: int) -> List[str]:
            found = store.similarity_search(query, k=top_k)
            if found:
                return [d.page_content for d in found]
            # No similar chunks (e.g. generic "summarize" / "what is this about") -> return first chunks so agent has content
            return chunk_texts[:top_k] if chunk_texts else []

        return _search
    except Exception:
        # Fallback: naive keyword search over the same raw docs; if no matches, return first chunks for summarization
        # Build chunk-like pieces from raw so we can return something for "summarize" / "what is this about"
        max_chars = config.rag_naive_chunk_max_chars or (config.rag_chunk_size * 2)
        fallback_chunks: List[str] = []
        for content, _ in raw:
            for i in range(0, len(content), max_chars):
                piece = content[i : i + max_chars].strip()
                if piece:
                    fallback_chunks.append(piece)

        def _naive(query: str, k: int) -> List[str]:
            query_lower = query.lower()
            words = [w for w in query_lower.split() if len(w) > 1]
            scored: List[tuple[float, str]] = []
            for content, _ in raw:
                content_lower = content.lower()
                score = sum(1 for w in words if w in content_lower)
                if score > 0:
                    scored.append((score, content))
            scored.sort(key=lambda x: -x[0])
            if scored:
                return [s[1][:max_chars] for _, s in scored[:k]]
            # No keyword matches (e.g. "summarize", "what is this about") -> return first chunks
            return fallback_chunks[:k] if fallback_chunks else []

        return _naive


def set_rag_scope(scope_paths: List[str] | None) -> None:
    """Set the RAG scope for the current run. None or [] = RAG disabled. Otherwise build scoped search from paths (files + folders)."""
    if not scope_paths:
        _rag_search_fn_ctx.set(None)
        return
    expanded = expand_rag_scope(scope_paths)
    if not expanded:
        _rag_search_fn_ctx.set(None)
        return
    try:
        _rag_search_fn_ctx.set(build_scoped_search(expanded))
    except Exception as e:
        import warnings
        warnings.warn(f"RAG scope build failed ({e}); RAG disabled for this run.", stacklevel=1)
        _rag_search_fn_ctx.set(None)


def get_rag_search_fn() -> Callable[[str, int], List[str]] | None:
    """Return the current run's RAG search function, or None if RAG is not in use."""
    return _rag_search_fn_ctx.get()


def _get_embeddings():
    """Lazy singleton for embeddings. Uses HuggingFaceBgeEmbeddings for BGE models (best RAG quality), else HuggingFaceEmbeddings."""
    global _embeddings
    if _embeddings is not None:
        return _embeddings
    model_name = config.rag_embedding_model
    device = config.rag_embedding_device
    if "bge" in model_name.lower():
        from langchain_community.embeddings import HuggingFaceBgeEmbeddings
        _embeddings = HuggingFaceBgeEmbeddings(
            model_name=model_name,
            model_kwargs={"device": device},
            encode_kwargs={"normalize_embeddings": True},
        )
    else:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        _embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": device},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings


def _get_text_splitter():
    """Return a text splitter for chunking documents."""
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        return RecursiveCharacterTextSplitter(
            chunk_size=config.rag_chunk_size,
            chunk_overlap=config.rag_chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
    except ImportError:
        # Fallback: simple fixed-size chunking
        from langchain_core.documents import Document

        class SimpleSplitter:
            def split_documents(self, docs: List) -> List:
                result = []
                for doc in docs:
                    text = doc.page_content if hasattr(doc, "page_content") else str(doc)
                    meta = doc.metadata if hasattr(doc, "metadata") else {}
                    for i in range(0, len(text), config.rag_chunk_size):
                        chunk = text[i : i + config.rag_chunk_size]
                        if chunk.strip():
                            result.append(Document(page_content=chunk, metadata=meta))
                return result
        return SimpleSplitter()


def _get_vector_store():
    """Build or load FAISS index from memory/docs/. Persists under memory/rag_faiss/."""
    global _vector_store
    if _vector_store is not None:
        return _vector_store

    from langchain_community.vectorstores import FAISS
    from langchain_core.documents import Document

    persist_dir = config.rag_index_dir
    persist_dir.mkdir(parents=True, exist_ok=True)
    index_path = persist_dir / "index.faiss"
    embeddings = _get_embeddings()

    # Try load existing index
    if (index_path.parent / "index.faiss").exists():
        try:
            _vector_store = FAISS.load_local(
                str(persist_dir),
                embeddings,
                allow_dangerous_deserialization=True,
            )
            return _vector_store
        except Exception:
            pass

    # Build from documents
    raw = _load_documents_from_docs_dir()
    if not raw:
        _vector_store = _empty_vector_store(embeddings)
        return _vector_store

    docs = [Document(page_content=content, metadata=meta) for content, meta in raw]
    splitter = _get_text_splitter()
    chunks = splitter.split_documents(docs)
    if not chunks:
        _vector_store = _empty_vector_store(embeddings)
        return _vector_store

    _vector_store = FAISS.from_documents(chunks, embeddings)
    _vector_store.save_local(str(persist_dir))
    return _vector_store


def _empty_vector_store(embeddings):
    """Return a minimal in-memory FAISS store so similarity_search returns [] without persisting."""
    from langchain_community.vectorstores import FAISS
    return FAISS.from_texts(["__placeholder__"], embeddings)


def rag_search(query: str, top_k: int | None = None) -> List[str]:
    """
    Search the local document store (memory/docs/) for chunks relevant to the query.
    Returns a list of top-k text chunks (strings). Uses embedding similarity (FAISS).
    If FAISS/embeddings are unavailable, falls back to naive keyword matching over docs.
    """
    k = top_k if top_k is not None else config.rag_top_k
    try:
        store = _get_vector_store()
        docs = store.similarity_search(query, k=k)
        chunks = [d.page_content for d in docs]
        # Filter out placeholder from empty store
        return [c for c in chunks if c and c.strip() != "__placeholder__"]
    except Exception:
        return _rag_search_naive(query, k)


def _rag_search_naive(query: str, k: int) -> List[str]:
    """Fallback: simple keyword-based retrieval over raw doc chunks (no embeddings)."""
    raw = _load_documents_from_docs_dir()
    if not raw:
        return []
    query_lower = query.lower()
    words = [w for w in query_lower.split() if len(w) > 1]
    scored: List[tuple[float, str]] = []
    for content, _ in raw:
        content_lower = content.lower()
        score = sum(1 for w in words if w in content_lower)
        if score > 0:
            scored.append((score, content))
    scored.sort(key=lambda x: -x[0])
    max_chars = config.rag_naive_chunk_max_chars or (config.rag_chunk_size * 2)
    return [s[1][:max_chars] for _, s in scored[:k]]


def rag_rebuild_index() -> str:
    """Force rebuild of the FAISS index from memory/docs/. Returns a short status message."""
    global _vector_store
    _vector_store = None
    _get_vector_store()
    docs_dir = _get_docs_dir()
    count = sum(1 for p in docs_dir.rglob("*") if p.is_file() and p.suffix.lower() in config.rag_allowed_extensions)
    return f"RAG index rebuilt from {docs_dir}. Documents found: {count}."
