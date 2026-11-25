from pathlib import Path
import shutil
from _support import Workspace


class ConsistencyTests(Workspace):
    def test_stale_index_is_detected_and_repaired(self):
        self.create()
        self.confirm()
        (self.root / 'spec/INDEX.md').write_text('旧总览')
        result = self.run_tool('check', ok=False)
        self.assertIn('INDEX 不同步', result.stderr)
        self.run_tool('index')
        self.run_tool('check')

    def test_duplicate_ids_across_states_are_rejected(self):
        folder = self.create()
        self.confirm()
        shutil.copytree(folder, self.root / 'spec/discard/SPEC-001-other')
        self.assertIn('编号重复', self.run_tool('check', ok=False).stderr)

    def test_missing_state_directory_is_rejected(self):
        shutil.rmtree(self.root / 'spec/discard')
        self.run_tool('check', ok=False)

    def test_mismatched_heading_is_rejected(self):
        folder = self.create()
        self.confirm()
        (folder / 'spec.md').write_text('# SPEC-999 错误标题\n')
        self.run_tool('check', ok=False)

    def test_invalid_config_is_rejected(self):
        (self.root / 'spec/config.json').write_text('{invalid')
        self.run_tool('check', ok=False)
        (self.root / 'spec/config.json').write_text('{"prefix":"../bad"}')
        self.run_tool('check', ok=False)

    def test_symlink_state_is_rejected(self):
        shutil.rmtree(self.root / 'spec/discard')
        (self.root / 'spec/discard').symlink_to(self.root / 'spec/planed', target_is_directory=True)
        self.run_tool('check', ok=False)

    def test_loose_files_in_state_are_rejected(self):
        (self.root / 'spec/planed/loose.md').write_text('不能绕过需求目录')
        self.run_tool('check', ok=False)

    def test_completed_spec_with_unchecked_item_fails_check(self):
        self.create()
        self.confirm()
        result = self.run_tool('move', 'SPEC-001', 'developing', '--reason', '开始')
        folder = Path(result.stdout.strip())
        self.complete_documents(folder)
        result = self.run_tool('move', 'SPEC-001', 'implement', '--reason', '已验证', '--verified')
        folder = Path(result.stdout.strip())
        with (folder / 'tasks.md').open('a') as stream:
            stream.write('\n- [ ] 遗漏任务\n')
        self.run_tool('check', ok=False)

    def test_noncanonical_number_is_rejected(self):
        folder = self.create()
        self.confirm()
        folder.rename(folder.with_name('SPEC-0001-sample'))
        self.run_tool('check', ok=False)
