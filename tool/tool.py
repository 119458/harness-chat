import ast
import json
import os
import subprocess
from pathlib import Path



WORKDIR = Path(os.getenv("WORKDIR"))
CURRENT_TODOS: list[dict] = []

def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"路径{p}不在工作内")
    return path

def run_bash(command: str, run_in_background: bool=False) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except (FileNotFoundError, OSError) as e:
        return f"Error: {e}"

def run_read(path: str, limit: int | None = None) -> str:

    try:
        lines = safe_path(path).read_text().splitlines()

        if limit and limit < len(lines):
            lines = lines[:limit] + [f"...({len(lines) - limit})多行"]

        return "\n".join(lines)
    except Exception as e:
        return f"错误: {e}"

def run_write(path: str, content: str) -> str:
    try:
        file_path = safe_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return f"写入{len(content)}字节到{path}中"
    except Exception as e:
        return f"错误: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        file_path = safe_path(path)
        text = file_path.read_text()
        if old_text not in text:
            return f"没有在{path}中发现需要修改的部分"
        file_path.write_text(text.replace(old_text, new_text, 1))
        return f"修改完成"
    except Exception as e:
        return f"错误: {e}"


def run_glob(pattern: str) -> str:
    import glob as g
    try:
        results = []
        for match in g.glob(pattern, root_dir=WORKDIR):
            if (WORKDIR / match).resolve().is_relative_to(WORKDIR):
                results.append(match)
        return "\n".join(results) if results else "没有匹配"
    except Exception as e:
        return f"错误: {e}"

def _normalize_todos(todos):
    if isinstance(todos, str):
        try:
            todos = json.loads(todos)
        except json.JSONDecodeError:
            try:
                todos = ast.literal_eval(todos)
            except (SyntaxError, ValueError):
                return None, "错误：todos必须是一个列表或JSON数组字符串"
    if not isinstance(todos, list):
        return None, "错误：todos必须是一个列表"
    for i, t in enumerate(todos):
        if not isinstance(t, dict):
            return None, f"错误：todos[{i}]必须是一个对象"
        if "content" not in t or "status" not in t:
            return None, f"错误：todos[{i}]缺少'内容'或'状态'"
        if t["status"] not in ("pending", "in_progress", "completed"):
            return None, f"错误：todos[{i}]具有无效状态'{t['status']}'"
    return todos, None

# def run_todo_write(todos: list) -> str:
#     global CURRENT_TODOS
#     todos, error = _normalize_todos(todos)
#     if error:
#         return error
#     CURRENT_TODOS = todos
#     lines = ["\n\033[33m## Current Tasks\033[0m"]
#     for t in CURRENT_TODOS:
#         icon = {
#             "pending": " ",
#             "in_progress": "\033[36m▸\033[0m", "completed": "\033[32m✓\033[0m"
#         }[t["status"]]
#         lines.append(f" [{icon}] {t['content']}")
#     print("\n".join(lines))
#     return f"更新{len(CURRENT_TODOS)}个任务"

TOOLS = [
    {
        "name": "bash",
        "description": "运行shell命令",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"},
                           "run_in_background": {"type": "boolean"},},
            "required": ["command"]
        }
    },
    {
        "name": "read_file",
        "description": "读取文件内容",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "将内容写入文件",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"]
        }
    },
    {
        "name": "edit_file",
        "description": "替换文件中的精确文本一次",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}},
            "required": ["path", "old_text", "new_text"]
        }
    },
    {
        "name": "glob",
        "description": "查找匹配glob模式的文件",
        "input_schema": {
            "type": "object",
            "properties": {"pattern": {"type": "string"}},
            "required": ["pattern"]
        }
    },
    # {
    #     "name": "todo_write",
    #     "description": "为当前编码会话创建和管理任务列表",
    #     "input_schema": {
    #         "type": "object",
    #         "properties": {
    #             "todos": {
    #                 "type": "array",
    #                 "items": {
    #                     "type": "object",
    #                     "properties": {
    #                         "content": {
    #                             "type": "string",
    #                             "status": {
    #                                 "type": "string",
    #                                 "enum": ["pending", "in_progress", "completed"]
    #                             }
    #                         },
    #                         "required": ["content", "status"]
    #                     }
    #                 }
    #             },
    #             "required": ["todos"]
    #         }
    #     }
    # },
    {
        "name": "load_skill",
        "description": "按名称加载技能的全部内容",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"]
        }
    },
    {
        "name": "compact",
        "description": "当上下文空间小于13k时，将聊天记录进行压缩总结以腾出空间"
    }
]

TOOL_HANDLERS = {
    "bash": run_bash,
    "read_file": run_read,
    "write_file": run_write,
    "edit_file": run_edit,
    "glob": run_glob,
    # "todo_write": run_todo_write
}

SUB_TOOLS = [
{
        "name": "bash",
        "description": "运行shell命令",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"]
        }
    },
    {
        "name": "read_file",
        "description": "读取文件内容",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "将内容写入文件",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"]
        }
    },
    {
        "name": "edit_file",
        "description": "替换文件中的精确文本一次",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}},
            "required": ["path", "old_text", "new_text"]
        }
    },
    {
        "name": "glob",
        "description": "查找匹配glob模式的文件",
        "input_schema": {
            "type": "object",
            "properties": {"pattern": {"type": "string"}},
            "required": ["pattern"]
        }
    }
]

SUB_HANDLERS = {
    "bash": run_bash,
    "read_file": run_read,
    "write_file": run_write,
    "edit_file": run_edit,
    "glob": run_glob
}

TOOLS.append({
    "name": "subagent",
    "description": "启动子代理来处理复杂的子任务,只返回最终结论。",
    "input_schema": {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
            }
        },
        "required": ["description"]
    }
})

TOOLS.append({
    "name": "create_task",
    "description": "创建新任务，可按需设置前置阻塞依赖（blockedBy）。",
    "input_schema": {
        "type": "object",
        "properties": {
            "subject": {"type": "string"},
            "description": {"type": "string"},
            "blockedBy": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["subject"]
    }
})
TOOLS.append({
    "name": "list_tasks",
    "description": "列出所有任务，附带任务状态、负责人以及依赖关系信息。",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
})
TOOLS.append({
    "name": "get_task",
    "description": "根据任务 ID 获取指定任务的完整详情。",
    "input_schema": {
        "type": "object",
        "properties": {"task_id": {"type": "string"}},
        "required": ["task_id"]
    }
})
TOOLS.append({
    "name": "claim_task",
    "description": "认领待处理任务：指定任务负责人，并将任务状态修改为进行中。",
    "input_schema": {
        "type": "object",
        "properties": {"task_id": {"type": "string"}},
        "required": ["task_id"]
    }
})
TOOLS.append({
    "name": "complete_task",
    "description": "完成正在进行中的任务，并自动解除后续下游任务的阻塞限制。",
    "input_schema": {
        "type": "object",
        "properties": {"task_id": {"type": "string"}},
        "required": ["task_id"]
    }
})

TOOLS.append({
    "name": "schedule_cron",
    "description": "创建定时调度任务，Cron 表达式采用 5 位格式：分 时 日 月 周。",
    "input_schema": {
        "type": "object",
        "properties": {
            "cron": {
                "type": "string",
                "description": "5字段Cron表达式"
            },
            "prompt": {
                "type": "string",
                "description": "任务触发时注入的消息内容"
            },
            "recurring": {
                "type": "boolean",
                "description": "True=recurring, False=one-shot"
            },
            "durable": {
                "type": "boolean",
                "description": "True=persist to disk"
            }
        },
        "required": ["cron", "prompt"]
    }
})

TOOLS.append({
    "name": "list_crons",
    "description": "列出所有已注册的定时任务。",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
})

TOOLS.append({
    "name": "cancel_cron",
    "description": "根据任务 ID 取消一条定时任务。",
    "input_schema": {
        "type": "object",
        "properties": {"job_id": {"type": "string"}},
        "required": ["job_id"]
    }
})

TOOLS.append({
    "name": "spawn_teammate",
    "description": "在后台线程中创建一个协作智能体。",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "role": {"type": "string"},
            "prompt": {"type": "string"},
        },
        "required": ["name", "role", "prompt"]
    }
})

TOOLS.append({
    "name": "send_message",
    "description": "通过消息总线（MessageBus）向协作成员发送消息。",
    "input_schema": {
        "type": "object",
        "properties": {
            "to": {"type": "string"},
            "content": {"type": "string"}
        },
        "required": ["to", "content"]
    }
})

TOOLS.append({
    "name": "check_inbox",
    "description": "查看负责人(lead)收件箱，协议类响应消息将自动完成路由分发",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
})

TOOLS.append({
    "name": "request_shutdown",
    "description": "请求一名协作成员执行合规关停",
    "input_schema": {
        "type": "object",
        "properties": {"teammate": {"type": "string"}},
        "required": ["teammate"]
    }
})

TOOLS.append({
    "name": "request_plan",
    "description": "指派协作成员提交方案以供审核",
    "input_schema": {
        "type": "object",
        "properties": {
            "teammate": {"type": "string"},
            "task": {"type": "string"},
        },
        "required": ["teammate", "task"]
    }
})

TOOLS.append({
    "name": "review_plan",
    "description": "根据请求ID(request_id)，对已提交的方案执行批准或驳回操作",
    "input_schema": {
        "type": "object",
        "properties": {
            "request_id": {"type": "string"},
            "approve": {"type": "boolean"},
            "feedback": {"type": "string"}
        },
        "required": ["request_id", "approve"]
    }
})

TOOLS.append({
    "name": "create_worktree",
    "description": "创建独立专属分支的隔离 Git Worktree",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "task_id": {"type": "string"},
        },
        "required": ["name"]
    }
})

TOOLS.append({
    "name": "remove_worktree",
    "description": "移除工作树，存在未提交修改时将拒绝操作，除非discard_changes=true。",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "discard_changes": {"type": "boolean"},
        },
        "required": ["name"]
    }
})

TOOLS.append({
    "name": "keep_worktree",
    "description": "保留工作树用于人工复核",
    "input_schema": {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"]
    }
})

TOOLS.append({
    "name": "connect_mcp",
    "description": "连接MCP服务端（文档、部署模块）并自动探测可用工具",
    "input_schema": {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"]
    }
})

try:
    from subagent.sub_agent import spawn_subagent
    TOOL_HANDLERS["subagent"] = spawn_subagent
except ImportError as e:
    pass

try:
    from tool.skill_load import load_skill
    TOOL_HANDLERS["load_skill"] = load_skill
except ImportError as e:
    pass

try:
    from task.tasks import run_create_task, run_list_tasks, run_get_task, run_claim_task, run_complete_task

    TOOL_HANDLERS["create_task"] = run_create_task
    TOOL_HANDLERS["list_tasks"] = run_list_tasks
    TOOL_HANDLERS["get_task"] = run_get_task
    TOOL_HANDLERS["claim_task"] = run_claim_task
    TOOL_HANDLERS["complete_task"] = run_complete_task
except ImportError as e:
    pass

try:
    from cron_scheduler.cron_scheduler import run_list_crons, run_cancel_cron, run_schedule_cron
    TOOL_HANDLERS["schedule_cron"] = run_schedule_cron
    TOOL_HANDLERS["list_crons"] = run_list_crons
    TOOL_HANDLERS["cancel_cron"] = run_cancel_cron
except ImportError as e:
    pass

try:
    from teams.teams_agent import run_spawn_teammate, run_send_message, run_check_inbox
    TOOL_HANDLERS["spawn_teammate"] = run_spawn_teammate
    TOOL_HANDLERS["send_message"] = run_send_message
    TOOL_HANDLERS["check_inbox"] = run_check_inbox
except ImportError as e:
    pass

try:
    from teams.teams_agent import run_request_shutdown, run_request_plan, run_review_plan
    TOOL_HANDLERS["request_shutdown"] = run_request_shutdown
    TOOL_HANDLERS["request_plan"] = run_request_plan
    TOOL_HANDLERS["review_plan"] = run_review_plan
except ImportError as e:
    pass

try:
    from worktree_isolation.worktree_isolation import run_create_worktree, run_remove_worktree, run_keep_worktree
    TOOL_HANDLERS["create_worktree"] = run_create_worktree
    TOOL_HANDLERS["remove_worktree"] = run_remove_worktree
    TOOL_HANDLERS["keep_worktree"] = run_keep_worktree
except ImportError as e:
    pass

try:
    from mcp_plugin.mcp_plugin import run_connect_mcp, mcp_clients, normalize_mcp_name

    TOOL_HANDLERS["connect_mcp"] = run_connect_mcp
except ImportError as e:
    pass

def assemble_tool_pool() -> tuple[list[dict], dict]:
    tools = list(TOOLS)
    handlers = dict(TOOL_HANDLERS)
    for server_name, mcp_client in mcp_clients.items():
        safe_server = normalize_mcp_name(server_name)
        for tool_def in mcp_client.tools:
            safe_tool = normalize_mcp_name(tool_def["name"])
            prefixed = f"mcp__{safe_server}__{safe_tool}"
            tools.append({
                "name": prefixed,
                "description": tool_def.get("description", ""),
                "input_schema": tool_def.get("input_schema", {}),
            })

            handlers[prefixed] = (
                lambda *, c=mcp_client, t=tool_def["name"], **kw: c.call_tool(t, kw)
            )

    return tools, handlers
