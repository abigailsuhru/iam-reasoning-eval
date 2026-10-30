"""Run independent single-turn Ollama trials and preserve their evidence."""
import argparse
import csv
import hashlib
import json
import platform
import re
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from graders.grade import grade
from graders.iam_oracle import evaluate

ROOT = Path(__file__).resolve().parent
SYSTEM = (
    'You are auditing access authorization for a deliberately scoped AWS IAM scenario. '
    'Only identity-based policies, an optional permissions boundary, and an optional SCP apply. '
    'The principal is a same-account IAM user in an Organizations member account. '
    'The supplied SCP is the sole policy at the account level; ancestors allow all actions. '
    'No resource policies, cross-account access, sessions, RCPs, or other restrictions exist. '
    'Use default implicit deny; any applicable explicit Deny wins. Identity-based Allow is required, '
    'and if a permissions boundary or SCP is provided each must also Allow. '
    'Match Action case-insensitively, Resource case-sensitively, with only * and ? wildcards. '
    'StringEquals matches values literally and case-sensitively; context key names are '
    'case-insensitive. Context values are single strings. A missing condition key does not match. '
    'Return ONLY a JSON object with exactly two keys: decision (ALLOW or DENY) and reason '
    '(a short, nonempty explanation).'
)

# General procedure only: no reference labels, task IDs, or worked benchmark answers.
CHECKLIST = (
    '\nBefore selecting the final decision, audit all policy layers. In the reason, briefly '
    'state these four findings for this exact action and resource: '
    '(1) whether any explicit Deny statement actually matches, '
    '(2) whether any identity Allow actually matches, '
    '(3) whether the boundary is absent or contains a matching Allow, and '
    '(4) whether the SCP is absent or contains a matching Allow. '
    'Check Action or NotAction, Resource or NotResource, and conditions together for each '
    'statement; an unrelated Deny is not a matching Deny. '
    'An Allow in one layer does not override a matching Deny or supply an Allow missing '
    'from another required layer. ALLOW requires no matching Deny, a matching identity '
    'Allow, and a matching Allow in every supplied restrictive layer. Otherwise DENY. '
    'Write the reason key FIRST and the decision key LAST in the JSON object. '
    'Return only those two keys. Do not stop at finding an identity Allow.'
)


def get_tasks():
    tasks = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT / 'tasks').glob('*.json'))]
    if not tasks:
        raise ValueError('No tasks found')
    ids = [t['id'] for t in tasks]
    if len(set(ids)) != len(ids) or any(not re.fullmatch(r'[A-Za-z0-9_-]+', i) for i in ids):
        raise ValueError('Task IDs must be unique and filename-safe')
    return tasks


def messages_for(task, strategy='baseline'):
    if strategy not in ('baseline', 'policy-checklist'):
        raise ValueError('Unknown prompt strategy: ' + strategy)
    # IDs and scenario descriptions contain answer clues. Keep them private.
    visible = {k: task[k] for k in ('request', 'identity_policies', 'permissions_boundary', 'scp') if k in task}
    system = SYSTEM if strategy == 'baseline' else SYSTEM + CHECKLIST
    return [{'role': 'system', 'content': system},
            {'role': 'user', 'content': 'Evaluate this request.\n' + json.dumps(visible, indent=2)}]


def request_json(url, timeout, payload=None):
    encoded = None if payload is None else json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, encoded, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def query_ollama(model, messages, timeout, temperature=0, seed=0, num_predict=256):
    payload = {'model': model, 'stream': False, 'format': 'json',
               'options': {'temperature': temperature, 'seed': seed, 'num_predict': num_predict},
               'messages': messages}
    response = request_json('http://localhost:11434/api/chat', timeout, payload)
    if not isinstance(response.get('message', {}).get('content'), str):
        raise ValueError('Ollama response has no string message.content')
    if response.get('done') is not True:
        raise ValueError('Ollama returned an incomplete response')
    return payload, response


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row['task_id']].append(row)
    responses = [r for r in rows if r['error'] is None]
    return {
        'total_trials': len(rows), 'total_passes': sum(r['correct'] for r in rows),
        'pass_rate': sum(r['correct'] for r in rows) / len(rows),
        'pass_power_k': sum(all(r['correct'] for r in rs) for rs in groups.values()) / len(groups),
        'pass_at_k': sum(any(r['correct'] for r in rs) for rs in groups.values()) / len(groups),
        'infrastructure_errors': len(rows) - len(responses),
        'format_failures': sum(not r['valid_format'] for r in responses),
        'decision_failures': sum(r['valid_format'] and not r['correct'] for r in responses),
        'per_task': {name: {'passes': sum(r['correct'] for r in rs), 'trials': len(rs),
                            'predictions': [r['predicted'] for r in rs],
                            'errors': sum(r['error'] is not None for r in rs)}
                     for name, rs in groups.items()},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode', choices=['oracle', 'ollama'], default='oracle')
    ap.add_argument('--model', default='llama3.2:3b')
    ap.add_argument('--strategy', choices=['baseline', 'policy-checklist'], default='baseline',
                    help='Optional prompt intervention; baseline preserves the original prompt')
    ap.add_argument('--trials', type=int, default=3)
    ap.add_argument('--timeout', type=int, default=240)
    ap.add_argument('--temperature', type=float, default=0)
    ap.add_argument('--seed', type=int, default=42, help='Base seed; increments on each trial')
    ap.add_argument('--num-predict', type=int, default=256)
    ap.add_argument('--run-id', help='Unique evidence directory name (defaults to UTC timestamp)')
    args = ap.parse_args(argv)
    if args.trials < 1 or args.timeout < 1 or args.num_predict < 1:
        ap.error('trials, timeout, and num-predict must be positive')
    if not 0 <= args.temperature <= 2:
        ap.error('temperature must be between 0 and 2')
    tasks = get_tasks()
    expected = json.loads((ROOT / 'reference' / 'expected.json').read_text(encoding='utf-8'))
    if set(expected) != {t['id'] for t in tasks}:
        raise ValueError('Reference IDs must match task IDs exactly')
    for task in tasks:
        if evaluate(task) != expected[task['id']]:
            raise ValueError('Reference mismatch in ' + task['id'])
    print(f'Oracle validation passed: {len(tasks)} reference solutions.', flush=True)
    if args.mode == 'oracle':
        return 0
    run_id = args.run_id or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id):
        ap.error('run-id must contain only letters, numbers, underscores, and hyphens')
    out, trans = ROOT / 'results' / run_id, ROOT / 'transcripts' / run_id
    if out.exists() or trans.exists():
        ap.error('run-id already exists; choose a new ID to preserve existing evidence')
    try:
        version = request_json('http://localhost:11434/api/version', args.timeout)
        models = request_json('http://localhost:11434/api/tags', args.timeout)['models']
        model_name = args.model if ':' in args.model else args.model + ':latest'
        model_info = next((m for m in models if m['name'] == model_name), None)
        if model_info is None:
            ap.error(f'Model is not installed. Run: ollama pull {args.model}')
    except (OSError, ValueError, KeyError) as exc:
        ap.error(f'Ollama preflight failed: {exc}. Start Ollama and check ollama list.')
    out.mkdir(parents=True)
    trans.mkdir(parents=True)
    started = datetime.now(timezone.utc).isoformat()
    run_start = time.monotonic()
    dataset_hash = hashlib.sha256(json.dumps(tasks, sort_keys=True).encode()).hexdigest()
    rows = []
    for task in tasks:
        for trial in range(1, args.trials + 1):
            stamp = time.monotonic()
            messages = messages_for(task, args.strategy)
            seed = args.seed + trial - 1
            raw, error, response, payload = '', None, {}, None
            try:
                payload, response = query_ollama(args.model, messages, args.timeout,
                                                 args.temperature, seed, args.num_predict)
                raw = response['message']['content']
            except (OSError, ValueError, KeyError, TypeError) as exc:
                error = f'{type(exc).__name__}: {exc}'
            result = grade(raw, expected[task['id']])
            record = {
                'task_id': task['id'], 'trial': trial, 'model': args.model,
                'strategy': args.strategy,
                'settings': {'temperature': args.temperature, 'seed': seed, 'num_predict': args.num_predict},
                'messages': messages, 'request_payload': payload,
                'raw_response': raw, 'provider_response': response, 'grade': result, 'error': error,
                'elapsed_seconds': round(time.monotonic() - stamp, 3),
                'utc_time': datetime.now(timezone.utc).isoformat(), 'dataset_sha256': dataset_hash,
            }
            (trans / f"{task['id']}_trial{trial}.json").write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
            rows.append({k: record[k] for k in ('task_id', 'trial', 'model', 'elapsed_seconds', 'error')} | result)
            print(task['id'], trial, 'ERROR' if error else ('PASS' if result['correct'] else 'FAIL'), error or '', flush=True)
            with (out / 'trials.csv').open('w', newline='', encoding='utf-8') as stream:
                writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
    summary = summarize(rows) | {
        'run_id': run_id, 'model': args.model, 'model_metadata': model_info,
        'strategy': args.strategy,
        'ollama_version': version, 'started_utc': started,
        'finished_utc': datetime.now(timezone.utc).isoformat(),
        'runtime_seconds': round(time.monotonic() - run_start, 3),
        'trials_per_task': args.trials, 'tasks': len(tasks),
        'settings': {'temperature': args.temperature, 'base_seed': args.seed, 'num_predict': args.num_predict,
                     'timeout_seconds': args.timeout},
        'dataset_sha256': dataset_hash, 'python_version': platform.python_version(),
        'environment': platform.platform(), 'api_cost_usd': 0,
        'note': 'Local inference has no API charge. Infrastructure errors are not evidence of model reasoning failure.',
    }
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print('Summary:', json.dumps(summary, indent=2), flush=True)
    print(f'Saved {out} and {trans}', flush=True)
    return 1 if summary['infrastructure_errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
