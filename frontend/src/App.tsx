import CanvasHeader from './components/MainCanvas/CanvasHeader'
import MessageList from './components/MainCanvas/MessageList'
import NewTaskButton from './components/Sidebar/NewTaskButton'
import NavList from './components/Sidebar/NavList'
import RecentTasksList from './components/Sidebar/RecentTasksList'
import UserArea from './components/Sidebar/UserArea'
import CommandDock from './components/CommandDock/CommandDock'
import { useChatStream } from './hooks/useChatStream'

// Final workspace shell (T034): left Sidebar + main canvas (CanvasHeader +
// MessageList with US1 streaming blocks + US2 collapse) + floating CommandDock
// (US3). Integrates useChatStream (T015). The temporary US1 StatusIndicator
// (T022) and StopButton (T021) are superseded by CanvasHeader and the
// dock-integrated StopButton per the plan's G2 pattern. The CommandDock is
// rendered inside <main> so its width column aligns with the message column
// (constitution Principle V).
export default function App() {
  const { send, stop, status, turns } = useChatStream()

  return (
    <div className="flex h-full w-full overflow-hidden bg-canvas text-fg">
      {/* Sidebar (US3) */}
      <aside className="flex w-60 shrink-0 flex-col gap-4 border-r border-hairline bg-canvas p-3">
        <NewTaskButton />
        <NavList />
        <div className="mt-auto flex flex-col gap-3">
          <RecentTasksList />
          <UserArea />
        </div>
      </aside>

      {/* Main canvas */}
      <main className="relative flex min-w-0 flex-1 flex-col">
        <CanvasHeader status={status} title="New Task" />
        {/* pb-36 clears the floating dock (3-line textarea) so the last turn stays visible */}
        <div className="min-h-0 flex-1 pb-36">
          <MessageList turns={turns} />
        </div>
        {/* Floating command dock (US3) - anchored to <main> so its max-w-3xl
            column aligns with the message content column (constitution V). */}
        <CommandDock status={status} onSend={send} onStop={stop} />
      </main>
    </div>
  )
}
