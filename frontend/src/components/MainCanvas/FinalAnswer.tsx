import type { AnswerBlockData } from '../../types/chat'

// Final assistant answer. Not collapsible - this is the persistent turn output.
// Uses the 16px emphasis tier (constitution V) so it outweighs the 12px
// thinking/tool summaries and remains the visual focus of the turn (point 4).
export default function FinalAnswer({ block }: { block: AnswerBlockData }) {
  if (!block.content) return null

  return (
    <div className="whitespace-pre-wrap text-emphasis leading-relaxed text-fg">
      {block.content}
    </div>
  )
}
