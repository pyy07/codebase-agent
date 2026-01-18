import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Paperclip, X, Image, FileCode, FileText } from 'lucide-react'
import { AttachedFile } from '../types'
import './ChatInput.css'

interface ChatInputProps {
  onSend: (text: string, files: AttachedFile[]) => void
  disabled?: boolean
}

function generateId() {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [text, setText] = useState('')
  const [files, setFiles] = useState<AttachedFile[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
    }
  }, [text])

  // Handle paste event for images
  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    const items = e.clipboardData.items
    
    for (const item of items) {
      if (item.type.startsWith('image/')) {
        e.preventDefault()
        const file = item.getAsFile()
        if (file) {
          processImageFile(file)
        }
        break
      }
    }
  }, [])

  // Process image file to base64
  const processImageFile = (file: File) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const base64 = e.target?.result as string
      const newFile: AttachedFile = {
        id: generateId(),
        name: file.name || `pasted-image-${Date.now()}.png`,
        type: 'image',
        content: base64,
        preview: base64,
        size: file.size,
      }
      setFiles(prev => [...prev, newFile])
    }
    reader.readAsDataURL(file)
  }

  // Process text/code file
  const processTextFile = (file: File) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const content = e.target?.result as string
      const type = file.name.endsWith('.log') || file.name.endsWith('.txt') ? 'log' : 'code'
      const newFile: AttachedFile = {
        id: generateId(),
        name: file.name,
        type,
        content,
        size: file.size,
      }
      setFiles(prev => [...prev, newFile])
    }
    reader.readAsText(file)
  }

  // Handle file selection
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files
    if (!selectedFiles) return

    Array.from(selectedFiles).forEach(file => {
      if (file.type.startsWith('image/')) {
        processImageFile(file)
      } else {
        processTextFile(file)
      }
    })
    
    // Reset input
    e.target.value = ''
  }

  // Handle drag and drop
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    
    const droppedFiles = e.dataTransfer.files
    Array.from(droppedFiles).forEach(file => {
      if (file.type.startsWith('image/')) {
        processImageFile(file)
      } else {
        processTextFile(file)
      }
    })
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  // Remove attached file
  const removeFile = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id))
  }

  // Handle send
  const handleSend = () => {
    const trimmedText = text.trim()
    if (!trimmedText && files.length === 0) return
    if (disabled) return

    onSend(trimmedText, files)
    setText('')
    setFiles([])
    
    // Focus textarea after send
    textareaRef.current?.focus()
  }

  // Handle key press
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Get file icon
  const getFileIcon = (type: string) => {
    switch (type) {
      case 'image':
        return <Image size={14} />
      case 'log':
        return <FileText size={14} />
      default:
        return <FileCode size={14} />
    }
  }

  return (
    <div 
      className={`chat-input-container ${isDragging ? 'dragging' : ''}`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
    >
      {/* Attached Files */}
      {files.length > 0 && (
        <div className="attached-files">
          {files.map(file => (
            <div key={file.id} className="attached-file">
              {file.type === 'image' && file.preview ? (
                <img src={file.preview} alt={file.name} className="file-preview" />
              ) : (
                <div className="file-icon">
                  {getFileIcon(file.type)}
                </div>
              )}
              <span className="file-name">{file.name}</span>
              <button 
                className="file-remove"
                onClick={() => removeFile(file.id)}
                aria-label="Remove file"
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Input Area */}
      <div className="input-wrapper">
        <div className="input-area">
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            placeholder="描述问题或粘贴错误日志... (可粘贴图片)"
            rows={1}
            disabled={disabled}
          />
        </div>
        
        <div className="input-actions">
          {/* File Upload Button */}
          <button
            type="button"
            className="action-btn attach-btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
            title="添加文件"
          >
            <Paperclip size={18} />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileSelect}
            accept=".py,.js,.ts,.tsx,.java,.go,.rs,.log,.txt,.json,.yaml,.yml,.md,.png,.jpg,.jpeg,.gif,.webp"
            className="hidden-input"
          />

          {/* Send Button */}
          <button
            type="button"
            className="action-btn send-btn"
            onClick={handleSend}
            disabled={disabled || (!text.trim() && files.length === 0)}
            title="发送 (Enter)"
          >
            <Send size={18} />
          </button>
        </div>
      </div>

      {/* Drag Overlay */}
      {isDragging && (
        <div className="drag-overlay">
          <div className="drag-content">
            <Paperclip size={24} />
            <span>拖放文件到此处</span>
          </div>
        </div>
      )}

      {/* Hint */}
      <div className="input-hint">
        <span>Enter 发送 · Shift+Enter 换行 · 可直接粘贴图片</span>
      </div>
    </div>
  )
}

