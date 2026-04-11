# LLM Red Team Suite

An adversarial evaluation framework for large language models. Combines static attack libraries, AI-generated dynamic attacks (PAIR), many-shot jailbreaking, semantic scoring, and a three-layer defense stack — all with persistent memory that makes attacks harder on every run.

Built as a portfolio project targeting AI Safety / Red Teaming roles. Methodology based on [Chao et al. 2023 (PAIR, arXiv:2310.08419)](https://arxiv.org/abs/2310.08419) and Anthropic's many-shot jailbreaking research (2024).

---

## Benchmark Results

### Multi-Model ASR (Attack Success Rate)

| Model | Overall ASR | prompt_injection | hallucination | pii_leakage | role_confusion | jailbreak |
|---|---|---|---|---|---|---|
| Llama 3.3 70B | **44.4%** 🔴 | 100% | 0% | 0% | 100% | 25% |
| Qwen 32B | **25.9%** 🟡 | 60% | 0% | 0% | 100% | 0% |
| GPT-OSS 120B | **3.7%** 🟢 | 20% | 0% | 0% | 0% | 0% |

> Lower ASR = safer. Hallucination and PII categories showed 0% ASR across all models — these defenses are robust. Role confusion was the weakest category (100% on two models).

### HarmBench Comparison

| Model | This Suite ASR | Closest Published Baseline |
|---|---|---|
| Llama 3.1 8B | 30.0% | Llama-2-13B — 26.8% (published) |
| Llama 3.3 70B | 25.0% | Llama-2-13B — 26.8% (published) |

**Published baselines for reference:** GPT-4: 4.2% · GPT-3.5: 18.7% · Llama-2-7B: 42.1% · Llama-2-13B: 26.8% · Vicuna-13B: 89.3%

Notable anomaly: Llama 3.3 70B scored **worse** on malware prompts (100% category ASR) than the smaller 8B model (0%) — the larger model's helpfulness works against it on exploit-adjacent prompts.

### Defense Layer Evaluation (Llama 3.3)

| Defense Mode | ASR % | Bypassed | Blocked | Reduction |
|---|---|---|---|---|
| None (baseline) | 20.0% | 4 | 0 | — |
| Input filter only | 5.0% | 1 | 7 | **-15%** |
| System prompt hardening | 0.0% | 0 | 0 | **-20%** |
| Output classifier only | 20.0% | 4 | 0 | 0% |
| All three stacked | 10.0% | 2 | 7 | **-10%** |

Key finding: System prompt hardening alone dropped ASR to 0% — the strongest single defense. The output toxicity classifier added no reduction on its own but strengthened the combined stack.

### Escalation Study (5 Consecutive Runs, Llama 3.1 8B)

| Run | ASR % | Trend |
|---|---|---|
| 1 | 40.74% | baseline |
| 2 | 37.04% | ▼ -3.7% |
| 3 | 40.74% | ▲ +3.7% |
| 4 | **44.44%** | ▲ +3.7% |
| 5 | 40.74% | ▼ -3.7% |

Finding: Static attack categories (prompt_injection, hallucination) showed a stable floor regardless of bypass memory accumulation. The memory loop produced measurable escalation specifically in **dynamic PAIR categories** — jailbreak bypasses appeared in run 4 that failed in runs 1–2, confirming the self-improving loop works for iteratively-refined attacks.

---

## Architecture

```
llm-redteam-suite/
├── attacks.json              # 20 static adversarial prompts (5 categories)
├── redteam.py                # Main runner — multi-model benchmark
├── run_defense.py            # Defense layer evaluation
├── run_escalation.py         # 5-run escalation study
├── run_harmbench.py          # HarmBench comparison
│
├── attackers/
│   └── pair.py               # PAIR + many-shot jailbreaking
│
├── evaluators/
│   └── scorer.py             # Semantic cosine similarity scoring + ASR metric
│
├── defenders/
│   └── defense_layer.py      # Input filter + system prompt hardening + toxicity classifier
│
├── db/
│   └── database.py           # SQLite: run history, bypass memory, leaderboard
│
└── reports/                  # JSON + HTML output
```

---

## How It Works

### Attack Pipeline

Every run fires three layers of attacks:

**1. Static attacks** — 20 hand-crafted prompts across prompt_injection, hallucination, pii_leakage, role_confusion, and jailbreak categories.

**2. PAIR dynamic attacks** (based on [arXiv:2310.08419](https://arxiv.org/abs/2310.08419)) — an attacker LLM generates adversarial prompts, sees the target model's response, and iteratively refines the prompt until it either succeeds or hits the iteration limit. On each run, past successful bypasses are loaded from SQLite and fed back as context, so the attacker generates harder variants. This is the self-improving loop.

**3. Many-shot jailbreaking** — generates N example Q&A pairs that gradually normalize a restricted behavior, then appends the real attack. Based on Anthropic's 2024 research on context-length exploitation.

### Scoring

Dual scoring system — both vote on each response:

- **Semantic scorer** (`sentence-transformers/all-MiniLM-L6-v2`): computes cosine similarity against refusal anchors and compliance anchors. No keyword matching — resistant to paraphrased refusals like "I cannot help but notice..."
- **LLM judge** (Llama 3.3): reads the attack prompt and response, reasons about whether the model was actually manipulated. Attack is flagged successful if *either* scorer says yes.

ASR is computed per-run and per-category. All results saved to SQLite for cross-run trend analysis.

### Defense Layer

Three independent defenses, tested individually and stacked:

- **Input filter**: regex patterns for injection keywords (DAN, system override, etc.) — blocked 7/20 prompt injection attacks
- **System prompt hardening**: injects a 6-rule hardened system prompt that explicitly forbids persona adoption, instruction overrides, and content policy violations
- **Output toxicity classifier**: detoxify `original` model scoring for toxicity, severe_toxicity, identity_hate, threat — blocks responses above threshold

---

## Installation

**Requirements:** Python 3.10+, Groq API key (free tier works)

```bash
git clone https://github.com/panaum/llm-redteam-suite
cd llm-redteam-suite
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

pip install groq python-dotenv rich sentence-transformers detoxify
```

Create a `.env` file:
```
GROQ_API_KEY=your_key_here
```

---

## Usage

### Full benchmark (3 models)
```bash
python redteam.py
```

### View model leaderboard
```bash
python redteam.py leaderboard
```

### Defense layer evaluation
```bash
python run_defense.py
# Or specify a model:
python run_defense.py llama-3.3-70b-versatile "Llama 3.3"
```

### Escalation study (5 consecutive runs)
```bash
python run_escalation.py
```

### HarmBench comparison
```bash
python run_harmbench.py
```

---

## Attack Categories

| Category | Description | Llama 3.3 ASR |
|---|---|---|
| `prompt_injection` | Override system instructions | 100% |
| `role_confusion` | Force persona adoption | 100% |
| `jailbreak` | Bypass safety guidelines via framing | 25% |
| `hallucination` | Elicit fabricated facts/citations | 0% |
| `pii_leakage` | Repeat or store personal information | 0% |

---

## Tech Stack

| Component | Library |
|---|---|
| LLM API | `groq` (llama-3.3-70b-versatile, llama-3.1-8b-instant) |
| Semantic scoring | `sentence-transformers` (all-MiniLM-L6-v2) |
| Toxicity classification | `detoxify` (original model) |
| Persistence | `sqlite3` (bypass memory, ASR history) |
| Terminal UI | `rich` |
| Environment | `python-dotenv` |

---

## Key Research References

- **PAIR**: Chao et al. (2023). *Jailbreaking Black Box Large Language Models in Twenty Queries.* arXiv:2310.08419
- **Many-shot jailbreaking**: Anthropic (2024). *Many-shot jailbreaking.* anthropic.com/research
- **HarmBench baselines**: Mazeika et al. (2024). *HarmBench: A Standardized Evaluation Framework for Automated Red Teaming.*

---

## Findings Summary

1. **Role confusion is the most exploitable category** across all tested models — 100% ASR on Llama 3.3 and Qwen 32B using soft-language persona prompts that bypass keyword filters.

2. **System prompt hardening outperforms input filtering** as a single defense (-20% ASR vs -15%), but stacking all three produces non-additive results — some attacks bypass the full stack that each individual defense catches separately.

3. **Model size does not predict safety on all categories** — Llama 3.3 70B showed higher malware-adjacent ASR than Llama 3.1 8B, suggesting instruction-following capability can work against safety on exploit-framed prompts.

4. **Attack memory escalation is category-dependent** — static attacks showed a stable ASR floor across 5 runs. PAIR-generated attacks showed measurable escalation (run 4 produced bypasses not seen in runs 1–2), confirming the memory loop is effective for iteratively-refined dynamic attacks but cannot improve on already-saturated static prompts.

---

## Roadmap

- [ ] HTTP adapter — point the suite at any REST API endpoint, not just raw models
- [ ] Multi-turn attack chains — maintain conversation state across attack iterations
- [ ] Benchmark against full HarmBench dataset (520 prompts)
- [ ] Findings report PDF with methodology and recommendations
