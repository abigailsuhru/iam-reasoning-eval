"""Independent minimal IAM-subset oracle; NOT a complete AWS authorization engine."""
import fnmatch


def matches(patterns, value, *, case_sensitive=True):
    if isinstance(patterns, str):
        patterns = [patterns]
    if not case_sensitive:
        value = value.lower()
        patterns = [p.lower() for p in patterns]
    return any(fnmatch.fnmatchcase(value, p) for p in patterns)


def statement_applies(s, request):
    action, resource = request['action'], request['resource']
    if ('Action' in s) == ('NotAction' in s):
        raise ValueError('Exactly one of Action/NotAction required')
    if ('Resource' in s) == ('NotResource' in s):
        raise ValueError('Exactly one of Resource/NotResource required')
    if 'Action' in s:
        action_match = matches(s['Action'], action, case_sensitive=False)
    else:
        action_match = not matches(s['NotAction'], action, case_sensitive=False)
    if 'Resource' in s:
        resource_match = matches(s['Resource'], resource)
    else:
        resource_match = not matches(s['NotResource'], resource)
    if not (action_match and resource_match):
        return False
    for operator, entries in s.get('Condition', {}).items():
        if operator != 'StringEquals':
            raise ValueError('Unsupported condition operator: '+operator)
        for key, accepted in entries.items():
            actual = request.get('context', {}).get(key)
            if actual is None or not matches_exact(accepted, actual):
                return False
    return True


def matches_exact(expected, actual):
    if isinstance(expected, str):
        expected = [expected]
    return actual in expected


def statements(policy):
    if policy is None:
        return []
    assert policy['Version'] == '2012-10-17'
    s = policy['Statement']
    return s if isinstance(s, list) else [s]


def evaluate(task):
    request = task['request']
    policies = list(task['identity_policies'])
    if task.get('permissions_boundary') is not None:
        policies.append(task['permissions_boundary'])
    if task.get('scp') is not None:
        policies.append(task['scp'])
    for policy in policies:
        for s in statements(policy):
            if s['Effect'] == 'Deny' and statement_applies(s, request):
                return 'DENY'
    def has_allow(policy):
        return any(s['Effect'] == 'Allow' and statement_applies(s, request)
                   for s in statements(policy))
    if not any(has_allow(p) for p in task['identity_policies']):
        return 'DENY'
    for optional in ('permissions_boundary', 'scp'):
        if task.get(optional) is not None and not has_allow(task[optional]):
            return 'DENY'
    return 'ALLOW'
