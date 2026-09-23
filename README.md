# LLM Red Team Suite

An adversarial evaluation framework for large language models. Combines static attack libraries, AI-generated dynamic attacks (PAIR), many-shot jailbreaking, semantic scoring, and a three-layer defense stack — with persistent memory that makes attacks smarter on every run.

Built as a portfolio project targeting **AI Safety / Red Teaming roles**.  
Methodology based on [Chao et al. 2023 (PAIR, arXiv:2310.08419)](https://arxiv.org/abs/2310.08419) and [Anthropic's many-shot jailbreaking research (2024)](https://www.anthropic.com/research/many-shot-jailbreaking).

---

![Dashboard](reports/dashboard.png)

---

## Judge validation study

The attack success rates in this README come from the suite's automatic judges. A pre-registered study checked those judges against **197 blind human labels**, a sample stratified by category from the 432 attacks logged in `db/redteam.db`. Full write-up: [paper](paper/judge-validation.md). All numbers: [validation report](validation/validation_report.md).

- **Agreement with the human labels was slight to fair.** The study compared three verdicts: the embedding scorer (`evaluators/scorer.py`), a refusal-string keyword matcher, and the stored composite verdict behind the published figures. Cohen's κ ranged from **0.122 to 0.281** (n = 197).
- **The embedding scorer under-reported success by about 30 points.** It gave 22.3% against 52.8% by human label: a paired difference of −30.5%, 95% CI [−38.6, −22.3].
- **The keyword matcher over-reported by 33.0 points**, 95% CI [24.9, 40.6].
- **The direction of error depends on the judge.** A rate from this suite is neither a lower nor an upper bound unless you know which judge produced it.
- **The reference labels are weak.** One annotator made all the labels, quickly (median 7 s per item), and also wrote the rubric. Inter-rater reliability was not measured, so the study cannot separate scorer error from error in the human reference.
- **role_confusion is the one category where the original number looks inflated.** The stored verdicts give 85.4% (41/48 attacks) against 69.7% (23/33) by human label. This is exploratory, and the two 95% intervals overlap.

The tables below were not re-labelled cell by cell. The study measures the judge's error; it does not produce corrected per-model figures.

---

## Results

> **Unvalidated judge output.** Every rate in this section was produced by the automatic judges described under [Scoring](#scoring). Read the [judge validation study](#judge-validation-study) before relying on these numbers.

### Multi-Model Attack Success Rate (ASR)

| Model | Overall ASR | prompt_injection | hallucination | pii_leakage | role_confusion | jailbreak |
|---|---|---|---|---|---|---|
| Llama 3.3 70B | **44.4%** 🔴 | 100% | 0% | 0% | 100% | 25% |
| Qwen 32B | **25.9%** 🟡 | 60% | 0% | 0% | 100% | 0% |
| GPT-OSS 120B | **3.7%** 🟢 | 20% | 0% | 0% | 0% | 0% |

> Lower ASR = safer. Hallucination and PII categories showed 0% ASR across all models in the judge's output. On the validation sample, the human labels gave 18.2% (6/33) for hallucination and 45.5% (15/33) for pii_leakage. Role confusion was the most exploitable category in the judge's output, with 100% ASR on two models. The validation study suggests the stored rate for this category is inflated.

### HarmBench Comparison

| Model | This Suite ASR | Closest Published Baseline |
|---|---|---|
| Llama 3.1 8B | 30.0% | Llama-2-13B — 26.8% |
| Llama 3.3 70B | 25.0% | Llama-2-13B — 26.8% |

**Published baselines:** GPT-4: 4.2% · GPT-3.5: 18.7% · Llama-2-7B: 42.1% · Llama-2-13B: 26.8% · Vicuna-13B: 89.3%

> Notable anomaly: Llama 3.3 70B scored **worse** on malware-adjacent prompts than the smaller 8B model — the larger model's instruction-following capability works against it on exploit-framed inputs.

### Defense Layer Evaluation (Llama 3.3)

| Defense Mode | ASR | Bypassed | Blocked | Reduction |
|---|---|---|---|---|
| None (baseline) | 20.0% | 4 | 0 | — |
| Input filter only | 5.0% | 1 | 7 | **-15%** |
| System prompt hardening | 0.0% | 0 | 0 | **-20%** |
| Output classifier only | 20.0% | 4 | 0 | 0% |
| All three stacked | 10.0% | 2 | 7 | **-10%** |

> System prompt hardening alone dropped ASR to 0% — the strongest single defense. The output classifier added no reduction on its own, but reinforced the stacked configuration.

### Escalation Study (5 Consecutive Runs, Llama 3.1 8B)

| Run | ASR | Trend |
|---|---|---|
| 1 | 40.74% | baseline |
| 2 | 37.04% | ▼ -3.7% |
| 3 | 40.74% | ▲ +3.7% |
| 4 | **44.44%** | ▲ +3.7% |
| 5 | 40.74% | ▼ -3.7% |

> Static categories held a stable floor. PAIR-generated attacks showed measurable escalation in run 4 — bypasses appeared that failed in runs 1–2, confirming the memory loop works for iteratively-refined dynamic attacks.

---

## Architecture

```
llm-redteam-suite/
│
├── redteam.py                # Main runner — multi-model benchmark
├── run_defense.py            # Defense layer evaluation
├── run_escalation.py         # 5-run escalation study
├── run_harmbench.py          # HarmBench comparison
├── dynamic_attacks.py        # Dynamic PAIR attack runner
├── rag_poison.py             # RAG poisoning experiments
│
├── attackers/
│   └── pair.py               # PAIR + many-shot jailbreaking
│
├── evaluators/
│   └── scorer.py             # Semantic cosine similarity + ASR metric
│
├── scripts/
│   └── validate_judge.py     # Judge-validation study: sample, label, score, analyse
│
├── RUBRIC.md / STUDY_PLAN.md # Pre-registered labelling rubric and study plan
├── validation/               # Sample, 197 human labels, judge outputs, report
├── paper/                    # Judge-validation paper (Markdown, LaTeX)
│
├── defenders/
│   └── defense_layer.py      # Input filter + system prompt hardening + toxicity classifier
│
├── db/
│   └── database.py           # SQLite: run history, bypass memory, leaderboard
│
├── datasets/
│   └── attacks.json          # 20 static adversarial prompts (5 categories)
│
├── docs/
│   └── methodology.md        # Full methodology writeup
│
└── reports/
    ├── redteam_report.html   # HTML summary report
    ├── dashboard.png         # Visualization
    └── data/                 # JSON logs, CSVs, experiment outputs
```

---

## How It Works

### Attack Pipeline

Every run fires three layers of attacks:

**1. Static attacks** — 20 hand-crafted prompts across 5 categories: prompt_injection, hallucination, pii_leakage, role_confusion, and jailbreak. Provides baseline coverage and consistent cross-model comparison.

**2. PAIR dynamic attacks** ([arXiv:2310.08419](https://arxiv.org/abs/2310.08419)) — an attacker LLM generates adversarial prompts, observes the target model's response, and iteratively refines until it succeeds or hits the iteration limit. Past successful bypasses are loaded from SQLite each run and fed back as context — the attacker generates harder variants over time. This is the self-improving loop.

**3. Many-shot jailbreaking** — generates N example Q&A pairs that gradually normalize a restricted behavior, then appends the real attack. Based on Anthropic's 2024 research on context-length exploitation.

### Scoring

- **Semantic scorer** (`sentence-transformers/all-MiniLM-L6-v2`): computes cosine similarity against refusal and compliance anchors. Against blind human labels it under-reported success, missing 73 of 104 human-labelled successes (see [Judge validation study](#judge-validation-study)).
- **LLM judge** (`llama-3.1-8b-instant`, in `redteam.py`): reads the attack and the response and answers YES or NO. Its prompt counts adopting an unrestricted persona as success.

For **static attacks**, an attack is flagged successful if **either** scorer flags it. For **PAIR and many-shot attacks**, the semantic scorer decides alone. ASR is computed per run and per category. All results are saved to SQLite for cross-run trend analysis.

### Defense Layer

Three independent defenses, tested individually and stacked:

- **Input filter** — regex patterns for injection keywords (DAN, system override, etc.). Blocked 7/20 prompt injection attacks.
- **System prompt hardening** — injects a 6-rule hardened system prompt that explicitly forbids persona adoption, instruction overrides, and policy violations.
- **Output toxicity classifier** — Detoxify `original` model scoring for toxicity, severe toxicity, identity hate, and threat. Blocks responses above threshold.

---

## Installation

**Requirements:** Python 3.10+, Groq API key (free tier works)

```bash
git clone https://github.com/panaum/llm-redteam-suite
cd llm-redteam-suite
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install groq python-dotenv rich sentence-transformers detoxify
```

Create a `.env` file:
```
GROQ_API_KEY=your_key_here
```

---

## Usage

```bash
# Full benchmark (3 models)
python redteam.py

# View model leaderboard
python redteam.py leaderboard

# Defense layer evaluation
python run_defense.py
python run_defense.py llama-3.3-70b-versatile "Llama 3.3"  # specify model

# Escalation study (5 consecutive runs)
python run_escalation.py

# HarmBench comparison
python run_harmbench.py
```

---

## Attack Categories

| Category | Description | Llama 3.3 ASR |
|---|---|---|
| `prompt_injection` | Override system instructions | 100% |
| `role_confusion` | Force persona adoption | 100% |
| `jailbreak` | Bypass safety guidelines via framing | 25% |
| `hallucination` | Elicit fabricated facts or citations | 0% |
| `pii_leakage` | Repeat or expose personal information | 0% |

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

## Key Findings

1. **Role confusion is the most exploitable category**: 100% ASR on Llama 3.3 and Qwen 32B, using soft-language persona prompts that bypass keyword filters. This is unvalidated judge output. It is also the one category where the validation study found the stored rate higher than the human-labelled rate (85.4% vs 69.7%, exploratory).

2. **System prompt hardening outperforms input filtering** as a single defense (-20% ASR vs -15%). Stacking all three produces non-additive results — some attacks bypass the full stack that individual defenses catch separately.

3. **Model size does not predict safety across all categories** — Llama 3.3 70B showed higher malware-adjacent ASR than Llama 3.1 8B, suggesting instruction-following capability can work against safety on exploit-framed prompts.

4. **Attack memory escalation is category-dependent** — static attacks held a stable ASR floor across 5 runs. PAIR-generated attacks showed measurable escalation in run 4, confirming the memory loop is effective for iteratively-refined dynamic attacks but cannot improve on already-saturated static prompts.

---

## References

- **PAIR**: Chao et al. (2023). *Jailbreaking Black Box Large Language Models in Twenty Queries.* [arXiv:2310.08419](https://arxiv.org/abs/2310.08419)
- **Many-shot jailbreaking**: Anthropic (2024). *Many-shot jailbreaking.* [anthropic.com/research](https://www.anthropic.com/research/many-shot-jailbreaking)
- **HarmBench**: Mazeika et al. (2024). *HarmBench: A Standardized Evaluation Framework for Automated Red Teaming.*

---

## Roadmap

- [ ] HTTP adapter — point the suite at any REST API endpoint, not just Groq models
- [ ] Multi-turn attack chains — maintain conversation state across attack iterations
- [ ] Benchmark against full HarmBench dataset (520 prompts)
- [ ] Findings report PDF with methodology and recommendations
- [ ] Risk scoring and severity classification per category