"""Protect imported grades against prompt changes and tool-assisted trials."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import import_manual


class ManualImportTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        source = import_manual.ROOT
        base = self.root / 'manual_frontier'
        (base / 'chat_exports').mkdir(parents=True)
        for relative in ('manifest.json', 'session_audit.json', 'chat_exports/collected_threads.json'):
            shutil.copyfile(source / 'manual_frontier' / relative, base / relative)
        shutil.copytree(source / 'manual_frontier/prompts', base / 'prompts')
        (self.root / 'reference').mkdir()
        shutil.copyfile(source / 'reference/expected.json', self.root / 'reference/expected.json')

    def test_captured_frontier_outputs_regrade(self):
        with patch.object(import_manual, 'ROOT', self.root):
            records = import_manual.load_records()
        self.assertEqual(len(records), 24)
        self.assertTrue(all(r['grade']['correct'] for r in records))

    def test_modified_prompt_is_rejected(self):
        prompt = self.root / 'manual_frontier/prompts/prompt01_trial1.txt'
        prompt.write_text('changed task', encoding='utf-8')
        with patch.object(import_manual, 'ROOT', self.root), self.assertRaisesRegex(ValueError, 'prompt changed'):
            import_manual.load_records()

    def test_tool_assisted_trial_is_flagged(self):
        path = self.root / 'manual_frontier/session_audit.json'
        audits = json.loads(path.read_text(encoding='utf-8'))
        audits[0]['tool_calls'] = [{'type': 'function_call'}]
        path.write_text(json.dumps(audits), encoding='utf-8')
        with patch.object(import_manual, 'ROOT', self.root), self.assertRaisesRegex(ValueError, 'protocol review'):
            import_manual.load_records()
