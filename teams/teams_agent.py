import json
import os
import threading
import time
from pathlib import Path

from anthropic import Anthropic

from task.tasks import list_tasks, claim_task, complete_task
from teams.team_protocols import match_response, new_request_id, pending_requests, ProtocolState
from tool.tool import run_bash, run_read, run_write, run_edit, run_glob

WORKDIR = Path(os.getenv("WORKDIR"))
MAILBOX_DIR = WORKDIR / ".mailbox"
MAILBOX_DIR.mkdir(exist_ok=True)

mailbox_lock = threading.Lock()

client = Anthropic(
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("BASE_URL")
)
MODEL = os.environ["MODEL"]

class MessageBus:

    def send(self, from_agent: str, to_agent: str, content: str, msg_type: str="message", metadata: dict=None):

        msg = {
            "from": from_agent,
            "to": to_agent,
            "content": content,
            "type": msg_type,
            "ts": time.time(),
            "metadata": metadata or {}
        }

        inbox = MAILBOX_DIR / f"{to_agent}.jsonl"

        with mailbox_lock:
            with open(inbox, "a") as f:
                f.write(json.dumps(msg) + "\n")

        print(f"\033[33m[bus] {from_agent} → {to_agent}: "
              f"{content[:50]}\033[0m")

    def read_inbox(self, agent: str) -> list[dict]:

        inbox = MAILBOX_DIR / f"{agent}.jsonl"
        with mailbox_lock:
            if not inbox.exists():
                return []
            try:
                content = inbox.read_text()
                inbox.unlink()
                return [json.loads(line) for line in content.splitlines() if line.strip()]
            except Exception as e:
                print(f"\033[31m[bus] 读取 {agent} 的信箱失败: {e}\033[0m")
                return []

    def peek(self, agent: str) -> bool:

        inbox = MAILBOX_DIR / f"{agent}.jsonl"
        with mailbox_lock:
            try:
                return inbox.exists() and inbox.stat().st_size > 0
            except FileNotFoundError:
                return False


BUS = MessageBus()
active_teammates: dict[str, bool] = {}

def consume_lead_inbox(route_protocol: bool=True) -> list[dict]:
    msgs = BUS.read_inbox("lead")
    if not msgs:
        return []
    if route_protocol:
        for msg in msgs:
            meta = msg.get("metadata", {})
            req_id = meta.get("request_id", "")
            msg_type = msg.get("type", "")
            if req_id and msg_type.endswith("_response"):
                approve = meta.get("approve", False)
                match_response(msg_type, req_id, approve)

    return msgs

def spawn_teammate_thread(name: str, role: str, prompt: str) -> str:

    if name in active_teammates:
        return f"成员{name}已存在"

    system = (
        f"You are '{name}', a {role}. "
        f"Use tools to complete tasks. "
        f"You can list and claim tasks from the board. "
        f"Check inbox for protocol messages."
    )

    def handle_inbox_message(name: str, msg: dict, messages: list) -> bool:

        msg_type = msg.get("type", "message")
        meta = msg.get("metadata", {})
        req_id = meta.get("request_id", "")

        if msg_type == "shutdown_request":
            BUS.send(
                name,
                "lead",
                "Shutting down gracefully.",
                "shutdown_response",
                {"request_id": req_id, "approve": True}
            )
            print(f"  \033[35m[protocol] {name}已确认同意关闭（请求编号：{req_id}）\033[0m")
            return True

        if msg_type == "plan_approval_response":
            approve = meta.get("approve", False)
            if approve:
                messages.append({
                    "role": "user",
                    "content": "[Plan approved] 开始执行任务"
                })
            else:
                messages.append({
                    "role": "user",
                    "content": f"[Plan rejected] 驳回意见: {msg['content']}"
                })
        return False

    def run():
        messages = [{"role": "user", "content": prompt}]

        sub_tools = [
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
            },
            {
                "name": "send_message",
                "description": "向另一个agent发送消息",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["to", "content"]
                }
            },
            {
                "name": "submit_plan",
                "description": "提交方案交由负责人审核批准",
                "input_schema": {
                    "type": "object",
                    "properties": {"plan": {"type": "string"}},
                    "required": ["plan"]
                }
            },
            {
                "name": "list_tasks",
                "description": "列出任务面板上所有任务",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "claim_task",
                "description": "认领一条待处理任务",
                "input_schema": {
                    "type": "object",
                    "properties": {"task_id": {"type": "string"}},
                    "required": ["task_id"]
                }
            },
            {
                "name": "complete_task",
                "description": "将进行中的任务标记为已完成",
                "input_schema": {
                    "type": "object",
                    "properties": {"task_id": {"type": "string"}},
                    "required": ["task_id"]
                }
            }
        ]

        def _run_list_tasks():
            tasks = list_tasks()
            if not tasks:
                return "没有任务"
            return "\n".join(
                f"{t.id}: {t.subject} [{t.status}]"
                for t in tasks
            )

        def _run_claim_task(task_id: str):
            return claim_task(task_id, owner=name)

        def _run_complete_task(task_id: str):
            return complete_task(task_id)

        sub_handlers = {
            "bash": run_bash, "read_file": run_read, "write_file": run_write,
            "edit_file": run_edit, "glob": run_glob, "send_message": lambda to, content: (BUS.send(name, to, content), "Sent")[1],
            "submit_plan": lambda plan: _teammate_submit_plan(name, plan),
            "list_tasks": _run_list_tasks, "claim_task": _run_claim_task, "complete_task": _run_complete_task
        }

        while True:
            if len(messages) <= 3:
                messages.insert(0, {
                    "role": "user",
                    "content": f"<identity>You are '{name}', role: {role}. "
                               f"Continue your work.</identity>"
                })
            should_shutdown = False
            while True:
                inbox = BUS.read_inbox(name)
                for msg in inbox:
                    stopped = handle_inbox_message(name, msg, messages)
                    if stopped:
                        should_shutdown = True
                        break
                if should_shutdown:
                    break
                if inbox and not should_shutdown:
                    non_protocol = [m for m in inbox if m.get("type") == "message"]
                    if non_protocol:
                        inbox_text = f"<inbox>{json.dumps(non_protocol, ensure_ascii=False)}</inbox>"
                        if messages and messages[-1]["role"] == "user":
                            last_msg = messages[-1]
                            if isinstance(last_msg["content"], str):
                                last_msg["content"] = [
                                    {"type": "text", "text": last_msg["content"]},
                                    {"type": "text", "text": inbox_text}
                                ]
                            elif isinstance(last_msg["content"], list):
                                last_msg["content"].append({
                                    "type": "text",
                                    "text": inbox_text
                                })
                        else:
                            messages.append({
                                "role": "user",
                                "content": inbox_text
                            })

                try:
                    response = client.messages.create(
                        model=MODEL,
                        system=system,
                        messages=messages,
                        tools=sub_tools,
                        max_tokens=8000
                    )
                except Exception as e:
                    print(f"\033[31m[teammate {name} API 异常] {e}\033[0m")
                    break
                messages.append({"role": "assistant", "content": response.content})

                if response.stop_reason != "tool_use":
                    break

                results = []
                for block in response.content:
                    if block.type == "tool_use":
                        handler = sub_handlers.get(block.name)
                        try:
                            output = handler(**block.input) if handler else "Unknown"
                        except Exception as err:
                            output = f"工具 {block.name} 执行失败: {err}"

                        results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(output)
                        })

                if results:
                    messages.append({
                        "role": "user",
                        "content": results
                    })
            if should_shutdown:
                break

            from teams.autonomous_agent import idle_poll

            idle_result = idle_poll(name, messages, role)

            if idle_result == "shutdown":
                break
            if idle_result == "timeout":
                break
            if idle_result == "work":
                continue

        def get_latest_summary(msgs) -> str:
            for msg in reversed(msgs):
                if msg["role"] == "assistant" and isinstance(msg["content"], list):
                    for b in msg["content"]:
                        if getattr(b, "type", None) == "text":
                            return b.text
            return "已完成"

        summary = get_latest_summary(messages)
        BUS.send(name, "lead", summary, "result")
        active_teammates.pop(name, None)
        print(f"\033[32m[teammate] {name}已完成任务\033[0m")

    active_teammates[name] = True
    threading.Thread(target=run, daemon=True).start()
    print(f"\033[36m[teammate] {name}已创建，角色为{role}\033[0m")
    return f"已创建成员{name}，角色：{role}"

def _teammate_submit_plan(from_name: str, plan: str) -> str:

    req_id = new_request_id()
    pending_requests[req_id] = ProtocolState(
        request_id=req_id,
        type="plan_approval",
        sender=from_name,
        target="lead",
        status="pending",
        payload=plan
    )
    BUS.send(
        from_name,
        "lead",
        plan,
        "plan_approval_request",
        {"request_id": req_id}
    )

    return f"案已提交（请求 ID：{req_id}），等待负责人审批……"

def run_spawn_teammate(name: str, role: str, prompt: str) -> str:

    return spawn_teammate_thread(name=name, role=role, prompt=prompt)

def run_send_message(to: str, content: str) -> str:
    BUS.send("lead", to, content)
    return f"Sent to {to}"

def run_check_inbox() -> str:
    msgs = consume_lead_inbox(route_protocol=True)
    if not msgs:
        return "(inbox empty)"

    lines = []
    for m in msgs:
        meta = m.get("metadata", {})
        req_id = meta.get("request_id", "")
        tag = f" [{m['type']} req:{req_id}]" if req_id else f" [{m['type']}]"
        lines.append(f" [{m['from']}]{tag} {m['content'][:200]}")

    return "\n".join(lines)

def run_request_shutdown(teammate: str) -> str:
    req_id = new_request_id()
    pending_requests[req_id] = ProtocolState(
        request_id=req_id,
        type="shutdown",
        sender="lead",
        target=teammate,
        status="pending",
        payload=""
    )
    BUS.send(
        "lead",
        teammate,
        "Please shut down gracefully.",
        msg_type="shutdown_request",
        metadata={"request_id": req_id}
    )
    print(f"  \033[35m[protocol] 向协作成员{teammate}下发关闭请求（请求编号：{req_id}）\033[0m")
    return f"已向协作成员{teammate}发送关闭请求（请求标识：{req_id}）"

def run_request_plan(teammate: str, task: str) -> str:
    BUS.send(
        "lead",
        teammate,
        f"请针对该项任务提交执行方案：{task}",
        "message"
    )
    return f"已通知协作成员 {teammate} 提交执行方案"

def run_review_plan(request_id: str, approve: bool, feedback: str="") -> str:
    state = pending_requests.get(request_id)
    if not state:
        return f"未查询到编号为{request_id}的请求"
    if state.status != "pending":
        return f"请求{request_id}当前状态已为{state.status}"
    state.status = "approved" if approve else "rejected"

    BUS.send(
        "lead",
        state.sender,
        feedback or ("Approved" if approve else "Rejected"),
        "plan_approval_response",
        {"request_id": request_id, "approve": approve}
    )

    icon = "✓" if approve else "✗"
    print(f"  \033[32m[protocol] plan {icon} ({request_id})\033[0m")
    return f"Plan {'approved' if approve else 'rejected'} ({request_id})"




