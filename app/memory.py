# app/memory.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json
from typing import Any

from .config import config

@dataclass
class ConversationTurn:
    role: str
    content: str
    timestamp: str | None = None

@dataclass
class MemoryStore:
    path: Path = config.memory_dir / "conversations.jsonl"
    buffer: list[ConversationTurn] = field(default_factory=list)

    def append(self, role: str, content: str) -> None:
        turn = ConversationTurn(
            role=role,
            content=content,
            timestamp=datetime.utcnow().isoformat(),
        )
        self.buffer.append(turn)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(turn.__dict__) + "\n")

    def load_recent(self, n: int | None = None) -> list[ConversationTurn]:
        if not self.path.exists():
            return []
        n = n if n is not None else config.memory_recent_turns
        lines = self.path.read_text(encoding="utf-8").splitlines()[-n:]
        return [ConversationTurn(**json.loads(l)) for l in lines]

memory_store = MemoryStore()
