// T031 - recent tasks list. Shows at most 4 rows visibly; the slim-scrollbar
// (FR-017, SC-006) appears only when items exceed that cap. Empty state is a
// muted hint with no scrollbar.
export default function RecentTasksList({
  items = [],
}: {
  items?: string[]
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="px-2 text-micro uppercase tracking-wider text-fg-faint">
        Recent Tasks
      </span>
      {items.length === 0 ? (
        <span className="px-2 text-control text-fg-faint">No recent tasks</span>
      ) : (
        <div className="slim-scrollbar max-h-[calc(4*1.75rem)] overflow-y-auto">
          {items.map((item, idx) => (
            <div
              key={`${item}-${idx}`}
              className="truncate px-2 py-1 text-control text-fg-subtle"
            >
              {item}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
