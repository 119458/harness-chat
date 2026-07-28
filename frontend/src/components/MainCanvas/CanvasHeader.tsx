import type { Status } from '../../types/chat'

// T032 - header row for the main canvas. Replaces the temporary StatusIndicator.
// Left: task title. Right: monochrome breathing status light whose color and
// animation reflect the current agent status. The status word stays on the 10px
// micro tier (constitution V: status/progress badges) per decision 3.
export default function CanvasHeader({
  status,
  title,
}: {
  status: Status
  title: string
}) {
  const dotClass =
    status === 'RUNNING'
      ? 'bg-fg animate-pulse'
      : status === 'ERROR'
        ? 'bg-red-500 animate-pulse'
        : 'bg-fg-faint'

  return (
    <header className="sticky top-0 z-10 flex h-12 items-center justify-between border-b border-hairline bg-canvas/80 px-4 backdrop-blur">
      <span className="truncate text-control font-medium tracking-wider text-fg">
        {title}
      </span>
      <div className="flex items-center gap-2">
        <span className={`h-1.5 w-1.5 rounded-full ${dotClass}`} />
        <span className="text-micro uppercase tracking-wider text-fg-subtle">
          {status}
        </span>
      </div>
    </header>
  )
}
