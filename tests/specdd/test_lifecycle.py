from pathlib import Path
from _support import Workspace


class LifecycleTests(Workspace):
    def test_development_completion_and_reopen(self):
        self.create()
        result = self.run_tool('move', 'SPEC-001', 'developing', '--reason', '开始执行')
        folder = Path(result.stdout.strip())
        self.complete_documents(folder)
        result = self.run_tool('move', 'SPEC-001', 'implement', '--reason', '验证通过', '--verified')
        folder = Path(result.stdout.strip())
        self.assertTrue(folder.is_dir())
        self.assertIn('developing → implement', (folder / 'spec.md').read_text())
        self.run_tool('check')
        self.run_tool('move', 'SPEC-001', 'developing', '--reason', '原验收存在遗漏')
        self.run_tool('check')

    def test_cannot_skip_development(self):
        self.create()
        self.run_tool('move', 'SPEC-001', 'implement', '--reason', '跳过', '--verified', ok=False)
        self.run_tool('check')

    def test_completion_requires_explicit_verification(self):
        self.create()
        result = self.run_tool('move', 'SPEC-001', 'developing', '--reason', '开始')
        self.complete_documents(Path(result.stdout.strip()))
        self.run_tool('move', 'SPEC-001', 'implement', '--reason', '完成', ok=False)

    def test_completion_rejects_unfinished_tasks(self):
        self.create()
        self.run_tool('move', 'SPEC-001', 'developing', '--reason', '开始')
        result = self.run_tool('move', 'SPEC-001', 'implement', '--reason', '完成', '--verified', ok=False)
        self.assertIn('未完成项', result.stderr)
        self.run_tool('check')

    def test_completion_rejects_missing_acceptance_result(self):
        folder = self.create()
        for name in ('spec.md', 'tasks.md'):
            p = folder / name
            p.write_text(p.read_text().replace('[ ]', '[x]'))
        self.run_tool('move', 'SPEC-001', 'developing', '--reason', '开始')
        result = self.run_tool('move', 'SPEC-001', 'implement', '--reason', '完成', '--verified', ok=False)
        self.assertIn('验收结论', result.stderr)

    def test_discard_and_restore(self):
        self.create()
        self.run_tool('move', 'SPEC-001', 'discard', '--reason', '被替代，关联后续需求')
        self.run_tool('move', 'SPEC-001', 'planed', '--reason', '重新评估')
        self.run_tool('check')

    def test_unknown_id_and_empty_reason_fail(self):
        self.create()
        self.run_tool('move', 'SPEC-999', 'developing', '--reason', '开始', ok=False)
        self.run_tool('move', 'SPEC-001', 'developing', '--reason', ' ', ok=False)
        self.run_tool('check')
