# Prompting experiment: policy checklist

## Result

The same local Llama 3.2 3B model scored **21/24 (87.5%)** with the optional policy checklist, compared with **15/24 (62.5%)** using the original prompt. This is a 25-percentage-point increase on the existing eight tasks, not a new model or evidence of a general capability ceiling.

| Configuration | Correct | Pass rate | Observed pass^3 | Runtime | Format / infrastructure failures |
|---|---:|---:|---:|---:|---|
| Original Llama prompt | 15/24 | 62.5% | 62.5% | 228.344 s | 0 / 0 |
| Llama + policy checklist | 21/24 | 87.5% | 87.5% | 359.688 s | 0 / 0 |

All nine previously incorrect decisions on explicit deny, permissions boundaries, and SCPs became correct. However, all three NotAction-exception attempts changed from correct ALLOW to incorrect DENY. That is nine corrected decisions and three regressions, for a net gain of six. No task had mixed decision outcomes within its three trials.

| Task | Original correct | Checklist correct | Change |
|---|---:|---:|---|
| 01 basic allow | 3/3 | 3/3 | unchanged |
| 02 explicit deny | 0/3 | 3/3 | 3 gains |
| 03 resource mismatch | 3/3 | 3/3 | unchanged |
| 04 wildcard action | 3/3 | 3/3 | unchanged |
| 05 NotAction exception | 3/3 | 0/3 | 3 regressions |
| 06 boundary intersection | 0/3 | 3/3 | 3 gains |
| 07 SCP restriction | 0/3 | 3/3 | 3 gains |
| 08 tag mismatch | 3/3 | 3/3 | unchanged |

On this dataset, false ALLOW decisions fell from 9 to 0, while false DENY decisions rose from 0 to 3. That observation is limited to these cases and does not establish security or production reliability.

## What changed in the code

`run_eval.py` now accepts `--strategy baseline` (the unchanged default) and `--strategy policy-checklist`. The checklist appends a general procedure to the original system prompt: check matching explicit denies, identity Allows, boundary Allows, and SCP Allows; explain those findings briefly; then decide. It also requests the reason field before the decision field.

The task JSON, reference answers, grading rules, model weights/digest, quantization, Ollama version, temperature, seeds, token budget, and timeout were unchanged between the two local runs. No reference labels, worked task answers, oracle evaluations, or previous responses were supplied to the model. Each attempt remained one model call with no tools and a fresh two-message conversation. Every request and response is recorded. The model did not follow the requested reason-first key order; key order is not part of the unchanged decision/format grader.

## Better decisions do not prove correct explanations

All 24 checklist responses were read during AI-assisted review. The improved score hides factual mistakes in several explanations:

- [Task 02, trial 1](../transcripts/llama32-3b-policy-checklist/02_explicit_deny_trial1.json) correctly returns DENY and identifies the matching Deny, but falsely says that no identity Allow matches. A matching Allow is present and overridden.
- [Task 06, trial 1](../transcripts/llama32-3b-policy-checklist/06_boundary_intersection_trial1.json) correctly returns DENY and identifies the missing boundary Allow, but also incorrectly says the identity Allow does not match.
- [Task 07, trial 1](../transcripts/llama32-3b-policy-checklist/07_scp_restriction_trial1.json) correctly returns DENY and identifies the missing SCP Allow, while again denying that the identity Allow matches.
- [Task 05, trial 1](../transcripts/llama32-3b-policy-checklist/05_notaction_exception_trial1.json) incorrectly returns DENY and claims a matching explicit Deny. In fact, the Deny's NotAction excludes the requested GetObject, and a separate identity policy allows it.

These are genuine model outputs, not rewritten explanations. The existing grader measures decision correctness and JSON format; it does not validate every factual statement. A checklist prompt is therefore a measured mitigation with regressions, not a complete reasoning fix. The baseline remains the default so users do not silently change the original benchmark.

## Reproduce

```powershell
python run_eval.py --mode ollama --model llama3.2:3b --strategy policy-checklist --trials 3
```

Windows launcher:

```powershell
.\run.ps1 --mode ollama --model llama3.2:3b --strategy policy-checklist --trials 3
```

The saved experiment used `--run-id llama32-3b-policy-checklist`; choose a fresh ID to repeat it. See [summary](llama32-3b-policy-checklist/summary.json), [CSV](llama32-3b-policy-checklist/trials.csv), and [24 transcripts](../transcripts/llama32-3b-policy-checklist/).

Model digest: `a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72`; Q4_K_M; Ollama 0.40.13; Python 3.12.14; temperature 0; seeds 42, 43, 44 per task; generation cap 256; timeout 240 s; JSON mode. Dataset SHA-256 remains `ab3e03e4df6cbca20c29680ed8584f38cb6b4a041c3e286d2c991c023ed81e71`. Local API/AWS charges were $0; hardware and electricity were consumed.

## Interpretation and limits

This strategy was designed after examining failures on the same tasks. It is exploratory prompt tuning on a known dataset, not held-out validation. We tested one checklist variant and retained every trial. These low-temperature attempts are correlated, and the eight synthetic tasks do not establish general AWS IAM reliability. Runtime figures are single-run measurements and include a longer prompt and longer output.

The observed lesson is that prompt design affects the measured score, and that fixing one error pattern can introduce another. Original Llama results, the Codex frontier run, and manual prompts remain intact. GPT-6.1 Sol was not tested with this new checklist prompt; its original 24/24 result still provides no frontier-model failure. See [the baseline model comparison](COMPARISON.md).
