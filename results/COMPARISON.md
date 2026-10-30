# Model comparison: eight-task baseline

## Headline result

| Model / collection interface | Trials per task | Correct | Pass rate | Observed pass^3 | Observed pass@3 | Recorded duration | Cost |
|---|---:|---:|---:|---:|---:|---|---|
| Llama 3.2 3B Q4_K_M / local Ollama | 3 | 15/24 | 62.5% | 62.5% | 62.5% | 228.344 s harness runtime | $0 API/AWS; local resources consumed |
| GPT-6.1 Sol, High / manual Codex chats | 3 | 24/24 | 100% | 100% | 100% | 78.390 s summed app turn durations; 31 min 20 s collection window | Account subscription/usage cost not measured |

The eight tasks and final-answer grader are shared. The interfaces differ: Ollama received system and user messages with JSON mode, temperature 0, recorded seeds, and a token limit; Codex received the combined text as a user message plus an instruction prohibiting tools, with High reasoning and additional runtime instructions. This comparison is descriptive. It does not isolate model identity as the cause of the score difference, and recorded durations are not a controlled speed comparison.

**The tested frontier model did not fail any baseline task.** The benchmark demonstrates a repeatable weakness in the tested small local model, plus a ceiling for these tasks on the selected stronger model. It does not establish a frontier-model limitation.

## Per-task comparison and evidence

| Task | Llama correct | GPT-6.1 Sol High correct | Representative frontier response |
|---|---:|---:|---|
| 01 identity allow | 3/3 | 3/3 | [Transcript](../transcripts/gpt61-sol-high-manual/01_basic_allow_trial1.json) |
| 02 explicit deny | 0/3 | 3/3 | [Transcript](../transcripts/gpt61-sol-high-manual/02_explicit_deny_trial1.json) |
| 03 resource mismatch | 3/3 | 3/3 | [Transcript](../transcripts/gpt61-sol-high-manual/03_resource_mismatch_trial1.json) |
| 04 wildcard action | 3/3 | 3/3 | [Transcript](../transcripts/gpt61-sol-high-manual/04_wildcard_action_trial1.json) |
| 05 NotAction exception | 3/3 | 3/3 | [Transcript](../transcripts/gpt61-sol-high-manual/05_notaction_exception_trial1.json) |
| 06 permissions boundary | 0/3 | 3/3 | [Transcript](../transcripts/gpt61-sol-high-manual/06_boundary_intersection_trial1.json) |
| 07 SCP restriction | 0/3 | 3/3 | [Transcript](../transcripts/gpt61-sol-high-manual/07_scp_restriction_trial1.json) |
| 08 tag condition | 3/3 | 3/3 | [Transcript](../transcripts/gpt61-sol-high-manual/08_condition_mismatch_trial1.json) |

All 24 frontier answers were read during the AI-assisted review. Explanations correctly identify the explicit deny, boundary restriction, SCP restriction, and mismatched tag in their corresponding tasks. They also identify the NotAction exception. Grading still checks labels and format rather than scoring explanations automatically. No failure transcripts exist for this frontier run; none should be invented.

## What was captured and checked

The participant ran 24 distinct Codex chats named IAM-prompt01-trial1 through IAM-prompt08-trial3. Each app export has one completed turn, one benchmark user message, and one final response. All pasted prompts match the prepared prompts after removing trailing whitespace only. The 24 responses were saved verbatim; no JSON was reformatted or extracted from surrounding prose.

Selected local session records independently confirm model ID `gpt-6.1-sol`, reasoning effort `high`, and Codex runtime `0.165.0-alpha.1.2` throughout. No function calls, custom tool calls, or web-search calls were observed. Reasoning indicators labeled Thinking are not tool use. The standard runtime also supplied environment and null-open-page context; this was not a bare API call. This audit does not prove absence of all hidden context or provide private latent reasoning.

The original participant-entered CSV is preserved as [collection_sheet.user_entered.csv](../manual_frontier/collection_sheet.user_entered.csv). The [updated collection sheet](../manual_frontier/collection_sheet.csv) uses logged UTC turn-start timestamps converted to CET, includes the date, and replaces Thinking with None observed (session audit). Those timestamps fall on October 30, 2026 in CET and October 31 in IST. Task 05 trial 1 was collected last, consistent with its recorded 23:02 CET time; row order is task order, not chronological order.

Evidence files:

- [24 raw response TXT files](../manual_frontier/responses/).
- [App-exported chats](../manual_frontier/chat_exports/collected_threads.json): visible user messages, available reasoning indicators, final answers, turn metadata, and IDs. This is not an export of inaccessible internal reasoning or every hidden runtime instruction.
- [Selected session audit metadata](../manual_frontier/session_audit.json): model, effort, timestamps, activity checks, and source-log hashes. Private full runtime logs are not bundled.
- [Machine-readable summary](gpt61-sol-high-manual/summary.json) and [trial CSV](gpt61-sol-high-manual/trials.csv).
- [Local failure analysis](ANALYSIS.md) and all local transcripts.

## Reproduce grading

```powershell
python -m unittest discover -s tests -v
python run_eval.py --mode oracle
python import_manual.py --verify
```

These commands validate code and regrade saved evidence without model calls. Repeating inference requires the same model access and fresh chats following `manual_frontier/README.md`; outcomes and runtime can change. Temperature, seed, token cap, immutable model snapshot, and per-run Codex account cost were not exposed and are not copied from the Ollama settings.

## Submission implications

The project now includes repeated testing of a stronger model, cross-model results, and recorded transcripts. The most significant remaining research gap is a frontier failure that matters to an IAM practitioner. If improving the benchmark, design realistic cases that require simultaneous policy interactions and specific troubleshooting conclusions, expert-review their references first, then run a separate versioned evaluation. Keep this baseline unchanged. Do not select or alter cases solely to force the observed model to fail.

Personal expert review and accurate prior-work disclosure are still required. The participant must record and publish the walkthrough, complete the submission description, and check the live HackerRank instructions. This report and the notes were AI-assisted; participant review must not be implied before it occurs.

## Subsequent prompting experiment

The same local model scored 21/24 (87.5%) with an optional policy-checklist prompt, versus 15/24 with the baseline. It corrected nine decisions but introduced three NotAction regressions, and some passing answers retained false explanations. This is a separate post-baseline prompt-tuning experiment on the same eight cases; it does not replace either baseline result. See [the experiment and all its evidence](PROMPTING_EXPERIMENT.md).
