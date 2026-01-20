import { useState, useCallback, useRef, useEffect } from 'react'
import { Terminal, Camera, Check } from 'lucide-react'
import { ThemeProvider } from './components/theme-provider'
import { ThemeToggle } from './components/theme-toggle'
import MessageList from './components/MessageList'
import ChatInput from './components/ChatInput'
import { ChatMessage, MessageContent, PlanStep, AttachedFile, AnalysisResult, StepExecutionData } from './types'
import { useSSE } from './hooks/useSSE'
import html2canvas from 'html2canvas'
import './App.css'

function generateId() {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [sseBody, setSseBody] = useState<any>(null)
  const [useStreaming, setUseStreaming] = useState(true)
  const [isCapturing, setIsCapturing] = useState(false)
  const [captureSuccess, setCaptureSuccess] = useState(false)
  const currentAssistantMessageRef = useRef<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)

  // DEV: 测试步骤显示功能
  const isDev = import.meta.env.DEV
  const addTestSteps = useCallback(() => {
    if (!currentAssistantMessageRef.current) {
      // 创建测试消息
      const assistantMessage: ChatMessage = {
        id: generateId(),
        role: 'assistant',
        content: [
          { 
            type: 'plan', 
            data: [
              { step: 1, action: '代码搜索', target: 'SecurityExchange 相关代码', status: 'pending' },
              { step: 2, action: '日志查询', target: '错误日志', status: 'pending' },
              { step: 3, action: '代码定位', target: '具体错误位置', status: 'pending' },
              { step: 4, action: '综合分析', target: '', status: 'pending' },
              { step: 5, action: '生成建议', target: '', status: 'pending' },
            ]
          },
          {
            type: 'step_execution',
            data: [
              { step: 1, action: '代码搜索', target: 'SecurityExchange 相关代码', status: 'completed', timestamp: new Date() },
              { step: 2, action: '日志查询', target: '错误日志', status: 'running', timestamp: new Date() },
              { step: 3, action: '代码定位', target: '具体错误位置', status: 'pending', timestamp: new Date() },
              { step: 4, action: '综合分析', target: '', status: 'pending', timestamp: new Date() },
              { step: 5, action: '生成建议', target: '', status: 'pending', timestamp: new Date() },
            ]
          },
          { type: 'progress', data: { message: '执行步骤 2/5', progress: 0.4, step: 'graph_execution' } }
        ],
        timestamp: new Date(),
        isStreaming: true,
      }
      currentAssistantMessageRef.current = assistantMessage.id
      setMessages(prev => [...prev, assistantMessage])
    }
  }, [])

  // 截图并复制到剪贴板
  const handleCaptureAndCopy = useCallback(async () => {
    if (!messagesContainerRef.current || messages.length === 0) {
      return
    }

    setIsCapturing(true)
    setCaptureSuccess(false)

    try {
      console.log('Starting screenshot capture with html2canvas...')
      
      const container = messagesContainerRef.current
      
      // 使用 html2canvas 截图
      const canvas = await html2canvas(container, {
        scale: 2,
        useCORS: true,
        allowTaint: true,
        backgroundColor: '#ffffff',
        logging: false,
        // 忽略无法加载的图片
        onclone: (clonedDoc) => {
          // 移除克隆文档中所有无法加载的图片
          const images = clonedDoc.querySelectorAll('img')
          images.forEach((img) => {
            if (!img.complete || img.naturalHeight === 0) {
              img.style.display = 'none'
            }
          })
        }
      })

      console.log('Canvas generated, size:', canvas.width, 'x', canvas.height)

      // 转换为 Blob
      const blob = await new Promise<Blob>((resolve, reject) => {
        canvas.toBlob((b) => {
          if (b) resolve(b)
          else reject(new Error('Failed to create blob'))
        }, 'image/png', 1.0)
      })
      
      console.log('Blob created, size:', blob.size, 'type:', blob.type)

      // 检查是否支持 Clipboard API
      if (!navigator.clipboard || !navigator.clipboard.write) {
        console.warn('Clipboard API not supported, downloading instead')
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.download = `codebase-agent-${Date.now()}.png`
        link.href = url
        link.click()
        URL.revokeObjectURL(url)
        
        setCaptureSuccess(true)
        setTimeout(() => setCaptureSuccess(false), 3000)
        return
      }

      // 复制到剪贴板
      await navigator.clipboard.write([
        new ClipboardItem({ 'image/png': blob })
      ])

      console.log('Screenshot copied to clipboard successfully ✅')
      setCaptureSuccess(true)
      setTimeout(() => setCaptureSuccess(false), 3000)
      
    } catch (error: any) {
      console.error('Failed to capture screenshot:', error)
      
      let errorMsg = '截图失败'
      if (error?.name === 'NotAllowedError') {
        errorMsg = '需要剪贴板权限，请在浏览器设置中允许'
      } else if (error?.message) {
        errorMsg = error.message
      }
      
      alert(`${errorMsg}`)
    } finally {
      setIsCapturing(false)
    }
  }, [messages])

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
    console.log('[App] Progress update:', { message, progress, step })
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
      // Remove thinking when progress arrives
      return [...contents.filter(c => c.type !== 'thinking'), { type: 'progress' as const, data: { message, progress, step } }]
    })

    // 更新步骤执行状态（根据 progress 推算当前执行的步骤）
    if (progress > 0) {
      updateAssistantMessage(contents => {
        const stepExecutionContent = contents.find(c => c.type === 'step_execution')
        if (stepExecutionContent && Array.isArray(stepExecutionContent.data)) {
          const totalSteps = stepExecutionContent.data.length
          const currentStepIndex = Math.floor(progress * totalSteps)
          
          console.log('[App] Updating step execution:', { totalSteps, currentStepIndex, progress })
          
          const updatedSteps = stepExecutionContent.data.map((s: any, index: number) => {
            if (index < currentStepIndex) {
              return { ...s, status: 'completed' as const }
            } else if (index === currentStepIndex) {
              return { ...s, status: 'running' as const }
            }
            return s
          })
          
          return contents.map(c => 
            c.type === 'step_execution' 
              ? { type: 'step_execution' as const, data: updatedSteps }
              : c
          )
        }
        return contents
      })
    }
  }, [updateAssistantMessage])

  const handlePlan = useCallback((steps: PlanStep[]) => {
    console.log('[App] Received plan with steps:', steps)
    updateAssistantMessage(contents => {
      const existingPlan = contents.find(c => c.type === 'plan')
      const previousStepCount = existingPlan && Array.isArray(existingPlan.data) ? existingPlan.data.length : 0
      const isExpanding = steps.length > previousStepCount
      
      if (isExpanding && previousStepCount > 0) {
        console.log(`[App] Plan expanding: ${previousStepCount} → ${steps.length} steps`)
      }
      
      if (existingPlan) {
        // 更新现有 plan，保留之前步骤的状态
        return contents.map(c => {
          if (c.type === 'plan') {
            // 合并新旧步骤，保留已完成步骤的状态
            const oldSteps = Array.isArray(c.data) ? c.data : []
            const mergedSteps = steps.map((newStep, index) => {
              const oldStep = oldSteps[index]
              // 如果是已存在的步骤，保留其状态
              if (oldStep && oldStep.step === newStep.step) {
                return oldStep.status ? { ...newStep, status: oldStep.status } : newStep
              }
              // 新步骤，标记为 pending 并添加 isNew 标识
              return { ...newStep, isNew: index >= previousStepCount }
            })
            return { type: 'plan' as const, data: mergedSteps }
          }
          return c
        })
      }
      // Remove thinking and progress when plan arrives, add plan
      return [...contents.filter(c => c.type !== 'progress' && c.type !== 'thinking'), { type: 'plan' as const, data: steps }]
    })

    // 初始化或更新步骤执行状态
    updateAssistantMessage(contents => {
      const hasStepExecution = contents.some(c => c.type === 'step_execution')
      if (!hasStepExecution && steps.length > 0) {
        const stepExecutions = steps.map(step => ({
          step: step.step,
          action: step.action,
          target: step.target,
          status: 'pending' as const,
          timestamp: new Date()
        }))
        console.log('[App] Initializing step execution with:', stepExecutions)
        return [...contents, { type: 'step_execution' as const, data: stepExecutions }]
      } else if (hasStepExecution) {
        // 更新 step_execution，添加新步骤
        return contents.map(c => {
          if (c.type === 'step_execution' && Array.isArray(c.data)) {
            const existingSteps = c.data
            // 如果新 plan 有更多步骤，添加到 execution
            if (steps.length > existingSteps.length) {
              const newSteps = steps.slice(existingSteps.length).map(step => ({
                step: step.step,
                action: step.action,
                target: step.target,
                status: 'pending' as const,
                timestamp: new Date(),
                isNew: true
              }))
              console.log('[App] Adding new steps to execution:', newSteps)
              return { type: 'step_execution' as const, data: [...existingSteps, ...newSteps] }
            }
          }
          return c
        })
      }
      return contents
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
    console.log('[App] Error received:', errorMsg)
    updateAssistantMessage(contents => {
      return [
        ...contents.filter(c => c.type !== 'progress' && c.type !== 'thinking'),
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

  const handleStepExecution = useCallback((stepExecution: StepExecutionData) => {
    console.log('[App] Step execution received:', stepExecution)
    updateAssistantMessage(contents => {
      const stepExecutionContent = contents.find(c => c.type === 'step_execution')
      if (stepExecutionContent && Array.isArray(stepExecutionContent.data)) {
        const updatedSteps = stepExecutionContent.data.map((s: any) => {
          if (s.step === stepExecution.step) {
            return {
              ...s,
              status: stepExecution.status,
              result: stepExecution.result,
              result_truncated: stepExecution.result_truncated,
              error: stepExecution.error,
              timestamp: stepExecution.timestamp || new Date(),
            }
          }
          return s
        })
        return contents.map(c => 
          c.type === 'step_execution' 
            ? { type: 'step_execution' as const, data: updatedSteps }
            : c
        )
      }
      return contents
    })
  }, [updateAssistantMessage])

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
      onStepExecution: handleStepExecution,
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
              <button 
                onClick={handleCaptureAndCopy}
                disabled={isCapturing || messages.length === 0}
                className="screenshot-button"
                title="截图并复制到剪贴板"
              >
                {captureSuccess ? (
                  <>
                    <Check size={16} />
                    <span>已复制</span>
                  </>
                ) : (
                  <>
                    <Camera size={16} />
                    <span>{isCapturing ? '截图中...' : '截图分享'}</span>
                  </>
                )}
              </button>
              <ThemeToggle />
            </div>
          </div>
        </header>

        {/* Messages Area */}
        <main className="chat-main">
          <div className="messages-container" ref={messagesContainerRef}>
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
