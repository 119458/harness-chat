import { ArrowUp } from 'lucide-react'

// Square icon button that submits the composer input. Disabled state is driven
// entirely by the parent (e.g. empty input) - this component only reflects it.
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
        'h-7 w-7 rounded-md flex items-center justify-center transition-colors',
        disabled
          ? 'bg-zinc-800 text-zinc-600 cursor-not-allowed'
          : 'bg-zinc-100 text-canvas hover:bg-white font-semibold',
      ].join(' ')}
      aria-label="Send"
    >
      <ArrowUp className="h-4 w-4" strokeWidth={2} />
    </button>
  )
}
