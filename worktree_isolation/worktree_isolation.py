import json
import os
import re
import subprocess
import time
from pathlib import Path

from task.tasks import save_task, load_task

WORKDIR = Path(os.getenv("WORKDIR"))
WORKTREES_DIR = WORKDIR / ".worktrees"
WORKTREES_DIR.mkdir(exist_ok=True)

VALID_WT_NAME = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

def validate_worktree_name(name: str) -> str | None:

    if not name:
        return "Worktree名称不能为空"
    if name == "." or name == "..":
        return f"{name} 不是合法的Worktree名称"

    if not VALID_WT_NAME.match(name):
        return f"无效Worktree名称{name}：仅允许字母、数字、点、下划线、短横线，长度限制 1~64 字符"

    return None

def run_git(args: list[str]) -> tuple[bool, str]:

    try:
        r = subprocess.run(
            ["git"] + args,
            cwd=WORKDIR,
            capture_output=True,
            text=True,
            timeout=30
        )

        out = (r.stdout + r.stderr).strip()
        out = out[:5000] if out else "没有输出"
        return r.returncode == 0, out
    except subprocess.TimeoutExpired:
        return False, "Error: git timeout"

def log_event(event_type: str, worktree_name: str, task_id: str=""):

    event = {
        "type": event_type,
        "worktree": worktree_name,
        "task_id": task_id,
        "ts": time.time()
    }

    events_file = WORKTREES_DIR / "events.jsonl"

    with open(events_file, "a") as f:
        f.write(json.dumps(event) + "\n")

def create_worktree(name: str, task_id: str="") -> str:

    err = validate_worktree_name(name)
    if err:
        return f"Error: {err}"

    path = WORKTREES_DIR / name
    if path.exists():
        return f"Worktree'{name}'已存在，路径：{path}"

    ok, result = run_git(["worktree", "add", str(path), "-b", f"wt/{name}", "HEAD"])

    if not ok:
        return f"Git error: {result}"
    if task_id:
        bind_task_to_worktree(task_id, name)

    log_event("create", name, task_id)

    print(f"\033[33m[worktree] 已创建工作树{name}，存放路径：{path}\033[0m")
    return f"工作树{name}已创建，路径：{path}"

def bind_task_to_worktree(task_id: str, worktree_name: str):

    task = load_task(task_id)
    task.worktree = worktree_name
    save_task(task)
    print(f"\033[33m[bind] {task.subject} → worktree:{worktree_name}\033[0m")

def _count_worktree_changes(path: Path) -> tuple[int, int]:

    try:
        r1 = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=10
        )
        files = len([l for l in r1.stdout.strip().splitlines() if l.strip()])
        r2 = subprocess.run(
            ["git", "log", "@{push}..HEAD", "--oneline"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=10
        )
        commits = len([l for l in r2.stdout.strip().splitlines() if l.strip()])
        return files, commits
    except Exception:
        return -1, -1

def remove_worktree(name: str, discard_changes: bool=False) -> str:
    err = validate_worktree_name(name)
    if err:
        return err

    path = WORKTREES_DIR / name
    if not path.exists():
        return f"Worktree '{name}' not found"
    if not discard_changes:
        files, commits = _count_worktree_changes(path)
        if files < 0:
            return f"无法校验工作树「{name}」状态，设置discard_changes=true可强制删除。"
        if files > 0 or commits > 0:
            return f"工作树「{name}」存在{files}个未提交文件、{commits}条未推送提交。设置discard_changes=true可强制删除，或启用keep_worktree保留以供复核。"

    ok1, _ = run_git(["worktree", "remove", str(path), "--force"])
    if not ok1:
        return f"删除「{name}」对应的工作树目录失败"
    run_git(["branch", "-D", f"wt/{name}"])
    log_event("remove", name)
    print(f"\033[33m[worktree] removed: {name}\033[0m")
    return f"Worktree '{name}' removed"

def keep_worktree(name: str) -> str:
    err = validate_worktree_name(name)
    if err:
        return err
    log_event("keep", name)
    print(f"  \033[36m[worktree] kept: {name}\033[0m")
    return f"Worktree '{name}' kept for review (branch: wt/{name})"

def run_create_worktree(name: str, task_id: str="") -> str:
    return create_worktree(name, task_id)

def run_remove_worktree(name: str, discard_changes: bool=False) -> str:
    return remove_worktree(name, discard_changes)

def run_keep_worktree(name: str) -> str:
    return keep_worktree(name)

