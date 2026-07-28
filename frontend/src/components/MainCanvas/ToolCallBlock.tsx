import { useEffect, useState } from 'react'
import { Check, ChevronDown, ChevronRight, Loader, Terminal } from 'lucide-react'
import type { ToolBlockData } from '../../types/chat'

// Collapsible tool call block. Same collapse sync pattern as ThinkingBlock:
// local state mirrors !block.collapsed so the hook can auto-collapse on turn
// completion while preserving input/result in block data. Rendered as a bordered
// card matching the ThinkingBlock (point 7). The running/done badges stay on the
// 10px micro tier (constitution V: status/progress badges) per decision 3.
export default function ToolCallBlock({ block }: { block: ToolBlockData }) {
  const [expanded, setExpanded] = useState(!block.collapsed)

  useEffect(() => {
    setExpanded(!block.collapsed)
  }, [block.collapsed])

  const running = block.result === null

  return (
    <div className="w-full rounded-lg border border-hairline bg-surface/60">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left"
      >
        <Terminal className="h-3.5 w-3.5 text-fg-subtle" strokeWidth={1.5} />
        <span className="text-control text-fg">{block.tool}</span>
        <span className="ml-auto flex items-center gap-1.5">
          {running ? (
            <>
              <Loader className="h-3 w-3 animate-spin text-fg-subtle" strokeWidth={1.5} />
              <span className="text-micro uppercase tracking-wider text-fg-subtle">
                running
              </span>
            </>
          ) : (
            <>
              <Check className="h-3 w-3 text-emerald-500" strokeWidth={1.5} />
              <span className="text-micro uppercase tracking-wider text-fg-subtle">
                done
              </span>
            </>
          )}
          {expanded ? (
            <ChevronDown className="h-3.5 w-3.5 text-fg-subtle" strokeWidth={1.5} />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-fg-subtle" strokeWidth={1.5} />
          )}
        </span>
      </button>
      {expanded && (
        <div className="border-t border-hairline px-3 pb-3 pt-2 font-mono text-control text-fg-muted">
          <div className="text-fg-subtle">{`$ ${block.tool}`}</div>
          <pre className="slim-scrollbar mt-1 overflow-auto whitespace-pre-wrap">
            {JSON.stringify(block.input, null, 2)}
          </pre>
          {!running && (
            <>
              <div className="my-2 h-px bg-hairline" />
              <pre className="slim-scrollbar max-h-60 overflow-auto whitespace-pre-wrap">
                {block.result}
              </pre>
            </>
          )}
        </div>
      )}
    </div>
  )
}
