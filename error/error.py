import os
import random
import time

PRIMARY_MODEL = os.environ["MODEL"]
FALLBACK_MODEL = os.getenv("MODEL")
ESCALATED_MAX_TOKENS = 64000
DEFAULT_MAX_TOKENS = 8000
MAX_RECOVERY_RETRIES = 3
MAX_RETRIES = 10
BASE_DELAY_MS = 500
MAX_CONSECUTIVE_529 = 3
CONTINUATION_PROMPT = "输出已达token上限，直接继续执行,无需道歉，无需重述前文，从中断处接续。"

class RecoveryState:

    def __init__(self):
        self.has_escalated = False
        self.recovery_count = 0
        self.consecutive_529 = 0
        self.has_attempted_reactive_compact = False
        self.current_model = PRIMARY_MODEL


def retry_delay(attempt, retry_after=None):

    if retry_after:
        return retry_after

    base = min(BASE_DELAY_MS * (2 ** attempt), 32000) / 1000
    jitter = random.uniform(0, base * 0.25)
    return base + jitter

def with_retry(fn, state: RecoveryState):
    for attempt in range(MAX_RETRIES):
        try:
            result = fn()
            state.consecutive_529 = 0
            return result
        except Exception as e:
            name = type(e).__name__
            msg = str(e).lower()

            if "ratelimit" in name.lower() or "429" in msg:
                delay = retry_delay(attempt)
                print(f"  \033[33m[429 rate limit] retry {attempt + 1}/{MAX_RETRIES},"
                      f" wait {delay:.1f}s\033[0m")
                time.sleep(delay)
                continue

            if "overloaded" in name.lower() or "529" in msg or "overloaded" in msg:
                state.consecutive_529 += 1
                if state.consecutive_529 >= MAX_CONSECUTIVE_529:
                    if FALLBACK_MODEL:
                        state.current_model = FALLBACK_MODEL
                        state.consecutive_529 = 0
                        print(f"  \033[31m[529 x{MAX_CONSECUTIVE_529}]"
                              f" switching to {FALLBACK_MODEL}\033[0m")

                    else:
                        state.consecutive_529 = 0
                        print(f"  \033[31m[529 x{MAX_CONSECUTIVE_529}]"
                              f" no FALLBACK_MODEL configured, continuing retry\033[0m")

                delay = retry_delay(attempt)
                print(f"  \033[33m[529 overloaded] retry {attempt + 1}/{MAX_RETRIES},"
                      f" wait {delay:.1f}s\033[0m")
                time.sleep(delay)
                continue

            raise

    return RuntimeError(f"Max retries ({MAX_RETRIES}) exceeded")

def is_prompt_too_long_error(e: Exception) -> bool:

    msg = str(e).lower()
    flag = (
        ("prompt" in msg and "long" in msg)
        or "prompt_is_too_long" in msg
        or "context_length_exceeded" in msg
        or "max_context_window" in msg
    )

    return flag

def reactive_compact(messages: list) -> list:

    print("  \033[31m[主动精简] 仅保留最近 5 条消息\033[0m")
    tail = messages[-5:]
    return [{
        "role": "user",
        "content": "[动态精简]前置对话已裁剪,从上次中断的地方继续对话。"
    }, *tail]

