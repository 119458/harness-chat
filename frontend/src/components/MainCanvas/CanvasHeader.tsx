import type { Status } from '../../types/chat'

// T032 - header row for the main canvas. Replaces the temporary StatusIndicator.
// Left: task title. Right: monochrome breathing status light whose color and
// animation reflect the current agent status.
export default function CanvasHeader({
  status,
  title,
}: {
  status: Status
  title: string
}) {
  const dotClass =
    status === 'RUNNING'
      ? 'bg-zinc-300 animate-pulse'
      : status === 'ERROR'
        ? 'bg-red-500 animate-pulse'
        : 'bg-zinc-600'

  return (
    <header className="flex items-center justify-between px-4 h-12 border-b border-white/5 bg-canvas/80 backdrop-blur sticky top-0 z-10">
      <span className="text-control text-zinc-200 font-medium tracking-wider truncate">
        {title}
      </span>
      <div className="flex items-center gap-2">
        <span className={`h-1.5 w-1.5 rounded-full ${dotClass}`} />
        <span className="text-micro uppercase tracking-wider text-zinc-500">
          {status}
        </span>
      </div>
    </header>
  )
}
