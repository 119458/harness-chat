import { Bot } from 'lucide-react'
import type { Turn } from '../../types/chat'
import ThinkingBlock from './ThinkingBlock'
import ToolCallBlock from './ToolCallBlock'
import FinalAnswer from './FinalAnswer'
import ErrorBlock from './ErrorBlock'

// One turn = a user message bubble + the assistant's response. The user message
// is a right-aligned bubble with its own background/rounded/padding (point 1);
// the assistant response is left-aligned under a Bot avatar so "AI is speaking"
// is unmistakable (point 2). Assistant blocks stack in the column to the right
// of the avatar.
export default function MessageBubble({ turn }: { turn: Turn }) {
  return (
    <div className="flex flex-col gap-3">
      {/* User message: right-aligned bubble (point 1). */}
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl border border-hairline bg-surface px-4 py-3">
          <span className="whitespace-pre-wrap text-body text-fg">
            {turn.user_message}
          </span>
        </div>
      </div>

      {/* Assistant response: left-aligned with an avatar marker (point 2). */}
      <div className="flex items-start gap-2.5">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-hairline bg-surface text-fg-subtle">
          <Bot className="h-4 w-4" strokeWidth={1.5} />
        </div>
        <div className="flex min-w-0 flex-1 flex-col gap-2">
          {turn.blocks.map((block) => {
            switch (block.kind) {
              case 'thinking':
                return (
                  <ThinkingBlock
                    key={block.block_id}
                    block={block}
                    streaming={turn.status === 'streaming'}
                  />
                )
              case 'tool':
                return <ToolCallBlock key={block.block_id} block={block} />
              case 'answer':
                return <FinalAnswer key={block.block_id} block={block} />
              case 'error':
                return <ErrorBlock key={block.block_id} block={block} />
              default:
                return null
            }
          })}
        </div>
      </div>
    </div>
  )
}
