import { Boxes, Clock, Sparkles } from 'lucide-react'

// T030 - sidebar navigation list. Static this iteration (FR-016): buttons are
// clickable but intentionally have no functional effect. They must never throw.
const NAV_ITEMS = [
  { label: 'Skills', Icon: Sparkles },
  { label: 'MCP & Extensions', Icon: Boxes },
  { label: 'Cron Jobs', Icon: Clock },
] as const

export default function NavList() {
  return (
    <nav className="flex flex-col gap-0.5">
      {NAV_ITEMS.map(({ label, Icon }) => (
        <button
          key={label}
          type="button"
          onClick={() => {}}
          className="flex items-center gap-2 px-3 py-1.5 w-full rounded-md hover:bg-zinc-800/40 transition-colors"
        >
          <Icon className="h-3.5 w-3.5 text-zinc-500" strokeWidth={1.5} />
          <span className="text-control text-zinc-400">{label}</span>
        </button>
      ))}
    </nav>
  )
}
