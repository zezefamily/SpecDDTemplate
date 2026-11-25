# SpecDDTemplate

面向自建项目的 SpecDD（Specification-Driven Development）脚手架：用需求规格驱动实现，用测试与验收证据管理进度，用统一开发规范和 Agent 入口让后续会话接续工作。

模板与业务语言、框架、部署平台无关。应用代码由你的项目选择，不预装 Node、Web、Agent 或数据库。文档可直接使用；可选管理工具仅需要 Python 3.9+，不需要额外依赖。

## 用于新项目

将本仓库作为 Git 模板创建新仓库，或复制到新目录。复制时排除 `.git`，保留目标项目自己的 Git 历史；本地示例（先把路径换成实际的新目录）：

```sh
mkdir -p /path/to/MyProject
rsync -av --exclude='.git/' --exclude='__pycache__/' --exclude='tmp/' /path/to/SpecDDTemplate/ /path/to/MyProject/
cd /path/to/MyProject
git init
```

复制之前确认目标是空目录。已有项目请使用下面的迁入流程，不直接覆盖文件。

1. 填写 [PROJECT.md](PROJECT.md)：项目名称、技术栈、目录、真实运行/测试命令和领域约束。
2. 在 [spec/config.json](spec/config.json) 设置需求编号前缀；默认 `SPEC`，第一次创建需求后保持稳定。
3. 填写 [spec/BASELINE.md](spec/BASELINE.md)：新项目注明暂无业务实现；已有内容依据事实记录。
4. 阅读 [AGENTS.md](AGENTS.md) 和 [SpecDD 规则](spec/README.md)，创建第一个需求：

```sh
python3 tools/specdd.py new first-feature --title "第一个功能"
python3 tools/specdd.py check
```

打开新建目录补全 spec.md、tasks.md、verification.md，不把空模板当作完成的设计。随后向用户展示具体 Spec 并等待明确确认；原始需求本身不能代替展示后的反馈。

## 一次需求的完整流转

```sh
# 先完善并向用户展示 Spec；只有收到真实确认后，才记录并开始实现
python3 tools/specdd.py confirm SPEC-001 --by "用户" \
  --evidence "确认" --source "用户查看当前 Spec 后的会话消息"
python3 tools/specdd.py move SPEC-001 developing --reason "需求已明确并开始实施"

# 开发完成后编写 test case，按影响执行增量或全量回归
# 在 verification.md 记录实际结果，完成适用验收，并写：验收结论：通过
# 只有实际完成的 spec/tasks 清单才能勾选
python3 tools/specdd.py move SPEC-001 implement --reason "实现、回归与适用验收完成" --verified
python3 tools/specdd.py check
```

`confirm` 只记录已经收到的用户反馈，不能由 Agent 自行批准；没有匹配确认不能进入开发。实质方案改变需重新展示确认。`--verified` 是操作者对已完成验证的声明，不运行测试。需要用户验收时必须等待真实反馈。取消使用 `move <编号> discard --reason "原因"`；恢复、退回和限制见 [工具说明](docs/tooling.md)。

## 迁入已有项目

先检查现有工作区、AGENTS.md、测试结构与文档，合并开发守则而非覆盖。按需迁入 spec/、tools/specdd.py 和 tests/specdd/；如果已有同名目录或编号，先处理冲突并保留历史。将工具测试整合进原有测试入口，命令填写到 PROJECT.md，建立现状基线。不得追溯伪造过去的 Spec、测试或验收记录。

迁入详细清单见 [使用指南](docs/adoption.md)。

## 模板自身的验证

```sh
python3 -m unittest discover -s tests/specdd -p 'test_*.py' -v
python3 tools/specdd.py check
```

这两条只验证 SpecDD 工具与目录，不验证你将来编写的产品。产品的增量/全量测试由项目实际技术栈决定，必须另行配置。本轮完整结果见 [模板维护验证记录](docs/template-verification.md)。

## 目录

```text
DEVELOPMENT.md            唯一开发规范正文
AGENTS.md / CLAUDE.md      Agent 发现/导入入口
GEMINI.md                 Gemini 上下文入口
.cursor/ / .github/       Cursor / Copilot 薄入口
PROJECT.md                项目技术栈、命令和领域约束
spec/
  config.json             需求编号前缀
  README.md               流转与交付规范
  INDEX.md                从目录自动生成的需求总览
  BASELINE.md             当前事实与已有能力
  planed/                 待实施
  developing/             实施、阻塞、待验证/验收
  implement/              已实现且完成适用验收
  discard/                已取消/被替代
  templates/              Spec、任务、测试与验证模板
tools/specdd.py           创建、流转、同步和检查工具
tests/                    按模块组织的测试与执行说明
docs/                     迁入、工具和模板维护说明
```

模板业务需求目录初始为空，首个需求默认从 SPEC-001 开始。没有业务功能、生产部署或业务测试已完成的隐含声明。

## 跨 Code Agent 的开发规范

统一约束见 [DEVELOPMENT.md](DEVELOPMENT.md)，各工具入口及实际验证边界见 [接入说明](docs/agent-integration.md)。不支持自动加载的 Agent 使用通用启动提示；工具不可用时遵循 [手工流程](docs/manual-workflow.md)。
