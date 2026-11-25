# SpecDD 管理工具

Python 3.9+ 标准库，无安装依赖。默认根目录取工具文件上一级，与命令执行位置无关；需要显式指定时将 `--root /path/to/project` 放在子命令之前。

| 命令 | 用途 |
| --- | --- |
| `python3 tools/specdd.py new slug --title "标题"` | 计算四目录最大编号 + 1，创建 planed 需求三件套，更新 INDEX |
| `python3 tools/specdd.py move SPEC-001 developing --reason "开始实施"` | 合法状态流转，追加原因与日期，更新 INDEX |
| `python3 tools/specdd.py move SPEC-001 implement --reason "必要验证和适用验收完成" --verified` | 检查完成项和显式验收结论后流转；不运行产品测试 |
| `python3 tools/specdd.py index` | 根据真实目录重建总览 |
| `python3 tools/specdd.py check` | 只读检查状态目录、唯一编号、标题、完成条件及 INDEX 是否同步 |

## 流转边界

允许 planed → developing/discard；developing → implement/discard/planed；implement → developing；discard → planed。每次必须记录原因。已实现需求的新扩展通常新建关联需求，而非改写历史。

进入 implement 同时要求：spec.md/tasks.md 中无未勾选项；verification.md 包含独立一行 `验收结论：通过`；操作者传入 `--verified`。合并式小需求可以把任务和验证写入 spec.md，工具使用该文件作为回退检查。

这些是防遗漏检查，不能证明测试真实运行，也不能检查“通过”是否诚实；开发者仍须记录完整证据，等待明确要求的用户验收。check 不校验所有文档语义、外部 URL、应用代码或业务行为。

## 命名与并发

编号前缀来自 spec/config.json；目录如 SPEC-001-user-login。slug 使用小写英文/数字/连字符；编号递增不复用。创建需求后不随意更换前缀；修改前缀时必须显式迁移历史编号和引用。

变更命令使用 spec/.specdd.lock，避免同一工作区并发分配编号；存在锁时会失败，确认无其他进程后才清理遗留锁。手工修改或不同 Git 分支不受此锁协调，合并时必须检查编号冲突。该工具面向本地 Git 工作区，不是事务数据库；进程或磁盘故障后检查目录，必要时运行 index 修复总览，并保留真实历史。

状态目录不能是符号链接，只允许需求子目录和 .gitkeep；需求 spec.md 不能是符号链接。失败返回非零。工具不会删除需求、推送仓库、部署服务或执行付费请求。
