import json
from pathlib import Path

LABELS = {'ALLOW', 'DENY'}

def parse_answer(raw):
    try:
        obj = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(obj, dict) or set(obj) != {'decision', 'reason'}:
        return None
    if obj['decision'] not in LABELS or not isinstance(obj['reason'], str) or not obj['reason'].strip():
        return None
    return obj['decision']

def grade(raw, expected):
    decision = parse_answer(raw)
    return {'valid_format': decision is not None, 'correct': decision == expected,
            'predicted': decision, 'expected': expected}
