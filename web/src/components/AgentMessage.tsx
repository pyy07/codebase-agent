import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { 
  Brain, 
  ListChecks, 
  Wrench, 
  CheckCircle2, 
  XCircle, 
  Loader2, 
  Circle,
  ChevronDown,
  ChevronRight,
  Copy,
  Check,
  AlertTriangle,
  Gauge,
  Lightbulb,
  FileCode,
  Clock
} from 'lucide-react'
import { ChatMessage, MessageContent, PlanStep, AnalysisResult, UserInputRequestData, UserReplyData } from '../types'
import { Badge } from '@/components/ui/badge'
import UnifiedStepsBlock from './UnifiedStepsBlock'
import UserInputRequest from './UserInputRequest'
import UserReply from './UserReply'
import './AgentMessage.css'

interface AgentMessageProps {
  message: ChatMessage
  onSubmitUserReply?: (requestId: string, reply: string) => Promise<void>
}

export default function AgentMessage({ message, onSubmitUserReply }: AgentMessageProps) {
  return (
    <div className="agent-message">
      {message.content.map((content, index) => (
        <ContentBlock 
          key={index} 
          content={content} 
          isStreaming={message.isStreaming}
          allContents={message.content}
          onSubmitUserReply={onSubmitUserReply}
        />
      ))}
    </div>
  )
}

function ContentBlock({ content, isStreaming, allContents, onSubmitUserReply }: { content: MessageContent; isStreaming?: boolean; allContents?: MessageContent[]; onSubmitUserReply?: (requestId: string, reply: string) => Promise<void> }) {
  switch (content.type) {
    case 'thinking':
      return <ThinkingBlock data={content.data} isStreaming={isStreaming} />
    case 'progress':
      return <ProgressBlock data={content.data} />
    case 'plan':
      // 尝试查找对应的 step_execution 和 decision_reasoning，如果存在则合并显示
      const stepExecution = allContents?.find(c => c.type === 'step_execution')
      // 收集所有推理原因（可能有多个，每个关联到不同的步骤）
      const allReasonings = allContents
        ?.filter(c => c.type === 'decision_reasoning')
        .map(c => c.data) || []
      // 收集用户输入请求和回复
      const userInputRequests = allContents
        ?.filter(c => c.type === 'user_input_request')
        .map(c => c.data) || []
      const userReplies = allContents
        ?.filter(c => c.type === 'user_reply')
        .map(c => c.data) || []
      if (stepExecution && Array.isArray(stepExecution.data)) {
        return <UnifiedStepsBlock 
          planSteps={content.data} 
          executionSteps={stepExecution.data}
          decisionReasonings={allReasonings}
          userInputRequests={userInputRequests}
          userReplies={userReplies}
          onSubmitUserReply={onSubmitUserReply}
          onSkipUserInput={onSubmitUserReply ? async (requestId: string) => {
            // 跳过用户输入，发送空回复或特殊标记
            if (onSubmitUserReply) {
              await onSubmitUserReply(requestId, '__SKIP__')
            }
          } : undefined}
        />
      }
      // 如果没有 step_execution，仍然显示 PlanBlock（向后兼容）
      return <PlanBlock steps={content.data} />
    case 'decision_reasoning': {
      // 如果已经有 plan，则 decision_reasoning 会被 UnifiedStepsBlock 合并显示，这里不单独显示
      const hasPlanForReasoning = allContents?.some(c => c.type === 'plan')
      if (hasPlanForReasoning) {
        return null // UnifiedStepsBlock 会处理显示
      }
      // 如果没有 plan，单独显示 decision_reasoning
      return <DecisionReasoningBlock reasoning={content.data} />
    }
    case 'step_execution': {
      // 如果已经有 plan，则 step_execution 会被 plan 合并显示，这里不单独显示
      const hasPlan = allContents?.some(c => c.type === 'plan')
      if (hasPlan) {
        return null // plan 会处理显示
      }
      // 如果没有 plan，单独显示 step_execution
      return <StepExecutionBlock steps={content.data} />
    }
    case 'tool_call':
      return <ToolCallBlock data={content.data} />
    case 'result':
      return <ResultBlock result={content.data} />
    case 'error':
      return <ErrorBlock message={content.data} />
    case 'text':
      return <TextBlock text={content.data} />
    case 'user_input_request': {
      // 用户输入请求现在由 UnifiedStepsBlock 处理，这里不单独显示
      // 但如果 UnifiedStepsBlock 不存在，则显示原始组件作为后备
      const hasPlan = allContents?.some(c => c.type === 'plan')
      if (hasPlan) {
        return null // UnifiedStepsBlock 会处理显示
      }
      // 如果没有 plan，显示原始组件
      if (!onSubmitUserReply) {
        console.warn('onSubmitUserReply not provided, cannot handle user input request')
        return null
      }
      return <UserInputRequest request={content.data} onSubmit={onSubmitUserReply} />
    }
    case 'user_reply': {
      // 用户回复现在由 UnifiedStepsBlock 处理，这里不单独显示
      const hasPlanForReply = allContents?.some(c => c.type === 'plan')
      if (hasPlanForReply) {
        return null // UnifiedStepsBlock 会处理显示
      }
      return <UserReply reply={content.data} />
    }
    default:
      return null
  }
}

// Decision Reasoning Block
function DecisionReasoningBlock({ reasoning }: { reasoning: DecisionReasoningData }) {
  return (
    <div className="content-block decision-reasoning-block">
      <div className="block-header">
        <Lightbulb size={16} className="block-icon reasoning" />
        <span>{reasoning.action === 'continue' ? '继续分析原因' : '结束分析原因'}</span>
      </div>
      <div className="block-body">
        <p className="reasoning-text">{reasoning.reasoning}</p>
      </div>
    </div>
  )
}

// Thinking Block
function ThinkingBlock({ data, isStreaming }: { data: string; isStreaming?: boolean }) {
  return (
    <div className="content-block thinking-block">
      <div className="block-header">
        <Brain size={16} className="block-icon thinking" />
        <span>思考中</span>
        {isStreaming && <Loader2 size={14} className="streaming-indicator" />}
      </div>
      <div className="block-body">
        <p className="thinking-text">{data}</p>
      </div>
    </div>
  )
}

// Progress Block
function ProgressBlock({ data }: { data: { message: string; progress: number; step?: string } }) {
  const percentage = Math.round(data.progress * 100)
  
  return (
    <div className="content-block progress-block">
      <div className="block-header">
        <Loader2 size={16} className="block-icon spinning" />
        <span>{data.message}</span>
        <span className="progress-percent">{percentage}%</span>
      </div>
      <div className="progress-bar-wrapper">
        <div className="progress-bar-track">
          <div className="progress-bar-fill" style={{ width: `${percentage}%` }} />
        </div>
      </div>
      {data.step && (
        <div className="progress-step">
          当前: <code>{data.step}</code>
        </div>
      )}
    </div>
  )
}

// Plan Block
function PlanBlock({ steps }: { steps: PlanStep[] }) {
  const [expanded, setExpanded] = useState(true)
  const completedCount = steps.filter(s => s.status === 'completed').length
  
  return (
    <div className="content-block plan-block">
      <button className="block-header clickable" onClick={() => setExpanded(!expanded)}>
        <ListChecks size={16} className="block-icon plan" />
        <span>分析计划</span>
        <Badge variant="outline" className="plan-badge">
          {completedCount}/{steps.length}
        </Badge>
        {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </button>
      {expanded && (
        <div className="block-body">
          <ol className="plan-steps-list">
            {steps.map((step, index) => (
              <li key={index} className={`plan-step step-${step.status}`}>
                <div className="step-status-icon">
                  {step.status === 'completed' && <CheckCircle2 size={16} className="completed" />}
                  {step.status === 'running' && <Loader2 size={16} className="running" />}
                  {step.status === 'failed' && <XCircle size={16} className="failed" />}
                  {step.status === 'pending' && <Circle size={16} className="pending" />}
                </div>
                <div className="step-info">
                  <span className="step-action">{step.action}</span>
                  {step.target && <span className="step-target">→ {step.target}</span>}
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  )
}

// Step Execution Block - 显示实时步骤执行状态
function StepExecutionBlock({ steps }: { steps: any[] }) {
  const [expanded, setExpanded] = useState(true)
  const [expandedResults, setExpandedResults] = useState<Set<number>>(new Set())
  const completedCount = steps.filter(s => s.status === 'completed').length
  const runningStep = steps.find(s => s.status === 'running')
  
  const toggleResult = (stepNumber: number) => {
    setExpandedResults(prev => {
      const newSet = new Set(prev)
      if (newSet.has(stepNumber)) {
        newSet.delete(stepNumber)
      } else {
        newSet.add(stepNumber)
      }
      return newSet
    })
  }
  
  return (
    <div className="content-block step-execution-block">
      <button className="block-header clickable" onClick={() => setExpanded(!expanded)}>
        <Wrench size={16} className="block-icon tool" />
        <span>执行步骤</span>
        {runningStep && (
          <Badge variant="outline" className="running-badge">
            正在执行: 步骤 {runningStep.step}
          </Badge>
        )}
        <Badge variant="outline" className="progress-badge">
          {completedCount}/{steps.length}
        </Badge>
        {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </button>
      {expanded && (
        <div className="block-body">
          <div className="step-execution-list">
            {steps.map((step, index) => (
              <div key={index} className={`execution-step step-${step.status}`}>
                <div className="execution-step-header">
                  <div className="execution-step-status">
                    {step.status === 'completed' && <CheckCircle2 size={18} className="completed" />}
                    {step.status === 'running' && <Loader2 size={18} className="running spinning" />}
                    {step.status === 'failed' && <XCircle size={18} className="failed" />}
                    {step.status === 'pending' && <Circle size={18} className="pending" />}
                  </div>
                  <div className="execution-step-info">
                    <div className="execution-step-title">
                      <span className="step-number">步骤 {step.step}</span>
                      <span className="step-action">{step.action}</span>
                    </div>
                    {step.target && (
                      <div className="execution-step-target">
                        <code>{step.target}</code>
                      </div>
                    )}
                  </div>
                  <div className="execution-step-badge">
                    <Badge 
                      variant="outline" 
                      className={`status-badge ${step.status}`}
                    >
                      {step.status === 'completed' && '已完成'}
                      {step.status === 'running' && '执行中'}
                      {step.status === 'failed' && '失败'}
                      {step.status === 'pending' && '等待中'}
                    </Badge>
                  </div>
                </div>
                {(step.result || step.error) && (
                  <div className="execution-step-result-container">
                    {step.result && (
                      <div className="execution-step-result">
                        <button 
                          className="result-toggle-button"
                          onClick={() => toggleResult(step.step)}
                        >
                          {expandedResults.has(step.step) ? (
                            <ChevronDown size={14} />
                          ) : (
                            <ChevronRight size={14} />
                          )}
                          <span className="result-label">执行结果</span>
                          {step.result_truncated && (
                            <Badge variant="outline" className="truncated-badge">已截断</Badge>
                          )}
                        </button>
                        {expandedResults.has(step.step) && (
                          <pre className="result-content">{step.result}</pre>
                        )}
                        {!expandedResults.has(step.step) && (
                          <pre className="result-content preview">{step.result.substring(0, 200)}{step.result.length > 200 ? '...' : ''}</pre>
                        )}
                      </div>
                    )}
                    {step.error && (
                      <div className="execution-step-error">
                        <button 
                          className="result-toggle-button"
                          onClick={() => toggleResult(step.step)}
                        >
                          {expandedResults.has(step.step) ? (
                            <ChevronDown size={14} />
                          ) : (
                            <ChevronRight size={14} />
                          )}
                          <AlertTriangle size={14} />
                          <span className="result-label">错误信息</span>
                        </button>
                        {expandedResults.has(step.step) && (
                          <pre className="error-content">{step.error}</pre>
                        )}
                        {!expandedResults.has(step.step) && (
                          <pre className="error-content preview">{step.error.substring(0, 200)}{step.error.length > 200 ? '...' : ''}</pre>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// Tool Call Block
function ToolCallBlock({ data }: { data: any }) {
  const [expanded, setExpanded] = useState(false)
  
  return (
    <div className="content-block tool-block">
      <button className="block-header clickable" onClick={() => setExpanded(!expanded)}>
        <Wrench size={16} className="block-icon tool" />
        <span>调用工具: {data.tool}</span>
        <Badge variant="outline" className={`tool-status ${data.status}`}>
          {data.status === 'completed' ? '完成' : data.status === 'running' ? '执行中' : '等待'}
        </Badge>
        {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </button>
      {expanded && (
        <div className="block-body">
          <div className="tool-detail">
            <span className="tool-label">输入:</span>
            <pre className="tool-content">{data.input}</pre>
          </div>
          {data.output && (
            <div className="tool-detail">
              <span className="tool-label">输出:</span>
              <pre className="tool-content">{data.output}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// Result Block
function ResultBlock({ result: rawResult }: { result: any }) {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['root-cause']))
  const [showRaw, setShowRaw] = useState(false)

  // 解析结果数据，支持多种格式
  const parseResult = (data: any): AnalysisResult | null => {
    if (!data) return null
    
    // 辅助函数：尝试从字符串中提取 JSON
    const extractJson = (str: string): any => {
      if (!str || typeof str !== 'string') return null
      
      // 尝试直接解析
      try {
        return JSON.parse(str)
      } catch {
        // 继续尝试其他方式
      }
      
      // 尝试从 ```json ``` 代码块中提取（使用贪婪匹配）
      const jsonCodeBlockMatch = str.match(/```json\s*([\s\S]+)\s*```/)
      if (jsonCodeBlockMatch) {
        const jsonContent = jsonCodeBlockMatch[1].trim()
        try {
          return JSON.parse(jsonContent)
        } catch {
          // JSON 可能格式不对，尝试提取 {} 部分
          const firstBrace = jsonContent.indexOf('{')
          const lastBrace = jsonContent.lastIndexOf('}')
          if (firstBrace !== -1 && lastBrace > firstBrace) {
            try {
              return JSON.parse(jsonContent.substring(firstBrace, lastBrace + 1))
            } catch {}
          }
        }
      }
      
      // 尝试从 ``` ``` 代码块中提取
      const codeBlockMatch = str.match(/```\s*([\s\S]+)\s*```/)
      if (codeBlockMatch) {
        const content = codeBlockMatch[1].trim()
        try {
          return JSON.parse(content)
        } catch {}
      }
      
      // 尝试找到 { 和 } 之间的内容
      const firstBrace = str.indexOf('{')
      const lastBrace = str.lastIndexOf('}')
      if (firstBrace !== -1 && lastBrace > firstBrace) {
        try {
          return JSON.parse(str.substring(firstBrace, lastBrace + 1))
        } catch {}
      }
      
      return null
    }
    
    // 如果是字符串，尝试解析JSON
    if (typeof data === 'string') {
      const parsed = extractJson(data)
      if (parsed) {
        data = parsed
      } else {
        // 如果解析失败，可能是纯文本，作为 root_cause 返回
        return {
          root_cause: data,
          suggestions: [],
          confidence: 0.5
        }
      }
    }
    
    // 检查是否有嵌套的 result 字段
    if (data.result && typeof data.result === 'object') {
      data = data.result
    }
    
    // 如果 root_cause 看起来像包含 JSON 代码块或嵌套 JSON
    if (typeof data.root_cause === 'string') {
      const rootCause = data.root_cause.trim()
      console.log('[parseResult] Checking root_cause:', rootCause.substring(0, 100))
      
      // 检查是否以 ```json 开头（说明是 LLM 返回的代码块格式）
      if (rootCause.startsWith('```json') || rootCause.startsWith('```')) {
        console.log('[parseResult] root_cause starts with code block, extracting...')
        // 直接提取代码块内容
        let content = rootCause
        // 移除开头的 ```json 或 ```
        content = content.replace(/^```json\s*\n?/, '').replace(/^```\s*\n?/, '')
        // 移除结尾的 ```
        content = content.replace(/\n?```\s*$/, '')
        console.log('[parseResult] Extracted content:', content.substring(0, 100))
        
        try {
          const parsed = JSON.parse(content)
          if (parsed && parsed.root_cause !== undefined) {
            console.log('[parseResult] Successfully parsed nested JSON:', parsed.root_cause?.substring(0, 50))
            data = parsed
          }
        } catch (e) {
          console.log('[parseResult] Failed to parse extracted content:', e)
        }
      } else if (rootCause.includes('"root_cause"')) {
        // 可能是直接嵌套的 JSON
        const parsed = extractJson(rootCause)
        if (parsed && (parsed.root_cause !== undefined || parsed.suggestions)) {
          console.log('[parseResult] Extracted nested JSON from root_cause')
          data = parsed
        }
      }
    }
    
    // 验证必要字段
    if (typeof data.root_cause === 'string' || Array.isArray(data.suggestions)) {
      const result = {
        root_cause: data.root_cause || '',
        suggestions: Array.isArray(data.suggestions) ? data.suggestions : [],
        confidence: typeof data.confidence === 'number' ? data.confidence : 0.5,
        related_code: data.related_code,
        related_logs: data.related_logs,
        related_data: data.related_data
      }
      console.log('[parseResult] Final parsed result:', result)
      return result
    }
    
    return null
  }

  const result = parseResult(rawResult)

  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev)
      if (next.has(section)) {
        next.delete(section)
      } else {
        next.add(section)
      }
      return next
    })
  }

  const copyToClipboard = async (text: string, index: number) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedIndex(index)
      setTimeout(() => setCopiedIndex(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  // 无法解析时显示原始数据
  if (!result) {
    return (
      <div className="content-block result-block">
        <div className="result-header">
          <div className="result-title">
            <AlertTriangle size={18} className="result-icon" />
            <span>分析结果</span>
          </div>
        </div>
        <div className="section-content">
          <pre className="raw-result">{JSON.stringify(rawResult, null, 2)}</pre>
        </div>
      </div>
    )
  }

  const confidenceLevel = result.confidence >= 0.8 ? 'high' : result.confidence >= 0.5 ? 'medium' : 'low'

  return (
    <div className="content-block result-block">
      {/* Header */}
      <div className="result-header">
        <div className="result-title">
          <AlertTriangle size={18} className="result-icon" />
          <span>分析结果</span>
        </div>
        <div className="confidence">
          <Gauge size={14} />
          <span>置信度: {(result.confidence * 100).toFixed(0)}%</span>
          <Badge variant="outline" className={`confidence-badge ${confidenceLevel}`}>
            {confidenceLevel === 'high' ? '高' : confidenceLevel === 'medium' ? '中' : '低'}
          </Badge>
        </div>
      </div>

      {/* Root Cause Section */}
      <div className="result-section">
        <button 
          className="section-header" 
          onClick={() => toggleSection('root-cause')}
        >
          <AlertTriangle size={16} className="section-icon" />
          <span>根因分析</span>
          {expandedSections.has('root-cause') ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </button>
        {expandedSections.has('root-cause') && (
          <div className="section-content markdown-content">
            <ReactMarkdown>{result.root_cause}</ReactMarkdown>
          </div>
        )}
      </div>

      {/* Suggestions Section */}
      {result.suggestions && result.suggestions.length > 0 && (
        <div className="result-section">
          <button 
            className="section-header" 
            onClick={() => toggleSection('suggestions')}
          >
            <Lightbulb size={16} className="section-icon suggestions" />
            <span>修复建议</span>
            <Badge variant="outline">{result.suggestions.length}</Badge>
            {expandedSections.has('suggestions') ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </button>
          {expandedSections.has('suggestions') && (
            <div className="section-content suggestions-list">
              {result.suggestions.map((suggestion, index) => (
                <div key={index} className="suggestion-item">
                  <div className="suggestion-header">
                    <span className="suggestion-number">{index + 1}</span>
                    <button 
                      className="copy-btn"
                      onClick={() => copyToClipboard(suggestion, index)}
                    >
                      {copiedIndex === index ? <Check size={14} /> : <Copy size={14} />}
                    </button>
                  </div>
                  <div className="markdown-content">
                    <ReactMarkdown>{suggestion}</ReactMarkdown>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Related Code Section */}
      {result.related_code && result.related_code.length > 0 && (
        <div className="result-section">
          <button 
            className="section-header" 
            onClick={() => toggleSection('code')}
          >
            <FileCode size={16} className="section-icon code" />
            <span>相关代码</span>
            <Badge variant="outline">{result.related_code.length}</Badge>
            {expandedSections.has('code') ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </button>
          {expandedSections.has('code') && (
            <div className="section-content code-list">
              {result.related_code.map((code, index) => (
                <div key={index} className="code-item">
                  <div className="code-header">
                    <code className="code-path">{code.file}</code>
                    {code.lines && (
                      <Badge variant="outline">L{code.lines[0]}-{code.lines[1]}</Badge>
                    )}
                  </div>
                  {code.description && <p className="code-desc">{code.description}</p>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Related Logs Section */}
      {result.related_logs && result.related_logs.length > 0 && (
        <div className="result-section">
          <button 
            className="section-header" 
            onClick={() => toggleSection('logs')}
          >
            <Clock size={16} className="section-icon logs" />
            <span>相关日志</span>
            <Badge variant="outline">{result.related_logs.length}</Badge>
            {expandedSections.has('logs') ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </button>
          {expandedSections.has('logs') && (
            <div className="section-content log-list">
              {result.related_logs.map((log, index) => (
                <div key={index} className="log-item">
                  <Badge variant="outline" className="log-time">
                    <Clock size={12} /> {log.timestamp}
                  </Badge>
                  <pre className="log-content">{log.content}</pre>
                  {log.description && <p className="log-desc">{log.description}</p>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Raw Data Toggle (for debugging) */}
      <div className="result-section raw-section">
        <button 
          className="section-header raw-toggle" 
          onClick={() => setShowRaw(!showRaw)}
        >
          <FileCode size={16} className="section-icon" />
          <span>原始数据</span>
          {showRaw ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </button>
        {showRaw && (
          <div className="section-content">
            <pre className="raw-result">{JSON.stringify(rawResult, null, 2)}</pre>
          </div>
        )}
      </div>
    </div>
  )
}

// Error Block
function ErrorBlock({ message }: { message: string }) {
  return (
    <div className="content-block error-block">
      <div className="block-header error">
        <XCircle size={16} className="block-icon error" />
        <span>错误</span>
      </div>
      <div className="block-body">
        <p className="error-text">{message}</p>
      </div>
    </div>
  )
}

// Text Block
function TextBlock({ text }: { text: string }) {
  return (
    <div className="content-block text-block">
      <div className="markdown-content">
        <ReactMarkdown>{text}</ReactMarkdown>
      </div>
    </div>
  )
}

