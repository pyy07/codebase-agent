export interface ContextFile {
  type: 'code' | 'log' | 'image'
  path: string
  content: string
  line_start?: number
  line_end?: number
  preview?: string  // Base64 preview for images
}

export interface AnalysisResult {
  root_cause: string
  suggestions: string[]
  confidence: number
  related_code?: Array<{
    file: string
    lines: number[]
    description: string
  }>
  related_logs?: Array<{
    timestamp: string
    content: string
    description: string
  }>
  related_data?: any
}

export interface AnalyzeRequest {
  input: string
  context_files?: ContextFile[]
}

export interface PlanStep {
  step: number
  action: string
  target: string
  status: "pending" | "running" | "completed" | "failed"
}

// Chat message types for AI conversation interface
export type MessageRole = 'user' | 'assistant' | 'system'

export type MessageContentType = 
  | 'text'           // Plain text
  | 'thinking'       // AI thinking process
  | 'plan'           // Analysis plan
  | 'tool_call'      // Tool being called
  | 'tool_result'    // Tool execution result
  | 'progress'       // Progress update
  | 'result'         // Final analysis result
  | 'error'          // Error message

export interface MessageContent {
  type: MessageContentType
  data: any
}

export interface ChatMessage {
  id: string
  role: MessageRole
  content: MessageContent[]
  timestamp: Date
  isStreaming?: boolean
}

export interface ToolCallData {
  tool: string
  input: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  output?: string
  duration?: number
}

export interface AttachedFile {
  id: string
  name: string
  type: 'code' | 'log' | 'image'
  content: string
  preview?: string  // For images
  size: number
}
