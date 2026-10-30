# Submission notes: two-model baseline

## Short description draft

This evaluation tests AWS IAM permission reasoning on eight synthetic S3 access cases involving identity policies, explicit denies, permissions boundaries, SCPs, wildcards, and principal tags. A deterministic Python grader checks ALLOW/DENY decisions and saves model transcripts. Across three trials per task, local Llama 3.2 3B Q4_K_M passed 15/24 attempts (62.5%), failing all trials on explicit-deny precedence, boundary restrictions, and SCP restrictions. GPT-6.1 Sol at High reasoning passed 24/24 in separate manual Codex chats. An optional policy-checklist prompt raised Llama to 21/24 (87.5%), while introducing NotAction regressions and retaining some false explanations. The result shows prompt-sensitive weaknesses in the tested small model and a task-difficulty ceiling for the stronger model; it does not demonstrate a frontier-model failure. Collection interfaces and inference settings differed and are disclosed.

## Walkthrough outline (under five minutes)

1. 0:00-0:45: Explain the access-denied troubleshooting problem, eight-task scope, and two tested models. These are synthetic same-account S3 scenarios, not a full IAM simulator.
2. 0:45-1:30: Open tasks 02 and 06 and their reference explanations. Show why an identity Allow is insufficient when an explicit Deny or permissions boundary applies. Explain that answers and descriptive task labels are withheld.
3. 1:30-2:15: Run `python -m unittest discover -s tests -v`, `python run_eval.py --mode oracle`, and `python import_manual.py --verify`. Explain that the grader checks decision labels and schema, while explanations require separate inspection. Saved-evidence verification does not rerun inference.
4. 2:15-3:45: Show `results/COMPARISON.md`: Llama 15/24 versus GPT-6.1 Sol High 24/24. Walk through one genuine Llama failure beside the correct Sol response on the same task. Both have 3 trials per task. Explain that Codex collected a combined user prompt and different runtime/settings; this is not a controlled API replication.
5. 3:45-4:30: Show the optional policy-checklist experiment: Llama rose to 21/24 (87.5%), correcting the original three failing task types but regressing on NotAction. Explain that even some correct labels have false explanations. State clearly that Sol solved all baseline cases, so these tasks reveal no frontier weakness.
6. 4:30-4:55: Disclose AI assistance, prior starter material, and only the personal review actually completed. Point to complete results and transcripts. Note the unknown Codex account cost and unavailable decoding settings rather than claiming identical settings or a free API run.

Record and upload the video yourself. Confirm its URL plays without requesting permission and with working audio. No video or public video URL has been created here. Any earlier narration script describing only the local model is now outdated; use this outline covering both models and the optional prompting experiment.

## Before submitting

- Read the live HackerRank Instructions tab and verify the final required format. It has not been supplied or checked here.
- Frontier testing is now recorded, but the model solved every task. Decide whether to submit this honest baseline or strengthen it with more realistic expert-designed cases and a new round of testing. Do not claim the baseline exposes a frontier-model weakness.
- Personally inspect all eight tasks, references, grading rules, both models, the optional prompting experiment, and the analysis. This review remains participant work.
- Confirm what starter material existed before the event. The starter came from an earlier ChatGPT conversation; exact creation timing remains unestablished.
- Edit the AI-assisted analysis and description to reflect your own reviewed conclusions.
- Record and publish the walkthrough, then supply its URL and the final description separately from the ZIP.

## Build and verify the ZIP

```powershell
python package_submission.py
```

If Python is missing from PATH on this Codex machine:

```powershell
& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" package_submission.py
```

The script writes `dist/iam-reasoning-eval.zip`, checks integrity and the 50 MB limit, and includes both models plus the optional checklist run, 72 graded transcripts, manual prompt/evidence files, code, tests, and documentation. It excludes Git history, caches, virtual environments, model weights, the supplied PDF/chat, and unrelated local Codex logs. Rebuild after changes. The separate manual-frontier-prompts.zip is a collection aid, not the final submission package.
