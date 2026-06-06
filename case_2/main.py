#!/usr/bin/env python3
"""
Macro Scenario Engine — Case 2
Usage:
    # Pass scenario as argument:
    python main.py "Selic cai para 10%, dólar em 5.50, commodities metálicas em alta"

    # Pass scenario from file:
    python main.py --file scenario.txt

    # Disable self-critique:
    python main.py "..." --no-critique

    # Custom output directory:
    python main.py "..." --output-dir my_outputs
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.analyzer import analyze_scenario
from src.reporter import generate_report

load_dotenv()
console = Console()


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        console.print(__doc__)
        sys.exit(0)

    # Parse flags
    enable_critique = "--no-critique" not in args
    output_dir = Path("outputs")
    scenario_text: str = ""

    clean_args = [a for a in args if a not in ("--no-critique",)]

    for i, a in enumerate(clean_args):
        if a == "--output-dir" and i + 1 < len(clean_args):
            output_dir = Path(clean_args[i + 1])
        elif a == "--file" and i + 1 < len(clean_args):
            p = Path(clean_args[i + 1])
            if not p.exists():
                console.print(f"[red]File not found:[/red] {p}")
                sys.exit(1)
            scenario_text = p.read_text(encoding="utf-8").strip()
        elif not a.startswith("--") and not scenario_text:
            scenario_text = a

    if not scenario_text:
        console.print("[red]Error:[/red] Please provide a macro scenario as an argument or --file.")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(Panel(f"[bold blue]Macro Scenario Engine[/bold blue]\n\n{scenario_text[:200]}..."))

    # Run analysis
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as p:
        task = p.add_task("Analyzing macro scenario (Pass 1: sector + ticker analysis)...", total=None)
        analysis = analyze_scenario(scenario_text, enable_self_critique=enable_critique)
        p.update(task, description="Generating report...")

    # Save outputs
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"scenario_{timestamp}.json"
    md_path = output_dir / f"scenario_{timestamp}.md"

    json_path.write_text(
        analysis.model_dump_json(indent=2, exclude_none=False),
        encoding="utf-8",
    )

    report = generate_report(analysis)
    md_path.write_text(report, encoding="utf-8")

    console.print("\n[bold green]Analysis complete![/bold green]")
    console.print(f"  JSON → [cyan]{json_path}[/cyan]")
    console.print(f"  Report → [cyan]{md_path}[/cyan]")
    console.print("\n" + "─" * 60)
    console.print(report)


if __name__ == "__main__":
    main()
