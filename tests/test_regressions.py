"""Regression checks for scoring, policy semantics, and recorded evidence."""
import copy
import json
import io
from contextlib import redirect_stdout, redirect_stderr
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_eval
from graders.grade import grade
from graders.iam_oracle import evaluate, matches


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.task = run_eval.get_tasks()[0]

    def test_untrusted_answers_never_crash(self):
        for decision in ([], {}, None, True, 1):
            with self.subTest(decision=decision):
                self.assertFalse(grade(json.dumps({'decision': decision, 'reason': 'x'}), 'ALLOW')['correct'])
        self.assertFalse(grade('{"decision":"DENY","decision":"ALLOW","reason":"x"}', 'ALLOW')['valid_format'])

    def test_iam_wildcards_only(self):
        self.assertFalse(matches('arn:aws:s3:::b/report[12].csv', 'arn:aws:s3:::b/report1.csv'))
        self.assertTrue(matches('arn:aws:s3:::b/report[12].csv', 'arn:aws:s3:::b/report[12].csv'))
        self.assertTrue(matches('arn:aws:s3:::b/?/*', 'arn:aws:s3:::b/a/deep/file'))
        self.assertFalse(matches('arn:aws:s3:::b/?/*', 'arn:aws:s3:::b/ab/file'))

    def test_condition_key_case_and_literal_values(self):
        st = self.task['identity_policies'][0]['Statement'][0]
        st['Condition'] = {'StringEquals': {'aws:PrincipalTag/team': ['platform', 'security']}}
        self.task['request']['context'] = {'AWS:PrincipalTag/TEAM': 'platform'}
        self.assertEqual(evaluate(self.task), 'ALLOW')
        self.task['request']['context']['AWS:PrincipalTag/TEAM'] = 'Platform'
        self.assertEqual(evaluate(self.task), 'DENY')
        self.task['request']['context']['AWS:PrincipalTag/TEAM'] = '*'
        self.assertEqual(evaluate(self.task), 'DENY')

    def test_invalid_unmatched_policy_is_rejected(self):
        st = self.task['identity_policies'][0]['Statement'][0]
        for change in ({'Effect': 'allow'}, {'Condition': {'Bool': {'aws:SecureTransport': 'true'}}},
                       {'Principal': '*'}, {'Action': 's3:Other', 'Resource': '${aws:username}'}):
            task = copy.deepcopy(self.task)
            task['identity_policies'][0]['Statement'][0] = st | change
            with self.subTest(change=change), self.assertRaises(ValueError):
                evaluate(task)

    def test_restrictive_policies_cannot_grant_identity_permission(self):
        self.task['identity_policies'] = []
        self.task['permissions_boundary'] = {'Version': '2012-10-17', 'Statement':
                                            {'Effect': 'Allow', 'Action': '*', 'Resource': '*'}}
        self.assertEqual(evaluate(self.task), 'DENY')

    def test_identity_union_and_notresource(self):
        self.task['identity_policies'].insert(0, {'Version': '2012-10-17', 'Statement':
                                                 {'Effect': 'Allow', 'Action': 's3:ListBucket', 'Resource': '*'}})
        self.task['scp'] = {'Version': '2012-10-17', 'Statement': [
            {'Effect': 'Allow', 'Action': '*', 'Resource': '*'},
            {'Effect': 'Deny', 'Action': '*', 'NotResource': 'arn:aws:s3:::project-data/*'}]}
        self.assertEqual(evaluate(self.task), 'ALLOW')
        self.task['request']['resource'] = 'arn:aws:s3:::other-bucket/file'
        self.assertEqual(evaluate(self.task), 'DENY')

    def test_scp_allow_resource_validation(self):
        self.task['scp'] = copy.deepcopy(self.task['identity_policies'][0])
        with self.assertRaises(ValueError):
            evaluate(self.task)

    def test_answer_clues_are_private(self):
        for task in run_eval.get_tasks():
            message = run_eval.messages_for(task)[1]['content']
            visible = json.loads(message.split('\n', 1)[1])
            self.assertNotIn('id', visible)
            self.assertNotIn('scenario', visible)
            self.assertNotIn(task['id'], message)

    def test_checklist_preserves_task_and_keeps_answers_private(self):
        for task in run_eval.get_tasks():
            baseline = run_eval.messages_for(task)
            checklist = run_eval.messages_for(task, 'policy-checklist')
            self.assertEqual(baseline[1], checklist[1])
            self.assertEqual(baseline[0]['content'], run_eval.SYSTEM)
            self.assertTrue(checklist[0]['content'].startswith(run_eval.SYSTEM))
            self.assertNotIn(task['id'], json.dumps(checklist))
            self.assertNotIn(task['scenario'], json.dumps(checklist))
        with self.assertRaises(ValueError):
            run_eval.messages_for(self.task, 'unknown')

    def test_default_prompts_match_frozen_baseline_evidence(self):
        for task in run_eval.get_tasks():
            path = run_eval.ROOT / 'transcripts' / 'llama32-3b-baseline' / f"{task['id']}_trial1.json"
            recorded = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(run_eval.messages_for(task), recorded['messages'])

    def test_metrics_separate_service_errors(self):
        rows = [
            {'task_id': 'a', 'correct': True, 'valid_format': True, 'predicted': 'ALLOW', 'error': None},
            {'task_id': 'a', 'correct': False, 'valid_format': True, 'predicted': 'DENY', 'error': None},
            {'task_id': 'b', 'correct': False, 'valid_format': False, 'predicted': None, 'error': 'offline'},
            {'task_id': 'b', 'correct': False, 'valid_format': False, 'predicted': None, 'error': None}]
        summary = run_eval.summarize(rows)
        self.assertEqual(summary['pass_rate'], .25)
        self.assertEqual(summary['pass_at_k'], .5)
        self.assertEqual(summary['pass_power_k'], 0)
        self.assertEqual(summary['infrastructure_errors'], 1)
        self.assertEqual(summary['decision_failures'], 1)
        self.assertEqual(summary['format_failures'], 1)

    def test_runner_records_exact_messages_and_refuses_overwrite(self):
        expected = {self.task['id']: 'ALLOW'}
        metadata = [{'name': 'test:latest', 'digest': 'fixture-only'}]
        response = {'message': {'content': '{"decision":"ALLOW","reason":"matching grant"}'}, 'done': True}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'reference').mkdir()
            (root / 'reference' / 'expected.json').write_text(json.dumps(expected))
            def provider(url, timeout, payload=None):
                if url.endswith('/version'):
                    return {'version': 'test-fixture'}
                if url.endswith('/tags'):
                    return {'models': metadata}
                self.assertEqual(payload['messages'], run_eval.messages_for(self.task))
                return response
            with patch.object(run_eval, 'ROOT', root), patch.object(run_eval, 'get_tasks', return_value=[self.task]), \
                    patch.object(run_eval, 'request_json', side_effect=provider):
                args = ['--mode', 'ollama', '--model', 'test', '--trials', '1', '--run-id', 'fixture']
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(run_eval.main(args), 0)
                transcript = json.loads(next((root / 'transcripts' / 'fixture').glob('*.json')).read_text())
                self.assertEqual(transcript['messages'], transcript['request_payload']['messages'])
                self.assertEqual(transcript['provider_response'], response)
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    run_eval.main(args)

    def test_incomplete_provider_response_is_not_scored_as_an_answer(self):
        with patch.object(run_eval, 'request_json', return_value={
                'message': {'content': '{"decision":"ALLOW","reason":"x"}'}, 'done': False}):
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                run_eval.query_ollama('fixture', run_eval.messages_for(self.task), 10)

    def test_connection_failure_does_not_create_fake_model_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'reference').mkdir()
            (root / 'reference' / 'expected.json').write_text(json.dumps({self.task['id']: 'ALLOW'}))
            with patch.object(run_eval, 'ROOT', root), patch.object(run_eval, 'get_tasks', return_value=[self.task]), \
                    patch.object(run_eval, 'request_json', side_effect=OSError('offline')), \
                    redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                run_eval.main(['--mode', 'ollama'])
            self.assertFalse((root / 'results').exists())


if __name__ == '__main__':
    unittest.main()
