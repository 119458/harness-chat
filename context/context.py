import json
import os
from pathlib import Path
import time

from anthropic import Anthropic

WORKDIR = Path(os.getenv("WORKDIR"))
CONTEXT_LIMIT = 62000
KEEP_RECENT = 4
PERSIST_THRESHOLD = 10000
TOOL_RESULTS_DIR = WORKDIR / ".task_outputs" / "tool-results"
TRANSCRIPT_DIR = WORKDIR / ".transcripts"

client = Anthropic(
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("BASE_URL")
)
MODEL = os.getenv("MODEL")

def estimate_size(msgs):
    return len(str(msgs))

def _block_type(block):
    return block.get("type") if isinstance(block, dict) else getattr(block, "type", None)

def _message_has_tool_use(msg):
    if msg.get("role") != "assistant":
        return False

    content = msg.get("content")
    if not isinstance(content, list):
        return False
    return any(_block_type(block) == "tool_use" for block in content)

def _is_tool_result_message(msg):
    if msg.get("role") == "user":
        return False

    content = msg.get("content")
    if not isinstance(content, list):
        return False
    return any(isinstance(block, dict) and block.get("type") == "tool_result" for block in content)

# L1 - trim middle messages
def snip_compact(messages, max_messages=100):
    if len(messages) <= max_messages:
        return messages
    keep_head, keep_tail = 3, max_messages - 3
    head_end, tail_start = keep_head, len(messages) - keep_tail
    if head_end > 0 and _message_has_tool_use(messages[head_end - 1]):
        while head_end < len(messages) and _is_tool_result_message(messages[head_end]):
            head_end += 1

    if 0 < tail_start < len(messages) and _is_tool_result_message(messages[tail_start]) and _message_has_tool_use(messages[tail_start - 1]):
        tail_start -= 1
    if head_end >= tail_start:
        return messages
    sniped = tail_start - head_end
    return messages[:head_end] + [{"role": "user", "content": f"[裁剪{sniped}条消息]"}] + messages[tail_start:]

# L2 - old result placeholders
def collect_tool_results(messages):
    blocks = []
    for mi, msg in enumerate(messages):
        if msg.get("role") != "user" or not isinstance(msg.get("content"), list):
            continue
        for bi, block in enumerate(msg["content"]):
            if isinstance(block, dict) and block.get("type") == "tool_result":
                blocks.append((mi, bi, block))
    return blocks

def micro_compact(messages):
    tool_results = collect_tool_results(messages)
    if len(tool_results) <= KEEP_RECENT:
        return messages
    for index, _, block in tool_results[:-KEEP_RECENT]:
        if index == len(messages) -1:
            continue
        if len(block.get("content", "")) > 300:
            block["content"] = "早期工具结果已经压缩，如果需要重新运行。"
    return messages

# L3 - persist large results to disk
def persist_large_output(tool_use_id, output):
    if len(output) <= PERSIST_THRESHOLD:
        return output
    TOOL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = TOOL_RESULTS_DIR / f"{tool_use_id}.txt"
    if not path.exists():
        path.write_text(output)
    return f"<persisted-output>\nFull output: {path}\nPreview:\n{output[:2000]}\n</persisted-output>"

def tool_result_budget(messages, max_bytes=20_000):
    last = messages[-1] if messages else None
    if not last or last.get("role") != "user" or not isinstance(last.get("content"), list):
        return messages

    blocks = [(i, b) for i, b in enumerate(last["content"]) if isinstance(b, dict) and b.get("type") == "tool_result"]
    total = sum(len(str(b.get("content", ""))) for _, b in blocks)
    if total <= max_bytes:
        return messages
    ranked = sorted(blocks, key=lambda p: len(str(p[1].get("content", ""))), reverse=True)
    for _, block in ranked:
        if total <= max_bytes:
            break
        content = str(block.get("content", ""))
        if len(content) <= PERSIST_THRESHOLD:
            continue
        tid = block.get("tool_use_id", "unknown")
        block["content"] = persist_large_output(tid, content)
        total = sum(len(str(b.get("content", ""))) for _, b in blocks)
    return messages

# L4 - LLM full summary
def write_transcript(messages):
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    path = TRANSCRIPT_DIR / f"transcript_{int(time.time())}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for msg in messages:
            f.write(json.dumps(msg, default=str) + "\n")
    return path

def summarize_history(messages):
    conversation = json.dumps(messages, default=str)
    system_prompt = f"""
对本次编码智能体对话内容做摘要整理，便于后续接续推进开发工作。
必须完整保留以下 5 项核心信息：
1. 当前整体开发目标
2. 已得出的关键结论与敲定的方案决策
3. 已读取、修改过的所有文件清单
4. 待完成的剩余任务项
5. 用户提出的全部硬性约束与要求

输出内容简洁凝练、信息具体无冗余。
"""
    response = client.messages.create(
        model=MODEL,
        system=system_prompt,
        messages=[{"role": "user", "content": conversation}],
        max_tokens=2000
    )
    return "\n".join(
        getattr(block, "text", "")
        for block in response.content
        if getattr(block, "type", None) == "text"
    ).strip() or "(空摘要)"

def compact_history(messages):
    transcript_path = write_transcript(messages)
    print(f"[transcript saved: {transcript_path}]")
    summary = summarize_history(messages)
    return [{"role": "user", "content": f"[历史消息压缩结果]\n\n{summary}"}]

# API error
def reactive_compact(messages):
    _ = write_transcript(messages)
    tail_start = max(0, len(messages) - 5)
    if 0 < tail_start < len(messages) and _is_tool_result_message(messages[tail_start]) and _message_has_tool_use(messages[tail_start - 1]):
        tail_start -= 1
    summary = summarize_history(messages[:tail_start])
    return [{"role": "user", "content": f"[Reactive compact]\n\n{summary}"}, *messages[tail_start:]]