import { useEffect, useRef } from 'react'
import type { Turn } from '../../types/chat'
import MessageBubble from './MessageBubble'

export default function MessageList({ turns }: { turns: Turn[] }) {
  const sentinelRef = useRef<HTMLDivElement>(null)
  const blockCount = turns.reduce((n, t) => n + t.blocks.length, 0)

  useEffect(() => {
    sentinelRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns, blockCount])

  if (turns.length === 0) {
    return (
      <div className="flex h-full items-center justify-center p-4">
        <span className="text-control tracking-wider text-fg-faint">
          Send an instruction to begin.
        </span>
      </div>
    )
  }

  return (
    <div className="slim-scrollbar h-full overflow-y-auto px-4 [scrollbar-gutter:stable_both-edges]">
      {/*
        Content column is capped to max-w-3xl and centered so it shares the
        exact width + left/right edges of the floating CommandDock (constitution
        Principle V: dock width must match the message column, not the main area).
        scrollbar-gutter:stable both-edges reserves a symmetric gutter so the
        vertical scrollbar no longer shifts the centered column off the dock.
      */}
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 pt-10 pb-4">
        {turns.map((turn) => (
          <MessageBubble key={turn.turn_id} turn={turn} />
        ))}
        <div ref={sentinelRef} aria-hidden="true" />
      </div>
    </div>
  )
}
