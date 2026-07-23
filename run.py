import threading
import time
import queue
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(override=True)

from loop.loop import agent_loop
from cron_scheduler.cron_scheduler import consume_cron_queue, agent_lock, has_cron_queue

from teams.teams_agent import BUS, active_teammates, consume_lead_inbox

try:
    import readline
    # macOS 的 lib edit 在处理中文输入时有退格问题，这四行修复它
    readline.parse_and_bind('set bind-tty-special-chars off')
    readline.parse_and_bind('set input-meta on')
    readline.parse_and_bind('set output-meta on')
    readline.parse_and_bind('set convert-meta off')
except ImportError:
    pass

def latest_assistant_text(messages: list):
    """Print text blocks from the latest assistant message."""
    if not messages:
        return ""
    msg = messages[-1]
    if not isinstance(msg, dict) or msg.get("role") != "assistant":
        return ""
    content = msg.get("content", "")
    if isinstance(content, str):
        return content
    for block in content:
        if getattr(block, "type", None) == "text":
            return block.text
        elif isinstance(block, dict) and block.get("type") == "text":
            return block.get("text", "")
    return ""

def print_response(history: list):

    if not history:
        return

    response_content = history[-1].get("content", "")
    if not response_content:
        return
    if isinstance(response_content, list):
        for block in response_content:
            if getattr(block, "type", None) == "text":
                print(block.text)
            elif isinstance(block, dict) and block.get("type") == "text":
                print(block.get("text", ""))

    elif isinstance(response_content, str):
        print(response_content)

events = queue.Queue()

def input_reader():
    while True:
        try:
            line = input("\033[36muser >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            events.put(("quit", None))
            return
        events.put(("user", line))


def background_poller():
    while True:
        time.sleep(1)

        if BUS.peek("lead"):
            events.put(("wake", None))

        if has_cron_queue():
            events.put(("cron", None))



def background_cron_executor():

    while True:
        time.sleep(2)
        fired_jobs = consume_cron_queue()
        if not fired_jobs:
            continue

        for job in fired_jobs:
            cron_history = [{"role": "user", "content": job.prompt}]

            with agent_lock:
                print(f"\n\033[35m[后台任务触发] 任务ID:{job.id} | 触发指令:{job.prompt[:40]}...\033[0m")
                try:
                    agent_loop(cron_history)
                except Exception as e:
                    print(f"\033[31m[后台任务异常] 运行任务 {job.id} 时出错: {e}\033[0m")
                print(f"\033[35m[后台任务结束] 任务{job.id}执行完毕。[执行结果]:{latest_assistant_text(cron_history)}\033[0m")

            cron_history.clear()
            print("\033[36muser >> \033[0m", end="", flush=True)

if __name__ == "__main__":
    # threading.Thread(target=background_cron_executor, daemon=True).start()
    # print("  \033[35m[cron] 后台任务执行引擎已启动\033[0m")
    print("  \033[35m[System] 事件驱动引擎、终端监听、状态轮询线程已全部就绪\033[0m\n")
    print("输入问题，回车发送。输入 q 退出。\n")
    threading.Thread(target=input_reader, daemon=True).start()
    threading.Thread(target=background_poller, daemon=True).start()
    history = []
    had_teammates = False
    while True:
        kind, payload = events.get()

        if kind == "quit":
            break

        if kind == "user":
            if payload.strip().lower() in ("q", "exit", ""):
                break
            history.append({"role": "user", "content": payload})

            agent_loop(history)
            print_response(history)
            print()

        elif kind == "wake":
            inbox = consume_lead_inbox(route_protocol=True)
            if not inbox:
                continue

            inbox_prompt = "[Inbox]\n" + "\n".join(
                f"From {m['from']}: {m['content']}" for m in inbox
            )
            history.append({"role": "user", "content": inbox_prompt})
            print(f"\n\033[33m[wake: 收到来自 {len(inbox)} 个队友的工作汇报，正在唤醒 Lead]\033[0m")

            agent_loop(history)
            print_response(history)
            print()

            if active_teammates:
                had_teammates = True
            print("\033[36muser >> \033[0m", end="", flush=True)

        elif kind == "cron":
            fired_jobs = consume_cron_queue()
            for job in fired_jobs:
                cron_history = [{"role": "user", "content": job.prompt}]
                print(f"\n\033[35m[定时任务触发] 任务ID:{job.id} | 指令:{job.prompt[:40]}...\033[0m")
                try:
                    agent_loop(cron_history)
                except Exception as e:
                    print(f"\033[31m[定时任务异常] {job.id}: {e}\033[0m")

                result = latest_assistant_text(cron_history)
                print(f"\033[35m[定时任务结束] 任务{job.id}执行完毕。[执行结果]:{result}\033[0m\n")
            print("\033[36muser >> \033[0m", end="", flush=True)

        if active_teammates:
            had_teammates = True
        elif had_teammates and not BUS.peek("lead"):
            print("\033[32m[all teammates done] 所有协作线程执行完毕。\033[0m")
            had_teammates = False
            print("\033[36muser >> \033[0m", end="", flush=True)