import random
from dataclasses import dataclass, asdict, field
import time


@dataclass
class ProtocolState:
    request_id: str
    type: str
    sender: str
    target: str
    status: str
    payload: str
    created_at: float = field(default_factory=time.time)

pending_requests: dict[str, ProtocolState] = {}

def new_request_id() -> str:

    return f"req_{random.randint(0, 999999):06d}"

def match_response(response_type: str, request_id: str, approve: bool):

    state = pending_requests.get(request_id)

    if not state:
        print(f"\033[31m[protocol] 未知请求编号：{request_id}\033[0m")
        return

    if state.type == "shutdown" and response_type != "shutdown_response":
        print(f"\033[31m[protocol] 类型不匹配：预期接收 shutdown_response，实际收到 {response_type}\033[0m")
        return

    if state.type == "plan_approval" and response_type != "plan_approval_response":
        print(f"\033[31m[protocol] 类型不匹配：预期接收 plan_approval_response，实际收到 {response_type}\033[0m")
        return

    if state.status != "pending":
        print(f"\033[31m[protocol] 请求ID{request_id}已处于{state.status}状态，忽略重复请求\033[0m")
        return

    state.status = "approved" if approve else "rejected"
    icon =  "✓" if approve else "✗"
    color = "32" if approve else "31"
    print(f"\033[{color}m[protocol] {state.type} {icon} "
          f"({request_id}: {state.status})\033[0m")

