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
  | 'step_execution' // Step execution details
  | 'decision_reasoning' // Decision reasoning
  | 'user_input_request' // Agent requests user input
  | 'user_reply'     // User reply to agent's request
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

export interface StepExecutionData {
  step: number
  action: string
  target?: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  result?: string
  result_truncated?: boolean
  error?: string
  timestamp?: Date
}

export interface DecisionReasoningData {
  reasoning: string
  action: 'continue' | 'synthesize'
  after_step?: number  // 在哪个步骤之后显示推理原因
  before_steps?: number[]  // 在哪些新步骤之前显示推理原因
  timestamp?: Date
}

export interface UserInputRequestData {
  request_id: string
  question: string
  context?: string
  timestamp?: Date
}

export interface UserReplyData {
  request_id: string
  reply: string
  timestamp?: Date
}

export interface AttachedFile {
  id: string
  name: string
  type: 'code' | 'log' | 'image'
  content: string
  preview?: string  // For images
  size: number
}

// Electron API 类型定义
export interface ElectronAPI {
  platform: string
  versions: {
    node: string
    chrome: string
    electron: string
  }
  apiBaseURL: string
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI
  }
}
