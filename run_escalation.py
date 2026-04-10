import os
import json
import time
from groq import Groq
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

load_dotenv()
from db.database import init_db, get_asr_trend
from redteam import run_model, MODELS

console = Console()
N_RUNS = 5
MODEL_ID   = "llama-3.1-8b-instant"
MODEL_NAME = "Llama 3.1 8B"

if __name__ == "__main__":
    init_db()
    console.print(f"\n[bold purple]Escalation Study — {N_RUNS} consecutive runs[/bold purple]")
    console.print(f"[dim]Model: {MODEL_ID} | Goal: show ASR increases as bypass memory accumulates[/dim]\n")

    asr_per_run = []

    for i in range(1, N_RUNS + 1):
        console.print(f"\n[bold]--- Run {i} of {N_RUNS} ---[/bold]")
        import uuid
        run_id = str(uuid.uuid4())[:8]
        try:
            asr_data, results = run_model(MODEL_NAME, MODEL_ID, run_id)
            asr_per_run.append({"run": i, "asr": asr_data["asr"], "run_id": run_id})
            console.print(f"[bold]Run {i} ASR: {asr_data['asr']}%[/bold]")
        except Exception as e:
            console.print(f"[red]Run {i} failed: {e}[/red]")
            asr_per_run.append({"run": i, "asr": None, "error": str(e)})

        if i < N_RUNS:
            console.print(f"[dim]Waiting 30s before next run to avoid rate limits...[/dim]")
            time.sleep(30)

    console.print("\n")
    table = Table(title="Escalation Study Results", border_style="dim")
    table.add_column("Run", justify="right")
    table.add_column("ASR %", justify="right")
    table.add_column("Trend")

    prev = None
    for r in asr_per_run:
        asr = r.get("asr")
        if asr is None:
            table.add_row(str(r["run"]), "[red]ERROR[/red]", "")
            continue
        color = "red" if asr > 40 else "yellow" if asr > 20 else "green"
        if prev is None:
            trend = "[dim]baseline[/dim]"
        elif asr > prev:
            trend = f"[red]▲ +{round(asr-prev,1)}%[/red]"
        elif asr < prev:
            trend = f"[green]▼ -{round(prev-asr,1)}%[/green]"
        else:
            trend = "[dim]→ no change[/dim]"
        table.add_row(str(r["run"]), f"[{color}]{asr}%[/{color}]", trend)
        prev = asr

    console.print(table)

    with open("reports/escalation_study.json", "w") as f:
        json.dump(asr_per_run, f, indent=2)
    console.print("\n[dim]Saved to reports/escalation_study.json[/dim]")

    valid = [r["asr"] for r in asr_per_run if r.get("asr") is not None]
    if len(valid) >= 2:
        delta = round(valid[-1] - valid[0], 1)
        if delta > 0:
            console.print(f"\n[bold red]Finding: ASR increased by {delta}% over {N_RUNS} runs — attack memory escalation confirmed[/bold red]")
        elif delta < 0:
            console.print(f"\n[bold green]Finding: ASR decreased by {abs(delta)}% — model has a vulnerability floor[/bold green]")
        else:
            console.print(f"\n[bold yellow]Finding: ASR stable across runs — memory loop had no escalation effect[/bold yellow]")