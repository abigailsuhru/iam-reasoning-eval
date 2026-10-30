# Reviewed local baseline

Run: `llama32-3b-baseline`, October 31, 2026, approximately 00:48-00:52 IST (UTC timestamps are October 30). All 24 saved outputs were read during the AI-assisted review. Participant expert review remains outstanding.

| Model | Trials per task | Passed | Pass rate | Observed pass^3 | Observed pass@3 | Runtime | API/AWS cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| llama3.2:3b, Q4_K_M | 3 | 15/24 | 62.5% | 62.5% | 62.5% | 228.344 s | $0 |

All 24 outputs passed the JSON schema. There were **9 wrong decisions, 0 formatting failures, and 0 infrastructure errors**. Five tasks passed all trials and three failed all trials; no task had mixed decision outcomes. This describes repeatability across these three low-diversity trials, not a confidence interval or an estimate of independent success probability.

## Per-task evidence

| Task | Expected | Predictions | Passes | Observation and representative transcript |
|---|---|---|---|---|
| 01 basic allow | ALLOW | ALLOW / ALLOW / ALLOW | 3/3 | [Baseline control](../transcripts/llama32-3b-baseline/01_basic_allow_trial1.json): matching identity grant recognized |
| 02 explicit deny | DENY | ALLOW / ALLOW / ALLOW | 0/3 | [Failure](../transcripts/llama32-3b-baseline/02_explicit_deny_trial1.json): cites Allow despite an applicable explicit Deny |
| 03 resource mismatch | DENY | DENY / DENY / DENY | 3/3 | [Correct rejection](../transcripts/llama32-3b-baseline/03_resource_mismatch_trial1.json): requested resource not allowed |
| 04 wildcard action | ALLOW | ALLOW / ALLOW / ALLOW | 3/3 | [Correct label](../transcripts/llama32-3b-baseline/04_wildcard_action_trial1.json): explanation cites identity grant |
| 05 NotAction exception | ALLOW | ALLOW / ALLOW / ALLOW | 3/3 | [Correct label, limited explanation](../transcripts/llama32-3b-baseline/05_notaction_exception_trial1.json): does not explain why the Deny is excluded |
| 06 boundary intersection | DENY | ALLOW / ALLOW / ALLOW | 0/3 | [Failure](../transcripts/llama32-3b-baseline/06_boundary_intersection_trial1.json): cites identity grant without applying restrictive boundary |
| 07 SCP intersection | DENY | ALLOW / ALLOW / ALLOW | 0/3 | [Failure](../transcripts/llama32-3b-baseline/07_scp_restriction_trial1.json): cites identity grant despite restrictive SCP |
| 08 tag condition | DENY | DENY / DENY / DENY | 3/3 | [Correct rejection](../transcripts/llama32-3b-baseline/08_condition_mismatch_trial1.json): mismatched tag condition |

## What the failures support

Task 02's first answer is `ALLOW`, with reason: "Identity-based policy allows the action". One policy does allow GetObject, but the second explicitly denies this exact request. All three trials give the same wrong label and explanation. The matching Deny should override the Allow.

Tasks 06 and 07 each return `ALLOW` in all three trials, with reason: "Identity-based policy allows s3:GetObject on the specified resource". That statement about the identity grant is true but insufficient: the boundary and SCP respectively allow only ListBucket. Neither permits the requested GetObject. These are the closest-to-correct failures: the model identifies a real grant but reaches the wrong final authorization decision.

Across these cases, the observable pattern is an answer justified solely by an identity Allow even when another policy blocks the request. This is consistent with incomplete policy aggregation. The brief explanations do not establish the model's internal reasoning process. In access-denied troubleshooting, accepting this answer could distract an engineer from the restriction actually blocking access.

Task 05 illustrates a scoring limit. The model gives the correct ALLOW label but only mentions the identity grant; it never explains the NotAction exception. The grader correctly passes the requested decision, but this cannot prove that the model understood every applicable rule. Explanation quality is not automatically scored.

## Reproduce and audit

```powershell
python -m unittest discover -s tests -v
python run_eval.py --mode oracle
python run_eval.py --mode ollama --model llama3.2:3b --trials 3 --temperature 0 --seed 42 --num-predict 256 --timeout 240
```

On this Windows machine, replace `python run_eval.py` with `.\run.ps1` if Python is not on PATH. Run IDs default to unique timestamps. The recorded run used `--run-id llama32-3b-baseline`; do not reuse it or delete the original evidence to rerun.

Python 3.12.14; Ollama 0.40.13; Windows 11; model digest `a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72`; 3.2B parameters; Q4_K_M quantization. Temperature 0; seeds 42, 43, 44 for each task; max generation 256 tokens; timeout 240 s; provider JSON mode. Each call receives exactly one system and one user message and no conversation history.

See [machine-readable summary](llama32-3b-baseline/summary.json), [trial CSV](llama32-3b-baseline/trials.csv), and all [24 transcripts](../transcripts/llama32-3b-baseline/). Dataset SHA-256: `ab3e03e4df6cbca20c29680ed8584f38cb6b4a041c3e286d2c991c023ed81e71` (canonical sorted-key JSON of the task list as loaded by the harness).

## Limits and next evidence needed

Only one small local model was measured. These results do not establish a frontier-model limitation, generalize to all Llama models, or validate the oracle against the AWS service. The task set is small, synthetic, and simple; zero-temperature trials are correlated. Prompts explicitly teach the bounded rules, so the benchmark measures applying those supplied rules rather than recalling all of AWS IAM. No task was changed after model failures were observed.

The technically useful finding is that this local model can identify a matching grant yet still produce the wrong final access decision. A stronger hackathon submission needs the same tasks tested on at least one frontier model, with additional expert-designed cases if stronger models solve these easily. The participant must personally review all tasks, answers, grader rules, and this analysis. A subsequent participant-collected GPT-6.1 Sol High run passed all 24 attempts; see COMPARISON.md. That adds frontier testing but does not demonstrate a frontier weakness. The video, public video URL, and official submission form remain participant work.
