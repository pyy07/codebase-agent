import { useState, useRef, useEffect } from 'react'
import { Send, Upload, X, FileCode, FileText, Settings2, Zap } from 'lucide-react'
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
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
  const [showSettings, setShowSettings] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  // 如果 Electron 提供了 API key，自动同步到 localStorage（用于显示）
  useEffect(() => {
    const electronAPI = (window as any).electronAPI
    if (electronAPI?.getApiKey) {
      electronAPI.getApiKey().then((envApiKey: string | null) => {
        if (envApiKey && !localStorage.getItem('apiKey')) {
          localStorage.setItem('apiKey', envApiKey)
          setApiKey(envApiKey)
        }
      }).catch((error: any) => {
        console.warn('[AnalysisForm] Failed to get API key from Electron:', error)
      })
    }
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmedInput = input.trim()
    if (!trimmedInput) {
      return
    }
    onSubmit(trimmedInput, contextFiles, useStreaming)
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files)
      setContextFiles(prev => [...prev, ...newFiles])
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const droppedFiles = Array.from(e.dataTransfer.files)
    setContextFiles(prev => [...prev, ...droppedFiles])
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const removeFile = (index: number) => {
    setContextFiles(prev => prev.filter((_, i) => i !== index))
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

  const getFileIcon = (filename: string) => {
    if (filename.endsWith('.log') || filename.endsWith('.txt')) {
      return <FileText size={14} />
    }
    return <FileCode size={14} />
  }

  const quickTemplates = [
    { label: '错误分析', prompt: '请帮我分析以下错误：\n\n' },
    { label: '代码审查', prompt: '请帮我审查以下代码的问题：\n\n' },
    { label: '性能优化', prompt: '请帮我分析代码的性能问题：\n\n' },
  ]

  return (
    <div className="analysis-form">
      {/* Header */}
      <div className="form-header">
        <div className="form-title">
          <Zap size={18} className="title-icon" />
          <span>新建分析</span>
        </div>
        <button 
          type="button"
          className="settings-toggle"
          onClick={() => setShowSettings(!showSettings)}
          aria-label="Settings"
        >
          <Settings2 size={18} />
        </button>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="settings-panel">
          <div className="setting-item">
            <Label htmlFor="api-key" className="setting-label">API Key</Label>
            <Input
              id="api-key"
              type="password"
              placeholder="输入 API Key（可选）"
              value={apiKey}
              onChange={handleApiKeyChange}
              className="setting-input"
            />
          </div>
          <div className="setting-item horizontal">
            <div className="setting-info">
              <Label htmlFor="streaming" className="setting-label">实时流式输出</Label>
              <span className="setting-description">显示分析进度和中间结果</span>
            </div>
            <Switch
              id="streaming"
              checked={useStreaming}
              onCheckedChange={setUseStreaming}
            />
          </div>
        </div>
      )}

      {/* Quick Templates */}
      <div className="quick-templates">
        {quickTemplates.map((template, index) => (
          <button
            key={index}
            type="button"
            className="template-btn"
            onClick={() => setInput(template.prompt)}
          >
            {template.label}
          </button>
        ))}
      </div>

      {/* Input Area */}
      <form onSubmit={handleSubmit}>
        <div className="input-container">
          <Textarea
            placeholder="描述问题或粘贴错误日志..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="main-input"
            rows={8}
          />
          <div className="input-footer">
            <span className="char-count">{input.length} 字符</span>
          </div>
        </div>

        {/* File Upload Area */}
        <div 
          className={`file-drop-zone ${isDragging ? 'dragging' : ''} ${contextFiles.length > 0 ? 'has-files' : ''}`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileChange}
            accept=".py,.js,.ts,.tsx,.java,.go,.rs,.log,.txt,.json,.yaml,.yml,.md"
            className="file-input-hidden"
          />
          
          {contextFiles.length === 0 ? (
            <div className="drop-placeholder">
              <Upload size={20} />
              <span>拖拽文件或点击上传</span>
              <span className="file-types">支持代码、日志、配置文件</span>
            </div>
          ) : (
            <div className="file-list" onClick={(e) => e.stopPropagation()}>
              {contextFiles.map((file, index) => (
                <div key={index} className="file-chip">
                  {getFileIcon(file.name)}
                  <span className="file-name">{file.name}</span>
                  <button
                    type="button"
                    className="file-remove"
                    onClick={(e) => {
                      e.stopPropagation()
                      removeFile(index)
                    }}
                    aria-label="Remove file"
                  >
                    <X size={14} />
                  </button>
                </div>
              ))}
              <button
                type="button"
                className="add-more-btn"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload size={14} />
                添加更多
              </button>
            </div>
          )}
        </div>

        {/* Submit Button */}
        <Button 
          type="submit" 
          disabled={loading || !input.trim()} 
          className="submit-button"
          size="lg"
        >
          {loading ? (
            <>
              <span className="spinner" />
              <span>分析中...</span>
            </>
          ) : (
            <>
              <Send size={18} />
              <span>开始分析</span>
            </>
          )}
        </Button>
      </form>
    </div>
  )
}

export default AnalysisForm
