# IAM Reasoning Under Conflicting Policies

A reproducible, **single-turn** evaluation of whether language models can correctly resolve AWS IAM identity policies, optional permissions boundaries, and AWS Organizations service control policies (SCPs) on synthetic S3 access requests.

## Important scope

This is an **explicitly bounded IAM subset**, not a complete AWS IAM simulator, security analyzer, or authorization API. Every task assumes one same-account IAM principal, with no resource-based policies, sessions, RCPs, cross-account access, service-specific rules or other constraints. It covers Action / NotAction, Resource, `*` and `?` wildcards, StringEquals (literal), identity policy union, boundary and SCP intersections, and explicit Deny precedence. The small domain is stated in the model prompt. In particular, no AWS account or deployment is involved.

## Why it matters

Security and DevOps engineers investigate access denied incidents where one policy appears to grant an action but another rule limits it. Incorrect reasoning can prolong outages or encourage overly broad privileges. The hypothesis is that an LLM may confuse policy union with restrictive boundaries/SCPs, misapply wildcards, or overlook explicit denies.

## Eight synthetic tasks

| ID | Topic | Expected |
|---|---|---|
| 01 | Basic allow | ALLOW |
| 02 | Explicit deny precedence | DENY |
| 03 | Resource ARN mismatch | DENY |
| 04 | Wildcard action | ALLOW |
| 05 | NotAction deny exception | ALLOW |
| 06 | Permissions boundary intersection | DENY |
| 07 | Restrictive SCP intersection | DENY |
| 08 | Principal tag StringEquals mismatch | DENY |

All policy documents are synthetic and supplied in `tasks/`. Every scenario includes full request context. `reference/expected.json` provides author-reviewed intended answers. `graders/iam_oracle.py` independently recomputes answers from the provided policies; it is not a live AWS authorization simulator.

## Install and run (Windows PowerShell)

1. Install Python 3.11+ from https://www.python.org/downloads/ if not installed. Open PowerShell, `cd` to the extracted project folder.
2. Validate reference and grader using only Python standard library:

   ```powershell
   python -m unittest discover -s tests -v
   python run_eval.py --mode oracle
   ```

3. Install Ollama from https://ollama.com/download/windows, and reopen PowerShell. Ensure Ollama is running. Download a local model (internet needed once):

   ```powershell
   ollama pull llama3.2:3b
   ollama list
   ```

4. Run the model: 

   ```powershell
   python run_eval.py --mode ollama --model llama3.2:3b --trials 3
   ```

   This performs **8 x 3 = 24 model calls**. For a quick smoke test, add `--trials 1`; rerun with 3 for the submission. On CPU, local generation may take a while. No AWS login, paid API, cloud charge, Docker, Python package or API key is required.

5. Examine `results/trials.csv`, `results/summary.json`, and *every* `transcripts/*.json` before reporting findings. Include representative failure transcripts in submission.

If `python` does not work on Windows, try `py -3` instead. If Ollama is unreachable, start Ollama from the Start menu and verify `ollama list`. If memory is tight, try `ollama pull llama3.2:1b` and pass `--model llama3.2:1b`, but label this as a different model. A model returning invalid JSON fails formatting; errors are recorded, not silently treated as correct.

## Grading

Models receive a JSON task and a common system prompt. Their answer must be a JSON object with exactly `decision` (`ALLOW` or `DENY`) and a nonempty string `reason`. A deterministic code grader checks the complete response for valid schema and exact correct decision. It does **not** judge wording of the reason; reasons are retained for human failure analysis. Tests verify acceptance of all eight reference answers and rejection of their opposite decisions, as well as malformed answers and oracle corner cases. A correct output could still be reached by lucky guessing, so read reasons and repeated trials.

`pass_rate` is successes / attempts. `pass_power_k` is the fraction of tasks passed on **every** trial (an empirical pass^k). Three trials with temperature=0 test output repeatability but do not guarantee independent samples; vary seeds/temperature if more diversity is needed and record the settings. Each call starts with no previous conversation state.

## Reproducibility / budget

Python 3.11+ (standard library), local Ollama, `llama3.2:3b` (downloaded separately); temperature 0, `num_predict` 180, 240-second request timeout. Timestamp, model, per-trial latency and optional input/output token counts are stored. Model files are not included in ZIP. Run cost: **$0 in API/cloud charges**; hardware and power consumed locally. CPU runtime depends on PC.

## Results and limitations (fill out after running)

**Not yet benchmarked unless `results/summary.json` exists.** Do not report invented model failures. Record measured pass rate, pass^3, version (`ollama --version`, model tag and optionally `ollama show llama3.2:3b`), total runtime, and one real failure explanation based on its transcript. If all eight tasks are solved perfectly, honestly report that the current benchmark did not demonstrate a limitation; add independently expert-reviewed cases instead of claiming a failure.

The hackathon guide recommends testing at least one frontier model with several trials. A local small model alone may meet a participation goal but cannot demonstrate frontier model limitations. If accessible without payment, use the **same tasks, grading and settings disclosure** to evaluate a frontier model, save complete prompts and transcripts, and avoid claiming equivalence between local and frontier performance.

## Source and provenance

Policy rules informed by AWS official documentation:
- https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html
- https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic_policy-eval-denyallow.html
- https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html

Synthetic policy inputs, Python oracle, grade rules and harness created for this hackathon. No confidential data. Record the actual development date and all AI assistance honestly. **Author must manually review each task and oracle outcome before submission** and disclose that AI helped generate scaffold/policies/code if applicable.

## Submission

The participant guide describes one ZIP (max 50 MB) with code and README, one publicly accessible walkthrough video link (up to 5 minutes), and a short description. The kickoff **Instructions tab takes precedence** if its required files or format differ. Do not include model weights, credentials, or videos inside ZIP. ZIP the project *after* model evaluation so it contains saved results and transcripts.

Video outline: 1 min real IAM incident type and hypothesis; 1.5 min two tasks plus grader/unit tests; 2 min real model failure examples and results; 0.5 min takeaway.

Potential short description (edit after real tests): "This evaluation tests reasoning about conflicting AWS IAM identity policies, permissions boundaries, and Organizations SCPs on eight reproducible synthetic S3 authorization cases. A Python oracle and deterministic grader test whether the model correctly predicts ALLOW or DENY, while recorded model explanations reveal its reasoning mistakes. [Insert measured model name, pass rate and confirmed failure pattern after evaluating.]"
