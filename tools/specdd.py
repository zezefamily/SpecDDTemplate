#!/usr/bin/env python3
"""Dependency-free SpecDD administration. Python 3.9+. Does not execute product tests."""
import argparse
from contextlib import contextmanager
from datetime import date, datetime, timezone
import json
import hashlib
import os
from pathlib import Path
import re
import sys

STATES = ('planed', 'developing', 'implement', 'discard')
LABELS = dict(zip(STATES, ('计划中', '实施中', '已实现', '已取消')))
TRANSITIONS = {
    'planed': {'developing', 'discard'},
    'developing': {'implement', 'discard', 'planed'},
    'implement': {'developing'},
    'discard': {'planed'},
}


class SpecError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise SpecError(message)


def config(root):
    path = root / 'spec/config.json'
    try:
        result = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise SpecError('无法读取 spec/config.json: ' + str(exc)) from exc
    require(isinstance(result, dict), 'config 必须是 JSON 对象')
    prefix = result.get('prefix', '')
    require(isinstance(prefix, str) and re.fullmatch(r'[A-Z][A-Z0-9]{1,15}', prefix),
            'prefix 必须是 2–16 位大写字母/数字，且以字母开头')
    legacy = result.get('legacy_spec_ids', [])
    require(isinstance(legacy, list) and all(isinstance(i, str) and re.fullmatch(re.escape(prefix) + r'-[0-9]{3,}', i) for i in legacy),
            'legacy_spec_ids 必须是历史已实现需求编号列表')
    require(len(set(legacy)) == len(legacy), '历史编号列表重复')
    return result


# Only these execution-only sections are excluded. Unknown sections remain protected.
EXECUTION_SECTIONS = {'用户确认', '实施与验证', '变更记录', '实施任务', '验证记录', '执行记录', '交付与验收', '关键决策与交接'}
PROPOSAL_SECTIONS = {'背景与目标', '范围与非目标', '方案与影响', '验收标准'}


def proposal_hash(folder):
    text = (folder / 'spec.md').read_text(encoding='utf-8')
    lines = text.splitlines()
    require(lines and lines[0].startswith('# '), 'Spec 缺少标题')
    protected = [lines[0].rstrip()]
    seen, current, fence = [], None, None
    for line in lines[1:]:
        stripped = line.lstrip()
        marker = re.match(r'(`{3,}|~{3,})', stripped)
        in_fence = fence is not None
        if marker:
            value = marker.group(1)
            if fence is None:
                fence = value
            elif value[0] == fence[0] and len(value) >= len(fence):
                fence = None
        if not in_fence and not marker and line.startswith('## '):
            current = line[3:].strip()
            seen.append(current)
        if current is not None and current not in EXECUTION_SECTIONS:
            normalized = line.rstrip()
            if not in_fence and not marker:
                normalized = re.sub(r'^(\s*[-*]\s+)\[[ xX]\]', r'\1[]', normalized)
            protected.append(normalized)
    require(all(seen.count(name) == 1 for name in PROPOSAL_SECTIONS),
            'Spec 必须各包含一次：背景与目标、范围与非目标、方案与影响、验收标准')
    return hashlib.sha256(('\n'.join(protected).strip() + '\n').encode('utf-8')).hexdigest()


def approval_record(folder, ident):
    path = folder / 'approval.json'
    require(not path.is_symlink(), '确认记录不能为符号链接')
    if not path.exists():
        return {'schema_version': 1, 'spec_id': ident, 'confirmations': []}
    try:
        record = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise SpecError('确认记录无法读取，保留原记录后人工核对') from exc
    require(isinstance(record, dict) and record.get('schema_version') == 1 and record.get('spec_id') == ident,
            '确认记录版本或需求编号不匹配')
    receipts = record.get('confirmations')
    require(isinstance(receipts, list), '确认记录格式错误')
    for receipt in receipts:
        require(isinstance(receipt, dict) and all(isinstance(receipt.get(k), str) and receipt[k].strip()
                for k in ('confirmed_by', 'confirmed_at', 'evidence', 'source', 'proposal_sha256')), '确认记录字段不完整')
        require(re.fullmatch(r'[a-f0-9]{64}', receipt['proposal_sha256']), '确认指纹格式无效')
        try:
            stamp = datetime.fromisoformat(receipt['confirmed_at'])
            require(stamp.tzinfo is not None, '确认时间须含时区')
        except ValueError as exc:
            raise SpecError('确认时间无效') from exc
    return record


def assert_confirmed(root, folder, ident, allow_legacy=False):
    # Only historical implement entries are exempt from retroactive approval, never new development.
    if allow_legacy and ident in config(root).get('legacy_spec_ids', []):
        return
    receipts = approval_record(folder, ident)['confirmations']
    require(receipts, 'Spec 尚未获得用户明确确认：先展示方案，收到反馈后使用 confirm 记录')
    require(receipts[-1]['proposal_sha256'] == proposal_hash(folder),
            'Spec 方案已变化，原确认失效；先重新展示并取得用户确认')


def confirm(root, ident, by, evidence, source):
    matches = [e for e in scan(root, validate_state=False) if e[1] == ident]
    require(len(matches) == 1, '未找到唯一需求: ' + ident)
    require(all(value.strip() for value in (by, evidence, source)), '确认人、原话和来源均不能为空')
    folder = matches[0][2]
    record = approval_record(folder, ident)
    record['confirmations'].append({'confirmed_at': datetime.now(timezone.utc).isoformat(),
        'confirmed_by': by.strip(), 'evidence': evidence.strip(), 'source': source.strip(),
        'proposal_sha256': proposal_hash(folder)})
    (folder / 'approval.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    write_index(root)
    return folder / 'approval.json'


def scan(root, validate_state=True):
    prefix = config(root)['prefix']
    entries, ids = [], set()
    for state in STATES:
        folder = root / 'spec' / state
        require(folder.is_dir() and not folder.is_symlink(), '状态目录缺失或为符号链接: ' + state)
        for child in sorted(folder.iterdir()):
            if child.name == '.gitkeep':
                continue
            require(not child.is_symlink() and child.is_dir(), '状态目录只允许需求子目录: ' + str(child))
            match = re.fullmatch(re.escape(prefix) + r'-(\d{3,})-([a-z0-9]+(?:-[a-z0-9]+)*)', child.name)
            require(match is not None, '需求目录命名无效: ' + child.name)
            number = int(match.group(1))
            require(number > 0, '需求编号必须大于 0')
            require(match.group(1) == f'{number:03d}', '编号须采用至少三位的规范格式: ' + child.name)
            ident = prefix + '-' + f'{number:03d}'
            require(ident not in ids, '需求编号重复: ' + ident)
            ids.add(ident)
            spec = child / 'spec.md'
            require(spec.is_file() and not spec.is_symlink(), '缺少 spec.md: ' + child.name)
            text = spec.read_text(encoding='utf-8')
            first = text.splitlines()[0] if text else ''
            require(first.startswith('# ' + ident + ' '), 'spec 标题编号不一致: ' + child.name)
            if validate_state and state in ('developing', 'implement'):
                assert_confirmed(root, child, ident, allow_legacy=state == 'implement')
            if validate_state and state == 'implement':
                assert_complete(child)
            entries.append((state, ident, child, first[2:]))
    return entries


def assert_complete(folder):
    for name in ('spec.md', 'tasks.md'):
        path = folder / name
        if path.exists():
            require(not path.is_symlink(), '需求文档不能为符号链接')
            require(not re.search(r'^\s*[-*]\s+\[ \]', path.read_text(encoding='utf-8'), re.M),
                    '存在未完成项，不能进入 implement: ' + name)
    verification = folder / 'verification.md'
    if verification.exists():
        require(not verification.is_symlink(), '验证记录不能为符号链接')
        text = verification.read_text(encoding='utf-8')
    else:
        text = (folder / 'spec.md').read_text(encoding='utf-8')
    require(re.search(r'^验收结论：通过\s*$', text, re.M),
            '验证记录须包含独立一行“验收结论：通过”，并先完成实际测试及适用验收')


def index_text(entries):
    lines = ['# 需求总览', '', '> 由 tools/specdd.py 生成；请勿手工维护本文件。状态由所在目录决定。',
             '> 项目现状见 [BASELINE.md](BASELINE.md)，规则见 [README.md](README.md)。', '']
    for state in STATES:
        lines += ['## ' + LABELS[state] + ' · ' + state, '']
        matching = sorted((e for e in entries if e[0] == state), key=lambda e: int(e[1].rsplit('-', 1)[1]))
        if matching:
            lines += ['| 需求 | 文档 |', '| --- | --- |']
            for _, _, folder, title in matching:
                lines.append('| ' + title.replace('|', '／') + ' | [查看](' + state + '/' + folder.name + '/spec.md) |')
        else:
            lines.append('暂无需求。')
        lines.append('')
    return '\n'.join(lines)


def write_index(root):
    text = index_text(scan(root, validate_state=False))
    (root / 'spec/INDEX.md').write_text(text, encoding='utf-8')


@contextmanager
def mutation_lock(root):
    path = root / 'spec/.specdd.lock'
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise SpecError('已有操作锁 spec/.specdd.lock；确认没有其他进程后才能清理遗留锁') from exc
    try:
        os.close(fd)
        yield
    finally:
        path.unlink()


def create(root, slug, title):
    require(re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug), 'slug 只能使用小写字母、数字与单个连字符')
    require(title.strip() and not any(c in title for c in '\n\r[]'), '标题不能为空，且不能含换行或方括号')
    entries = scan(root)
    prefix = config(root)['prefix']
    number = max((int(e[1].rsplit('-', 1)[1]) for e in entries), default=0) + 1
    ident = prefix + '-' + f'{number:03d}'
    folder = root / 'spec/planed' / (ident + '-' + slug)
    replacements = {'{{SPEC_ID}}': ident, '{{TITLE}}': title.strip(), '{{DATE}}': date.today().isoformat()}
    documents = {}
    for name in ('spec.md', 'tasks.md', 'verification.md'):
        text = (root / 'spec/templates' / name).read_text(encoding='utf-8')
        for key, value in replacements.items():
            text = text.replace(key, value)
        require(not re.search(r'\{\{[^}]+\}\}', text), '模板存在未知占位符: ' + name)
        documents[name] = text
    folder.mkdir()
    for name, text in documents.items():
        (folder / name).write_text(text, encoding='utf-8')
    write_index(root)
    return folder


def move(root, ident, target, reason, verified=False):
    entries = scan(root, validate_state=False)
    matches = [e for e in entries if e[1] == ident]
    require(len(matches) == 1, '未找到唯一需求: ' + ident)
    source, _, folder, _ = matches[0]
    require(target in TRANSITIONS[source], '不允许流转: ' + source + ' → ' + target)
    require(reason.strip() and '\n' not in reason and '\r' not in reason, '流转原因必须是非空单行文本')
    if target in ('developing', 'implement'):
        assert_confirmed(root, folder, ident)
    if target == 'implement':
        require(verified, '进入 implement 需要 --verified，表示已实际完成必要验证和适用验收')
        assert_complete(folder)
    dest = root / 'spec' / target / folder.name
    require(not dest.exists(), '目标目录已存在')
    folder.rename(dest)
    with (dest / 'spec.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- ' + date.today().isoformat() + '：' + source + ' → ' + target + '；' + reason.strip() + '\n')
    write_index(root)
    return dest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest='command', required=True)
    new = sub.add_parser('new', help='创建 planed 需求并同步总览')
    new.add_argument('slug')
    new.add_argument('--title', required=True)
    confirmation = sub.add_parser('confirm', help='仅在用户查看当前方案并明确确认后记录；不会自动取得用户批准')
    confirmation.add_argument('id')
    confirmation.add_argument('--by', required=True)
    confirmation.add_argument('--evidence', required=True)
    confirmation.add_argument('--source', required=True)
    mv = sub.add_parser('move', help='移动状态；不会替你运行测试')
    mv.add_argument('id')
    mv.add_argument('state', choices=STATES)
    mv.add_argument('--reason', required=True)
    mv.add_argument('--verified', action='store_true')
    sub.add_parser('index', help='从目录重建总览')
    sub.add_parser('check', help='只读检查目录、编号、完成条件及总览一致性')
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        config(root)
        if args.command == 'check':
            entries = scan(root)
            require((root / 'spec/INDEX.md').read_text(encoding='utf-8') == index_text(entries),
                    'INDEX 不同步，请运行 python3 tools/specdd.py index')
            print('SpecDD 检查通过：' + str(len(entries)) + ' 个需求')
        else:
            with mutation_lock(root):
                if args.command == 'new':
                    print(create(root, args.slug, args.title))
                elif args.command == 'confirm':
                    print(confirm(root, args.id, args.by, args.evidence, args.source))
                elif args.command == 'move':
                    print(move(root, args.id, args.state, args.reason, args.verified))
                else:
                    write_index(root)
                    print('INDEX 已同步')
    except (SpecError, OSError) as exc:
        print('SpecDD: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
