# Submission notes: local-model baseline

## Short description draft

This evaluation tests AWS IAM permission reasoning on eight synthetic S3 access cases involving identity policies, explicit denies, permissions boundaries, SCPs, wildcards, and principal tags. A deterministic Python grader checks ALLOW/DENY decisions and saves complete model transcripts. Across three trials per task, local Llama 3.2 3B (Q4_K_M) passed 15 of 24 attempts (62.5%). It failed all trials involving explicit-deny precedence, boundary restrictions, and SCP restrictions, repeatedly citing an identity Allow despite the blocking policy. This is a local-model baseline; frontier models have not been tested.

## Walkthrough outline (under five minutes)

1. 0:00-0:45: Explain the access-denied troubleshooting problem and the narrowly defined policy scope. State that this run uses a small local model.
2. 0:45-1:30: Open tasks 02 and 06 and their reference explanations. Show the identity Allow and the policy that still blocks access. Explain that metadata and answers are withheld from the model.
3. 1:30-2:15: Run `python -m unittest discover -s tests -v` (17 tests) and `python run_eval.py --mode oracle`. Explain label grading, format checks, and why explanations still need inspection.
4. 2:15-3:45: Open `results/ANALYSIS.md` and two actual failing transcripts. Show the exact messages, model response, expected decision, and grade. Report 15/24 correct, 62.5% observed pass^3, zero format failures, and zero infrastructure errors. Do not present the test fixtures as model output.
5. 3:45-4:30: Explain the recurring failure: a valid identity grant is insufficient when a Deny, boundary, or SCP blocks the action. Acknowledge that correct labels alone do not prove correct reasoning.
6. 4:30-4:55: State the limits: one local model, simple synthetic tasks, correlated trials, pending frontier comparison and participant expert review. Disclose AI help and describe only the personal review actually completed.

Record and upload the video yourself. Confirm that its URL plays without requesting permission and with working audio. No video or public video URL has been created by this review.

## Before submitting

- Read the live HackerRank Instructions tab; it takes precedence over the supplied participant guide.
- Test at least one frontier model with multiple trials, as requested by the guide's checklist. The current local-only package does not satisfy that item.
- Personally inspect all eight tasks, reference answers, grading rules, and failure transcripts. Do not claim this review has already happened.
- Confirm what starter material existed before the event. The starter came from an earlier ChatGPT conversation; exact creation timing has not been established here.
- Edit the AI-assisted analysis and description to reflect your own reviewed conclusions.
- Supply the video URL and final description separately from the ZIP.

## Build the ZIP

```powershell
python package_submission.py
```

If Python is missing from PATH on this Codex machine:

```powershell
& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" package_submission.py
```

This writes `dist/iam-reasoning-eval.zip`, checks ZIP integrity and the 50 MB size limit, and includes code, documentation, tasks, references, test source, measured results, and transcripts. It excludes Git history, caches, virtual environments, model weights, the supplied PDF/chat, and unrelated files. Rebuild it after any changes to the final analysis or evidence. Do not describe the local-only ZIP as a complete frontier-model submission.
