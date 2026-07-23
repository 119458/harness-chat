import os
from pathlib import Path

WORKDIR = os.getenv("WORKDIR")
WORKDIR = Path(WORKDIR)

DENY_LIST = ["rm -rf", "sudo", "shutdown", "reboot", "mkfs", "dd if=", "> /dev/sda"]
DESTRUCTIVE = ["rm ", "> /etc/", "chmod 777"]

def check_deny_list(command: str) -> str | None:
    for pattern in DENY_LIST:
        if pattern in command:
            return f"{pattern}操作不被允许"
        return None

PERMISSION_RULES = [
    {
        "tools": ["write_file", "edit_file"],
        "check": lambda agrs: not (WORKDIR / agrs.get("path", "")).resolve().is_relative_to(WORKDIR),
        "message": "创建和编辑文件在工作区外"
    },
    {
        "tools": ["bash"],
        "check": lambda args: any(kw in args.get("command", "") for kw in DESTRUCTIVE),
        "message": "潜在的破坏性命令"
    }
]

def check_rules(tool_name: str, args: dict) -> str | None:
    for rule in PERMISSION_RULES:
        if tool_name in rule["tools"] and rule["check"](args):
            return rule["message"]
    return None

def ask_user(tool_name: str, args: dict, reason: str) -> str:
    print(f"\n\033[33m⚠  {reason}\033[0m")
    print(f"   Tool: {tool_name}({args})")
    choice = input("   Allow? [y/N] ").strip().lower()
    return "allow" if choice in ("y", "yes") else "deny"

def check_permission(block) -> bool:
    if block.name == "bash":
        reason = check_deny_list(block.input.get("command", ""))
        if reason:
            print(f"\n\033[31m⛔ {reason}\033[0m")
            return False
    reason = check_rules(block.name, block.input)
    if reason:
        decision = ask_user(block.name, block.input, reason)
        if decision == "deny":
            return False
    return True