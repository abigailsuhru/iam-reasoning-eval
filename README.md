# IAM Reasoning Under Conflicting Policies

A single-turn evaluation of whether a language model can apply conflicting AWS IAM permissions to synthetic S3 access requests. It targets access-denied troubleshooting: a matching identity Allow may still be restricted by an explicit Deny, a permissions boundary, or an Organizations service control policy (SCP).

This is a bounded reasoning benchmark, not an AWS authorization simulator or a tool for deciding real production access. No AWS account, credentials, or deployment is required.

## Quick start

Python 3.11+ and its standard library are sufficient. No pip packages are required. For inference, install [Ollama](https://ollama.com/download/windows) and download `llama3.2:3b`.

```powershell
python -m unittest discover -s tests -v
python run_eval.py --mode oracle
ollama pull llama3.2:3b
python run_eval.py --mode ollama --model llama3.2:3b --trials 3
```

On Windows, if `python` is missing from PATH, this project includes a launcher:

```powershell
.\run.ps1 -Test
.\run.ps1 --mode oracle
.\run.ps1 --mode ollama --model llama3.2:3b --trials 3
```

The launcher checks `python`, `py -3`, then the optional Codex bundled Python. Judges can use any normal Python 3.11+ installation; Codex is not a dependency. Ollama must be running and the model installed. Preflight failures stop before creating model evidence. Start Ollama and check `ollama list` if it is unreachable.

Each run saves `results/<run-id>/trials.csv`, `results/<run-id>/summary.json`, and `transcripts/<run-id>/*.json`. The default run ID is a UTC timestamp; `--run-id my-run` gives it a name. An existing ID is rejected so earlier results cannot be overwritten. The CSV is checkpointed after every trial. An interrupted run has partial evidence and no completed summary.

## Tasks and defensible reference answers

| ID | Task | Expected | Rule being tested |
|---|---|---|---|
| 01 | Matching identity permission | ALLOW | Baseline control |
| 02 | Conflicting identity policies | DENY | An applicable explicit Deny overrides an Allow |
| 03 | Permission in a different bucket | DENY | The resource must match |
| 04 | Wildcard action permission | ALLOW | `s3:Get*` matches GetObject |
| 05 | Read action excluded from a NotAction Deny | ALLOW | A nonapplicable Deny does not cancel a separate Allow |
| 06 | Boundary allows only ListBucket | DENY | Identity and boundary permissions intersect |
| 07 | SCP allows only ListBucket | DENY | Identity and SCP permissions intersect |
| 08 | Principal tag mismatch | DENY | StringEquals condition must match |

`reference/expected.json` stores decision labels. `reference/solutions.json` contains complete reference answers and explanations that pass the same grader as model outputs. Tests check every reference and reject opposite decisions. These references were reviewed by AI against the policies and official documentation; participant expert review is still required.

The system prompt supplies the rules and the user prompt supplies the request and policies. Task IDs, descriptive scenarios, reference answers, and grading code are withheld. The original scaffold exposed answer-revealing descriptions; the corrected run does not. Tasks were retained from the starter rather than selected after observing failures. These are basic diagnostic cases, not a claim of frontier-level difficulty.

## Exact scope

One same-account IAM user in an Organizations member account. Only identity policies, an optional permissions boundary, and an optional account-level SCP apply. The supplied SCP is the sole policy at that account level and ancestors allow everything. There are no resource-based grants, cross-account access, session policies, RCPs, root/service-linked-role exemptions, or service-specific checks.

Supported syntax: policy version `2012-10-17`, Action/NotAction, Resource/NotResource, string or list patterns with only `*` and `?`, and StringEquals with single-valued string request context. Action matching and condition-key names are case-insensitive; resource and StringEquals value matching are case-sensitive. Missing condition keys do not match. Identity permissions form a union; boundaries and the supplied SCP restrict that union. Applicable explicit denies take precedence.

Unsupported statement fields, condition operators, policy variables, multivalued context, and malformed policies are rejected, including in statements that do not match the request. The oracle is deliberately small and not independently validated by the live AWS IAM simulator.

## Grading and metrics

Responses must be one JSON object with exactly `decision` (ALLOW or DENY) and a nonempty string `reason`. The deterministic grader checks the whole response, rejects duplicate keys and invalid schemas, and compares the decision. It does not score the explanation. A passing label with a wrong explanation is possible; inspect transcripts before claiming sound reasoning.

The regression suite covers known-correct and deliberately wrong answers, malformed outputs, IAM wildcard semantics, condition-key case, identity union, restrictive boundaries, NotResource, SCP syntax, unsupported inputs, prompt leakage, provider failures, metric calculations, and preservation of exact messages and previous evidence. Provider fixtures in tests are synthetic and never reported as benchmark evidence.

- `pass_rate`: correct, correctly formatted responses divided by all attempted trials.
- `pass_at_k`: fraction of tasks solved at least once in the observed k trials.
- `pass_power_k`: fraction of tasks solved in every observed trial (empirical pass^k).
- `infrastructure_errors`, `format_failures`, `decision_failures`: separate counts. A connection error is not evidence of an IAM reasoning limitation.

Defaults: temperature 0, seeds 42/43/44 for three trials, `num_predict=256`, timeout 240 seconds, Ollama JSON output mode. Options: `--temperature`, `--seed`, `--num-predict`, `--timeout`. Every trial starts with a new two-message conversation. Zero-temperature trials are correlated and can repeat identical outputs; these metrics describe observed repeatability, not independent statistical estimates. Provider prompt caching does not add previous conversation messages.

## Measured results

See [the baseline report](results/ANALYSIS.md) for measured scores, runtime, per-task results, and links to genuine transcripts. The run metadata includes the Python/Ollama versions, model digest and quantization, dataset SHA-256, decoding options, timestamps, and platform. Transcripts retain the exact request payload and complete provider response, including token counts, timing, and stop reason when returned.

Only the installed local `llama3.2:3b` model has been tested. This does **not** establish a frontier-model limitation or cross-model spread. The participant confirmed access to local Ollama only. No API or AWS charges are incurred; local electricity and hardware still have costs. Results can vary with model digest, runtime version, hardware, and inference backend.

## Sources and provenance

Policies are synthetic; no customer data or external benchmark tasks were used. The starter code and eight tasks were supplied from an earlier ChatGPT conversation. During this review, Codex corrected the grader, oracle, prompt isolation, SCP example, and evidence collection; expanded regression checks and reference explanations; ran local model trials; and drafted the analysis and submission notes. The participant must confirm which starter material predates the event and personally review the tasks, references, grader, and analysis before submission. Do not describe AI review as human expert review.

Official sources checked during this review:

- [AWS policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html): explicit denies and policy intersections.
- [AWS resource elements](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_resource.html): `*` and `?` wildcards.
- [AWS condition elements](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_condition.html): condition-key names versus value case.
- [SCP syntax](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps_syntax.html): Allow statements require Resource `*`. Task 07 was corrected accordingly, without changing its expected denial.

## Hackathon status and packaging

The supplied participant guide supports a focused single-turn eval with roughly 5-10 tasks, reference solutions, deterministic grading, repeated trials, saved transcripts, reproducible commands, and disclosed AI assistance. This project supplies those technical pieces.

Outstanding: the guide's checklist asks for at least one frontier model with multiple trials. That comparison has not been performed. The participant must also complete personal expert review, supply accurate prior-work provenance, record a publicly accessible walkthrough of up to five minutes, and check the live HackerRank Instructions tab. Those instructions take precedence over the participant guide; they were not supplied or checked here.

See [submission notes](SUBMISSION.md) for a video outline and description grounded in the actual local run. The guide requests a ZIP under 50 MB containing code, README, results, and transcripts, plus a separate video URL and short description. Exclude `.git`, caches, virtual environments, credentials, and model weights. A local-only package should be labeled as such; it is not a completed frontier-model submission.
