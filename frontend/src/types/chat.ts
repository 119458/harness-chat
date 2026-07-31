// Client-side data model (data-model.md E3/E4/E6). No enums (erasableSyntaxOnly).

export type Status = 'IDLE' | 'RUNNING' | 'ERROR'
export type TurnStatus = 'streaming' | 'done' | 'error' | 'stopped'

export interface ThinkingBlockData {
  block_id: string
  kind: 'thinking'
  collapsed: boolean
  content: string
}

export interface ToolBlockData {
  block_id: string
  kind: 'tool'
  collapsed: boolean
  tool: string
  input: Record<string, unknown>
  result: string | null
}

export interface AnswerBlockData {
  block_id: string
  kind: 'answer'
  content: string
}

export interface ErrorBlockData {
  block_id: string
  kind: 'error'
  content: string
  // 002-loop-robustness US3: exit reason for semantic copy in ErrorBlock
  // (contracts/api-contract-extension.md). Absent = unclassified (001 behavior).
  reason?: string
}

export type Block = ThinkingBlockData | ToolBlockData | AnswerBlockData | ErrorBlockData

export interface Turn {
  turn_id: string
  user_message: string
  blocks: Block[]
  status: TurnStatus
  started_at: number
  ended_at: number | null
}
