#!/usr/bin/env python3
"""verify_robustness.py - 002-loop-robustness fault-injection verification.

Proves the agent_loop robustness mechanisms ACTUALLY trigger (spec US5 /
FR-007 / SC-005), not just that the happy path runs. Faults are injected via
monkeypatch into the REAL ``agent_loop``; peripheral I/O (memory LLM calls,
system prompt, tool pool, hooks) is stubbed hermetically so the suite needs no
network and writes nothing to WORKDIR. The logic under test - ``turn_count``,
``forced_continue_count``, ``needs_follow_up``, ``RetryExhaustedError``
handling, ``reactive_compact`` recovery - is the real ``loop/loop.py`` +
``error/error.py`` code.

Run from the repo root::

    python verify_robustness.py

This script lives at the repo root and is NOT part of the agent's WORKDIR
sandbox (a dev-time tool, per quickstart.md scenario 5 / research R9).
"""

import os
import sys
import types
from pathlib import Path

# Repo root on sys.path + load .env BEFORE importing the agent chain: loop/
# error/ read WORKDIR/MODEL at import time.
_REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(_REPO))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(override=True)
os.environ.setdefault("MODEL", os.environ.get("MODEL", "test-model"))
os.environ.setdefault("WORKDIR", str(_REPO / "sandbox"))

import error.error as error_mod  # noqa: E402
import loop.loop as loop_mod  # noqa: E402

# ---------------------------------------------------------------------------
# Fakes: a controllable Anthropic stream + message shape.
# ---------------------------------------------------------------------------


class Fake429(Exception):
    """Message carries '429' so with_retry's 429 branch matches."""


class Fake529(Exception):
    """Message carries '529'/'overloaded' so with_retry's 529 branch matches."""


class FakeToolUseBlock:
    def __init__(self, name="test_tool", inp=None, bid="tu_1"):
        self.type = "tool_use"
        self.name = name
        self.input = inp if inp is not None else {}
        self.id = bid


class FakeTextBlock:
    def __init__(self, text="hello"):
        self.type = "text"
        self.text = text


class FakeMessage:
    def __init__(self, stop_reason="end_turn", content=None):
        self.stop_reason = stop_reason
        self.content = content if content is not None else []


def _text_delta(text):
    d = types.SimpleNamespace(type="text_delta", text=text)
    return types.SimpleNamespace(type="content_block_delta", delta=d)


def _tool_use_start():
    cb = types.SimpleNamespace(type="tool_use")
    return types.SimpleNamespace(type="content_block_start", content_block=cb)


class FakeStream:
    """Mimics the Anthropic stream CM: ``__enter__`` -> self, iterable,
    ``get_final_message``. ``enter_exc`` raises at stream entry (429/529/...
    surface there); ``mid_exc`` raises mid-iteration after ``raise_after``
    yields (stream disconnect)."""

    def __init__(self, events=None, final=None, enter_exc=None,
                 mid_exc=None, raise_after=0):
        self._events = list(events or [])
        self._final = final
        self._enter_exc = enter_exc
        self._mid_exc = mid_exc
        self._raise_after = raise_after

    def __enter__(self):
        if self._enter_exc is not None:
            exc = self._enter_exc
            if isinstance(exc, type):
                exc = exc("injected fault")
            raise exc
        return self

    def __exit__(self, *a):
        return False

    def __iter__(self):
        for i, ev in enumerate(self._events):
            yield ev
            if self._mid_exc is not None and i + 1 >= self._raise_after:
                raise self._mid_exc
        if self._mid_exc is not None and self._raise_after == 0:
            raise self._mid_exc

    def get_final_message(self):
        return self._final


class FakeMessages:
    def __init__(self, factory):
        self._factory = factory
        self.models = []  # model kwarg per stream call (for degrade asserts)

    def stream(self, **kwargs):
        self.models.append(kwargs.get("model"))
        return self._factory()


class FakeClient:
    def __init__(self, factory):
        self.messages = FakeMessages(factory)


def seq_factory(streams):
    """Return ``streams[i]`` on call ``i``; repeat the last afterwards."""
    state = {"i": 0, "calls": 0}

    def factory():
        state["calls"] += 1
        i = state["i"]
        if i < len(streams):
            state["i"] += 1
            return streams[i]
        return streams[-1] if streams else FakeStream()

    factory.state = state
    return factory


# ---------------------------------------------------------------------------
# Hermetic stubs for peripheral I/O (the robustness logic stays real).
# ---------------------------------------------------------------------------

_test_stop_hooks: list = []
_captured: dict = {}

_real_recovery = loop_mod.RecoveryState


class _CapturingRecoveryState(_real_recovery):
    def __init__(self):
        super().__init__()
        _captured["state"] = self


def _stub_trigger_hooks(event, *args):
    if event == "Stop":
        for fn in _test_stop_hooks:
            r = fn(*args)
            if r is not None:
                return r
        return None
    if event == "NoAPISummaryHook":
        return args[0]  # pass messages through unchanged (skip compaction)
    return None  # PreToolUse / PostToolUse / UserPromptSubmit


# Patch the heavy peripherals once; per-case state is reset in run_case.
loop_mod.load_memories = lambda msgs: None
loop_mod.extract_memories = lambda *a, **k: None
loop_mod.consolidate_memories = lambda *a, **k: None
loop_mod.get_system_prompt = lambda: "test system prompt"
loop_mod.trigger_hooks = _stub_trigger_hooks
loop_mod.RecoveryState = _CapturingRecoveryState
error_mod.time.sleep = lambda *a, **k: None  # make retries instant


def run_case(streams, handlers=None, stop_hooks=None, max_turns=None,
             fallback_model=None, messages=None):
    """Run one fault-injection case. Returns (events, state, factory)."""
    _test_stop_hooks.clear()
    _captured.clear()
    if stop_hooks:
        _test_stop_hooks.extend(stop_hooks)
    loop_mod.MAX_TURNS = max_turns if max_turns is not None else 50
    # FALLBACK_MODEL is read by with_retry as an error_mod global.
    error_mod.FALLBACK_MODEL = fallback_model

    factory = seq_factory(streams)
    loop_mod.client = FakeClient(factory)
    loop_mod.assemble_tool_pool = lambda: ([], dict(handlers or {}))

    events: list = []
    loop_mod.agent_loop(messages or [{"role": "user", "content": "test"}],
                        on_event=events.append)
    state = _captured.get("state")
    return events, state, factory


def terminal(events):
    for ev in reversed(events):
        if ev.get("type") in ("done", "error", "stopped"):
            return ev
    return None


def reason_of(events):
    t = terminal(events)
    return t.get("reason") if t and t.get("type") == "error" else None


# ---------------------------------------------------------------------------
# Test cases (quickstart scenario 5.1 - 5.9).
# ---------------------------------------------------------------------------

_RESULTS: list = []


def check(case, ok, detail):
    _RESULTS.append((case, ok, detail))
    mark = "\033[32mPASS\033[0m" if ok else "\033[31mFAIL\033[0m"
    print(f"  [{mark}] {case}: {detail}")


def test_5_1_429_backoff():
    ok_stream = FakeStream(events=[_text_delta("recovered")],
                           final=FakeMessage("end_turn", [FakeTextBlock("recovered")]))
    streams = [
        FakeStream(enter_exc=Fake429("429 Too Many Requests")),
        FakeStream(enter_exc=Fake429("429 Too Many Requests")),
        ok_stream,
    ]
    events, state, factory = run_case(streams)
    t = terminal(events)
    ok = (t is not None and t.get("type") == "done"
          and factory.state["calls"] == 3
          and state.consecutive_529 == 0)
    check("5.1 429 退避恢复", ok,
          f"terminal={t['type'] if t else None} calls={factory.state['calls']} "
          f"reason={reason_of(events)!r}")


def test_5_2_529_degrade():
    ok_stream = FakeStream(events=[_text_delta("on fallback")],
                           final=FakeMessage("end_turn", [FakeTextBlock("on fallback")]))
    streams = [FakeStream(enter_exc=Fake529("529 overloaded"))] * 3 + [ok_stream]
    events, state, factory = run_case(
        streams, fallback_model="fallback-model-x")
    switched = state.current_model == "fallback-model-x"
    t = terminal(events)
    ok = switched and t is not None and t.get("type") == "done"
    check("5.2 529 降级到 FALLBACK_MODEL", ok,
          f"current_model={state.current_model!r} terminal={t['type'] if t else None}")


def test_5_3_retry_exhausted():
    streams = [FakeStream(enter_exc=Fake529("529 overloaded"))]  # always 529
    events, state, factory = run_case(streams, fallback_model=None)
    t = terminal(events)
    ok = (t is not None and t.get("type") == "error"
          and t.get("reason") == "retry_exhausted")
    check("5.3 重试耗尽 retry_exhausted", ok,
          f"terminal={t['type'] if t else None} reason={reason_of(events)!r} "
          f"calls={factory.state['calls']}")


def test_5_4_turn_limit():
    tu_stream = FakeStream(
        events=[_tool_use_start()],
        final=FakeMessage("tool_use", [FakeToolUseBlock()]))
    streams = [tu_stream]
    events, state, factory = run_case(
        streams, handlers={"test_tool": lambda **k: "ok"}, max_turns=3)
    t = terminal(events)
    ok = (t is not None and t.get("type") == "error"
          and t.get("reason") == "turn_limit_reached"
          and state.turn_count >= 3)
    check("5.4 轮次上限 turn_limit_reached", ok,
          f"terminal={t['type'] if t else None} reason={reason_of(events)!r} "
          f"turn_count={state.turn_count}")


def test_5_5_hook_protection():
    text_stream = FakeStream(events=[_text_delta("done")],
                             final=FakeMessage("end_turn", [FakeTextBlock("done")]))
    streams = [text_stream]
    events, state, factory = run_case(
        streams, stop_hooks=[lambda msgs: "再跑一轮"])  # always force-continue
    t = terminal(events)
    ok = (t is not None and t.get("type") == "error"
          and t.get("reason") == "stop_hook_protection_triggered"
          and state.forced_continue_count > 3)
    check("5.5 钩子保护 stop_hook_protection_triggered", ok,
          f"terminal={t['type'] if t else None} reason={reason_of(events)!r} "
          f"forced_continue_count={state.forced_continue_count}")


def test_5_6_midstream_disconnect():
    # Yield one delta, then raise a connection error mid-iteration.
    streams = [FakeStream(events=[_text_delta("partial")],
                          final=FakeMessage("end_turn", []),
                          mid_exc=ConnectionError("stream disconnected"),
                          raise_after=1)]
    events, state, factory = run_case(streams)
    t = terminal(events)
    types_seen = [e.get("type") for e in events]
    partial_kept = "text_delta" in types_seen
    # reason is null/absent (unclassified; stream_error not细分, analyze C1).
    reason = reason_of(events)
    ok = (t is not None and t.get("type") == "error"
          and partial_kept and (reason is None)
          and state.turn_count == 1 and state.forced_continue_count == 0)
    check("5.6 流中途断开 reason=null", ok,
          f"terminal={t['type'] if t else None} reason={reason!r} "
          f"events={types_seen}")


def test_5_7_tool_exception():
    def boom(**k):
        raise ValueError("tool boom")
    tu_stream = FakeStream(
        events=[_tool_use_start()],
        final=FakeMessage("tool_use", [FakeToolUseBlock()]))
    text_stream = FakeStream(events=[_text_delta("after")],
                             final=FakeMessage("end_turn", [FakeTextBlock("after")]))
    streams = [tu_stream, text_stream]
    events, state, factory = run_case(streams, handlers={"test_tool": boom})
    t = terminal(events)
    # The handler exception is caught by execute_tool -> tool_call_result with
    # the error string; the loop continues and ends with done (no crash).
    tool_results = [e for e in events if e.get("type") == "tool_call_result"]
    caught = any("工具执行错误" in (r.get("result") or "") for r in tool_results)
    ok = (t is not None and t.get("type") == "done" and caught)
    check("5.7 工具异常（循环不崩溃）", ok,
          f"terminal={t['type'] if t else None} tool_results={len(tool_results)} "
          f"caught={caught}")


def test_5_8_needs_follow_up():
    # stop_reason lags ("end_turn") but the stream already has a tool_use block
    # -> needs_follow_up=True -> dispatch + continue (old stop_reason code would
    # have stopped prematurely without dispatching the tool).
    tu_stream = FakeStream(
        events=[_tool_use_start()],
        final=FakeMessage("end_turn", [FakeToolUseBlock()]))  # lagging reason
    text_stream = FakeStream(events=[_text_delta("final")],
                             final=FakeMessage("end_turn", [FakeTextBlock("final")]))
    streams = [tu_stream, text_stream]
    events, state, factory = run_case(streams, handlers={"test_tool": lambda **k: "ok"})
    t = terminal(events)
    dispatched = any(e.get("type") == "tool_call_start" for e in events)
    ok = (dispatched and t is not None and t.get("type") == "done"
          and state.turn_count == 2)
    check("5.8 needs_follow_up 续跑判断", ok,
          f"dispatched={dispatched} terminal={t['type'] if t else None} "
          f"turn_count={state.turn_count}")


def test_5_9_reactive_compact():
    # First stream entry raises a prompt-too-long error -> reactive_compact
    # recovers same-turn (continue); second turn succeeds. No ExitReason.
    prompt_long = FakeStream(enter_exc=Exception("prompt is too long"))
    ok_stream = FakeStream(events=[_text_delta("after compact")],
                           final=FakeMessage("end_turn", [FakeTextBlock("after compact")]))
    streams = [prompt_long, ok_stream]
    events, state, factory = run_case(streams)
    t = terminal(events)
    reason = reason_of(events)
    ok = (state.has_attempted_reactive_compact
          and t is not None and t.get("type") == "done"
          and reason is None)
    check("5.9 响应式压缩 reactive_compact", ok,
          f"reactive_compact={state.has_attempted_reactive_compact} "
          f"terminal={t['type'] if t else None} reason={reason!r}")


def main():
    print("\n\033[35m[verify_robustness] 002-loop-robustness fault injection\033[0m\n")
    for fn in [
        test_5_1_429_backoff,
        test_5_2_529_degrade,
        test_5_3_retry_exhausted,
        test_5_4_turn_limit,
        test_5_5_hook_protection,
        test_5_6_midstream_disconnect,
        test_5_7_tool_exception,
        test_5_8_needs_follow_up,
        test_5_9_reactive_compact,
    ]:
        try:
            fn()
        except Exception as e:  # noqa: BLE001 - surface as a failed case
            import traceback
            _RESULTS.append((fn.__name__, False, f"raised: {type(e).__name__}: {e}"))
            print(f"  [\033[31mFAIL\033[0m] {fn.__name__}: raised {type(e).__name__}: {e}")
            traceback.print_exc()

    passed = sum(1 for _, ok, _ in _RESULTS if ok)
    total = len(_RESULTS)
    print(f"\n\033[35m[verify_robustness] {passed}/{total} cases passed\033[0m")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
