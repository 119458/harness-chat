import CanvasHeader from './components/MainCanvas/CanvasHeader'
import MessageList from './components/MainCanvas/MessageList'
import NewTaskButton from './components/Sidebar/NewTaskButton'
import NavList from './components/Sidebar/NavList'
import RecentTasksList from './components/Sidebar/RecentTasksList'
import CommandDock from './components/CommandDock/CommandDock'
import { useChatStream } from './hooks/useChatStream'

// Final workspace shell (T034): left Sidebar + main canvas (CanvasHeader +
// MessageList with US1 streaming blocks + US2 collapse) + floating CommandDock
// (US3). Integrates useChatStream (T015). The temporary US1 StatusIndicator
// (T022) and StopButton (T021) are superseded by CanvasHeader and the
// dock-integrated StopButton per the plan's G2 pattern.
export default function App() {
  const { send, stop, status, turns } = useChatStream()

  return (
    <div className="h-full w-full flex bg-canvas text-zinc-300 overflow-hidden">
      {/* Sidebar (US3) */}
      <aside className="w-60 shrink-0 border-r border-white/5 bg-canvas flex flex-col gap-4 p-3">
        <NewTaskButton />
        <NavList />
        <div className="mt-auto">
          <RecentTasksList />
        </div>
      </aside>

      {/* Main canvas */}
      <main className="flex-1 flex flex-col min-w-0 relative">
        <CanvasHeader status={status} title="New Task" />
        {/* pb-28 clears the floating dock so the last turn stays visible */}
        <div className="flex-1 min-h-0 pb-28">
          <MessageList turns={turns} />
        </div>
      </main>

      {/* Floating command dock (US3) */}
      <CommandDock status={status} onSend={send} onStop={stop} />
    </div>
  )
}
