# app/tools.py
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

import certifi
import httpx
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage

# Use certifi bundle for HTTPS on Windows when system CA is missing
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

from .types import (
    PlanTaskInput,
    WebFetchInput,
    CodeExecInput,
    NoteInput,
    SummarizeInput,
)
from .config import config
from .llm import get_base_llm

@tool("plan_tasks", args_schema=PlanTaskInput)
def plan_tasks_tool(goal: str, max_steps: int | None = None) -> str:
    """
    Break a high-level goal into an ordered step-by-step plan.
    """
    input = PlanTaskInput(goal=goal, max_steps=max_steps if max_steps is not None else config.plan_max_steps)
    llm = get_base_llm()
    system = (
        "You are a senior project planner. Create a numbered, concise, but actionable plan. "
        f"For each step include: short title, what will be done, and what tools might be needed (if any). "
        f"Use at most {input.max_steps} steps. Output only the plan, no preamble or repetition."
    )
    human = input.goal
    messages = [SystemMessage(content=system), HumanMessage(content=human)]
    return llm.invoke(messages).content

def _web_fetch(url: str, verify: bool = True) -> tuple[str, bool]:
    """Fetch URL; returns (content or error message, verification_used)."""
    with httpx.Client(timeout=config.web_fetch_timeout, verify=certifi.where() if verify else False) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text[: config.web_fetch_max_chars], verify


@tool("web_fetch", args_schema=WebFetchInput)
def web_fetch_tool(url: str) -> str:
    """
    Fetch the raw HTML/text from a given URL using HTTP GET. No JavaScript.
    """
    input = WebFetchInput(url=url)
    try:
        return _web_fetch(input.url)[0]
    except Exception as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e) or "SSL" in str(type(e).__name__):
            try:
                text, verified = _web_fetch(input.url, verify=False)
                return "[SSL verification disabled; system CA store unavailable.]\n\n" + text
            except Exception as fallback_e:
                return f"ERROR fetching {input.url}: {fallback_e}"
        return f"ERROR fetching {input.url}: {e}"

@tool("code_exec", args_schema=CodeExecInput)
def code_exec_tool(code: str) -> str:
    """
    Execute short Python code snippets in a subprocess.
    The snippet MUST use print() to display results; otherwise stdout will be empty.
    WARNING: This is local and can be dangerous. Use only for trusted users.
    """
    input = CodeExecInput(code=code)
    # Unbuffered (-u) so print() is captured reliably on Windows.
    try:
        completed = subprocess.run(
            [sys.executable, "-u", "-c", input.code],
            capture_output=True,
            text=True,
            timeout=config.code_exec_timeout,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
    except subprocess.TimeoutExpired:
        return "ERROR: Code execution timed out."

    output = (completed.stdout or "").strip()
    err = (completed.stderr or "").strip()
    if completed.returncode != 0:
        return f"Non-zero return code {completed.returncode}. stderr:\n{err}"
    if err:
        output = f"{output}\n[stderr]\n{err}" if output else f"[stderr]\n{err}"
    return output or "Code ran successfully (exit 0) but produced no stdout. Use print(...) in the snippet to display results."

@tool("write_note", args_schema=NoteInput)
def write_note_tool(title: str, content: str) -> str:
    """
    Write a note to the memory directory with the given title and content.
    """
    input = NoteInput(title=title, content=content)
    safe_title = "".join(c for c in input.title if c.isalnum() or c in ("-", "_")).strip() or "note"
    path = config.memory_dir / f"{safe_title}.md"
    text = f"# {input.title}\n\n{input.content}\n"
    path.write_text(text, encoding="utf-8")
    return f"Note written to {path}"

@tool("summarize_text", args_schema=SummarizeInput)
def summarize_text_tool(text: str, max_words: int | None = None) -> str:
    """
    Summarize the provided text into a concise form.
    """
    input = SummarizeInput(text=text, max_words=max_words if max_words is not None else config.summarize_max_words)
    llm = get_base_llm()
    system = (
        "You are a professional summarizer. Summarize in at most the requested number of words. "
        "Preserve key technical details and decisions. Output only the summary, no preamble or repetition."
    )
    messages = [SystemMessage(content=system), HumanMessage(content=f"Max words: {input.max_words}\n\nTEXT:\n{input.text}")]
    return llm.invoke(messages).content
