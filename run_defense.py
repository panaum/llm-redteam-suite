import os
import sys
import json
import uuid
from groq import Groq
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

load_dotenv()
from db.database import init_db
from defenders.defense_layer import run_defense_comparison

console = Console()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def make_target_fn(model_id: str):
    def target(prompt: str) -> str:
        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[ERROR] {str(e)}"
    return target

if __name__ == "__main__":
    init_db()

    model_id   = sys.argv[1] if len(sys.argv) > 1 else "llama-3.3-70b-versatile"
    model_name = sys.argv[2] if len(sys.argv) > 2 else "Llama 3.3"

    console.print(Panel(
        f"[bold]Model:[/bold] {model_name} ({model_id})\n"
        f"[bold]Modes:[/bold] none to input filter to system prompt to output classifier to all\n"
        f"[bold]Goal:[/bold] Measure ASR reduction per defense layer",
        title="[bold purple]Defense Layer Evaluation[/bold purple]",
        border_style="purple"
    ))

    with open("attacks.json", "r") as f:
        attacks = json.load(f)

    attack_list = [{"prompt": a["prompt"], "category": a["category"]} for a in attacks]
    target_fn   = make_target_fn(model_id)

    results = run_defense_comparison(attack_list, target_fn, model_name, model_id)

    out_path = f"reports/defense_{model_id.replace('/','_')}_{str(uuid.uuid4())[:6]}.json"
    os.makedirs("reports", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    console.print(f"\n[dim]Defense report saved: {out_path}[/dim]")

    console.print("\n[bold]Key findings:[/bold]")
    baseline = results["none"]["asr"]
    all_asr  = results["all"]["asr"]
    reduction = round(baseline - all_asr, 1)
    console.print(f"  Stacking all 3 defenses reduced ASR from [red]{baseline}%[/red] to [green]{all_asr}%[/green] ([green]-{reduction}%[/green])")

    bypassed_with_all = results["all"]["succeeded"]
    if bypassed_with_all > 0:
        console.print(f"  [yellow]{bypassed_with_all} attack(s) bypassed even with all defenses active — these are your hardest findings[/yellow]")
    else:
        console.print(f"  [green]All attacks blocked with full defense stack[/green]")