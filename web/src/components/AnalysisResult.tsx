import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Copy, Check, FileCode, Clock, ChevronDown, ChevronRight, Lightbulb, AlertTriangle, FileText, Gauge } from 'lucide-react'
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { AnalysisResult as AnalysisResultType } from '../types'
import './AnalysisResult.css'

interface AnalysisResultProps {
  result: AnalysisResultType
}

const AnalysisResult: React.FC<AnalysisResultProps> = ({ result }) => {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)
  const [expandedSuggestions, setExpandedSuggestions] = useState<Set<number>>(new Set([0]))

  const copyToClipboard = async (text: string, index: number) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedIndex(index)
      setTimeout(() => setCopiedIndex(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const toggleSuggestion = (index: number) => {
    setExpandedSuggestions(prev => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

  const getConfidenceLevel = (confidence: number) => {
    if (confidence >= 0.8) return { label: '高', color: 'success' }
    if (confidence >= 0.5) return { label: '中', color: 'warning' }
    return { label: '低', color: 'error' }
  }

  const confidenceInfo = getConfidenceLevel(result.confidence)

  return (
    <div className="analysis-result">
      {/* Header */}
      <div className="result-header">
        <div className="header-left">
          <div className="result-title">
            <AlertTriangle size={18} className="title-icon" />
            <span>分析结果</span>
          </div>
        </div>
        <div className="header-right">
          <div className={`confidence-indicator confidence-${confidenceInfo.color}`}>
            <Gauge size={14} />
            <span>置信度: {(result.confidence * 100).toFixed(0)}%</span>
            <Badge variant="outline" className={`confidence-badge ${confidenceInfo.color}`}>
              {confidenceInfo.label}
            </Badge>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="root-cause" className="result-tabs">
        <TabsList className="tabs-list">
          <TabsTrigger value="root-cause" className="tab-trigger">
            <AlertTriangle size={14} />
            根因分析
          </TabsTrigger>
          <TabsTrigger value="suggestions" className="tab-trigger">
            <Lightbulb size={14} />
            修复建议
            {result.suggestions.length > 0 && (
              <span className="tab-count">{result.suggestions.length}</span>
            )}
          </TabsTrigger>
          <TabsTrigger value="details" className="tab-trigger">
            <FileCode size={14} />
            相关详情
          </TabsTrigger>
        </TabsList>

        {/* Root Cause Tab */}
        <TabsContent value="root-cause" className="tab-content">
          <div className="root-cause-content">
            <div className="markdown-content">
              <ReactMarkdown>{result.root_cause}</ReactMarkdown>
            </div>
          </div>
        </TabsContent>

        {/* Suggestions Tab */}
        <TabsContent value="suggestions" className="tab-content">
          <div className="suggestions-list">
            {result.suggestions.map((suggestion, index) => (
              <div 
                key={index} 
                className={`suggestion-card ${expandedSuggestions.has(index) ? 'expanded' : ''}`}
              >
                <button 
                  className="suggestion-header"
                  onClick={() => toggleSuggestion(index)}
                >
                  <div className="suggestion-title">
                    <span className="suggestion-number">{index + 1}</span>
                    <span className="suggestion-preview">
                      {suggestion.split('\n')[0].replace(/^#+\s*/, '').slice(0, 60)}
                      {suggestion.length > 60 ? '...' : ''}
                    </span>
                  </div>
                  <div className="suggestion-actions">
                    <button
                      className="copy-btn"
                      onClick={(e) => {
                        e.stopPropagation()
                        copyToClipboard(suggestion, index)
                      }}
                      title="复制"
                    >
                      {copiedIndex === index ? (
                        <Check size={14} className="copied" />
                      ) : (
                        <Copy size={14} />
                      )}
                    </button>
                    {expandedSuggestions.has(index) ? (
                      <ChevronDown size={16} />
                    ) : (
                      <ChevronRight size={16} />
                    )}
                  </div>
                </button>
                {expandedSuggestions.has(index) && (
                  <div className="suggestion-body">
                    <div className="markdown-content">
                      <ReactMarkdown>{suggestion}</ReactMarkdown>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </TabsContent>

        {/* Details Tab */}
        <TabsContent value="details" className="tab-content">
          <div className="details-content">
            {/* Related Code */}
            {result.related_code && result.related_code.length > 0 && (
              <div className="detail-section">
                <h4 className="section-title">
                  <FileCode size={16} />
                  相关代码
                </h4>
                <div className="code-list">
                  {result.related_code.map((code, index) => (
                    <div key={index} className="code-item">
                      <div className="code-header">
                        <div className="code-file">
                          <FileCode size={14} />
                          <code>{code.file}</code>
                        </div>
                        {code.lines && (
                          <Badge variant="outline" className="code-lines">
                            L{code.lines[0]}-{code.lines[1]}
                          </Badge>
                        )}
                      </div>
                      {code.description && (
                        <p className="code-description">{code.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Related Logs */}
            {result.related_logs && result.related_logs.length > 0 && (
              <div className="detail-section">
                <h4 className="section-title">
                  <FileText size={16} />
                  相关日志
                </h4>
                <div className="log-list">
                  {result.related_logs.map((log, index) => (
                    <div key={index} className="log-item">
                      <div className="log-header">
                        <Badge variant="outline" className="log-timestamp">
                          <Clock size={12} />
                          {log.timestamp}
                        </Badge>
                      </div>
                      <pre className="log-content">{log.content}</pre>
                      {log.description && (
                        <p className="log-description">{log.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Empty State */}
            {(!result.related_code || result.related_code.length === 0) && 
             (!result.related_logs || result.related_logs.length === 0) && (
              <div className="empty-details">
                <FileCode size={32} />
                <p>没有相关的代码或日志信息</p>
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default AnalysisResult
