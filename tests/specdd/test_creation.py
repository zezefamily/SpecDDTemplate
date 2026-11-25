import json
from _support import Workspace


class CreationTests(Workspace):
    def test_empty_template_is_valid(self):
        result = self.run_tool('check')
        self.assertIn('0 个需求', result.stdout)

    def test_new_creates_three_documents_and_index(self):
        folder = self.create('user-login', '用户登录')
        self.assertEqual(folder.name, 'SPEC-001-user-login')
        self.assertEqual(folder.parent.name, 'planed')
        self.assertEqual({p.name for p in folder.iterdir()}, {'spec.md', 'tasks.md', 'verification.md'})
        self.assertIn('# SPEC-001 用户登录', (folder / 'spec.md').read_text(encoding='utf-8'))
        for p in folder.iterdir():
            self.assertNotIn('{{', p.read_text(encoding='utf-8'))
        self.assertIn('planed/SPEC-001-user-login/spec.md', (self.root / 'spec/INDEX.md').read_text())
        self.run_tool('check')

    def test_numbering_scans_all_states(self):
        self.create()
        self.run_tool('move', 'SPEC-001', 'discard', '--reason', '取消需求')
        second = self.create('second')
        self.assertEqual(second.name, 'SPEC-002-second')

    def test_custom_prefix(self):
        (self.root / 'spec/config.json').write_text(json.dumps({'prefix': 'APP'}))
        self.assertEqual(self.create().name, 'APP-001-sample')
        self.run_tool('check')

    def test_invalid_slug_does_not_escape_workspace(self):
        self.run_tool('new', '../escape', '--title', '测试', ok=False)
        self.assertFalse((self.root / 'spec/escape').exists())
        self.run_tool('check')

    def test_invalid_title_is_rejected(self):
        self.run_tool('new', 'sample', '--title', '坏标题\n第二行', ok=False)
        self.run_tool('check')

    def test_unknown_template_token_leaves_no_partial_spec_or_lock(self):
        template = self.root / 'spec/templates/spec.md'
        template.write_text(template.read_text() + '\n{{UNKNOWN}}\n')
        self.run_tool('new', 'sample', '--title', '功能', ok=False)
        self.assertFalse((self.root / 'spec/.specdd.lock').exists())
        self.assertFalse(list((self.root / 'spec/planed').glob('SPEC-*')))

    def test_concurrent_operation_lock_refuses_mutation(self):
        lock = self.root / 'spec/.specdd.lock'
        lock.touch()
        self.run_tool('new', 'sample', '--title', '功能', ok=False)
        self.assertTrue(lock.exists())
        self.assertFalse(list((self.root / 'spec/planed').glob('SPEC-*')))
