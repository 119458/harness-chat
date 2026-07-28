import { User } from 'lucide-react'
import type { Turn } from '../../types/chat'
import ThinkingBlock from './ThinkingBlock'
import ToolCallBlock from './ToolCallBlock'
import FinalAnswer from './FinalAnswer'

export default function MessageBubble({ turn }: { turn: Turn }) {
  return (
    <div className="turn mb-6">
      <div className="mb-2 flex items-start gap-2">
        <User size={14} className="mt-0.5 shrink-0 text-zinc-500" />
        <span className="text-body text-zinc-300">{turn.user_message}</span>
      </div>
      {turn.blocks.map((block) => (
        <div key={block.block_id} className="mb-2">
          {(() => {
            switch (block.kind) {
              case 'thinking':
                return <ThinkingBlock block={block} />
              case 'tool':
                return <ToolCallBlock block={block} />
              case 'answer':
                return <FinalAnswer block={block} />
            }
          })()}
        </div>
      ))}
    </div>
  )
}
