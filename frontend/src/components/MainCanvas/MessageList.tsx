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
        <span className="text-control text-zinc-600 tracking-wider">
          Send an instruction to begin.
        </span>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 p-4 h-full overflow-y-auto slim-scrollbar">
      {turns.map((turn) => (
        <MessageBubble key={turn.turn_id} turn={turn} />
      ))}
      <div ref={sentinelRef} aria-hidden="true" />
    </div>
  )
}
