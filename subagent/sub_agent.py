import os
from anthropic import Anthropic
from humanfriendly.terminal import output

from hooks.hooks import trigger_hooks
from tool.tool import SUB_TOOLS, SUB_HANDLERS

client = Anthropic(
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("BASE_URL")
)
MODEL = os.getenv("MODEL")
SUB_SYSTEM = (
    f"You are a coding agent at {os.getenv("WORKDIR")}. "
    "Complete the task you were given, then return a concise summary. "
    "Do not delegate further."
)

def extract_text(content) -> str:
    if not isinstance(content, list):
        return str(content)
    return "\n".join(getattr(b, "text", "") for b in content if getattr(b, "type", None) == "text")

def spawn_subagent(description: str) -> str:
    print(f"\n\033[35m[子代理]\033[0m")
    messages = [{"role": "user", "content": description}]

    while True:
        response = client.messages.create(
            model=MODEL,
            system=SUB_SYSTEM,
            messages=messages,
            tools=SUB_TOOLS,
            max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            break
        results = []
        for block in response.content:
            if block.type == "tool_use":
                blocked = trigger_hooks("PreToolUse", block)
                if blocked:
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(blocked)
                    })
                    continue
                handler = SUB_HANDLERS.get(block.name)
                output = handler(**block.input) if handler else f"{block.name}工具不支持"
                trigger_hooks("PostToolUse", block, output)
                print(f"  \033[90m[sub] {block.name}: {str(output)[:100]}\033[0m")
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output
                })
        messages.append({
            "role": "user",
            "content": results
        })

    result = extract_text(messages[-1]["content"])
    if not result:
        for msg in reversed(messages):
            if msg["role"] == "assistant":
                result = extract_text(msg["content"])
                if result:
                    break

    print(f"\033[35m[子代理执行完毕]\033[0m")
    return result