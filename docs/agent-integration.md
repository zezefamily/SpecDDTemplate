# Code Agent 接入与验证

核实日期：2026-11-25。规范正文统一维护在 [DEVELOPMENT.md](../DEVELOPMENT.md)。这些入口只负责发现、导入或引导读取，不保存第二套规则。开发前必须先展示具体 Spec 并得到用户明确确认；更换 Agent 不会取消已有门槛。

## 分层

- DEVELOPMENT.md：Agent 无关的开发约束正文。
- 项目配置/运行文档：项目事实、目录、技术栈、真实命令和专属边界。
- spec/README.md、INDEX.md 与需求目录：流转细节、当前工作和确认/验证证据。
- 各 Agent 入口：使用其支持的格式指向正文；特定导入语法不进入规范正文。

## 已提供的入口

| 工具/环境 | 本项目入口 | 读取方式与限制 | 官方依据 |
| --- | --- | --- | --- |
| Codex | [AGENTS.md](../AGENTS.md) | 原生项目指令入口，引导显式读取 DEVELOPMENT.md；不声称普通 Markdown 链接会自动内联，注意子目录/override 与运行目录 | [官方 AGENTS 指南](https://learn.chatgpt.com/docs/agent-configuration/agents-md) |
| Claude Code | [CLAUDE.md](../CLAUDE.md) | 使用根文件中的 @DEVELOPMENT.md 导入；不要将该语法当作所有 Agent 的共同能力 | [官方内存与导入说明](https://code.claude.com/docs/en/memory#import-additional-files) |
| Cursor | [.cursor/rules/specdd.mdc](../.cursor/rules/specdd.mdc) | alwaysApply: true 使入口规则持续加入上下文；正文仍需 Agent 通过工具读取，不假设引用会自动展开 | [官方规则与文件引用说明](https://cursor.com/docs/rules) |
| GitHub Copilot | [.github/copilot-instructions.md](../.github/copilot-instructions.md) | 仓库级入口通过自然语言要求读取规范；客户端/功能支持及启用设置存在差异，按实际 References 检查 | [官方仓库指令说明](https://docs.github.com/en/copilot/how-tos/copilot-in-your-ide/customize-copilot/configure-custom-instructions/add-repository-instructions-in-your-ide?tool=vscode)、[功能支持矩阵](https://docs.github.com/en/copilot/reference/custom-instructions-support) |
| Gemini CLI | [GEMINI.md](../GEMINI.md) | 使用 @./DEVELOPMENT.md 导入；上下文发现受工作区/信任根与配置影响，不修改用户全局配置 | [官方上下文与导入说明](https://geminicli.com/docs/cli/gemini-md/) |
| 其他 Agent / 人工开发 | 显式打开 DEVELOPMENT.md | 使用下方通用启动提示；不依赖某个固定保留文件名或导入宏 | 本仓库工作约定 |

这些是依据官方文档提供的适配，不保证每个版本、客户端或受限环境都会自动发现。入口无法加载时使用显式路径；不要把相互冲突的完整规则复制到多个文件里。迁入已有项目时先合并，保留其已有局部规则，不覆盖入口文件中的其他有效约束。

## 通用会话启动提示

```text
请从当前项目根目录完整读取 DEVELOPMENT.md，
再读取项目配置与真实运行/测试命令、spec/README.md、spec/INDEX.md
以及本次相关 Spec。修改子目录前读取适用的局部规则。
请先列出已实际读取的文件和当前需求所处阶段。
如果本次是新需求，先完成并展示 Spec 等我确认，再开始开发。
```

提示只要求文件读取和正常协作，没有工具特定宏指令。无法读取、文件缺失或权限受限时，说明实际阻塞；不能把“已看到入口文件”写成“已读完整规范”。用户或运行环境的更高优先级指令与权限边界仍适用。

## 怎么验证接入

1. 在目标项目根目录开启新会话，检查客户端是否展示适用入口；必要时要求 Agent 列出已读文件，并核对其对当前需求/阶段的回答。
2. Claude Code 可查看 /memory；Gemini CLI 可查看 /memory show；Copilot 可查看响应 References。Codex 按官方指南检查已加载指令和启动目录；Cursor 检查该 .mdc 的 Always Apply 设置，并确认 Agent 实际读取规范正文。
3. 用一条只读请求让 Agent 说明新需求开工前条件，预期为“先展示 Spec 并等待明确确认”；不能为了测试接入而自动确认需求或开始业务实现。
4. 记录产品/版本、入口、验证步骤、实际结果与未验证项。不能把测试工具通过、--version 输出或入口文件存在当作 Agent 自动遵循规则的证明。

## 本次实际验证状态

- 五种入口的格式、正文引用及所有本地路径完成静态检查，模板复制后再次检查。
- 本次 Codex 会话显式读取了 DEVELOPMENT.md，并核对当前已确认方案的记录；这是显式读取验证，不是新会话自动发现验证。
- 可用本地命令版本：codex-cli 0.164.0-alpha.11.1、Claude Code 2.1.110。只运行 --version，没有启动其他 Agent 的模型会话或修改其账户/全局配置。
- 各客户端的新会话自动加载及模型实际遵循情况均未完成独立实测；Cursor、Copilot、Gemini CLI 的 CLI 未在本次命令路径中发现。这些客户端标记为“依据官方文档配置，未实测”。

没有 Python 时仍遵循 [手工流程](manual-workflow.md)，不能省略 Spec 确认和测试验收。
