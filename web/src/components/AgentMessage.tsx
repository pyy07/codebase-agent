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
import { ChatMessage, MessageContent, PlanStep, AnalysisResult } from '../types'
import { Badge } from '@/components/ui/badge'
import './AgentMessage.css'

interface AgentMessageProps {
  message: ChatMessage
}

export default function AgentMessage({ message }: AgentMessageProps) {
  return (
    <div className="agent-message">
      {message.content.map((content, index) => (
        <ContentBlock key={index} content={content} isStreaming={message.isStreaming} />
      ))}
    </div>
  )
}

function ContentBlock({ content, isStreaming }: { content: MessageContent; isStreaming?: boolean }) {
  switch (content.type) {
    case 'thinking':
      return <ThinkingBlock data={content.data} isStreaming={isStreaming} />
    case 'progress':
      return <ProgressBlock data={content.data} />
    case 'plan':
      return <PlanBlock steps={content.data} />
    case 'tool_call':
      return <ToolCallBlock data={content.data} />
    case 'result':
      return <ResultBlock result={content.data} />
    case 'error':
      return <ErrorBlock message={content.data} />
    case 'text':
      return <TextBlock text={content.data} />
    default:
      return null
  }
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
function ResultBlock({ result }: { result: AnalysisResult }) {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['root-cause']))

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
      {result.suggestions.length > 0 && (
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

