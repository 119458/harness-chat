import { useEffect, useState } from 'react'
import { Brain, ChevronDown, ChevronRight } from 'lucide-react'
import type { ThinkingBlockData } from '../../types/chat'

// FR-007/008/009/010 - collapsible thinking trace. The hook sets block.collapsed
// to true when the turn finishes; the useEffect below mirrors that into local
// state so the block auto-collapses without losing content (it stays in
// block.content, just hidden).
export default function ThinkingBlock({ block }: { block: ThinkingBlockData }) {
  const [expanded, setExpanded] = useState(!block.collapsed)

  useEffect(() => {
    setExpanded(!block.collapsed)
  }, [block.collapsed])

  if (!block.content) return null

  return (
    <div className="w-full">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center gap-2 py-1 text-left"
      >
        <Brain className="h-3.5 w-3.5 text-zinc-500" strokeWidth={1.5} />
        <span className="text-control tracking-wider text-zinc-400">
          Thinking Process
        </span>
        <span className="ml-auto">
          {expanded ? (
            <ChevronDown className="h-3.5 w-3.5 text-zinc-500" strokeWidth={1.5} />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-zinc-500" strokeWidth={1.5} />
          )}
        </span>
      </button>
      {expanded && (
        <div className="pl-6">
          <pre className="slim-scrollbar max-h-60 overflow-auto whitespace-pre-wrap text-micro leading-relaxed text-zinc-500">
            {block.content}
          </pre>
        </div>
      )}
    </div>
  )
}
