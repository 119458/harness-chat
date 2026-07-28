import { useEffect, useRef, useState } from 'react'
import { Cpu, Folder, Sparkles, Square } from 'lucide-react'
import type { Status } from '../../types/chat'
import SendButton from './SendButton'

// Floating glassmorphic command dock (T033). Owns its textarea state and
// integrates the functional SendButton plus a dock-integrated StopButton that
// replaces the temporary one. The textarea sits on top; the control row sits
// BELOW it inside the same card, separated by a hairline (point 5). Anchored to
// <main> with an inner max-w-3xl column so it aligns with the message content
// column (constitution Principle V, point 8). Controls are STATIC placeholders
// (FR-019/020): clickable, hover-responsive, no functional effect, never error.
export default function CommandDock({
  status,
  onSend,
  onStop,
}: {
  status: Status
  onSend: (message: string) => void
  onStop: () => void
}) {
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  // Auto-resize: grow with content up to 160px (max-h-40), then scroll.
  // Resetting to 'auto' first lets scrollHeight re-measure the collapsed height.
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
  }, [text])

  const send = () => {
    const trimmed = text.trim()
    if (trimmed === '' || status === 'RUNNING') return
    onSend(trimmed)
    setText('')
  }

  // FR-020 edge case: send is disabled while RUNNING or when input is blank.
  const sendDisabled = status === 'RUNNING' || text.trim() === ''

  return (
    <div className="absolute bottom-4 left-0 right-0 z-20 px-4">
      <div className="mx-auto max-w-3xl rounded-xl border border-hairline bg-surface/80 px-4 py-2 shadow-2xl shadow-black/40 backdrop-blur">
        <div className="flex items-end gap-2">
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                send()
              }
            }}
            placeholder="Send an instruction..."
            rows={3}
            className="slim-scrollbar max-h-40 flex-1 resize-none bg-transparent py-1 text-body text-fg placeholder:text-fg-faint outline-none"
          />
          {status === 'RUNNING' && (
            <button
              type="button"
              onClick={onStop}
              aria-label="Stop"
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded border border-hairline bg-canvas/60 text-fg-subtle hover:bg-canvas hover:text-fg"
            >
              <Square size={14} strokeWidth={1.5} />
            </button>
          )}
          <SendButton onSend={send} disabled={sendDisabled} />
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-2 border-t border-hairline pt-2">
          <SandboxPathIndicator />
          <ChatAgentToggle />
          <ModelSelector />
          <DeepThinkToggle />
        </div>
      </div>
    </div>
  )
}

// FR-019/020 static placeholder controls. Each renders a button that responds
// visually (hover) but has NO functional effect and never errors (SC-008).
function SandboxPathIndicator() {
  return (
    <button
      type="button"
      onClick={() => {}}
      className="flex items-center gap-1 text-control text-fg-subtle hover:text-fg"
    >
      <Folder size={12} strokeWidth={1.5} />
      <span>sandbox/</span>
    </button>
  )
}

function ChatAgentToggle() {
  return (
    <button
      type="button"
      onClick={() => {}}
      className="rounded bg-canvas/60 px-2 py-1 text-control text-fg-muted hover:bg-canvas hover:text-fg"
    >
      Chat
    </button>
  )
}

function ModelSelector() {
  return (
    <button
      type="button"
      onClick={() => {}}
      className="flex items-center gap-1 text-control text-fg-subtle hover:text-fg"
    >
      <Cpu size={12} strokeWidth={1.5} />
      <span>deepseek-v4-flash</span>
    </button>
  )
}

function DeepThinkToggle() {
  return (
    <button
      type="button"
      onClick={() => {}}
      className="flex items-center gap-1 text-control text-fg-subtle hover:text-fg"
    >
      <Sparkles size={12} strokeWidth={1.5} />
      <span>Deep Think</span>
    </button>
  )
}
