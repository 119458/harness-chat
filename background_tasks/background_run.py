import threading

from tool.tool import TOOL_HANDLERS

_bg_counter = 0
background_tasks: dict[str, dict] = {}
background_results: dict[str, str] = {}
background_lock = threading.Lock()

def is_slow_operation(tool_name: str, tool_input: dict) -> bool:

    if tool_name != "bash":
        return False

    cmd = tool_input.get("command", "").lower()
    slow_keywords = ["install", "build", "test", "deploy", "compile",
                     "docker build", "pip install", "npm install",
                     "cargo build", "pytest", "make"]

    return any(kw in cmd for kw in slow_keywords)

def should_run_background(tool_name: str, tool_input: dict) -> bool:

    if tool_input.get("run_in_background"):
        return True
    return is_slow_operation(tool_name, tool_input)

def execute_tool(block, tool_handler: dict) -> str:

    handle = tool_handler.get(block.name)
    if not handle:
        return f"{block.name}工具不支持"
    try:
        return handle(**block.input)
    except Exception as e:
        return f"工具执行错误: {e}"



def start_background_task(block, handlers: dict) -> str:

    global _bg_counter
    _bg_counter += 1
    bg_id = f"bg_{_bg_counter:04d}"
    cmd = block.input.get("command", block.name)

    def worker():
        result = execute_tool(block, handlers)
        with background_lock:
            background_tasks[bg_id]["status"] = "completed"
            background_results[bg_id] = result


    with background_lock:
        background_tasks[bg_id] = {
            "tool_use_id": block.id,
            "command": cmd,
            "status": "running"
        }

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    print(f"  \033[33m[background] dispatched {bg_id}: {cmd[:40]}\033[0m")
    return bg_id

def collect_background_results() -> list[str]:

    with background_lock:
        ready_ids = [
            bid for bid, task in background_tasks.items()
            if task["status"] == "completed"
        ]

    notifications = []
    for bg_id in ready_ids:
        with background_lock:
            task = background_tasks.pop(bg_id)
            output = background_results.pop(bg_id, "")

        summary = output[:200] if len(output) > 200 else output
        notifications.append(
            f"<task_notification>\n"
            f"  <task_id>{bg_id}</task_id>\n"
            f"  <status>completed</status>\n"
            f"  <command>{task['command']}</command>\n"
            f"  <summary>{summary}</summary>\n"
            f"</task_notification>"
        )
        print(f"\033[32m[background done] {bg_id}: "
              f"{task['command'][:40]} ({len(output)} chars)\033[0m")

    return notifications