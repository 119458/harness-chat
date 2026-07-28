import { useEffect, useState } from 'react'
import { Brain, ChevronDown, ChevronRight } from 'lucide-react'
import type { ThinkingBlockData } from '../../types/chat'

// FR-007/008/009/010 - collapsible thinking trace. The hook sets block.collapsed
// to true when the turn finishes; the useEffect below mirrors that into local
// state so the block auto-collapses without losing content (it stays in
// block.content, just hidden). Rendered as a bordered card (point 3): the header
// is a one-line capsule (icon + summary + chevron), the body sits under a
// hairline divider. Summary + body both use the 12px control tier so they sit
// below the 16px final answer in the type hierarchy (point 4).
export default function ThinkingBlock({
  block,
  streaming,
}: {
  block: ThinkingBlockData
  streaming: boolean
}) {
  const [expanded, setExpanded] = useState(!block.collapsed)

  useEffect(() => {
    setExpanded(!block.collapsed)
  }, [block.collapsed])

  // Waiting state: while the turn is streaming and no thinking_delta has
  // arrived yet (block.content empty), reuse the same capsule shell with a
  // "思考中" label and an opacity breathing animation (40% -> 100% -> 40%,
  // ~1.2s) for immediate feedback instead of a frozen screen. The first
  // thinking_delta fills this same block instance in place -> the capsule
  // smoothly becomes the real Thinking Process card (same React key, no
  // remount, no flicker). If the turn ends with no thinking content, render
  // nothing.
  if (!block.content) {
    if (!streaming) return null
    return (
      <div className="w-full rounded-lg border border-hairline bg-surface/60">
        <div className="flex w-full items-center gap-2 px-3 py-2">
          <span className="flex items-center gap-2 animate-[thinking-breath_1.2s_ease-in-out_infinite]">
            <Brain className="h-3.5 w-3.5 text-fg-subtle" strokeWidth={1.5} />
            <span className="text-control tracking-wider text-fg-muted">
              思考中
            </span>
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full rounded-lg border border-hairline bg-surface/60">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left"
      >
        <Brain className="h-3.5 w-3.5 text-fg-subtle" strokeWidth={1.5} />
        <span className="text-control tracking-wider text-fg-muted">
          Thinking Process
        </span>
        <span className="ml-auto">
          {expanded ? (
            <ChevronDown className="h-3.5 w-3.5 text-fg-subtle" strokeWidth={1.5} />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-fg-subtle" strokeWidth={1.5} />
          )}
        </span>
      </button>
      {expanded && (
        <div className="border-t border-hairline px-3 pb-3 pt-2">
          <pre className="slim-scrollbar max-h-60 overflow-auto whitespace-pre-wrap text-control leading-relaxed text-fg-subtle">
            {block.content}
          </pre>
        </div>
      )}
    </div>
  )
}
