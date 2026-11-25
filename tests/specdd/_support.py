"""Every case gets its own filesystem; no application services or credentials."""
from pathlib import Path
import shutil
import json
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

TEMPLATE = Path(__file__).resolve().parents[2]
TOOL = TEMPLATE / 'tools/specdd.py'


class Workspace(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix='specdd-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'spec').mkdir()
        shutil.copytree(TEMPLATE / 'spec/templates', self.root / 'spec/templates')
        (self.root / 'spec/config.json').write_text(json.dumps({'prefix': 'SPEC'}))
        for state in ('planed', 'developing', 'implement', 'discard'):
            folder = self.root / 'spec' / state
            folder.mkdir()
            (folder / '.gitkeep').touch()
        self.run_tool('index')

    def run_tool(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(TOOL), '--root', str(self.root), *args],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0 if ok else 1, result.stdout + result.stderr)
        return result

    def create(self, slug='sample', title='示例功能'):
        result = self.run_tool('new', slug, '--title', title)
        return Path(result.stdout.strip())

    def confirm(self, ident='SPEC-001'):
        return self.run_tool('confirm', ident, '--by', '测试用户', '--evidence', '确认当前展示的方案',
                             '--source', '隔离测试夹具中的模拟反馈，不代表真实项目授权')

    def complete_documents(self, folder):
        for name in ('spec.md', 'tasks.md'):
            path = folder / name
            path.write_text(path.read_text(encoding='utf-8').replace('[ ]', '[x]'), encoding='utf-8')
        path = folder / 'verification.md'
        path.write_text(path.read_text(encoding='utf-8').replace('验收结论：未完成', '验收结论：通过'), encoding='utf-8')
