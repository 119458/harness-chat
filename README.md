# harness-chat

一个从零开始、单进程的 Python 教学型智能体编码框架复刻项目，复刻了 Claude Code 风格的智能体编码助手核心机制。项目以"可读、可跑、可拆解"为目标，把一个工业级编码智能体的各个子系统拆成独立模块，便于逐块学习其内部实现与拼接方式。

> 本项目参考并基于 [shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code) 学习复刻，在此向原作者致以感谢。
> 当前项目在该项目的基础上进行了**完善与延伸**：补全了若干缺失的子系统、修复了其中存在的问题与缺陷，使整体更完整、更健壮。后续计划采用**网页形式**对整套框架进行可视化展示，作为对该项目的进一步完善与延伸。

## 项目定位

- **学习参考，而非生产产品**：模块对应 Claude Code 的各个子系统（智能体循环、工具、钩子、权限、上下文压缩、记忆、子代理、多智能体协作、定时任务、后台任务、工作树隔离、MCP、技能），需要跨模块阅读才能理解各部分如何拼接。
- **单进程 + 多线程**：主进程内用守护线程驱动事件循环、后台任务、定时调度与队友协作，不依赖外部消息队列或数据库。
- **接驳大模型**：通过 `anthropic` SDK 调用模型；默认配置指向火山方舟（Volcengine Ark），模型为 `deepseek-v4-flash`（仅作示例，可自行更换）。

## 核心特性

| 子系统 | 模块 | 说明 |
| --- | --- | --- |
| 事件循环 / 入口 | `run.py` | 终端输入、收件箱轮询、cron 触发共同向事件队列投递，主循环分发 `user`/`wake`/`cron`/`quit` |
| 智能体循环 | `loop/loop.py` | 可复用的轮次引擎：记忆注入、API 调用、max_tokens 续聊、prompt 过长应急压缩、工具分发、收尾记忆提取 |
| 工具体系 | `tool/` | 内置工具 + MCP 工具统一装配，文件操作沙盒化；子代理/队友用更小的工具子集 |
| 系统提示词 | `system_prompt/` | 静态段（身份/规则/安全）+ 动态段（工作区、技能目录、记忆索引）实时拼装 |
| 上下文压缩 | `context/` | 四级机制：裁剪中间消息 → 旧结果占位 → 大输出溢出落盘 → LLM 摘要，并在 API 拒绝过长 prompt 时应急触发 |
| 记忆 | `memory/` | 文件式记忆库（每条一个 `.md` + frontmatter），LLM 筛选注入、轮末提取、超量合并 |
| 钩子 | `hooks/` | 按事件注册（PreToolUse/PostToolUse/Stop/...），首个非空返回短路 |
| 权限 | `permission/` | bash 危险命令黑名单 / 破坏性命令交互确认 / 工作区外写操作拦截 |
| 重试与恢复 | `error/` | 429 退避、529 降级、max_tokens 阈值上调与续聊、reactive 压缩 |
| 后台任务 | `background_tasks/` | 慢命令自动后台执行，结果在下一轮以通知注入 |
| 定时任务 | `cron_scheduler/` | 手写 5 段 cron 匹配器，durable 任务持久化，主循环内联触发 |
| 任务看板 | `task/` | 带依赖（blockedBy）的任务持久化，认领校验、完成自动解锁下游 |
| 多智能体协作 | `teams/` | 文件式消息总线、后台队友线程、方案审批/关停协议、空闲自主认领任务 |
| 子代理 | `subagent/` | 一次性隔离循环，仅返回最终结论 |
| 工作树隔离 | `worktree_isolation/` | 在沙盒下创建 git worktree，可绑定任务，未提交改动时拒绝删除 |
| MCP | `mcp_plugin/` | 模拟 MCP 服务端（docs/deploy），工具按 `mcp__<server>__<tool>` 前缀接入 |
| 技能 | `tool/skill_load.py` + `skills/` | 扫描 `SKILL.md`（YAML frontmatter）入注册表 |

## 快速开始

### 环境依赖

- Python 3.10+（代码使用了 `X | Y` 类型注解等 3.10+ 语法）
- 依赖（仓库无 requirements 文件，手动安装）：

```bash
pip install anthropic python-dotenv pyyaml humanfriendly
```

### 配置

在仓库根目录创建 `.env`：

```dotenv
BASE_URL=base_url   # 模型服务地址（示例为火山方舟）
API_KEY=your-api-key
MODEL=****
WORKDIR=工作路径                              # 智能体的沙盒根目录
```

> `MODEL`/`API_KEY`/`BASE_URL` 是仅有的模型配置项。代码使用 `anthropic` SDK，但可指向任意兼容端点，并非必须使用真正的 Anthropic API。

### 运行

```bash
python run.py        # 必须在仓库根目录运行：包式导入（from loop.loop import ...）依赖当前工作目录
```

输入消息 + 回车发送；`q` / `exit` 退出。

## 智能体的世界是 `WORKDIR`

`WORKDIR`（默认 `sandbox/`）是智能体的全部活动范围。运行时产生的一切状态都在其下，文件类工具通过 `safe_path` 被限制在内：

```
sandbox/
├── .mailbox/                 # 队友收件箱（<name>.jsonl）
├── .memory_store/            # 记忆库（*.md + MEMORY.md 索引）
├── .tasks/                   # 任务看板（task_*.json）
├── .task_outputs/tool-results/   # 溢出的大输出
├── .transcripts/             # 上下文压缩时的完整转写
├── .worktrees/               # git 工作树
├── .scheduled_tasks.json     # 持久化的定时任务
└── hook.log                  # 钩子日志
```

仓库自身的源码（包括本文件）在智能体工具的可达范围之外。

## 目录结构

```
study_harness/
├── run.py                    # 入口 / 事件循环
├── loop/                     # 智能体核心循环
├── tool/                     # 工具定义、装配、技能加载
├── system_prompt/            # 系统提示词拼装
├── context/                  # 上下文压缩
├── memory/                   # 记忆子系统
├── hooks/                    # 钩子注册表与内置钩子
├── permission/               # 权限规则
├── error/                    # 重试 / 恢复
├── background_tasks/         # 后台任务
├── cron_scheduler/           # 定时任务
├── task/                     # 任务看板
├── teams/                    # 多智能体协作（消息总线 / 协议 / 自主认领）
├── subagent/                 # 子代理
├── worktree_isolation/       # 工作树隔离
├── mcp_plugin/               # MCP（模拟）
├── skills/                   # 技能定义（SKILL.md）
└── sandbox/                  # WORKDIR：智能体沙盒
└── backend/                  # FastAPI：后端启动
└── frontend/                 # 整体前端代码
```

## 程序启动
```
pip install fastapi uvicorn pydantic humanfriendly pyyaml
python -m uvicorn backend.main:app --port 8000
cd frontend && npm install && npm run dev
```

## 后续计划

- **网页可视化展示**：将整套框架以网页形式呈现，让交互、工具调用、钩子触发、上下文压缩、多智能体协作等过程直观可见，降低学习门槛。
- 持续修复遗留缺陷、补全边界场景，使整体更完整健壮。

## 致谢

本项目在学习复刻过程中参考了 [shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)，感谢其开源分享为理解 Claude Code 风格智能体框架提供了起点。本项目在其基础上进行完善与延伸，旨在补全能力、修复缺陷，并以网页形式进一步展示。
