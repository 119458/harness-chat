import { useEffect, useState } from 'react'
import { Check, ChevronDown, ChevronRight, Loader, Terminal } from 'lucide-react'
import type { ToolBlockData } from '../../types/chat'

// Collapsible tool call block. Same collapse sync pattern as ThinkingBlock:
// local state mirrors !block.collapsed so the hook can auto-collapse on turn
// completion while preserving input/result in block data.
export default function ToolCallBlock({ block }: { block: ToolBlockData }) {
  const [expanded, setExpanded] = useState(!block.collapsed)

  useEffect(() => {
    setExpanded(!block.collapsed)
  }, [block.collapsed])

  const running = block.result === null

  return (
    <div className="w-full">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center gap-2 py-1 text-left"
      >
        <Terminal className="h-3.5 w-3.5 text-zinc-500" strokeWidth={1.5} />
        <span className="text-control text-zinc-300">{block.tool}</span>
        <span className="ml-auto flex items-center gap-1.5">
          {running ? (
            <>
              <Loader
                className="h-3 w-3 animate-spin text-zinc-500"
                strokeWidth={1.5}
              />
              <span className="text-micro uppercase tracking-wider text-zinc-500">
                running
              </span>
            </>
          ) : (
            <>
              <Check className="h-3 w-3 text-emerald-500" strokeWidth={1.5} />
              <span className="text-micro uppercase tracking-wider text-zinc-500">
                done
              </span>
            </>
          )}
          {expanded ? (
            <ChevronDown className="h-3.5 w-3.5 text-zinc-500" strokeWidth={1.5} />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-zinc-500" strokeWidth={1.5} />
          )}
        </span>
      </button>
      {expanded && (
        <div className="mt-1 rounded border border-white/5 bg-canvas/60 p-3 font-mono text-micro text-zinc-400">
          <div className="text-zinc-500">{`$ ${block.tool}`}</div>
          <pre className="slim-scrollbar mt-1 overflow-auto whitespace-pre-wrap text-zinc-400">
            {JSON.stringify(block.input, null, 2)}
          </pre>
          {!running && (
            <>
              <div className="my-2 h-px bg-white/5" />
              <pre className="slim-scrollbar max-h-60 overflow-auto whitespace-pre-wrap text-zinc-400">
                {block.result}
              </pre>
            </>
          )}
        </div>
      )}
    </div>
  )
}
