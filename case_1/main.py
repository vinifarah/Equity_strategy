#!/usr/bin/env python3
"""
Earnings Call Intelligence Tracker — Case 1
Usage:
    python main.py transcripts/petrobras_4t24.txt
    python main.py transcripts/petrobras_4t24.txt --no-critique
    python main.py transcripts/petrobras_4t24.txt --output-dir my_outputs
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.ingestion import load_transcript, split_into_chunks
from src.analyzer import analyze_transcript
from src.reporter import generate_report

load_dotenv()
console = Console()


def _parse_args(args: list[str]) -> tuple[str, bool, Path]:
    """Return (transcript_path, enable_critique, output_dir)."""
    if not args or args[0] in ("-h", "--help"):
        console.print(__doc__)
        sys.exit(0)

    transcript_path = args[0]
    enable_critique = "--no-critique" not in args
    output_dir = Path("outputs")

    for i, a in enumerate(args):
        if a == "--output-dir" and i + 1 < len(args):
            output_dir = Path(args[i + 1])

    return transcript_path, enable_critique, output_dir


def main() -> None:
    transcript_path, enable_critique, output_dir = _parse_args(sys.argv[1:])
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(Panel(
        f"[bold blue]Earnings Call Intelligence Tracker[/bold blue]\n"
        f"Transcript: {transcript_path} | Self-critique: {'on' if enable_critique else 'off'}"
    ))

    # Load transcript
    try:
        transcript = load_transcript(transcript_path)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    chunks = split_into_chunks(transcript)
    if len(chunks) > 1:
        console.print(
            f"[yellow]Transcript is long ({len(transcript):,} chars). "
            f"Analyzing first chunk ({len(chunks[0]):,} chars).[/yellow]"
        )
        transcript = chunks[0]

    console.print(f"Transcript: [green]{len(transcript):,}[/green] chars")

    # Run analysis (both passes handled inside analyze_transcript)
    pass_desc = "Analyzing transcript (extraction + self-critique)..." if enable_critique else "Analyzing transcript..."
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as p:
        p.add_task(pass_desc, total=None)
        analysis = analyze_transcript(transcript, enable_self_critique=enable_critique)

    # Save outputs
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ticker = (analysis.ticker or "unknown").replace(".", "_")
    json_path = output_dir / f"{ticker}_{timestamp}.json"
    md_path = output_dir / f"{ticker}_{timestamp}.md"

    json_path.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")
    report = generate_report(analysis)
    md_path.write_text(report, encoding="utf-8")

    # Print results
    console.print(f"\n[bold green]Done![/bold green]")
    console.print(f"  JSON → [cyan]{json_path}[/cyan]")
    console.print(f"  Report → [cyan]{md_path}[/cyan]")
    console.print("\n" + "─" * 60)
    console.print(report)


if __name__ == "__main__":
    main()
