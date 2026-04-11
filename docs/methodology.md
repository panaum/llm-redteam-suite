\# Methodology



\## 1. Threat Model



This framework evaluates LLM systems against adversarial behaviors observed in real-world deployments, including:



\- Prompt injection (instruction override)

\- Jailbreaking (policy bypass through framing)

\- Role confusion (persona manipulation)

\- Hallucination (fabricated outputs)

\- PII leakage (sensitive data exposure)



The objective is to simulate adaptive attackers that iteratively refine prompts to exploit model weaknesses.



\---



\## 2. Attack Strategy



The system employs a hybrid attack approach combining static and adaptive techniques:



\### 2.1 Static Attack Library

A fixed set of 20 adversarial prompts across five categories:

\- prompt\_injection

\- role\_confusion

\- jailbreak

\- hallucination

\- pii\_leakage



These provide baseline coverage and allow consistent cross-model comparison.



\### 2.2 Dynamic PAIR Attacks

Based on PAIR (Chao et al., 2023), an attacker LLM generates adversarial prompts and iteratively refines them using feedback from the target model’s responses.



A persistent memory system (SQLite) stores successful bypasses and injects them into future runs, enabling:

\- Progressive attack refinement

\- Cross-run learning

\- Emergent attack escalation



\### 2.3 Many-Shot Jailbreaking

Implements context-length exploitation by generating multiple benign-looking Q\&A examples that gradually normalize restricted behavior before issuing the final attack.



\---



\## 3. Execution Pipeline



Each run follows a structured pipeline:



1\. Load static attacks and historical bypass memory

2\. Generate dynamic attacks via PAIR

3\. Execute many-shot jailbreak sequences

4\. Send all prompts to target model APIs

5\. Collect and store responses

6\. Evaluate responses using dual scoring



This pipeline supports multi-model benchmarking and reproducible experiments.



\---



\## 4. Evaluation Framework



The system uses a dual-scoring approach to improve robustness:



\### 4.1 Semantic Similarity Scoring

Uses `sentence-transformers` (all-MiniLM-L6-v2) to compute cosine similarity between responses and predefined:

\- refusal anchors

\- compliance anchors



This avoids brittle keyword matching and captures paraphrased behaviors.



\### 4.2 LLM-Based Judging

A secondary LLM evaluates whether the response demonstrates successful manipulation.



\### 4.3 Decision Rule

An attack is marked successful if \*\*either scorer detects a failure\*\*, prioritizing recall over precision in vulnerability detection.



Attack Success Rate (ASR) is computed per category and per model.



\---



\## 5. Defense Evaluation



The framework evaluates three independent defense mechanisms:



\- Input filtering (regex-based prompt detection)

\- System prompt hardening (rule-based behavioral constraints)

\- Output toxicity classification (Detoxify)



Defenses are tested:

\- Individually

\- In combination (stacked)



This enables measurement of:

\- Absolute effectiveness

\- Interaction effects between defenses



\---



\## 6. Experimentation Design



The system supports structured experimental workflows:



\### 6.1 Multi-Model Benchmarking

Compares ASR across different model architectures and sizes.



\### 6.2 HarmBench Comparison

Aligns results with standardized evaluation baselines for external validity.



\### 6.3 Escalation Studies

Runs consecutive attack cycles with persistent memory enabled to measure:

\- Attack improvement over time

\- Category-specific escalation behavior



\---



\## 7. Data Persistence \& Memory



All runs are stored in SQLite, including:

\- Prompts

\- Responses

\- Success/failure labels

\- Model metadata



Successful attacks are reused in future runs, enabling a feedback loop that simulates adaptive adversaries.



\---



\## 8. Output \& Reporting



Results are generated in multiple formats:



\- JSON logs for reproducibility and analysis

\- HTML reports summarizing vulnerabilities

\- Dashboard visualizations for quick inspection



\---



\## 9. Limitations



\- Semantic scoring may misclassify nuanced responses

\- LLM-based judging introduces evaluator bias

\- Static attack coverage is limited to predefined templates

\- Memory loop benefits dynamic attacks but not saturated categories

\- Results vary across model configurations and sampling parameters



\---



\## 10. Future Work



\- Multi-turn attack chains with conversational state

\- Expanded prompt libraries (e.g., full HarmBench dataset)

\- Risk scoring and severity classification

\- API abstraction for testing production LLM applications

