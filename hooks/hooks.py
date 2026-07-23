import os
from pathlib import Path
from datetime import datetime

WORKDIR = os.getenv("WORKDIR")
WORKDIR = Path(WORKDIR)

from permission.permission import DENY_LIST, DESTRUCTIVE

HOOKS = {
    "UserPromptSubmit": [],
    "PreToolUse": [],
    "PostToolUse": [],
    "Stop": [],
    "NoAPISummaryHook": []
}

def register_hooks(event: str, callback):
    HOOKS[event].append(callback)

def trigger_hooks(event: str, *args):
    for callback in HOOKS[event]:
        result = callback(*args)
        if result is not None:
            return result

    return None

def permission_hook(block):
    if block.name == "bash":
        for pattern in DENY_LIST:
            if pattern in block.input.get("command", ""):
                print(f"\n\033[31m⛔ Blocked: '{pattern}'\033[0m")
                return "该cli命令被拒绝使用"
        for kw in DESTRUCTIVE:
            if kw in block.input.get("command", ""):
                print(f"\n\033[33m⚠  潜在的破坏性命令\033[0m")
                print(f"   Tool: {block.name}({block.input})")
                choice = input("   Allow? [y/N] ").strip().lower()
                if choice not in ["y", "yes"]:
                    return "用户拒绝许可"
    if block.name in ("write_file", "edit_file"):
        path = block.input.get("path", "")
        if not (WORKDIR / path).resolve().is_relative_to(WORKDIR):
            print(f"\n\033[33m⚠  创建和编辑文件在工作区外\033[0m")
            print(f"   Tool: {block.name}({block.input})")
            choice = input("   Allow? [y/N] ").strip().lower()
            if choice not in ["y", "yes"]:
                return "用户拒绝许可"

    return None

def log_hook(block):
    path = str(WORKDIR / "hook.log")
    args_preview = str(list(block.input.values())[:2])[:60]
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"[HOOK] {block.name}({args_preview}) -- {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}。\n")
    print(f"\033[90m[HOOK] {block.name}({args_preview})\033[0m")
    return None

def large_output_hook(block, output):
    if len(str(output)) > 100000:
        print(f"\033[33m[HOOK] ⚠ {block.name}: {len(str(output))}输出大于10万字符\033[0m")
    return None

def context_inject_hook(query: str):
    return None

def summary_hook(messages: list):
    tool_count = sum(1 for m in messages
                     for b in (m.get("content") if isinstance(m.get("content"), list) else [])
                     if isinstance(b, dict) and b.get("type") == "tool_result")
    print(f"\033[90m[HOOK] Stop: 当前会话使用{tool_count}次工具调用\033[0m")
    return None

def no_api_summary_hook(messages: list):
    from context.context import tool_result_budget, snip_compact, micro_compact, estimate_size, CONTEXT_LIMIT, \
        compact_history
    messages = tool_result_budget(messages)
    messages = snip_compact(messages)
    messages = micro_compact(messages)
    if estimate_size(messages) > CONTEXT_LIMIT:
        print("[自动压缩]")
        messages = compact_history(messages)
    return messages

register_hooks("UserPromptSubmit", context_inject_hook)
register_hooks("PreToolUse", permission_hook)
register_hooks("PreToolUse", log_hook)
register_hooks("PostToolUse", large_output_hook)
register_hooks("Stop", summary_hook)
register_hooks("NoAPISummaryHook", no_api_summary_hook)