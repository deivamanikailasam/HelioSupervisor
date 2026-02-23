# app/types.py
from pydantic import BaseModel, Field

from .config import config


class PlanTaskInput(BaseModel):
    goal: str = Field(..., description="High-level user goal, natural language.")
    max_steps: int = Field(
        default_factory=lambda: config.plan_max_steps,
        description="Maximum number of steps in the plan.",
    )

class WebFetchInput(BaseModel):
    url: str = Field(..., description="HTTP/HTTPS URL to fetch.")

class CodeExecInput(BaseModel):
    code: str = Field(
        ...,
        description="Short, safe Python code to execute. Must use print() to display results.",
    )

class NoteInput(BaseModel):
    title: str = Field(..., description="Short note title.")
    content: str = Field(..., description="Full note content.")

class SummarizeInput(BaseModel):
    text: str = Field(..., description="Text to summarize.")
    max_words: int = Field(
        default_factory=lambda: config.summarize_max_words,
        description="Rough max words for summary.",
    )


class RagSearchInput(BaseModel):
    query: str = Field(..., description="Search query to find relevant document chunks.")
    top_k: int = Field(
        default_factory=lambda: config.rag_top_k,
        description="Number of top chunks to return (default from config).",
    )
