"""Static adapter contracts and reconciliation, not proof of model instruction following."""
from pathlib import Path
import re
import shutil
from tempfile import TemporaryDirectory
import unittest
from _support import TEMPLATE, Workspace

ENTRIES = ('AGENTS.md', 'CLAUDE.md', 'GEMINI.md', '.cursor/rules/specdd.mdc', '.github/copilot-instructions.md')


def check_entries(root):
    core = root / 'DEVELOPMENT.md'
    if not core.is_file():
        raise ValueError('missing canonical DEVELOPMENT.md')
    for name in ENTRIES:
        path = root / name
        text = path.read_text(encoding='utf-8')
        refs = re.findall(r'\]\(([^)]+)\)', text) + re.findall(r'^@([^\s]+)$', text, re.M)
        resolved = []
        for ref in refs:
            if re.match(r'^[a-z]+:', ref):
                continue
            dest = (path.parent / ref.split('#')[0]).resolve()
            if root.resolve() not in dest.parents or not dest.is_file():
                raise ValueError('broken or escaping reference: ' + name)
            resolved.append(dest)
        if core.resolve() not in resolved:
            raise ValueError('entry does not reference canonical rules: ' + name)
        if len(text.splitlines()) > 20 or '## SpecDD 实施' in text:
            raise ValueError('entry duplicates policy instead of delegating: ' + name)


class AdapterTests(unittest.TestCase):
    def test_all_thin_entries_resolve_to_one_canonical_document(self):
        check_entries(TEMPLATE)

    def test_native_imports_stay_in_specific_adapters(self):
        self.assertRegex((TEMPLATE / 'CLAUDE.md').read_text(), r'(?m)^@DEVELOPMENT\.md$')
        self.assertRegex((TEMPLATE / 'GEMINI.md').read_text(), r'(?m)^@\./DEVELOPMENT\.md$')
        core = (TEMPLATE / 'DEVELOPMENT.md').read_text()
        self.assertIsNone(re.search(r'^@\S+', core, re.M))
        self.assertNotIn('alwaysApply:', core)

    def test_cursor_entry_is_always_applied_mdc_with_explicit_read(self):
        text = (TEMPLATE / '.cursor/rules/specdd.mdc').read_text()
        self.assertTrue(text.startswith('---\n'))
        header = text.split('---', 2)[1]
        self.assertRegex(header, r'(?m)^alwaysApply: true$')
        check_entries(TEMPLATE)

    def test_copy_preserves_hidden_adapters_and_portable_paths(self):
        with TemporaryDirectory(prefix='specdd-adapters-') as temp:
            root = Path(temp) / 'copy'
            shutil.copytree(TEMPLATE, root, ignore=shutil.ignore_patterns('.git', '__pycache__', 'tmp'))
            check_entries(root)
            for name in (*ENTRIES, 'DEVELOPMENT.md', 'PROJECT.md'):
                self.assertNotIn('/Users/', (root / name).read_text())

    def test_missing_core_is_not_a_successful_configuration(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, 'missing canonical'):
                check_entries(root)

    def test_broken_adapter_reference_is_detected(self):
        with TemporaryDirectory() as temp:
            root = Path(temp) / 'copy'
            shutil.copytree(TEMPLATE, root, ignore=shutil.ignore_patterns('.git', '__pycache__', 'tmp'))
            path = root / 'GEMINI.md'
            path.write_text(path.read_text().replace('@./DEVELOPMENT.md', '@./missing.md'))
            with self.assertRaisesRegex(ValueError, 'broken'):
                check_entries(root)


class ManualReconciliationTests(Workspace):
    def test_manual_confirmation_requires_honest_backfill_before_cli_check_passes(self):
        # Simulate filesystem-only workflow without calling new/confirm/move.
        folder = self.root / 'spec/planed/SPEC-001-manual'
        folder.mkdir()
        for name in ('spec.md', 'tasks.md', 'verification.md'):
            text = (self.root / 'spec/templates' / name).read_text()
            for key, value in {'{{SPEC_ID}}': 'SPEC-001', '{{TITLE}}': '手工流程演练', '{{DATE}}': '2026-11-25'}.items():
                text = text.replace(key, value)
            (folder / name).write_text(text)
        (folder / 'approval-snapshot.md').write_text((folder / 'spec.md').read_text())
        (folder / 'confirmation.md').write_text('隔离演练：工具不可用，模拟用户确认展示方案，非真实业务授权。')
        target = self.root / 'spec/developing' / folder.name
        folder.rename(target)
        self.run_tool('index')
        self.run_tool('check', ok=False)  # A Markdown receipt is not a forged CLI approval.
        self.run_tool('confirm', 'SPEC-001', '--by', '测试用户', '--evidence', '确认模拟方案',
                      '--source', '手工确认记录补录；已核对本测试 confirmation.md 与 approval-snapshot.md 未发生方案变化')
        self.run_tool('check')
        self.assertTrue((target / 'confirmation.md').exists())
        self.assertTrue((target / 'approval-snapshot.md').exists())
