// T031 - recent tasks list. Shows at most 4 rows visibly; the slim-scrollbar
// (FR-017, SC-006) appears only when items exceed that cap. Empty state is a
// muted micro-label with no scrollbar.
export default function RecentTasksList({
  items = [],
}: {
  items?: string[]
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-micro uppercase tracking-wider text-zinc-600">
        Recent Tasks
      </span>
      {items.length === 0 ? (
        <span className="text-micro text-zinc-700 px-2">No recent tasks</span>
      ) : (
        <div className="slim-scrollbar max-h-[calc(4*1.75rem)] overflow-y-auto">
          {items.map((item, idx) => (
            <div
              key={`${item}-${idx}`}
              className="text-control text-zinc-500 px-2 py-1 truncate"
            >
              {item}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
