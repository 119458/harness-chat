import { ArrowUp } from 'lucide-react'

// Square icon button that submits the composer input. Disabled state is driven
// entirely by the parent (e.g. empty input) - this component only reflects it.
// Theme-aware via semantic tokens: active = bg-fg / text-canvas (high contrast
// in both themes), disabled = bg-surface / text-fg-faint.
export default function SendButton({
  onSend,
  disabled,
}: {
  onSend: () => void
  disabled: boolean
}) {
  return (
    <button
      type="button"
      onClick={onSend}
      disabled={disabled}
      className={[
        'flex h-7 w-7 items-center justify-center rounded-md transition-colors',
        disabled
          ? 'bg-surface text-fg-faint cursor-not-allowed'
          : 'bg-fg text-canvas font-semibold hover:opacity-90',
      ].join(' ')}
      aria-label="Send"
    >
      <ArrowUp className="h-4 w-4" strokeWidth={2} />
    </button>
  )
}
