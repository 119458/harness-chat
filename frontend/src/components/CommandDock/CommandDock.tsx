import { useEffect, useRef, useState } from 'react'
import { Cpu, Folder, Sparkles, Square } from 'lucide-react'
import type { Status } from '../../types/chat'
import SendButton from './SendButton'

// Floating glassmorphic command dock (T033). Owns its textarea state and
// integrates the functional SendButton plus a dock-integrated StopButton that
// replaces the temporary one. Top-row controls are STATIC placeholders
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
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 w-full max-w-3xl px-4 z-20">
      <div className="bg-surface/80 backdrop-blur border border-white/5 rounded-xl shadow-2xl shadow-black/40 p-2">
        <div className="flex flex-wrap items-center gap-2">
          <SandboxPathIndicator />
          <ChatAgentToggle />
          <ModelSelector />
          <DeepThinkToggle />
        </div>
        <div className="mt-2 flex items-end gap-2">
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
            rows={1}
            className="slim-scrollbar flex-1 resize-none bg-transparent py-1 text-body text-zinc-200 placeholder:text-zinc-600 outline-none max-h-40"
          />
          {status === 'RUNNING' && (
            <button
              type="button"
              onClick={onStop}
              aria-label="Stop"
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded border border-white/5 bg-zinc-800/60 text-zinc-300 hover:bg-zinc-700/60"
            >
              <Square size={14} strokeWidth={1.5} />
            </button>
          )}
          <SendButton onSend={send} disabled={sendDisabled} />
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
      className="flex items-center gap-1 text-micro text-zinc-500 hover:text-zinc-300"
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
      className="rounded bg-zinc-800/60 px-2 py-1 text-micro text-zinc-400 hover:bg-zinc-700/60 hover:text-zinc-200"
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
      className="flex items-center gap-1 text-micro text-zinc-500 hover:text-zinc-300"
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
      className="flex items-center gap-1 text-micro text-zinc-500 hover:text-zinc-300"
    >
      <Sparkles size={12} strokeWidth={1.5} />
      <span>Deep Think</span>
    </button>
  )
}
