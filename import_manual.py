"""Import and regrade the captured manual Codex trials without calling a model."""
import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from graders.grade import grade
from run_eval import ROOT, get_tasks, summarize


def load_records():
    base = ROOT / 'manual_frontier'
    manifest = json.loads((base / 'manifest.json').read_text(encoding='utf-8'))
    chats = json.loads((base / 'chat_exports' / 'collected_threads.json').read_text(encoding='utf-8'))
    audits = json.loads((base / 'session_audit.json').read_text(encoding='utf-8'))
    audit_by_id = {a['thread_id']: a for a in audits}
    by_title = {c['title']: c for c in chats}
    if len(by_title) != 24 or len(audit_by_id) != 24 or len(manifest['trials']) != 24:
        raise ValueError('Expected exactly 24 distinct chats, audits, and scheduled trials')
    expected = json.loads((ROOT / 'reference' / 'expected.json').read_text(encoding='utf-8'))
    records = []
    for entry in manifest['trials']:
        filename = Path(entry['prompt_file']).name
        match = re.fullmatch(r'prompt(\d{2})_trial([123])\.txt', filename)
        if not match:
            raise ValueError('Unexpected prompt filename: ' + filename)
        title = f'IAM-prompt{match[1]}-trial{match[2]}'
        chat = by_title[title]
        audit = audit_by_id[chat['id']]
        data = chat['data']
        if data['page']['hasMore'] or len(data['turns']) != 1:
            raise ValueError('Expected one complete page and one turn: ' + title)
        turn = data['turns'][0]
        if turn['status'] != 'completed' or turn['error'] is not None:
            raise ValueError('Trial did not complete: ' + title)
        users = [i for i in turn['items'] if i['type'] == 'userMessage']
        finals = [i for i in turn['items'] if i['type'] == 'agentMessage' and i.get('phase') == 'final_answer']
        if len(users) != 1 or len(finals) != 1:
            raise ValueError('Expected one prompt and one final answer: ' + title)
        pasted = ''.join(c.get('text', '') for c in users[0]['content'])
        scheduled = (base / entry['prompt_file']).read_text(encoding='utf-8')
        if hashlib.sha256(scheduled.encode()).hexdigest() != entry['prompt_sha256']:
            raise ValueError('Scheduled prompt changed: ' + title)
        if pasted.rstrip() != scheduled.rstrip():
            raise ValueError('Pasted prompt differs from scheduled prompt: ' + title)
        allowed = {'userMessage', 'reasoning', 'agentMessage'}
        if any(i['type'] not in allowed for i in turn['items']) or audit['tool_calls']:
            raise ValueError('Unexpected activity requires manual protocol review: ' + title)
        if (audit['turn_count'] != 1 or audit['benchmark_user_message_count'] != 1
                or not audit['response_cross_checked_with_session_log']):
            raise ValueError('Session audit is incomplete: ' + title)
        raw = finals[0]['text']
        result = grade(raw, expected[entry['task_id']])
        records.append({
            'task_id': entry['task_id'], 'trial': entry['trial'], 'prompt_file': filename,
            'thread_id': chat['id'], 'chat_title': title, 'model': audit['model'],
            'reasoning_effort': audit['reasoning_effort'],
            'messages': [{'role': 'user', 'content': pasted}],
            'raw_response': raw, 'grade': result, 'error': None,
            'started_utc': datetime.fromtimestamp(audit['started_at_utc_epoch'], timezone.utc).isoformat(),
            'finished_utc': datetime.fromtimestamp(audit['completed_at_utc_epoch'], timezone.utc).isoformat(),
            'elapsed_seconds': audit['duration_ms'] / 1000,
            'protocol_checks': {'prompt_matches_ignoring_trailing_whitespace': True,
                                'tool_calls_observed': 0, 'single_completed_turn': True},
            'interface': 'Codex desktop, manual user message', 'session_audit': audit,
            'source_export': f'manual_frontier/chat_exports/collected_threads.json#{title}',
        })
    if len({(r['task_id'], r['trial']) for r in records}) != 24:
        raise ValueError('Duplicate trial mapping')
    if {(r['model'], r['reasoning_effort']) for r in records} != {('gpt-6.1-sol', 'high')}:
        raise ValueError('Unexpected model or reasoning effort; review before import')
    return records


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true', help='Recheck source evidence and saved results without modifying files')
    args = parser.parse_args(argv)
    records = load_records()
    rid = 'gpt61-sol-high-manual'
    out, trans = ROOT / 'results' / rid, ROOT / 'transcripts' / rid
    rows = [{k: r[k] for k in ('task_id', 'trial', 'model', 'reasoning_effort', 'elapsed_seconds', 'error')} | r['grade'] for r in records]
    metrics = summarize(rows)
    if args.verify:
        saved = json.loads((out / 'summary.json').read_text(encoding='utf-8'))
        if any(saved[k] != v for k, v in metrics.items()):
            raise ValueError('Saved metrics disagree with source responses')
        if saved['dataset_sha256'] != hashlib.sha256(json.dumps(get_tasks(), sort_keys=True).encode()).hexdigest():
            raise ValueError('Dataset changed since import')
        with (out / 'trials.csv').open(encoding='utf-8', newline='') as stream:
            saved_rows = list(csv.DictReader(stream))
        expected_csv = [{key: '' if value is None else str(value) for key, value in row.items()} for row in rows]
        if saved_rows != expected_csv:
            raise ValueError('Saved trial CSV differs from source responses')
        for r in records:
            raw_path = ROOT / 'manual_frontier' / 'responses' / r['prompt_file']
            if raw_path.read_text(encoding='utf-8') != r['raw_response']:
                raise ValueError('Saved response differs: ' + r['chat_title'])
            transcript = json.loads((trans / f"{r['task_id']}_trial{r['trial']}.json").read_text(encoding='utf-8'))
            if transcript != r:
                raise ValueError('Saved transcript differs: ' + r['chat_title'])
        print(f"Verified 24 responses, prompts, metadata, transcripts, and grades: {metrics['total_passes']}/24 correct.")
        return
    if out.exists() or trans.exists():
        parser.error('Imported run already exists; use --verify to recheck it')
    response_dir = ROOT / 'manual_frontier' / 'responses'
    if response_dir.exists() and any(response_dir.iterdir()):
        parser.error('Response folder is not empty; refusing to overwrite participant evidence')
    out.mkdir(parents=True)
    trans.mkdir(parents=True)
    response_dir.mkdir(exist_ok=True)
    for r in records:
        (response_dir / r['prompt_file']).write_text(r['raw_response'], encoding='utf-8')
        (trans / f"{r['task_id']}_trial{r['trial']}.json").write_text(json.dumps(r, indent=2) + '\n', encoding='utf-8')
    with (out / 'trials.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    first = min(r['started_utc'] for r in records)
    last = max(r['finished_utc'] for r in records)
    summary = metrics | {
        'run_id': rid, 'model': 'gpt-6.1-sol', 'reasoning_effort': 'high',
        'interface': 'Codex desktop manual trials', 'tasks': 8, 'trials_per_task': 3,
        'started_utc': first, 'finished_utc': last,
        'runtime_seconds': round(sum(r['elapsed_seconds'] for r in records), 3),
        'collection_window_seconds': (datetime.fromisoformat(last) - datetime.fromisoformat(first)).total_seconds(),
        'runtime_note': 'runtime_seconds sums app-recorded turn durations; collection window includes human time between trials.',
        'api_cost_usd': None, 'cost_note': 'Used the participant Codex account; attributable subscription or usage cost was not measured.',
        'settings': {'reasoning_effort': 'high', 'temperature': None, 'seed': None, 'max_output_tokens': None},
        'codex_runtime_versions': sorted({r['session_audit']['cli_version'] for r in records}),
        'dataset_sha256': hashlib.sha256(json.dumps(get_tasks(), sort_keys=True).encode()).hexdigest(),
        'limitations': ['Manual Codex interface differs from Ollama system/user roles and decoding settings.',
                        'Codex adds runtime instructions and environment context; these are not a controlled API replication.',
                        'No tool calls or observed model switches in the selected session records.',
                        'Underlying model snapshot, latent reasoning, temperature, seed and account cost are not available.',
                        '100% on these tasks does not demonstrate a frontier-model limitation.'],
    }
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    sheet = ROOT / 'manual_frontier' / 'collection_sheet.csv'
    backup = sheet.with_name('collection_sheet.user_entered.csv')
    if not backup.exists():
        backup.write_bytes(sheet.read_bytes())
    with sheet.open(encoding='utf-8-sig', newline='') as stream:
        collection = list(csv.DictReader(stream))
    by_name = {r['prompt_file']: r for r in records}
    cet = timezone(timedelta(hours=1), 'CET')
    for row in collection:
        r = by_name[row['prompt_file']]
        row['model_name'] = r['model']
        row['reasoning_setting'] = 'High'
        row['date_time_with_timezone'] = datetime.fromisoformat(r['started_utc']).astimezone(cet).isoformat()
        row['tool_use_observed'] = 'None observed (session audit)'
        row['unexpected_context_or_model_switch'] = 'No model switch; standard Codex runtime/environment context present'
        row['notes'] = 'Date/time derived from recorded UTC turn start and converted to CET. Original user-entered values retained in collection_sheet.user_entered.csv. Thinking is not a tool call.'
    with sheet.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=collection[0].keys())
        writer.writeheader()
        writer.writerows(collection)
    print(json.dumps(summary, indent=2))
    print('Saved 24 response files and transcripts; updated collection sheet while preserving original.')


if __name__ == '__main__':
    main()
