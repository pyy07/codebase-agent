import { useState, useCallback, useRef, useEffect } from 'react'
import { Terminal, Camera, Check } from 'lucide-react'
import { ThemeProvider } from './components/theme-provider'
import { ThemeToggle } from './components/theme-toggle'
import MessageList from './components/MessageList'
import ChatInput from './components/ChatInput'
import { ChatMessage, MessageContent, PlanStep, AttachedFile, AnalysisResult, StepExecutionData, DecisionReasoningData, UserInputRequestData, UserReplyData } from './types'
import { useSSE } from './hooks/useSSE'
import { buildApiUrl } from './utils/api'
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
        // 忽略无法加载的图片和对话框遮罩
        onclone: (clonedDoc) => {
          // 移除克隆文档中所有无法加载的图片
          const images = clonedDoc.querySelectorAll('img')
          images.forEach((img) => {
            if (!img.complete || img.naturalHeight === 0) {
              img.style.display = 'none'
            }
          })
          
          // 移除所有对话框遮罩层和对话框内容
          // 方法1: 查找所有具有高 z-index 的 fixed 定位元素
          const allElements = clonedDoc.querySelectorAll('*')
          allElements.forEach((element) => {
            const el = element as HTMLElement
            const style = window.getComputedStyle(el)
            const zIndex = parseInt(style.zIndex) || 0
            const position = style.position
            const backgroundColor = style.backgroundColor
            
            // 如果 z-index 很高（>= 9998）且是 fixed 定位，可能是对话框或遮罩层
            if (position === 'fixed' && zIndex >= 9998) {
              // 检查是否是遮罩层（全屏覆盖，有背景色和模糊效果）
              const hasBackdropFilter = style.backdropFilter !== 'none' || 
                                       el.getAttribute('style')?.includes('backdrop-filter') ||
                                       el.getAttribute('style')?.includes('backdropFilter')
              
              // 如果是遮罩层（有模糊效果或半透明背景），隐藏它
              if (hasBackdropFilter || 
                  (backgroundColor !== 'rgba(0, 0, 0, 0)' && backgroundColor !== 'transparent')) {
                el.style.display = 'none'
              }
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

  // 只在消息数量变化时滚动，而不是每次 messages 引用变化时滚动
  const messagesLengthRef = useRef(messages.length)
  useEffect(() => {
    // 只在消息数量真正增加时才滚动
    if (messages.length > messagesLengthRef.current) {
      messagesLengthRef.current = messages.length
      scrollToBottom()
    }
  }, [messages.length, scrollToBottom])

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
    
    // 如果分析已完成（有 result 内容），忽略心跳消息（step: "waiting"）
    const messageId = currentAssistantMessageRef.current
    if (messageId) {
      const currentMessage = messages.find(msg => msg.id === messageId)
      if (currentMessage) {
        const hasResult = currentMessage.content.some(c => c.type === 'result')
        const isHeartbeat = step === 'waiting' || (message === '等待中...' && progress === 0.5)
        
        if (hasResult && isHeartbeat) {
          console.log('[App] Ignoring heartbeat progress after analysis completed')
          return
        }
      }
    }
    
    updateAssistantMessage(contents => {
      // 如果已有 result，不再更新进度条
      const hasResult = contents.some(c => c.type === 'result')
      if (hasResult) {
        console.log('[App] Analysis already completed, ignoring progress update')
        return contents
      }
      
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
    // 注意：只有当 progress 明确表示步骤进度时才更新，避免心跳消息（progress: 0.5, step: "processing"）覆盖已完成步骤的状态
    // 如果分析已完成（有 result），不再根据 progress 更新步骤状态，避免将未执行的步骤标记为 completed
    if (progress > 0 && step === 'graph_execution') {
      updateAssistantMessage(contents => {
        // 检查是否已有 result（分析已完成）
        const hasResult = contents.some(c => c.type === 'result')
        if (hasResult) {
          // 分析已完成，不再根据 progress 更新步骤状态
          // 未执行的步骤应该保持 pending 状态
          return contents
        }
        
        const stepExecutionContent = contents.find(c => c.type === 'step_execution')
        let updatedContents = contents
        
        if (stepExecutionContent && Array.isArray(stepExecutionContent.data)) {
          const totalSteps = stepExecutionContent.data.length
          const currentStepIndex = Math.floor(progress * totalSteps)
          
          console.log('[App] Updating step execution:', { totalSteps, currentStepIndex, progress, step })
          
          const updatedSteps = stepExecutionContent.data.map((s: any, index: number) => {
            // 如果步骤已经有明确的完成状态（completed/failed），不要被 progress 覆盖
            if (s.status === 'completed' || s.status === 'failed') {
              return s
            }
            // 只更新 pending 或 running 状态的步骤
            // 注意：当 progress 接近 1.0 时，不要将所有步骤都标记为 completed
            // 只标记实际执行过的步骤（index < currentStepIndex）
            if (index < currentStepIndex && progress < 1.0) {
              return { ...s, status: 'completed' as const }
            } else if (index === currentStepIndex && progress < 1.0) {
              return { ...s, status: 'running' as const }
            }
            return s
          })
          
          updatedContents = updatedContents.map(c => 
            c.type === 'step_execution' 
              ? { type: 'step_execution' as const, data: updatedSteps }
              : c
          )
          
          // 同步更新 plan 部分的步骤状态（同样避免覆盖已完成状态）
          const planContent = updatedContents.find(c => c.type === 'plan')
          if (planContent && Array.isArray(planContent.data)) {
            updatedContents = updatedContents.map(c => {
              if (c.type === 'plan' && Array.isArray(c.data)) {
                const updatedPlanSteps = c.data.map((step: any, index: number) => {
                  // 如果步骤已经有明确的完成状态，不要被 progress 覆盖
                  if (step.status === 'completed' || step.status === 'failed') {
                    return step
                  }
                  // 只更新 pending 或 running 状态的步骤
                  // 注意：当 progress 接近 1.0 时，不要将所有步骤都标记为 completed
                  if (index < currentStepIndex && progress < 1.0) {
                    return { ...step, status: 'completed' as const }
                  } else if (index === currentStepIndex && progress < 1.0) {
                    return { ...step, status: 'running' as const }
                  }
                  return step
                })
                return { type: 'plan' as const, data: updatedPlanSteps }
              }
              return c
            })
          }
        }
        return updatedContents
      })
    }
  }, [updateAssistantMessage, messages])

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
    console.log('[App] Done event received, marking analysis as complete')
    setIsProcessing(false)
    const messageId = currentAssistantMessageRef.current
    if (messageId) {
      setMessages(prev => prev.map(msg => {
        if (msg.id === messageId) {
          // 移除进度条，因为分析已完成
          const updatedContents = msg.content.filter(c => c.type !== 'progress')
          return { ...msg, isStreaming: false, content: updatedContents }
        }
        return msg
      }))
    }
  }, [])

  const handleStepExecution = useCallback((stepExecution: StepExecutionData) => {
    console.log('[App] Step execution received:', stepExecution)
    updateAssistantMessage(contents => {
      // 更新 step_execution 部分
      const stepExecutionContent = contents.find(c => c.type === 'step_execution')
      let updatedContents = contents
      
      if (stepExecutionContent && Array.isArray(stepExecutionContent.data)) {
        // 更新现有步骤
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
        updatedContents = updatedContents.map(c => 
          c.type === 'step_execution' 
            ? { type: 'step_execution' as const, data: updatedSteps }
            : c
        )
      } else {
        // 如果没有 step_execution，创建一个新的
        updatedContents = [...updatedContents, { 
          type: 'step_execution' as const, 
          data: [{
            step: stepExecution.step,
            action: stepExecution.action,
            target: stepExecution.target,
            status: stepExecution.status,
            result: stepExecution.result,
            result_truncated: stepExecution.result_truncated,
            error: stepExecution.error,
            timestamp: stepExecution.timestamp || new Date(),
          }]
        }]
      }
      
      // 同步更新 plan 部分的步骤状态
      const planContent = updatedContents.find(c => c.type === 'plan')
      if (planContent && Array.isArray(planContent.data)) {
        updatedContents = updatedContents.map(c => {
          if (c.type === 'plan' && Array.isArray(c.data)) {
            const updatedPlanSteps = c.data.map((step: any) => {
              if (step.step === stepExecution.step) {
                return {
                  ...step,
                  status: stepExecution.status
                }
              }
              return step
            })
            return { type: 'plan' as const, data: updatedPlanSteps }
          }
          return c
        })
      }
      
      return updatedContents
    })
  }, [updateAssistantMessage])

  const handleDecisionReasoning = useCallback((reasoning: DecisionReasoningData) => {
    console.log('[App] Decision reasoning received:', reasoning)
    updateAssistantMessage(contents => {
      // 支持多个推理原因，每个关联到不同的步骤
      // 如果已有相同 after_step 的推理原因，则更新；否则添加新的
      const existingReasoningIndex = contents.findIndex(
        c => c.type === 'decision_reasoning' && c.data.after_step === reasoning.after_step
      )
      if (existingReasoningIndex >= 0) {
        // 更新现有的推理原因
        return contents.map((c, idx) => 
          idx === existingReasoningIndex
            ? { type: 'decision_reasoning' as const, data: reasoning }
            : c
        )
      } else {
        // 添加新的推理原因
        return [...contents, { type: 'decision_reasoning' as const, data: reasoning }]
      }
    })
  }, [updateAssistantMessage])

  const handleUserInputRequest = useCallback((request: UserInputRequestData) => {
    console.log('[App] User input request received:', request)
    updateAssistantMessage(contents => {
      // 添加用户输入请求到消息内容
      return [...contents, { type: 'user_input_request' as const, data: request }]
    })
  }, [updateAssistantMessage])

  const handleUserReply = useCallback((reply: UserReplyData) => {
    console.log('[App] User reply received:', reply)
    updateAssistantMessage(contents => {
      // 添加用户回复到消息内容
      return [...contents, { type: 'user_reply' as const, data: reply }]
    })
  }, [updateAssistantMessage])

  // 提交用户回复到后端
  const submitUserReply = useCallback(async (requestId: string, reply: string) => {
    // 立即显示用户回复，不等待后端响应
    const isSkip = reply === '__SKIP__'
    handleUserReply({
      request_id: requestId,
      reply: isSkip ? '[已跳过，Agent 将基于已有信息得出结论]' : reply,
      timestamp: new Date(),
    })
    
    // 在后台发送请求，不阻塞 UI
    // 优先使用 Electron 暴露的 API key（从 .env 文件读取），如果没有则使用 localStorage
    const electronAPI = (window as any).electronAPI
    let apiKey = localStorage.getItem('apiKey')
    
    // 如果 Electron API 可用，尝试获取 API key（异步等待）
    if (electronAPI?.getApiKey) {
      try {
        const envApiKey = await electronAPI.getApiKey()
        if (envApiKey) {
          apiKey = envApiKey
        }
      } catch (error) {
        console.warn('[App] Failed to get API key from Electron:', error)
      }
    }
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    if (apiKey) {
      headers['X-API-Key'] = apiKey
    }

    const endpoint = isSkip ? '/api/v1/analyze/skip' : '/api/v1/analyze/reply'
    const fullUrl = buildApiUrl(endpoint)
    const body = isSkip 
      ? JSON.stringify({ request_id: requestId })
      : JSON.stringify({ request_id: requestId, reply })

    // 异步发送请求，不等待响应（后端会在后台处理并通过 SSE 流式返回结果）
    fetch(fullUrl, {
      method: 'POST',
      headers,
      body,
    })
      .then(async (response) => {
        if (!response.ok) {
          const errorData = await response.json()
          console.error(`[App] User ${isSkip ? 'skip' : 'reply'} failed:`, errorData)
          handleError(errorData.detail || (isSkip ? '跳过失败' : '提交回复失败'))
        } else {
          const result = await response.json()
          console.log(`[App] User ${isSkip ? 'skip' : 'reply'} submitted successfully:`, result)
        }
      })
      .catch((error) => {
        console.error('[App] Error submitting user reply:', error)
        handleError(error instanceof Error ? error.message : '提交回复失败')
      })
    
    // 立即返回，不等待后端处理
    return Promise.resolve({ success: true })
  }, [handleUserReply, handleError])

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
      onDecisionReasoning: handleDecisionReasoning,
      onUserInputRequest: handleUserInputRequest,
      onUserReply: handleUserReply,
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
            <MessageList messages={messages} onSubmitUserReply={submitUserReply} />
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
