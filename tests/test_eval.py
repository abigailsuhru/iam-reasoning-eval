import json
import unittest
from pathlib import Path
from graders.grade import grade
from graders.iam_oracle import evaluate, matches, statement_applies

ROOT=Path(__file__).resolve().parents[1]
class EvalTests(unittest.TestCase):
    def test_reference_answers(self):
        expected=json.loads((ROOT/'reference/expected.json').read_text())
        solutions=json.loads((ROOT/'reference/solutions.json').read_text())
        self.assertEqual(set(solutions), set(expected))
        tasks=list((ROOT/'tasks').glob('*.json'))
        self.assertEqual(len(tasks),8)
        for path in tasks:
            task=json.loads(path.read_text())
            with self.subTest(task=task['id']):
                self.assertEqual(evaluate(task),expected[task['id']])
                self.assertTrue(grade(json.dumps(solutions[task['id']]), expected[task['id']])['correct'])
                self.assertTrue(grade(json.dumps({'decision':expected[task['id']], 'reason':'Validated rule'}), expected[task['id']])['correct'])
                wrong='DENY' if expected[task['id']]=='ALLOW' else 'ALLOW'
                self.assertFalse(grade(json.dumps({'decision':wrong, 'reason':'Incorrect rule'}),expected[task['id']])['correct'])
    def test_malformed_answers_fail(self):
        for raw in ['ALLOW','{"decision":"ALLOW"}', '{"decision":"ALLOW","reason":""}',
                    '{"decision":"ALLOW","reason":"x","extra":1}',
                    '{"decision":"ALLOW","reason":"x"} extra',
                    '{"decision":"ALLOW","reason":12}',
                    '{"decision":"ALLOW or DENY","reason":"x"}']:
            with self.subTest(raw=raw):self.assertFalse(grade(raw,'ALLOW')['correct'])
    def test_wildcard_and_case(self):
        self.assertTrue(matches('s3:Get*','S3:GetObject',case_sensitive=False))
        self.assertFalse(matches('arn:aws:s3:::Bucket/*','arn:aws:s3:::bucket/a'))
    def test_missing_condition(self):
        st={'Effect':'Allow','Action':'s3:GetObject','Resource':'*',
            'Condition':{'StringEquals':{'aws:PrincipalTag/team':'platform'}}}
        self.assertFalse(statement_applies(st,{'action':'s3:GetObject','resource':'arn:aws:s3:::b/x','context':{}}))
    def test_explicit_deny_boundary(self):
        task=json.loads((ROOT/'tasks/01_basic_allow.json').read_text())
        task['permissions_boundary']={'Version':'2012-10-17','Statement':[
            {'Effect':'Allow','Action':'*','Resource':'*'},
            {'Effect':'Deny','Action':'s3:GetObject','Resource':'*'}]}
        self.assertEqual(evaluate(task),'DENY')
if __name__=='__main__': unittest.main()
