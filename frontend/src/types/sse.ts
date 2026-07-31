// SSE event types mirroring backend/streaming/schemas.py.
// `type` is the discriminator. Single source of truth for the client side
// (contracts/api-contract.md).

export interface ThinkingDelta {
  type: 'thinking_delta'
  content: string
}

export interface TextDelta {
  type: 'text_delta'
  content: string
}

export interface ToolCallStart {
  type: 'tool_call_start'
  tool: string
  input: Record<string, unknown>
}

export interface ToolCallResult {
  type: 'tool_call_result'
  tool: string
  result: string
}

export interface Done {
  type: 'done'
}

export interface ErrorEvent {
  type: 'error'
  message: string
  // 002-loop-robustness (Principle VII; data-model E3.1): optional exit reason.
  // 'retry_exhausted' | 'turn_limit_reached' | 'stop_hook_protection_triggered'
  // Absent = unclassified error (backwards-compatible with 001).
  reason?: string
}

export interface Stopped {
  type: 'stopped'
}

export type SSEEvent =
  | ThinkingDelta
  | TextDelta
  | ToolCallStart
  | ToolCallResult
  | Done
  | ErrorEvent
  | Stopped

export type SSEEventType = SSEEvent['type']

export const TERMINAL_EVENTS: ReadonlySet<SSEEventType> = new Set([
  'done',
  'error',
  'stopped',
])
