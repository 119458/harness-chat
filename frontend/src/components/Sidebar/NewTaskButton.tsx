import { Plus } from 'lucide-react'

// T029 - sidebar card that starts a new task. Static this iteration (FR-016):
// the onClick is wired but the parent may pass a no-op until US2 plumbing lands.
// Given heavier visual weight than plain nav items (border + surface fill +
// font-medium + brighter text) so it reads as the primary action.
export default function NewTaskButton({
  onClick,
}: {
  onClick?: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full cursor-pointer items-center gap-2 rounded-md border border-hairline bg-surface px-3 py-2 transition-colors hover:bg-canvas/60"
    >
      <Plus className="h-3.5 w-3.5 text-fg" strokeWidth={1.5} />
      <span className="text-control font-medium text-fg">New Task</span>
    </button>
  )
}
