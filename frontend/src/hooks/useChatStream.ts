import { fetchEventSource } from '@microsoft/fetch-event-source'
import { useCallback, useEffect, useRef, useState } from 'react'
import type { SSEEvent } from '../types/sse'
import type { Status, Turn } from '../types/chat'

// Fresh per page load (clarification Q5). Module-level so it is stable across
// re-renders but new on reload.
const SESSION_ID = crypto.randomUUID()

const ERROR_AUTO_IDLE_MS = 2500

class FatalError extends Error {}

function newTurn(message: string): Turn {
  return {
    turn_id: crypto.randomUUID(),
    user_message: message,
    blocks: [],
    status: 'streaming',
    started_at: Date.now(),
    ended_at: null,
  }
}

/** Mark all collapsible (thinking/tool) blocks of a turn collapsed (FR-008). */
function collapseCollapsible(turn: Turn): Turn {
  return {
    ...turn,
    blocks: turn.blocks.map((b) =>
      b.kind === 'answer' ? b : { ...b, collapsed: true },
    ),
  }
}

export interface UseChatStream {
  send: (message: string) => void
  stop: () => void
  status: Status
  turns: Turn[]
  session_id: string
}

export function useChatStream(): UseChatStream {
  const [turns, setTurns] = useState<Turn[]>([])
  const [status, setStatus] = useState<Status>('IDLE')

  const abortRef = useRef<AbortController | null>(null)
  const epochRef = useRef(0)
  const terminalRef = useRef(false)
  const userStoppedRef = useRef(false)

  /** Apply one SSE event to the current (last) turn. Pure state update. */
  const applyToCurrentTurn = useCallback((ev: SSEEvent) => {
    setTurns((prev) => {
      if (prev.length === 0) return prev
      const last = prev[prev.length - 1]
      if (last.status !== 'streaming') return prev
      const blocks = [...last.blocks]
      switch (ev.type) {
        case 'thinking_delta': {
          const tail = blocks[blocks.length - 1]
          if (tail && tail.kind === 'thinking') {
            blocks[blocks.length - 1] = { ...tail, content: tail.content + ev.content }
          } else {
            blocks.push({
              block_id: crypto.randomUUID(),
              kind: 'thinking',
              collapsed: false,
              content: ev.content,
            })
          }
          break
        }
        case 'text_delta': {
          const tail = blocks[blocks.length - 1]
          if (tail && tail.kind === 'answer') {
            blocks[blocks.length - 1] = { ...tail, content: tail.content + ev.content }
          } else {
            blocks.push({
              block_id: crypto.randomUUID(),
              kind: 'answer',
              content: ev.content,
            })
          }
          break
        }
        case 'tool_call_start': {
          blocks.push({
            block_id: crypto.randomUUID(),
            kind: 'tool',
            collapsed: false,
            tool: ev.tool,
            input: ev.input,
            result: null,
          })
          break
        }
        case 'tool_call_result': {
          for (let i = blocks.length - 1; i >= 0; i--) {
            const b = blocks[i]
            if (b.kind === 'tool' && b.result === null) {
              blocks[i] = { ...b, result: ev.result }
              break
            }
          }
          break
        }
        default:
          break
      }
      return [...prev.slice(0, -1), { ...last, blocks }]
    })
  }, [])

  /** Terminal event: finalize the current turn + drive status (FR-011..014). */
  const finalizeCurrentTurn = useCallback(
    (kind: 'done' | 'error' | 'stopped', message?: string) => {
      setTurns((prev) => {
        if (prev.length === 0) return prev
        const last = prev[prev.length - 1]
        if (last.status !== 'streaming') return prev
        const finalized: Turn = {
          ...collapseCollapsible(last),
          status: kind,
          ended_at: last.ended_at ?? Date.now(),
        }
        if (kind === 'error' && message) {
          // carry the error message as a final answer block so it is visible
          finalized.blocks = [
            ...finalized.blocks,
            {
              block_id: crypto.randomUUID(),
              kind: 'answer',
              content: `[error] ${message}`,
            },
          ]
        }
        return [...prev.slice(0, -1), finalized]
      })
      if (kind === 'error') {
        setStatus('ERROR')
        window.setTimeout(() => setStatus('IDLE'), ERROR_AUTO_IDLE_MS)
      } else {
        setStatus('IDLE')
      }
    },
    [],
  )

  const send = useCallback(
    (message: string) => {
      const text = message.trim()
      if (!text || abortRef.current) return // send disabled while RUNNING (edge case)

      const myEpoch = ++epochRef.current
      terminalRef.current = false
      userStoppedRef.current = false

      setTurns((prev) => [...prev, newTurn(text)])
      setStatus('RUNNING')

      const ctrl = new AbortController()
      abortRef.current = ctrl

      const isCurrent = () => myEpoch === epochRef.current
      const guardedFinalize = (
        kind: 'done' | 'error' | 'stopped',
        message?: string,
      ) => {
        if (!isCurrent() || terminalRef.current) return
        terminalRef.current = true
        finalizeCurrentTurn(kind, message)
      }

      fetchEventSource('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: SESSION_ID, message: text }),
        signal: ctrl.signal,
        openWhenHidden: true,
        async onopen(response) {
          if (response.ok) return
          let msg = `request failed (${response.status})`
          try {
            const body = await response.json()
            if (body?.message) msg = body.message
          } catch {
            /* keep default */
          }
          // 409 concurrent-turn rejection (U2) and any other non-2xx -> error
          guardedFinalize('error', msg)
          throw new FatalError(msg)
        },
        onmessage(ev) {
          if (!isCurrent() || terminalRef.current || !ev.data) return
          let parsed: SSEEvent
          try {
            parsed = JSON.parse(ev.data) as SSEEvent
          } catch {
            return
          }
          if (
            parsed.type === 'done' ||
            parsed.type === 'stopped' ||
            parsed.type === 'error'
          ) {
            guardedFinalize(
              parsed.type,
              parsed.type === 'error' ? parsed.message : undefined,
            )
          } else {
            applyToCurrentTurn(parsed)
          }
        },
        onerror(err) {
          if (err instanceof FatalError) throw err // from onopen: already finalized
          if (!isCurrent() || userStoppedRef.current) throw err // stale / user abort
          if (!terminalRef.current) {
            guardedFinalize('error', 'connection lost')
          }
          throw err // no auto-retry
        },
        onclose() {
          if (!isCurrent() || terminalRef.current || userStoppedRef.current) {
            throw new FatalError('closed') // prevent reconnect
          }
          guardedFinalize('error', 'stream closed unexpectedly')
          throw new FatalError('closed')
        },
      }).catch(() => {
        if (isCurrent()) abortRef.current = null
      })
    },
    [applyToCurrentTurn, finalizeCurrentTurn],
  )

  const stop = useCallback(() => {
    if (!abortRef.current) return
    // Invalidate in-flight callbacks for this turn (epoch bump) and abort.
    epochRef.current += 1
    userStoppedRef.current = true
    terminalRef.current = true
    abortRef.current.abort()
    abortRef.current = null

    // Immediate client-side IDLE (clarification U3); a later `stopped` event
    // is a no-op (terminalRef already true). Preserve partial content; mark
    // the current turn stopped + collapse (FR-026, SC-009).
    setStatus('IDLE')
    setTurns((prev) => {
      if (prev.length === 0) return prev
      const last = prev[prev.length - 1]
      if (last.status !== 'streaming') return prev
      return [
        ...prev.slice(0, -1),
        {
          ...collapseCollapsible(last),
          status: 'stopped',
          ended_at: last.ended_at ?? Date.now(),
        },
      ]
    })
  }, [])

  useEffect(() => () => abortRef.current?.abort(), [])

  return { send, stop, status, turns, session_id: SESSION_ID }
}
