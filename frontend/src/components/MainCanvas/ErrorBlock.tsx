import { AlertTriangle } from 'lucide-react'
import type { ErrorBlockData } from '../../types/chat'

// Inline error notice for a failed turn. Rendered as a bordered card with a
// light red tint + matching border/icon (point 4) so it reads as a distinct
// error state, not bare text. Sits in the assistant response column after any
// partial content. Red tints are opacity-based so the card reads correctly in
// both themes; the message body stays on text-fg for readability.
export default function ErrorBlock({ block }: { block: ErrorBlockData }) {
  if (!block.content) return null

  return (
    <div className="flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2.5">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" strokeWidth={1.5} />
      <div className="min-w-0 flex-1">
        <span className="text-micro uppercase tracking-wider text-red-500">
          Error
        </span>
        <p className="mt-0.5 whitespace-pre-wrap text-body text-fg">
          {block.content}
        </p>
      </div>
    </div>
  )
}
