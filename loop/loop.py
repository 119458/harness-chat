from anthropic import Anthropic

from background_tasks.background_run import should_run_background, start_background_task, execute_tool, \
    collect_background_results
from context.context import reactive_compact, compact_history
from cron_scheduler.cron_scheduler import consume_cron_queue
from error.error import RecoveryState, DEFAULT_MAX_TOKENS, with_retry, is_prompt_too_long_error, ESCALATED_MAX_TOKENS, \
    CONTINUATION_PROMPT, MAX_RECOVERY_RETRIES
from hooks.hooks import trigger_hooks
from memory.memory import read_memory_index, load_memories, extract_memories, consolidate_memories
from system_prompt.system_prompt import get_system_prompt
from tool.skill_load import list_skills
from tool.tool import *

client = Anthropic(
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("BASE_URL")
)

reactive_retries = 0
MAX_REACTIVE_RETRIES = 1

def agent_loop(messages: list):
    tools, handlers = assemble_tool_pool()
    system_prompt = get_system_prompt()
    state = RecoveryState()
    max_tokens = DEFAULT_MAX_TOKENS
    global reactive_retries
    memories_content = load_memories(messages)
    memory_turn = len(messages) -1 if messages and isinstance(messages[-1].get("content"), str) else None

    while True:
        pre_compress = [
            m if isinstance(m, dict) else {"role": m.get("role", ""), "content": str(m.get("content", ""))}
            for m in messages
        ]
        messages[:] = trigger_hooks("NoAPISummaryHook", messages)
        try:
            request_messages = messages
            if memories_content and memory_turn is not None and memory_turn < len(messages):
                request_messages = messages.copy()
                request_messages[memory_turn] = {
                    **messages[memory_turn],
                    "content": memories_content + "\n\n" + messages[memory_turn]["content"]
                }
            response = with_retry(
                lambda mt=max_tokens, model=state.current_model:
                client.messages.create(
                    model=model,
                    system=system_prompt,
                    messages=request_messages,
                    tools=tools,
                    max_tokens=mt
                ),
                state=state
            )
            reactive_retries = 0
        except Exception as e:
            if is_prompt_too_long_error(e):
                if not state.has_attempted_reactive_compact:
                    messages[:] = reactive_compact(messages)
                    state.has_attempted_reactive_compact = True
                    continue
                print("\033[31m[无法恢复] 精简上下文之后，内容依旧过长\033[0m")
                messages.append({
                    "role": "assistant",
                    "content": [{"type": "text", "text": "[错误] 上下文内容超限，无法继续运行。"}]
                })
                return

            name = type(e).__name__
            print(f"  \033[31m[不可恢复错误] {name}: {str(e)[:100]}\033[0m")
            messages.append({
                "role": "assistant",
                "content": [{"type": "text", "text": f"[错误] {name}: {str(e)[:200]}"}]
            })
            return

        if response.stop_reason == "max_tokens":

            if not state.has_escalated:
                max_tokens = ESCALATED_MAX_TOKENS
                state.has_escalated = True
                print(f"\033[33m[max_tokens] 上调阈值"
                      f" {DEFAULT_MAX_TOKENS} -> {ESCALATED_MAX_TOKENS}\033[0m")
                continue
            messages.append({
                "role": "assistant",
                "content": response.content
            })

            if state.recovery_count < MAX_REACTIVE_RETRIES:
                messages.append({
                    "role": "user",
                    "content": CONTINUATION_PROMPT
                })

                state.recovery_count += 1
                print(f"\033[33m[max_tokens] 执行续聊恢复重试"
                      f" {state.recovery_count}/{MAX_RECOVERY_RETRIES}\033[0m")
                continue
            print("\033[31m[max_tokens] 已达到最大恢复重试次数\033[0m")
            return
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            extract_memories(pre_compress)
            consolidate_memories()
            force = trigger_hooks("Stop", messages)
            if force:
                messages.append({"role": "user", "content": force})
                continue
            return
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            if block.name == "compact":
                messages[:] = compact_history(messages)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "[已对历史对话进行压缩总结]"
                })
                messages.append({"role": "user", "content": results})
                break
            blocked = trigger_hooks("PreToolUse", block)
            if blocked:
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(blocked)
                })
                continue
            print(f"\033[36m> {block.name}\033[0m")
            if should_run_background(block.name, block.input):
                bg_id = start_background_task(block)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": f"""[后台任务 {bg_id} 已启动]
指令：{block.input.get('command', '')}。
任务完成后即可查看执行结果。"""
                })
            else:
                output = execute_tool(block, handlers)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output
                })

                trigger_hooks("PostToolUse", block, output)

        user_content = list(results)
        bg_notifications = collect_background_results()
        if bg_notifications:
            for notif in bg_notifications:
                user_content.append({"type": "text", "text": notif})
            print(f"  \033[32m[inject] {len(bg_notifications)} background "
                  f"notification(s)\033[0m")

        messages.append({"role": "user", "content": user_content})

