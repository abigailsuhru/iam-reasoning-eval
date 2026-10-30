# Manual frontier-model testing in Codex

These files contain eight benchmark inputs repeated three times: 24 trials, not 24 different tasks.
The export originally prepared prompts only. The participant has now completed 24 Codex trials; verbatim responses are saved in responses/, visible chat exports in chat_exports/, and audited results in ../results/gpt61-sol-high-manual/. Run `python import_manual.py --verify` from the project root to recheck the captured evidence. The instructions below document the collection protocol.

## Do this for every trial

1. Open ALL_24_PROMPTS.md locally, or open an individual TXT file in prompts/.
2. Start a NEW Codex chat WITHOUT the iam-reasoning-eval project or any attached project folder. Official instructions: https://learn.chatgpt.com/docs/projects#start-a-chat-without-a-project . Do not fork or continue the development chat. A worktree of this repository also contains answers and is unsuitable.
3. Select one specific model and reasoning setting. Keep both unchanged across all 24 trials. Record their exact displayed labels. The model name, rather than the Codex product name, identifies what was tested; confirm that the selected model is suitable for the guide's frontier-model requirement.
4. Remove attachments, editor context, and connected sources that might expose the benchmark's answers. Disable relevant memories or personalization where the interface allows it; record any context you cannot control. A project-free chat alone is not a guarantee of complete context isolation.
5. Paste ONLY the entire content of one TXT file, or ONLY its fenced block in ALL_24_PROMPTS.md. Do not paste this README, manifest, headings, the whole prompt bundle, this development chat, reference answers, or results.
6. Submit it once. The prompt asks for no tools and JSON only. Do not ask the tested chat to read or save files. Do not supply hints, corrections, or follow-up questions, and do not regenerate a failed answer.
7. Copy the COMPLETE final answer verbatim into the response filename listed in collection_sheet.csv. Create a responses/ folder yourself when collecting. Preserve code fences and extra text if returned; removing them would change the graded response.
8. Save the complete chat transcript/export when possible, including any commentary and tool calls, plus a screenshot showing the selected model and setting. Record a chat title or accessible URL, timestamp with timezone, model/setting, and any tool use or model switch in the collection sheet. Do not rely solely on a screenshot of a correct JSON label.
9. Start another fresh, project-free chat for the next TXT file. If the service blocks an attempt or changes models, record that event instead of silently substituting a model. Keep all attempted evidence and document any reruns.

If a trial reads reference files or searches for answers, retain its evidence and flag the protocol deviation. Do not count it as an ordinary unaided reasoning trial. If memory/project context cannot be adequately isolated, use an API-based evaluation instead.

## Trial order

prompt01_trial1.txt, prompt01_trial2.txt, prompt01_trial3.txt,
then prompt02_trial1.txt through prompt08_trial3.txt.
There are 24 files total. Each file is a self-contained prompt.

## Important reporting limits

- Report this as a manual Codex-interface run, with the exact selected model and reasoning setting. It is not a controlled API replication.
- Benchmark rules and task JSON come directly from run_eval.messages_for. They are concatenated into a USER message here; the Ollama run used separate SYSTEM and USER roles. The manual prompt additionally prohibits tools. Hidden Codex instructions and interface settings differ.
- Temperature, seed, token limits, or underlying model snapshots may not be exposed. Record unavailable values as unknown, not as the Ollama defaults. Do not claim inference settings were identical.
- This process produces outputs to be scored with the existing grader. It does not guarantee failure, acceptance by the judges, or fulfillment of all submission requirements.
- If all 24 attempts pass, report that honestly. This task set has not demonstrated a limitation of that tested model.
- Keep these prompts and the local baseline unchanged while collecting the comparison. Use the same decision grader afterward. Raw responses and collection metadata can be returned to the development chat for import and analysis; never bring that analysis into a tested trial.

The manifest is for the participant's audit only. It maps neutral prompt numbers to source task IDs and retains the original two-message inputs and SHA-256 of the pasted prompt. Do not show it to the tested model.
