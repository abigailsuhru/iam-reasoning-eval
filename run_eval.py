"""Run the single-turn eval against local Ollama, or validate the oracle offline."""
import argparse
import csv
import json
import platform
import time
import urllib.request
import urllib.error
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from graders.grade import grade
from graders.iam_oracle import evaluate

ROOT = Path(__file__).resolve().parent
SYSTEM = ("You are auditing access authorization for a deliberately scoped AWS IAM scenario. "
"Only identity-based policies, an optional permissions boundary, and an optional SCP apply. "
"No resource policies, cross-account access, sessions, RCPs, or other restrictions exist. "
"Use default implicit deny; any applicable explicit Deny wins. Identity-based Allow is required, "
"and if a permissions boundary or SCP is provided each must also Allow. "
"Match Action case-insensitively, Resource case-sensitively, wildcard * and ?, and conditions "
"StringEquals exactly. A missing condition key does not match. "
"Return ONLY a JSON object with exactly two keys: decision (ALLOW or DENY) and reason (a short explanation).")

def get_tasks():
    return [json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT/'tasks').glob('*.json'))]

def query_ollama(model, system, task, timeout):
    payload = json.dumps({'model':model,'stream':False,'format':'json',
        'options':{'temperature':0, 'num_predict':180},
        'messages':[{'role':'system','content':system},
                    {'role':'user','content':'Evaluate this request.\n'+json.dumps(task, indent=2)}]}).encode()
    req = urllib.request.Request('http://localhost:11434/api/chat', payload,
        {'Content-Type':'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)
    return data['message']['content'], data.get('eval_count'), data.get('prompt_eval_count')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['oracle','ollama'], default='oracle')
    ap.add_argument('--model', default='llama3.2:3b')
    ap.add_argument('--trials', type=int, default=3)
    ap.add_argument('--timeout', type=int, default=240)
    args=ap.parse_args()
    if args.trials < 1: ap.error('trials must be positive')
    tasks=get_tasks()
    expected=json.loads((ROOT/'reference'/'expected.json').read_text(encoding='utf-8'))
    for t in tasks:
        actual=evaluate(t)
        if actual != expected[t['id']]:
            raise AssertionError(f"Reference mismatch in {t['id']}: {actual} != {expected[t['id']]}")
    print(f'Oracle validation passed: {len(tasks)} reference solutions.')
    if args.mode=='oracle': return
    out=ROOT/'results'; out.mkdir(exist_ok=True)
    trans=ROOT/'transcripts';trans.mkdir(exist_ok=True)
    rows=[]
    start=datetime.now(timezone.utc).isoformat()
    for t in tasks:
        for trial in range(1,args.trials+1):
            stamp=time.monotonic()
            raw=''; error=None; tokens=None; prompt_tokens=None
            try:
                raw,tokens,prompt_tokens=query_ollama(args.model,SYSTEM,t,args.timeout)
                result=grade(raw,expected[t['id']])
            except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
                error=f'{type(exc).__name__}: {exc}'
                result=grade(raw,expected[t['id']])
            record={'task_id':t['id'],'trial':trial,'model':args.model,
              'temperature':0,'prompt':{'system':SYSTEM,'user':t},
              'raw_response':raw,'grade':result,'error':error,
              'elapsed_seconds':round(time.monotonic()-stamp,2),
              'output_tokens':tokens,'input_tokens':prompt_tokens,
              'utc_time':datetime.now(timezone.utc).isoformat()}
            (trans/f"{t['id']}_trial{trial}.json").write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
            rows.append({k:record[k] for k in ('task_id','trial','model','elapsed_seconds','error')}|
                        {k:result[k] for k in ('valid_format','correct','predicted','expected')})
            print(t['id'],trial,'PASS' if result['correct'] else 'FAIL',error or '')
    with (out/'trials.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
    groups=defaultdict(list)
    for row in rows:groups[row['task_id']].append(row['correct'])
    all_pass=sum(r['correct'] for r in rows)
    summary={'model':args.model,'started_utc':start,'trials_per_task':args.trials,
      'tasks':len(tasks),'total_trials':len(rows),'total_passes':all_pass,
      'pass_rate':all_pass/len(rows),'pass_power_k':sum(all(x) for x in groups.values())/len(groups),
      'per_task':{name:{'passes':sum(values),'trials':len(values)} for name,values in groups.items()},
      'environment':platform.platform(),'api_cost_usd':0,
      'note':'Local inference has no API charge; electricity and hardware resources are not free.'}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print('Summary:',json.dumps(summary,indent=2))
    print('Saved results/trials.csv, results/summary.json and transcripts/*.json')
if __name__=='__main__':main()
