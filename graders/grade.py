import json

LABELS = {'ALLOW', 'DENY'}


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError('Duplicate JSON key: ' + key)
        obj[key] = value
    return obj

def parse_answer(raw):
    try:
        obj = json.loads(raw, object_pairs_hook=unique_object)
    except (ValueError, TypeError):
        return None
    if not isinstance(obj, dict) or set(obj) != {'decision', 'reason'}:
        return None
    if not isinstance(obj['decision'], str) or obj['decision'] not in LABELS or not isinstance(obj['reason'], str) or not obj['reason'].strip():
        return None
    return obj['decision']

def grade(raw, expected):
    decision = parse_answer(raw)
    return {'valid_format': decision is not None, 'correct': decision == expected,
            'predicted': decision, 'expected': expected}
