import { Boxes, Clock, Sparkles } from 'lucide-react'

// T030 - sidebar navigation list. Static this iteration (FR-016): buttons are
// clickable but intentionally have no functional effect. They must never throw.
// Rendered under a 10px uppercase group title so the section reads as a distinct
// group (constitution V: 10px is reserved for group titles + status badges).
const NAV_ITEMS = [
  { label: 'Skills', Icon: Sparkles },
  { label: 'MCP & Extensions', Icon: Boxes },
  { label: 'Cron Jobs', Icon: Clock },
] as const

export default function NavList() {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="px-3 text-micro uppercase tracking-wider text-fg-faint">
        Navigation
      </span>
      <nav className="flex flex-col gap-0.5">
        {NAV_ITEMS.map(({ label, Icon }) => (
          <button
            key={label}
            type="button"
            onClick={() => {}}
            className="flex w-full items-center gap-2 rounded-md px-3 py-1.5 transition-colors hover:bg-canvas/60"
          >
            <Icon className="h-3.5 w-3.5 text-fg-subtle" strokeWidth={1.5} />
            <span className="text-control text-fg-muted">{label}</span>
          </button>
        ))}
      </nav>
    </div>
  )
}
