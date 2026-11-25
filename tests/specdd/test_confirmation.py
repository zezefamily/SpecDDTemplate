import json
from pathlib import Path
import shutil
from _support import Workspace


class ConfirmationTests(Workspace):
    def develop(self):
        self.create()
        self.confirm()
        result = self.run_tool('move', 'SPEC-001', 'developing', '--reason', '按已确认方案实施')
        return Path(result.stdout.strip())

    def test_unconfirmed_spec_cannot_develop(self):
        folder = self.create()
        result = self.run_tool('move', 'SPEC-001', 'developing', '--reason', '仅提出需求', ok=False)
        self.assertIn('尚未获得用户明确确认', result.stderr)
        self.assertTrue(folder.exists())
        self.assertFalse((folder / 'approval.json').exists())
        self.run_tool('check')

    def test_confirm_records_evidence_then_development_is_allowed(self):
        folder = self.create()
        self.confirm()
        record = json.loads((folder / 'approval.json').read_text())
        self.assertEqual(record['spec_id'], 'SPEC-001')
        receipt = record['confirmations'][0]
        self.assertTrue(receipt['confirmed_at'].endswith('+00:00'))
        self.assertEqual(receipt['confirmed_by'], '测试用户')
        self.assertIn('当前展示', receipt['evidence'])
        self.assertEqual(len(receipt['proposal_sha256']), 64)
        self.run_tool('move', 'SPEC-001', 'developing', '--reason', '明确确认后实施')
        self.run_tool('check')

    def test_scope_change_invalidates_approval_and_new_confirmation_retains_history(self):
        folder = self.create()
        self.confirm()
        path = folder / 'spec.md'
        path.write_text(path.read_text().replace('填写交付范围', '新增收费范围'))
        self.run_tool('move', 'SPEC-001', 'developing', '--reason', '使用旧确认', ok=False)
        self.confirm()
        receipts = json.loads((folder / 'approval.json').read_text())['confirmations']
        self.assertEqual(len(receipts), 2)
        self.assertNotEqual(receipts[0]['proposal_sha256'], receipts[1]['proposal_sha256'])
        self.run_tool('move', 'SPEC-001', 'developing', '--reason', '已重新展示确认')

    def test_check_detects_stale_active_spec_and_reconfirm_repairs(self):
        folder = self.develop()
        path = folder / 'spec.md'
        path.write_text(path.read_text().replace('期望行为与收益', '新的目标行为'))
        self.assertIn('原确认失效', self.run_tool('check', ok=False).stderr)
        self.run_tool('index')
        self.run_tool('check', ok=False)
        self.confirm()
        self.run_tool('check')

    def test_unconfirmed_manual_move_is_detected(self):
        folder = self.create()
        folder.rename(self.root / 'spec/developing' / folder.name)
        self.run_tool('index')
        self.run_tool('check', ok=False)

    def test_progress_timestamps_history_and_checkboxes_do_not_invalidate(self):
        folder = self.develop()
        path = folder / 'spec.md'
        text = path.read_text().replace('更新：', '最近更新：').replace('[ ]', '[x]')
        text = text.replace('当前阶段：Spec 待用户确认。', '当前阶段：已确认并执行中。')
        text += '\n- 新增执行进展日志。\n'
        path.write_text(text)
        with (folder / 'tasks.md').open('a') as stream:
            stream.write('\n- [x] 新增已完成任务记录。\n')
        self.run_tool('check')
        self.complete_documents(folder)
        self.run_tool('move', 'SPEC-001', 'implement', '--reason', '按约定验证通过', '--verified')
        self.run_tool('check')

    def test_changed_acceptance_text_requires_new_confirmation(self):
        folder = self.develop()
        path = folder / 'spec.md'
        path.write_text(path.read_text().replace('可检查的行为或结果', '要求不同的业务行为'))
        self.run_tool('check', ok=False)

    def test_unknown_added_section_is_protected(self):
        folder = self.develop()
        with (folder / 'spec.md').open('a') as stream:
            stream.write('\n## 新的约定\n必须支持额外平台。\n')
        self.run_tool('check', ok=False)

    def test_fenced_heading_does_not_hide_scope_content(self):
        folder = self.create()
        path = folder / 'spec.md'
        text = path.read_text().replace('## 方案与影响\n', '## 方案与影响\n\n```md\n## 变更记录\n核心规则 A\n```\n')
        path.write_text(text)
        self.confirm()
        path.write_text(text.replace('核心规则 A', '核心规则 B'))
        self.run_tool('move', 'SPEC-001', 'developing', '--reason', '不能把代码内标题用来藏范围', ok=False)

    def test_empty_evidence_is_rejected(self):
        self.create()
        self.run_tool('confirm', 'SPEC-001', '--by', '用户', '--evidence', ' ', '--source', '消息', ok=False)

    def test_malformed_and_wrong_id_records_are_preserved(self):
        folder = self.create()
        path = folder / 'approval.json'
        path.write_text('{bad')
        self.confirm_fails()
        self.assertEqual(path.read_text(), '{bad')
        path.write_text(json.dumps({'schema_version': 1, 'spec_id': 'SPEC-999', 'confirmations': []}))
        self.confirm_fails()
        self.assertEqual(json.loads(path.read_text())['spec_id'], 'SPEC-999')

    def confirm_fails(self):
        self.run_tool('confirm', 'SPEC-001', '--by', '用户', '--evidence', '确认', '--source', '展示后反馈', ok=False)

    def test_symlink_record_is_rejected(self):
        folder = self.create()
        outside = self.root / 'outside.json'
        outside.write_text('{}')
        (folder / 'approval.json').symlink_to(outside)
        self.confirm_fails()
        self.assertEqual(outside.read_text(), '{}')

    def test_discard_and_restore_cannot_skip_confirmation(self):
        self.create()
        self.run_tool('move', 'SPEC-001', 'discard', '--reason', '取消不需要批准开发')
        self.run_tool('move', 'SPEC-001', 'planed', '--reason', '重新评估')
        self.run_tool('move', 'SPEC-001', 'developing', '--reason', '未确认', ok=False)
        self.confirm()
        self.run_tool('move', 'SPEC-001', 'developing', '--reason', '确认后恢复')

    def test_legacy_completed_exemption_never_authorizes_reopening(self):
        folder = self.create()
        self.complete_documents(folder)
        dest = self.root / 'spec/implement' / folder.name
        folder.rename(dest)
        self.run_tool('index')
        self.run_tool('check', ok=False)
        cfg = self.root / 'spec/config.json'
        cfg.write_text(json.dumps({'prefix': 'SPEC', 'legacy_spec_ids': ['SPEC-001']}))
        self.run_tool('check')
        self.run_tool('move', 'SPEC-001', 'developing', '--reason', '历史不等于本次批准', ok=False)
        self.confirm()
        self.run_tool('move', 'SPEC-001', 'developing', '--reason', '本次方案已明确确认')
        self.run_tool('check')

    def test_legacy_id_in_planed_does_not_bypass_gate(self):
        self.create()
        (self.root / 'spec/config.json').write_text(json.dumps({'prefix': 'SPEC', 'legacy_spec_ids': ['SPEC-001']}))
        self.run_tool('move', 'SPEC-001', 'developing', '--reason', '不能豁免新开发', ok=False)

    def test_missing_proposal_sections_cannot_be_confirmed(self):
        folder = self.create()
        path = folder / 'spec.md'
        path.write_text(path.read_text().replace('## 范围与非目标', '## 普通描述'))
        self.confirm_fails()

    def test_development_confirmation_does_not_replace_final_verification(self):
        self.develop()
        self.run_tool('move', 'SPEC-001', 'implement', '--reason', '把确认当成完成', '--verified', ok=False)
