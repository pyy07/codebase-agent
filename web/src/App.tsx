import { useState, useCallback, useRef, useEffect } from 'react'
import { Terminal } from 'lucide-react'
import { ThemeProvider } from './components/theme-provider'
import { ThemeToggle } from './components/theme-toggle'
import MessageList from './components/MessageList'
import ChatInput from './components/ChatInput'
import { ChatMessage, MessageContent, PlanStep, AttachedFile, AnalysisResult } from './types'
import { useSSE } from './hooks/useSSE'
import './App.css'

function generateId() {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [sseBody, setSseBody] = useState<any>(null)
  const [useStreaming, setUseStreaming] = useState(true)
  const currentAssistantMessageRef = useRef<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto scroll to bottom when new messages arrive
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  // Helper to update the current assistant message
  const updateAssistantMessage = useCallback((updater: (contents: MessageContent[]) => MessageContent[]) => {
    const messageId = currentAssistantMessageRef.current
    if (!messageId) return
    
    setMessages(prev => prev.map(msg => {
      if (msg.id === messageId) {
        return { ...msg, content: updater(msg.content) }
      }
      return msg
    }))
  }, [])

  // SSE Handlers
  const handleProgress = useCallback((message: string, progress: number, step?: string) => {
    updateAssistantMessage(contents => {
      // Update or add progress content
      const hasProgress = contents.some(c => c.type === 'progress')
      if (hasProgress) {
        return contents.map(c => 
          c.type === 'progress' 
            ? { type: 'progress' as const, data: { message, progress, step } }
            : c
        )
      }
      return [...contents, { type: 'progress' as const, data: { message, progress, step } }]
    })
  }, [updateAssistantMessage])

  const handlePlan = useCallback((steps: PlanStep[]) => {
    updateAssistantMessage(contents => {
      const hasPlan = contents.some(c => c.type === 'plan')
      if (hasPlan) {
        return contents.map(c => 
          c.type === 'plan' ? { type: 'plan' as const, data: steps } : c
        )
      }
      // Remove progress when plan arrives, add plan
      return [...contents.filter(c => c.type !== 'progress'), { type: 'plan' as const, data: steps }]
    })
  }, [updateAssistantMessage])

  const handleResult = useCallback((result: AnalysisResult) => {
    updateAssistantMessage(contents => {
      return [
        ...contents.filter(c => c.type !== 'progress'),
        { type: 'result' as const, data: result }
      ]
    })
    setIsProcessing(false)
    
    // Mark message as not streaming anymore
    const messageId = currentAssistantMessageRef.current
    if (messageId) {
      setMessages(prev => prev.map(msg => 
        msg.id === messageId ? { ...msg, isStreaming: false } : msg
      ))
    }
  }, [updateAssistantMessage])

  const handleError = useCallback((errorMsg: string) => {
    updateAssistantMessage(contents => {
      return [
        ...contents.filter(c => c.type !== 'progress'),
        { type: 'error' as const, data: errorMsg }
      ]
    })
    setIsProcessing(false)
    
    const messageId = currentAssistantMessageRef.current
    if (messageId) {
      setMessages(prev => prev.map(msg => 
        msg.id === messageId ? { ...msg, isStreaming: false } : msg
      ))
    }
  }, [updateAssistantMessage])

  const handleDone = useCallback(() => {
    setIsProcessing(false)
    const messageId = currentAssistantMessageRef.current
    if (messageId) {
      setMessages(prev => prev.map(msg => 
        msg.id === messageId ? { ...msg, isStreaming: false } : msg
      ))
    }
  }, [])

  // SSE Hook
  const { error: sseError } = useSSE(
    useStreaming && sseBody ? '/api/v1/analyze/stream' : '',
    sseBody,
    {
      onProgress: handleProgress,
      onResult: handleResult,
      onError: handleError,
      onDone: handleDone,
      onPlan: handlePlan,
    }
  )

  // Handle SSE errors
  useEffect(() => {
    if (sseError) {
      handleError(sseError)
    }
  }, [sseError, handleError])

  // Send message handler
  const handleSendMessage = useCallback(async (text: string, files: AttachedFile[]) => {
    // Create user message
    const userMessageContent: MessageContent[] = [{ type: 'text', data: text }]
    
    // Add file references to user message
    if (files.length > 0) {
      files.forEach(file => {
        if (file.type === 'image' && file.preview) {
          userMessageContent.push({ type: 'text', data: { type: 'image', name: file.name, preview: file.preview } })
        }
      })
    }

    const userMessage: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: userMessageContent,
      timestamp: new Date(),
    }

    // Create assistant message placeholder
    const assistantMessage: ChatMessage = {
      id: generateId(),
      role: 'assistant',
      content: [{ type: 'thinking', data: '正在分析你的问题...' }],
      timestamp: new Date(),
      isStreaming: true,
    }

    currentAssistantMessageRef.current = assistantMessage.id
    setMessages(prev => [...prev, userMessage, assistantMessage])
    setIsProcessing(true)

    // Prepare request
    const contextFilesData = files.map(file => ({
      type: file.type,
      path: file.name,
      content: file.content,
    }))

    const requestBody: any = { input: text }
    if (contextFilesData.length > 0) {
      requestBody.context_files = contextFilesData
    }

    // Use streaming
    setUseStreaming(false)
    setSseBody(null)
    
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        setUseStreaming(true)
        setSseBody(requestBody)
      })
    })
  }, [])

  return (
    <ThemeProvider>
      <div className="chat-app">
        {/* Header */}
        <header className="chat-header">
          <div className="header-content">
            <div className="logo">
              <div className="logo-icon">
                <Terminal size={18} />
              </div>
              <div className="logo-text">
                <h1>Codebase Agent</h1>
              </div>
            </div>
            <div className="header-actions">
              <ThemeToggle />
            </div>
          </div>
        </header>

        {/* Messages Area */}
        <main className="chat-main">
          <div className="messages-container">
            <MessageList messages={messages} />
            <div ref={messagesEndRef} />
          </div>
        </main>

        {/* Input Area */}
        <footer className="chat-footer">
          <ChatInput 
            onSend={handleSendMessage} 
            disabled={isProcessing} 
          />
        </footer>
      </div>
    </ThemeProvider>
  )
}

export default App
