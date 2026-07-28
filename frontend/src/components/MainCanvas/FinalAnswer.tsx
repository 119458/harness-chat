import type { AnswerBlockData } from '../../types/chat'

// Final assistant answer. Not collapsible - this is the persistent turn output.
export default function FinalAnswer({ block }: { block: AnswerBlockData }) {
  if (!block.content) return null

  return (
    <div className="whitespace-pre-wrap text-body leading-relaxed text-zinc-200">
      {block.content}
    </div>
  )
}
