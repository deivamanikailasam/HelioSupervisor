# app/supervisor.py
from __future__ import annotations
import gc
import os
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain.agents import create_agent

from .config import config
from .llm import get_base_llm, _api_keys_ctx
from . import rag
from .tools import (
    plan_tasks_tool,
    web_fetch_tool,
    code_exec_tool,
    write_note_tool,
    summarize_text_tool,
    rag_search_tool,
)
from .types import SummarizeInput
from .memory import memory_store

def get_supervisor_system_prompt(
    require_human_approval: bool = True,
    rag_scope: List[str] | None = None,
    rag_documents_only: bool = False,
) -> str:
    approval_block = (
        "- For any action that is potentially risky (code_exec, write_note, web_fetch):\n"
        "  - FIRST explain what you plan to do.\n"
        "  - Ask explicitly: \"Do you approve running this action? (yes/no)\"\n"
        "  - Wait for a clear 'yes' before proceeding with that tool.\n"
        if require_human_approval
        else "- For potentially risky actions (code_exec, write_note, web_fetch): briefly explain what you will do, then proceed without asking for approval (user has enabled auto-approve).\n"
    )
    tools_list = "plan_tasks, web_fetch, code_exec, write_note, summarize_text, rag_search"
    rag_block = "- Use rag_search only when the user has attached a document or selected documents/folders for this run; the tool will tell you if no documents were selected. When available, use it for questions about those docs, then summarize_text or reason over the returned chunks."
    if rag_scope:
        rag_block += (
            "\n- When answering from rag_search results: base your answer ONLY on the provided chunks; do not add information that is not in the chunks; if the answer is not in the chunks, say so (e.g. \"Not stated in the document(s)\"). Do not hallucinate or invent content."
        )
    if rag_scope and rag_documents_only:
        rag_block += (
            "\n- This run is documents-only (offline): do NOT use web_fetch or any external sources. Use only rag_search and the returned chunks (and summarize_text). Answer strictly from the selected documents."
        )
        tools_list = "plan_tasks, code_exec, write_note, summarize_text, rag_search"  # no web_fetch
    return f"""
You are a Hierarchical Supervisor Agent for 2026-style workflows.

Your responsibilities:
- Understand the user's high-level goal.
- Decide which tools to use and in what order.
- Break work into clear subtasks. Use `plan_tasks` when helpful.
- Avoid unnecessary tool calls.
{approval_block}- Keep the user informed in natural language.
- At the end, summarize what you did and any remaining open questions.

You have access to the following tools: {tools_list}.

{rag_block}
Be concise, transparent, and safety-conscious. Prefer local processing and avoid unnecessary external requests.
""".strip()


def get_supervisor_tools(include_web_fetch: bool = True) -> List[BaseTool]:
    base = [
        plan_tasks_tool,
        code_exec_tool,
        write_note_tool,
        summarize_text_tool,
        rag_search_tool,
    ]
    if include_web_fetch:
        base.insert(1, web_fetch_tool)
    return base


def create_supervisor_graph(
    require_human_approval: bool = True,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    api_keys: dict | None = None,
    rag_scope: List[str] | None = None,
    rag_documents_only: bool = False,
):
    """Create the supervisor agent graph (LangChain 1.2 / LangGraph)."""
    llm = get_base_llm(provider=llm_provider, model=llm_model, api_keys=api_keys)
    include_web_fetch = not (rag_scope and rag_documents_only)
    tools = get_supervisor_tools(include_web_fetch=include_web_fetch)
    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=get_supervisor_system_prompt(
            require_human_approval,
            rag_scope=rag_scope,
            rag_documents_only=rag_documents_only,
        ),
    )


def _last_ai_content(messages: List[Any]) -> str:
    """Extract the last AI message content from the messages list."""
    for m in reversed(messages):
        if isinstance(m, AIMessage) and hasattr(m, "content"):
            return m.content or ""
    return ""


def _tool_name_from_tool_call(tc: Any) -> str | None:
    """Get tool name from a single tool call (dict or object). Some APIs use 'tool' or 'name'."""
    if isinstance(tc, dict):
        return tc.get("name") or tc.get("tool")
    return getattr(tc, "name", None) or getattr(tc, "tool", None)


def _tools_used_from_messages(messages: List[Any]) -> List[str]:
    """Collect unique tool names that were invoked (AIMessage.tool_calls and ToolMessage.name)."""
    seen: set[str] = set()
    out: List[str] = []
    for m in messages:
        # Dict-shaped message (e.g. from some runtimes)
        if isinstance(m, dict):
            if m.get("type") == "ai" and m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    name = _tool_name_from_tool_call(tc)
                    if name and name not in seen:
                        seen.add(name)
                        out.append(name)
            elif m.get("type") == "tool" and m.get("name"):
                name = m["name"]
                if name and name not in seen:
                    seen.add(name)
                    out.append(name)
            continue
        # Any message with tool_calls (AIMessage or duck-typed)
        tool_calls = getattr(m, "tool_calls", None) or []
        for tc in tool_calls:
            name = _tool_name_from_tool_call(tc)
            if name and name not in seen:
                seen.add(name)
                out.append(name)
        # Any message with .name (ToolMessage or duck-typed)
        name = getattr(m, "name", None)
        if name and isinstance(name, str) and name not in seen:
            seen.add(name)
            out.append(name)
    return out


def run_supervisor(
    user_input: str,
    chat_history: List[Any] | None = None,
    config_overrides: Dict[str, Any] | None = None,
    include_critique: bool = False,
    require_human_approval: bool | None = None,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    api_keys: dict | None = None,
    rag_scope: List[str] | None = None,
    rag_documents_only: bool = False,
) -> Dict[str, Any]:
    """
    Run the supervisor with the given user input.
    Returns a dict with 'output', 'tools_used', and optionally 'self_critique'.
    api_keys: optional dict with keys 'openai', 'google', 'perplexity' (from UI; .env not used).
    rag_scope: optional list of paths (relative to memory/docs): file paths and/or folder paths.
      When provided, RAG search runs only over those docs. When None or empty, RAG is not used.
    rag_documents_only: when True and rag_scope is set, agent may not use web_fetch; answer only from documents (offline).
    """
    env_backup: Dict[str, str | None] = {}
    if api_keys is not None:
        _api_keys_ctx.set(api_keys)
        for env_name in ("OPENAI_API_KEY", "GOOGLE_API_KEY", "PERPLEXITY_API_KEY"):
            env_backup[env_name] = os.environ.pop(env_name, None)

    rag.set_rag_scope(rag_scope)
    try:
        # When RAG scope is set, hint the agent so it uses rag_search
        effective_input = (
            "[RAG is enabled for this run. Use the rag_search tool to search the attached/selected documents when answering.]\n\n"
            + user_input
            if rag_scope
            else user_input
        )
        history_msgs: List[Any] = []
        recent = memory_store.load_recent(config.memory_recent_turns)
        for turn in recent:
            if turn.role == "user":
                history_msgs.append(HumanMessage(content=turn.content))
            else:
                history_msgs.append(AIMessage(content=turn.content))

        if chat_history:
            for entry in chat_history:
                if isinstance(entry, dict):
                    if entry.get("role") == "user":
                        history_msgs.append(HumanMessage(content=entry.get("content", "")))
                    else:
                        history_msgs.append(AIMessage(content=entry.get("content", "")))
                else:
                    history_msgs.append(entry)

        history_msgs.append(HumanMessage(content=effective_input))

        approval = require_human_approval if require_human_approval is not None else config.enable_human_approval
        graph = create_supervisor_graph(
            require_human_approval=approval,
            llm_provider=llm_provider,
            llm_model=llm_model,
            api_keys=api_keys,
            rag_scope=rag_scope,
            rag_documents_only=rag_documents_only,
        )
        result_state = graph.invoke(
            {"messages": history_msgs},
            config=config_overrides or {"recursion_limit": config.recursion_limit},
        )

        messages = result_state.get("messages", [])
        output = _last_ai_content(messages)
        tools_used = _tools_used_from_messages(messages)

        memory_store.append("user", user_input)
        memory_store.append("assistant", output)

        result: Dict[str, Any] = {"output": output, "tools_used": tools_used}
        if include_critique:
            critique = summarize_text_tool.invoke(
                SummarizeInput(
                    text=f"User request: {user_input}\n\nAgent answer:\n{output}",
                    max_words=config.summarize_critique_max_words,
                ).model_dump()
            )
            result["self_critique"] = critique
            memory_store.append("assistant", f"[SELF_CRITIQUE]\n{critique}")
        return result
    finally:
        rag.set_rag_scope(None)
        gc.collect()  # Release RAG FAISS index and other run-scoped objects to reduce RAM
        for env_name, value in env_backup.items():
            if value is not None:
                os.environ[env_name] = value
