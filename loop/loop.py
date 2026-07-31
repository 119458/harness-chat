from typing import Callable

from anthropic import Anthropic

from background_tasks.background_run import should_run_background, start_background_task, execute_tool, \
    collect_background_results
from context.context import reactive_compact, compact_history
from cron_scheduler.cron_scheduler import consume_cron_queue
from error.error import RecoveryState, DEFAULT_MAX_TOKENS, with_retry, is_prompt_too_long_error, ESCALATED_MAX_TOKENS, \
    CONTINUATION_PROMPT, MAX_RECOVERY_RETRIES, MAX_TURNS, MAX_FORCED_CONTINUES, RetryExhaustedError
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

def agent_loop(messages: list, on_event: Callable[[dict], None] = None):
    tools, handlers = assemble_tool_pool()
    system_prompt = get_system_prompt()
    state = RecoveryState()
    max_tokens = DEFAULT_MAX_TOKENS
    global reactive_retries
    memories_content = load_memories(messages)
    memory_turn = len(messages) -1 if messages and isinstance(messages[-1].get("content"), str) else None

    def _emit(event: dict) -> None:
        """Forward a streaming event to the optional hook (no-op when absent).

        Additive streaming surface (constitution v1.1.0 Principle II named
        exception). The bridge's callback may raise ``StopRequested`` (a
        ``BaseException``) to cooperatively stop the turn at a safe boundary
        (between deltas / between tool dispatches, never mid-``execute_tool``).
        """
        if on_event is not None:
            on_event(event)

    def _preview(value) -> str:
        """Truncate a tool result to a 2k-char preview for SSE (contracts)."""
        s = value if isinstance(value, str) else str(value)
        return s[:2000]

    while True:
        # 002-loop-robustness US1/FR-002 (R2, data-model E5 step 1): bounded
        # termination. Increment per model-call iteration; stop at MAX_TURNS so a
        # runaway tool chain / rogue hook can never loop forever.
        state.turn_count += 1
        if state.turn_count >= MAX_TURNS:
            print(f"\033[31m[turn_limit] 已达轮次上限 {MAX_TURNS}，任务停止\033[0m")
            _emit({"type": "error",
                   "message": "已达轮次上限，任务停止。",
                   "reason": "turn_limit_reached"})
            return
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
            # Streaming swap (constitution v1.1.0 Principle II named exception):
            # ``client.messages.create`` -> ``client.messages.stream`` so
            # ``on_event`` can emit incremental thinking/text deltas (R1, R7).
            # ``with_retry`` wraps stream *entry* (the ``__enter__`` HTTP
            # request) so 429/529 + 529-fallback still apply at the same flow
            # point; mid-stream failures are NOT retried (a partial stream
            # cannot be resumed) and propagate to the existing ``except`` (R1).
            def _open_stream(mt=max_tokens, model=state.current_model):
                cm = client.messages.stream(
                    model=model,
                    system=system_prompt,
                    messages=request_messages,
                    tools=tools,
                    max_tokens=mt,
                )
                return cm.__enter__()  # performs the HTTP request -> 429/529 surface here
            stream = with_retry(_open_stream, state=state)
            # 002-loop-robustness US4/FR-001 (R1): whether this turn needs a
            # follow-up is decided by whether a tool_use block appears in the
            # stream (content_block_start), NOT by the lagging stop_reason.
            needs_follow_up = False
            try:
                for event in stream:
                    etype = getattr(event, "type", None)
                    # Forward each content delta immediately, no buffering (R7).
                    if etype == "content_block_delta":
                        delta = getattr(event, "delta", None)
                        dt = getattr(delta, "type", None)
                        if dt == "thinking_delta":
                            _emit({"type": "thinking_delta", "content": getattr(delta, "thinking", "")})
                        elif dt == "text_delta":
                            _emit({"type": "text_delta", "content": getattr(delta, "text", "")})
                    elif etype == "content_block_start":
                        # R1: a tool_use block in the stream => follow-up needed.
                        cb = getattr(event, "content_block", None)
                        if getattr(cb, "type", None) == "tool_use":
                            needs_follow_up = True
                # Full Message post-drain; max_tokens still uses stop_reason
                # (R1); the continue/stop decision now uses needs_follow_up.
                response = stream.get_final_message()
            finally:
                stream.__exit__(None, None, None)
            reactive_retries = 0
        except RetryExhaustedError as e:
            # 002-loop-robustness US2/FR-005 (R6, data-model E4/E5 step 3):
            # 429/529 retries exhausted -> clean terminal exit, not a crash that
            # leaves the bridge to fire its generic fallback. MUST precede the
            # broad ``except Exception`` (RetryExhaustedError is an Exception).
            print(f"\033[31m[retry_exhausted] {e}\033[0m")
            _emit({"type": "error",
                   "message": "请求重试耗尽，任务终止。",
                   "reason": "retry_exhausted"})
            return
        except Exception as e:
            if is_prompt_too_long_error(e):
                if not state.has_attempted_reactive_compact:
                    messages[:] = reactive_compact(messages)
                    state.has_attempted_reactive_compact = True
                    continue
                # 002-loop-robustness US3 (R4/clarify Q4, data-model E5 step 5):
                # emit a terminal event (not a silent return) so the bridge
                # doesn't fire its fallback. reason=null: unclassified
                # (stream_error intentionally not细分, analyze C1).
                print("\033[31m[无法恢复] 精简上下文之后，内容依旧过长\033[0m")
                _emit({"type": "error",
                       "message": "上下文内容超限，无法继续运行。",
                       "reason": None})
                return

            # 002-loop-robustness US3 (data-model E5 step 5): same emit-error
            # pattern; mid-stream disconnects also land here (R4/clarify Q4).
            name = type(e).__name__
            print(f"  \033[31m[不可恢复错误] {name}: {str(e)[:100]}\033[0m")
            _emit({"type": "error",
                   "message": f"{name}: {str(e)[:200]}",
                   "reason": None})
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
            # 002-loop-robustness US1 (R7, data-model E5 step 6): recovery
            # exhausted -> normal_completion (assistant content already appended
            # above). emit done instead of a silent return (fixes silent-stop,
            # SC-003).
            print("\033[31m[max_tokens] 已达到最大恢复重试次数\033[0m")
            _emit({"type": "done"})
            return
        messages.append({"role": "assistant", "content": response.content})

        # 002-loop-robustness US4/FR-001 (R1, data-model E5 step 7/8): continue
        # iff a tool_use block appeared in the stream (needs_follow_up), NOT iff
        # stop_reason == "tool_use" (which can lag the stream content, US4).
        if not needs_follow_up:
            extract_memories(pre_compress)
            consolidate_memories()
            force = trigger_hooks("Stop", messages)
            if force:
                # 002-loop-robustness US1/FR-003 (R8, data-model E5 step 7):
                # bounded Stop-hook forced-continue. MAX_FORCED_CONTINUES=3
                # consecutive forced continues are allowed; the next is rejected
                # so a rogue "always continue" hook can't loop forever. Counter
                # is per-task cumulative (NOT reset on tool_use turns, R8).
                state.forced_continue_count += 1
                if state.forced_continue_count > MAX_FORCED_CONTINUES:
                    print(f"\033[31m[stop_hook_protection] Stop 钩子强制续跑已达上限"
                          f" {MAX_FORCED_CONTINUES}，任务停止\033[0m")
                    _emit({"type": "error",
                           "message": "Stop 钩子强制续跑保护触发，任务停止。",
                           "reason": "stop_hook_protection_triggered"})
                    return
                messages.append({"role": "user", "content": force})
                continue
            _emit({"type": "done"})
            return
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            tool_input = block.input if isinstance(block.input, dict) else {}
            _emit({"type": "tool_call_start", "tool": block.name, "input": tool_input})
            if block.name == "compact":
                messages[:] = compact_history(messages)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "[已对历史对话进行压缩总结]"
                })
                _emit({"type": "tool_call_result", "tool": block.name,
                       "result": "[已对历史对话进行压缩总结]"})
                messages.append({"role": "user", "content": results})
                break
            blocked = trigger_hooks("PreToolUse", block)
            if blocked:
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(blocked)
                })
                _emit({"type": "tool_call_result", "tool": block.name,
                       "result": _preview(blocked)})
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
                _emit({"type": "tool_call_result", "tool": block.name,
                       "result": f"[background task {bg_id} started]"})
            else:
                output = execute_tool(block, handlers)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output
                })
                _emit({"type": "tool_call_result", "tool": block.name,
                       "result": _preview(output)})

                trigger_hooks("PostToolUse", block, output)

        user_content = list(results)
        bg_notifications = collect_background_results()
        if bg_notifications:
            for notif in bg_notifications:
                user_content.append({"type": "text", "text": notif})
            print(f"  \033[32m[inject] {len(bg_notifications)} background "
                  f"notification(s)\033[0m")

        messages.append({"role": "user", "content": user_content})

