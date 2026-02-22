# app/cli.py
from __future__ import annotations
from typing import List

from rich.console import Console
from rich.markdown import Markdown

from .supervisor import run_supervisor

console = Console()

def main() -> None:
    console.print("[bold green]Hierarchical Supervisor Agent (Local, 2026 Edition)[/bold green]")
    console.print("Type 'exit' to quit.\n")

    chat_history: List = []

    while True:
        user_input = console.input("[bold cyan]You:[/bold cyan] ")
        if user_input.strip().lower() in {"exit", "quit"}:
            break

        include_critique_raw = console.input(
            "[dim]Include self-critique summary? (y/n) [n]:[/dim] "
        ).strip().lower()
        include_critique = include_critique_raw in ("y", "yes")

        result = run_supervisor(
            user_input,
            chat_history=chat_history,
            include_critique=include_critique,
        )
        output = result["output"]
        tools_used = result.get("tools_used") or []
        # Always show tools first when present, as Supervisor saying it
        if tools_used:
            tools_str = ", ".join(tools_used)
            console.print("[bold green]Supervisor:[/bold green] [dim]I am using: {}.[/dim]".format(tools_str))
        console.print(Markdown(f"**Supervisor:** {output}"))
        critique = result.get("self_critique")
        if critique:
            console.print(Markdown(f"**Self-critique summary:** {critique}"))

        chat_history.append({"role": "user", "content": user_input})
        chat_history.append({"role": "assistant", "content": output})

if __name__ == "__main__":
    main()
