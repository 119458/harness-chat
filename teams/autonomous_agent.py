import json
import time

from task.tasks import TASKS_DIR, can_start, claim_task
from teams.teams_agent import BUS

IDLE_POLL_INTERVAL = 5
IDLE_TIMEOUT = 60

def scan_unclaimed_tasks() -> list[dict]:

    unclaimed = []
    for f in sorted(TASKS_DIR.glob("task_*.json")):
        task = json.loads(f.read_text())

        if (
            task.get("status") == "pending"
            and not task.get("owner")
            and can_start(task["id"])
        ):
            unclaimed.append(task)

    return unclaimed

def idle_poll(name: str, messages: list, role: str) -> str:

    for _ in range(IDLE_TIMEOUT // IDLE_POLL_INTERVAL):
        time.sleep(IDLE_POLL_INTERVAL)

        if BUS.peek(name):
            print(f"\033[36m[idle] {name}检测到收件箱存在待处理消息，准备唤醒\033[0m")
            return "work"

        unclaimed = scan_unclaimed_tasks()
        if unclaimed:
            task = unclaimed[0]
            result = claim_task(task["id"], name)

            if "Claimed" in result:
                messages.append({
                    "role": "user",
                    "content": f"<auto-claimed>Task {task['id']}: "
                               f"{task['subject']}</auto-claimed>"
                })

                print(f"\033[36m[idle] {name}自动认领任务：{task ['subject']}\033[0m")
                return "work"

            print(f"\033[36m[idle] {name}任务认领失败：{result}\033[0m")

    print(f"\033[31m[idle] {name}空闲超时（超时时长：{IDLE_TIMEOUT}秒\033[0m")
    return "timeout"