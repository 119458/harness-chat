import json
import os
import random
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime

WORKDIR = Path(os.getenv("WORKDIR"))
DURABLE_PATH = WORKDIR / ".scheduled_tasks.json"

@dataclass
class CronJob:
    id: str
    cron: str
    prompt: str
    recurring: bool
    durable: bool

scheduled_jobs: dict[str, CronJob] = {}
cron_queue: list[CronJob] = []
cron_lock = threading.Lock()
agent_lock = threading.Lock()
_last_fired: dict[str, str] = {}

def _cron_field_matches(field: str, value: int) -> bool:

    if field == "*":
        return True
    if field.startswith("*/"):
        step = int(field[2:])
        return step > 0 and value % step == 0
    if "," in field:
        return any(_cron_field_matches(f.strip(), value) for f in field.split(","))
    if "-" in field:
        lo, hi = field.split("-", 1)
        return int(lo) <= value <= int(hi)
    return value == int(field)

def cron_matches(cron_expr: str, dt: datetime) -> bool:

    fields = cron_expr.strip().split()
    if len(fields) != 5:
        return False

    minute, hour, dom, month, dow = fields
    dow_val = (dt.weekday() + 1) % 7

    m = _cron_field_matches(minute, dt.minute)
    h = _cron_field_matches(hour, dt.hour)
    dom_ok = _cron_field_matches(dom, dt.day)
    month_ok = _cron_field_matches(month, dt.month)
    dow_ok = _cron_field_matches(dow, dow_val)

    if not (m and h and month_ok):
        return False

    dom_unconstrained = dom == "*"
    dow_unconstrained = dow == "*"
    if dom_unconstrained and dow_unconstrained:
        return True

    if dom_unconstrained:
        return dow_ok
    if dow_unconstrained:
        return dom_ok

    return dom_ok or dow_ok

def _validate_cron_field(field: str, lo: int, hi: int) -> str | None:

    if field == "*":
        return None

    if field.startswith("*/"):
        step_str = field[2:]
        if not step_str.isdigit():
            return f"无效步骤：{field}"

        step = int(step_str)

        if step <= 0:
            return f"步骤数值必须大于 0：{field}"
        return None

    if "," in field:
        for part in field.split(","):
            err = _validate_cron_field(part.strip(), lo, hi)
            if err:
                return err
        return None

    if "-" in field:
        parts = field.split("-", 1)
        if not parts[0].isdigit() or not parts[1].isdigit():
            return f"取值范围非法：{field}"
        a, b = int(parts[0]), int(parts[1])
        if a < lo or a > hi or b < lo or b > hi:
            return f"字段{field}超出取值范围，合法区间为 [{lo}~{hi}]"
        if a > b:
            return f"区间起始值大于终止值：{field}"
        return None

    if not field.isdigit():
        return f"无效字段：{field}"

    val = int(field)
    if val < lo or val > hi:
        return f"字段{val}超出取值范围，合法区间为 [{lo}~{hi}]"

    return None

def validate_cron(cron_expr: str) -> str | None:
    fields = cron_expr.strip().split()

    if len(fields) != 5:
        return f"应传入5个字段，实际获取到{len(fields)}个"

    bounds = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]
    names = ["minute", "hour", "day-of-month", "month", "day-of-week"]

    for i, (field, (lo, ho), name) in enumerate(zip(fields, bounds, names)):
        err = _validate_cron_field(field, lo, ho)
        if err:
            return f"{name}: {err}"

    return None

def save_durable_jobs():
    try:
        durable = [asdict(j) for j in scheduled_jobs.values() if j.durable]
        DURABLE_PATH.write_text(json.dumps(durable, indent=2))
    except Exception as e:
        print("[定时任务]",e)

def load_durable_jobs():

    if not DURABLE_PATH.exists():
        return

    try:
        jobs = json.loads(DURABLE_PATH.read_text())
        for j in jobs:
            job = CronJob(**j)
            err = validate_cron(job.cron)

            if err:
                print(f"\033[31m[定时任务] 跳过无效任务{job.id}: {err}\033[0m")
                continue
            scheduled_jobs[job.id] = job

        valid = [j for j in jobs if j["id"] in scheduled_jobs]
        if valid:
            print(f"\033[35m[定时任务] 已加载{len(valid)}个持久化任务\033[0m")
    except Exception as e:
        print(e)

def schedule_job(cron: str, prompt: str, recurring: bool=True, durable: bool=True) -> CronJob | str:

    err = validate_cron(cron)
    if err:
        return err
    job = CronJob(
        id=f"cron_{random.randint(0, 999999):06d}",
        cron=cron,
        prompt=prompt,
        recurring=recurring,
        durable=durable
    )
    with cron_lock:
        scheduled_jobs[job.id] = job
    if durable:
        save_durable_jobs()

    print(f"  \033[35m[定时任务注册] 任务ID{job.id} 定时规则{cron} → 指令前40字符 {prompt[:40]}\033[0m")
    return job

def cancel_job(job_id: str) -> str:

    with cron_lock:
        job = scheduled_jobs.pop(job_id, None)

    if not job:
        return f"未查询到ID为{job_id}的任务"
    if job.durable:
        save_durable_jobs()

    print(f"\033[31m[定时任务取消] {job_id}\033[0m")
    return f"已取消任务{job_id}"

def cron_scheduler_loop():

    while True:
        time.sleep(1)
        now = datetime.now()
        minute_marker = now.strftime("%Y-%m-%d %H:%M")
        with cron_lock:
            for job in list(scheduled_jobs.values()):
                try:
                    if cron_matches(job.cron, now):
                        if _last_fired.get(job.id) != minute_marker:
                            cron_queue.append(job)
                            _last_fired[job.id] = minute_marker
                            print(f"\033[35m[定时任务触发] {job.id} → "
                                  f"{job.prompt[:40]}\033[0m")
                        if not job.recurring:
                            scheduled_jobs.pop(job.id, None)
                            if job.durable:
                                save_durable_jobs()
                except Exception as e:
                    print(f"\033[31m[定时任务错误] {job.id}: {e}\033[0m")


def consume_cron_queue() -> list[CronJob]:

    with cron_lock:
        fired = list(cron_queue)
        cron_queue.clear()

    return fired

def has_cron_queue() -> bool:
    with cron_lock:
        return bool(cron_queue)


def run_schedule_cron(cron: str, prompt: str, recurring: bool=True, durable: bool=True) -> str:

    result = schedule_job(cron, prompt, recurring, durable)

    if isinstance(result, str):
        return f"错误: {result}"
    return f"已创建定时任务 {result.id}: '{cron}' → {prompt}"

def run_list_crons() -> str:
    with cron_lock:
        jobs = list(scheduled_jobs.values())

    if not jobs:
        return "没有定时任务，使用schedule_cron添加一个。"

    lines = []
    for j in jobs:
        tag = "recurring" if j.recurring else "one-shot"
        dur = "durable" if j.durable else "session"
        lines.append(f"{j.id}: '{j.cron}' → {j.prompt[:40]}"
                     f"[{tag}, {dur}]")

    return "\n".join(lines)

def run_cancel_cron(job_id: str) -> str:
    return cancel_job(job_id)


load_durable_jobs()
threading.Thread(target=cron_scheduler_loop, daemon=True).start()
print("  \033[35m[cron] [定时任务] 调度线程已启动\033[0m")