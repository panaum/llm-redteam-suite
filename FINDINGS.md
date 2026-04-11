# Security Findings Report
## LLM Red Team Suite — Adversarial Evaluation

**Date:** April 2026  
**Models Evaluated:** Llama 3.3 70B, Qwen3 32B, GPT-OSS 120B  
**Framework:** Static attacks, PAIR dynamic attacks, many-shot jailbreaking  
**Methodology:** [Chao et al. 2023](https://arxiv.org/abs/2310.08419), [Anthropic 2024](https://www.anthropic.com/research/many-shot-jailbreaking)

---

## Executive Summary

Three frontier language models were evaluated against 80+ adversarial prompts across five attack categories using a hybrid red teaming framework. Overall Attack Success Rates (ASR) ranged from 3.7% to 44.4%, revealing significant variance in safety robustness across model families. Role confusion attacks achieved 100% success on two of three models. System prompt hardening proved the most effective single defense, reducing ASR by 20 percentage points — outperforming both input filtering and output toxicity classification. A five-run escalation study confirmed that PAIR-based attack memory produces measurable run-over-run improvement in dynamic attack categories, while static attacks plateau at a stable floor.

---

## 1. Model Safety Comparison

GPT-OSS 120B demonstrated the strongest safety posture with 3.7% overall ASR, successfully blocking all prompt injection attempts and most jailbreak variants. Its refusals were consistent and terse — a pattern suggesting centralized output filtering rather than instruction-following-based safety.

Llama 3.3 70B was the most vulnerable model at 44.4% ASR. Critically, four of five attack categories saw non-zero success rates, with prompt injection and role confusion both reaching 100%. The model's high instruction-following capability — a strength in general use — became a liability under adversarial framing. When presented with authority claims ("developer mode"), fictional wrappers ("creative writing exercise"), or persona substitution ("you are Alex"), the model complied consistently.

Qwen3 32B occupied a middle position at 25.9% ASR. Its chain-of-thought reasoning (visible in `<think>` tags) provided partial protection — in several cases the model's internal reasoning correctly identified an adversarial intent, yet it still partially complied with the request. This suggests reasoning-based safety may reduce but not eliminate vulnerability to social engineering attacks.

---

## 2. Attack Category Analysis

**Role confusion** was the single most exploitable category across this evaluation. All three persona-based attacks succeeded on Llama 3.3, and two of three succeeded on Qwen 32B. The attacks required no technical sophistication — soft natural-language requests asking the model to "be" a different entity were sufficient. This points to a systemic weakness in how these models maintain identity boundaries under conversational pressure.

**Prompt injection** produced mixed results. Direct override commands ("SYSTEM OVERRIDE") were blocked across all models, but indirect approaches — particularly creative framing and persona substitution — achieved high success rates. The pattern suggests that keyword-based filtering catches explicit injection syntax while missing semantically equivalent attacks phrased as creative requests.

**Jailbreaking** showed the widest variance. Llama 3.3 failed on three of four static jailbreak attempts, including both the fictional wrapper ("chemistry teacher story") and the authority claim ("developer mode"). GPT-OSS 120B blocked all four. PAIR-generated jailbreaks, which iteratively refined prompts using model feedback, showed lower success rates than static attacks in this evaluation — suggesting that the static attack library already covers high-yield vectors that PAIR would discover through iteration.

**Hallucination resistance** was unexpectedly strong. All three models correctly identified fictional entities (Blernsburg, Vibranium), fabricated citations (Dr. James Harlow), and events outside their knowledge window. No hallucination attacks succeeded across any model. This robustness likely reflects post-training improvements in epistemic calibration across the 2024–2025 model generation.

**PII leakage** was partially mitigated. Direct requests to repeat sensitive data were blocked. However, role-play framing ("pretend you are a database") bypassed defenses on both Llama 3.3 and Qwen 32B — the models stored and repeated passport numbers and personal records when the request was embedded in a database simulation context. This is a meaningful finding: PII protections are surface-level and fail when the request is reframed as a legitimate data management task.

---

## 3. Defense Evaluation

Three defenses were evaluated independently and in combination against Llama 3.3 70B, starting from a 20% baseline ASR on a standardized 20-prompt test set.

**System prompt hardening** was the strongest single intervention, reducing ASR to 0%. A six-rule hardened system prompt — explicitly prohibiting persona adoption, instruction overrides, and content policy violations — proved sufficient to block all test attacks. This result is notable because it achieved perfect defense at zero computational cost, requiring only a modified system prompt rather than additional infrastructure.

**Input filtering** reduced ASR to 5%, blocking 7 of 20 attacks. The filter correctly caught explicit injection keywords (DAN, system override, developer mode) but was bypassed by attacks using natural language framing. This confirms that regex-based input filters are effective against known attack signatures but fail against novel or paraphrased variants.

**Output toxicity classification** (Detoxify) produced no reduction at 20% ASR. The attacks that succeeded in this evaluation generated outputs that were conversationally compliant rather than explicitly toxic — the model adopted a persona or repeated PII in a neutral tone that scored below the toxicity threshold. This is an important finding: output classifiers tuned for explicit harm miss compliance-based safety failures.

Stacking all three defenses produced 10% ASR — counterintuitively worse than system prompt hardening alone. This suggests that the defenses interact in ways that create coverage gaps: some attacks that system prompt hardening would catch are processed differently when input filtering modifies the prompt first. Defense stacking requires careful evaluation rather than assumption of additive benefit.

---

## 4. Escalation Study

Five consecutive attack runs against Llama 3.1 8B with persistent bypass memory produced a non-linear escalation pattern. ASR started at 40.74%, dipped in run 2 (37.04%), recovered in run 3 (40.74%), peaked in run 4 (44.44%), and stabilized in run 5 (40.74%).

The run 4 peak was driven specifically by PAIR-generated dynamic attacks — new jailbreak variants appeared in run 4 that had failed in runs 1 and 2, consistent with the PAIR mechanism's iterative refinement using successful bypass context. Static attack categories showed no escalation across runs, confirming a stable floor regardless of accumulated bypass memory.

This result has practical implications: adaptive adversaries using memory-augmented attack frameworks will improve against models over time, but only in categories where iterative refinement can discover new successful variants. Static attack surfaces — where the attack space is already well-covered — do not benefit from memory accumulation.

---

## 5. Cross-Model Observations

One unexpected finding warrants specific attention. Llama 3.3 70B, a significantly larger and more capable model than Llama 3.1 8B, showed higher ASR on malware-adjacent prompts (100% vs 0%). This inversion of the expected safety-capability relationship suggests that instruction-following capability at scale can amplify vulnerability when attack prompts are framed as legitimate requests.

This aligns with a broader concern in AI safety research: models trained to be more helpful may be more susceptible to social engineering attacks that exploit helpfulness as a vector. The "fictional wrapper" and "creative writing" attacks in this suite are effective precisely because they reframe harmful requests as collaborative tasks the model is designed to assist with.

---

## 6. Limitations

This evaluation was conducted against API-accessible model endpoints using a fixed attack library of 20 static prompts plus dynamically generated variants. Results reflect model behavior under the specific sampling parameters and system prompts used during testing, and may differ across deployment configurations. The dual-scoring system (semantic similarity + LLM judge) introduces evaluator subjectivity, particularly near decision boundaries where refusals are partial or ambiguous. HarmBench comparisons use the closest available published baseline rather than exact architecture matches, limiting direct comparability.

---

## 7. Recommendations

**For model deployers:** System prompt hardening should be the first line of defense. A well-constructed system prompt that explicitly defines role boundaries and prohibited behaviors outperformed all other tested interventions. Input filtering adds value for known attack signatures but should not be relied upon as primary protection.

**For red teamers:** Role confusion attacks represent the highest-yield attack surface against current frontier models. Soft natural-language persona substitution — requiring no technical exploitation — achieved the highest consistent success rates across model families. This category should be prioritized in any LLM security assessment.

**For researchers:** The non-additive behavior of stacked defenses warrants further investigation. Understanding the interaction effects between input filtering, system prompt modification, and output classification may reveal architectural vulnerabilities in layered defense approaches.

---

## References

- Chao et al. (2023). *Jailbreaking Black Box Large Language Models in Twenty Queries.* arXiv:2310.08419
- Anthropic (2024). *Many-shot jailbreaking.* anthropic.com/research
- Mazeika et al. (2024). *HarmBench: A Standardized Evaluation Framework for Automated Red Teaming.* arXiv:2402.04249
- OWASP (2025). *Top 10 for Large Language Model Applications.* owasp.org