import { Moon, Settings, Sun, User } from 'lucide-react'
import { useTheme } from '../../hooks/useTheme'

// Sidebar footer ("底部：用户信息 + 设置入口" from the original specify, which
// the plan/tasks phase had dropped). Avatar + name are STATIC placeholders with
// no login logic; the theme toggle is the one functional control. Sits at the
// very bottom of the sidebar, below RECENT TASKS.
export default function UserArea() {
  const { theme, toggle } = useTheme()

  return (
    <div className="flex items-center gap-2 rounded-lg border border-hairline bg-surface px-2.5 py-2">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-hairline bg-canvas text-fg-subtle">
        <User className="h-3.5 w-3.5" strokeWidth={1.5} />
      </div>
      <span className="flex-1 truncate text-control text-fg">Operator</span>
      <button
        type="button"
        onClick={() => {}}
        aria-label="Settings"
        className="flex h-6 w-6 items-center justify-center rounded text-fg-subtle transition-colors hover:bg-canvas/60 hover:text-fg"
      >
        <Settings className="h-3.5 w-3.5" strokeWidth={1.5} />
      </button>
      <button
        type="button"
        onClick={toggle}
        aria-label="Toggle theme"
        className="flex h-6 w-6 items-center justify-center rounded text-fg-subtle transition-colors hover:bg-canvas/60 hover:text-fg"
      >
        {theme === 'dark' ? (
          <Sun className="h-3.5 w-3.5" strokeWidth={1.5} />
        ) : (
          <Moon className="h-3.5 w-3.5" strokeWidth={1.5} />
        )}
      </button>
    </div>
  )
}
