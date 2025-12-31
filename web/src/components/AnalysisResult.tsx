import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { AnalysisResult as AnalysisResultType } from '../types'
import './AnalysisResult.css'

interface AnalysisResultProps {
  result: AnalysisResultType
}

const AnalysisResult: React.FC<AnalysisResultProps> = ({ result }) => {
  const [showThoughtTrace, setShowThoughtTrace] = useState(false)

  return (
    <div className="analysis-result">
      <div className="result-header">
        <h2>分析结果</h2>
        <div className="confidence-badge">
          置信度: {(result.confidence * 100).toFixed(0)}%
        </div>
      </div>

      <div className="result-section">
        <h3>根本原因</h3>
        <div className="result-content">
          <ReactMarkdown>{result.root_cause}</ReactMarkdown>
        </div>
      </div>

      <div className="result-section">
        <h3>处理建议</h3>
        <ul className="suggestions-list">
          {result.suggestions.map((suggestion, index) => (
            <li key={index}>
              <ReactMarkdown>{suggestion}</ReactMarkdown>
            </li>
          ))}
        </ul>
      </div>

      {result.related_code && result.related_code.length > 0 && (
        <div className="result-section">
          <h3>相关代码</h3>
          {result.related_code.map((code, index) => (
            <div key={index} className="code-reference">
              <div className="code-header">
                <strong>{code.file}</strong>
                {code.lines && (
                  <span className="code-lines">行 {code.lines[0]}-{code.lines[1]}</span>
                )}
              </div>
              {code.description && (
                <p className="code-description">{code.description}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {result.related_logs && result.related_logs.length > 0 && (
        <div className="result-section">
          <h3>相关日志</h3>
          {result.related_logs.map((log, index) => (
            <div key={index} className="log-reference">
              <div className="log-header">
                <strong>{log.timestamp}</strong>
              </div>
              <pre className="log-content">{log.content}</pre>
              {log.description && (
                <p className="log-description">{log.description}</p>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="result-section">
        <button
          className="toggle-button"
          onClick={() => setShowThoughtTrace(!showThoughtTrace)}
        >
          {showThoughtTrace ? '隐藏' : '显示'} Agent 思考过程
        </button>
        {showThoughtTrace && (
          <div className="thought-trace">
            <p className="thought-trace-note">
              思考过程将在这里显示（需要从 API 返回 intermediate_steps）
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export default AnalysisResult

