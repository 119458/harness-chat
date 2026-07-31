import { AlertTriangle } from 'lucide-react'
import type { ErrorBlockData } from '../../types/chat'

// 002-loop-robustness US3 (contracts "客户端处理约定"): map an exit `reason`
// to user-facing copy. Bounded stops (turn_limit_reached /
// stop_hook_protection_triggered) use non-alarm copy so they don't read as a
// failure; retry_exhausted / stream_error read as errors. No reason = existing
// error render (backwards-compatible with 001). Copy-only branch - no new UI
// structure / colors / icons (constitution Principle V; plan Constitution Check).
const REASON_COPY: Record<string, string> = {
  turn_limit_reached: '已达轮次上限，任务停止',
  stop_hook_protection_triggered: 'Stop 钩子强制续跑保护触发，任务停止',
  retry_exhausted: '请求重试耗尽，任务终止',
  stream_error: '流式连接中断，任务终止',
}

const BOUNDED_STOP_REASONS = new Set([
  'turn_limit_reached',
  'stop_hook_protection_triggered',
])

// Inline error notice for a failed turn. Rendered as a bordered card with a
// light red tint + matching border/icon (point 4) so it reads as a distinct
// error state, not bare text. Sits in the assistant response column after any
// partial content. Red tints are opacity-based so the card reads correctly in
// both themes; the message body stays on text-fg for readability.
export default function ErrorBlock({ block }: { block: ErrorBlockData }) {
  if (!block.content && !block.reason) return null
  // Prefer reason-derived copy when available; fall back to the backend message.
  const body = (block.reason && REASON_COPY[block.reason]) || block.content
  // Bounded stops are not failures - soften the label copy accordingly.
  const label =
    block.reason && BOUNDED_STOP_REASONS.has(block.reason) ? '已停止' : 'Error'

  return (
    <div className="flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2.5">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" strokeWidth={1.5} />
      <div className="min-w-0 flex-1">
        <span className="text-micro uppercase tracking-wider text-red-500">
          {label}
        </span>
        <p className="mt-0.5 whitespace-pre-wrap text-body text-fg">
          {body}
        </p>
      </div>
    </div>
  )
}
