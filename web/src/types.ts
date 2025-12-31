export interface ContextFile {
  type: 'code' | 'log'
  path: string
  content: string
  line_start?: number
  line_end?: number
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

