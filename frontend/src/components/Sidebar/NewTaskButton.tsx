import { Plus } from 'lucide-react'

// T029 - sidebar card that starts a new task. Static this iteration (FR-016):
// the onClick is wired but the parent may pass a no-op until US2 plumbing lands.
export default function NewTaskButton({
  onClick,
}: {
  onClick?: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center gap-2 px-3 py-2 rounded-md border border-white/5 bg-surface hover:bg-zinc-800/60 cursor-pointer transition-colors w-full"
    >
      <Plus className="h-3.5 w-3.5 text-zinc-300" strokeWidth={1.5} />
      <span className="text-control text-zinc-300">New Task</span>
    </button>
  )
}
