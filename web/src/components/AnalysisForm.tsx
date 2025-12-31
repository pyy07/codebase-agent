import React, { useState } from 'react'
import './AnalysisForm.css'

interface AnalysisFormProps {
  onSubmit: (input: string, contextFiles: File[], streaming?: boolean) => void
  loading: boolean
}

const AnalysisForm: React.FC<AnalysisFormProps> = ({ onSubmit, loading }) => {
  const [input, setInput] = useState('')
  const [contextFiles, setContextFiles] = useState<File[]>([])
  const [apiKey, setApiKey] = useState(localStorage.getItem('apiKey') || '')
  const [useStreaming, setUseStreaming] = useState(true)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmedInput = input.trim()
    if (!trimmedInput) {
      alert('请输入问题描述')
      return
    }
    onSubmit(trimmedInput, contextFiles, useStreaming)
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setContextFiles(Array.from(e.target.files))
    }
  }

  const handleApiKeyChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const key = e.target.value
    setApiKey(key)
    if (key) {
      localStorage.setItem('apiKey', key)
    } else {
      localStorage.removeItem('apiKey')
    }
  }

  return (
    <form className="analysis-form" onSubmit={handleSubmit}>
      <div className="form-group">
        <label htmlFor="api-key">API Key（可选）</label>
        <input
          id="api-key"
          type="password"
          value={apiKey}
          onChange={handleApiKeyChange}
          placeholder="输入 API Key（如果配置了认证）"
        />
      </div>

      <div className="form-group">
        <label htmlFor="input">问题描述或错误日志</label>
        <textarea
          id="input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="请输入问题描述、错误日志或其他需要分析的内容..."
          rows={10}
          required
        />
      </div>

      <div className="form-group">
        <label htmlFor="context-files">上下文文件（可选）</label>
        <input
          id="context-files"
          type="file"
          multiple
          onChange={handleFileChange}
          accept=".py,.js,.ts,.java,.go,.rs,.log,.txt"
        />
        <small>支持代码文件（.py, .js, .ts, .java, .go, .rs）和日志文件（.log, .txt）</small>
        {contextFiles.length > 0 && (
          <div className="file-list">
            <strong>已选择文件：</strong>
            <ul>
              {contextFiles.map((file, index) => (
                <li key={index}>{file.name}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="form-group">
        <label>
          <input
            type="checkbox"
            checked={useStreaming}
            onChange={(e) => setUseStreaming(e.target.checked)}
          />
          <span style={{ marginLeft: '0.5rem' }}>使用流式接口（实时显示进度）</span>
        </label>
      </div>

      <button type="submit" disabled={loading} className="submit-button">
        {loading ? '分析中...' : '开始分析'}
      </button>
    </form>
  )
}

export default AnalysisForm

