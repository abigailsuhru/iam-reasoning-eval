"""Independent minimal IAM-subset oracle; NOT a complete AWS authorization engine."""
import re


def string_list(value):
    values = [value] if isinstance(value, str) else value
    if not isinstance(values, list) or not values or any(not isinstance(v, str) or not v for v in values):
        raise ValueError('Expected a string or nonempty list of strings')
    if any('${' in v for v in values):
        raise ValueError('Policy variables are outside this subset')
    return values


def matches(patterns, value, *, case_sensitive=True):
    patterns = string_list(patterns)
    if not case_sensitive:
        value = value.lower()
        patterns = [p.lower() for p in patterns]
    # IAM supports * and ?, not shell character classes such as [ab].
    return any(re.fullmatch(re.escape(p).replace(r'\*', '.*').replace(r'\?', '.'),
                            value, flags=re.DOTALL) is not None for p in patterns)


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
            actual = {k.lower(): v for k, v in request.get('context', {}).items()}.get(key.lower())
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
    if not isinstance(policy, dict) or policy.get('Version') != '2012-10-17':
        raise ValueError('Policy Version must be 2012-10-17')
    if set(policy) - {'Version', 'Id', 'Statement'}:
        raise ValueError('Unsupported policy elements')
    s = policy['Statement']
    return s if isinstance(s, list) else [s]


def validate(task):
    """Reject unsupported inputs before evaluation, even in unmatched statements."""
    request = task['request']
    for key in ('action', 'resource'):
        if not isinstance(request.get(key), str) or not request[key]:
            raise ValueError('Request needs a nonempty ' + key)
    context = request.get('context', {})
    if not isinstance(context, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in context.items()):
        raise ValueError('Only single-valued string request context is supported')
    if len({k.lower() for k in context}) != len(context):
        raise ValueError('Ambiguous case-duplicate context keys')
    if not isinstance(task['identity_policies'], list):
        raise ValueError('identity_policies must be a list')
    policies = [('identity', p) for p in task['identity_policies']]
    policies += [(key, task[key]) for key in ('permissions_boundary', 'scp') if task.get(key) is not None]
    for kind, policy in policies:
        if policy is None:
            raise ValueError('Identity policy cannot be null')
        entries = statements(policy)
        if not entries:
            raise ValueError('Policy must contain at least one statement')
        for s in entries:
            if not isinstance(s, dict) or set(s) - {'Sid', 'Effect', 'Action', 'NotAction', 'Resource', 'NotResource', 'Condition'}:
                raise ValueError('Unsupported statement elements')
            if s.get('Effect') not in ('Allow', 'Deny'):
                raise ValueError('Effect must be Allow or Deny')
            for positive, negative in (('Action', 'NotAction'), ('Resource', 'NotResource')):
                if (positive in s) == (negative in s):
                    raise ValueError('Exactly one of ' + positive + '/' + negative + ' required')
                string_list(s[positive] if positive in s else s[negative])
            if kind == 'scp' and s['Effect'] == 'Allow' and s.get('Resource') != '*':
                raise ValueError('SCP Allow must use Resource * in this subset')
            condition = s.get('Condition', {})
            if not isinstance(condition, dict):
                raise ValueError('Condition must be an object')
            for operator, values in condition.items():
                if operator != 'StringEquals' or not isinstance(values, dict) or not values:
                    raise ValueError('Only nonempty StringEquals conditions are supported')
                for key, value in values.items():
                    if not isinstance(key, str) or not key:
                        raise ValueError('Condition keys must be nonempty strings')
                    string_list(value)


def evaluate(task):
    validate(task)
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
