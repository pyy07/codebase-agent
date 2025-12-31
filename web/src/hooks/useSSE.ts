import { useState, useEffect, useRef } from 'react'

export interface SSEMessage {
  event: string
  data: any
}

export interface UseSSEOptions {
  onProgress?: (message: string, progress: number, step?: string) => void
  onResult?: (result: any) => void
  onError?: (error: string) => void
  onDone?: () => void
  onPlan?: (steps: Array<{step: number, action: string, target: string, status: string}>) => void
}

export function useSSE(url: string, body: any, options: UseSSEOptions = {}) {
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const controllerRef = useRef<AbortController | null>(null)
  const bodyStringRef = useRef<string | null>(null)
  const connectionIdRef = useRef<number>(0) // 用于跟踪连接ID，确保每次都是新连接

  useEffect(() => {
    if (!url || !body) {
      // 清空状态，确保可以重新连接
      setIsConnected(false)
      setError(null)
      bodyStringRef.current = null
      if (controllerRef.current) {
        controllerRef.current.abort()
        controllerRef.current = null
      }
      return
    }

    // 稳定化 body 的字符串表示，避免因为对象引用不同而重新连接
    const bodyString = JSON.stringify(body)
    
    // 如果 body 内容没有变化，且连接仍然活跃，不重新连接
    // 但是，如果连接已断开（aborted）或未连接，即使内容相同也要重新连接
    const isBodyChanged = bodyStringRef.current !== bodyString
    const hasNoController = !controllerRef.current
    const isControllerAborted = controllerRef.current?.signal.aborted || false
    
    // 只有在 body 改变、没有控制器、或控制器已中止时才重新连接
    const shouldReconnect = isBodyChanged || hasNoController || isControllerAborted
    
    if (!shouldReconnect) {
      console.log('Skipping reconnect - connection still active')
      return
    }
    
    // 如果之前有连接，先断开
    if (controllerRef.current && !controllerRef.current.signal.aborted) {
      console.log('Aborting previous connection')
      controllerRef.current.abort()
      controllerRef.current = null
    }

    // 更新连接ID，确保每次都是新连接
    connectionIdRef.current += 1
    bodyStringRef.current = bodyString
    
    // 重置连接状态
    setIsConnected(false)
    setError(null)

    // 使用 POST 请求发送 SSE
    // 注意：标准 EventSource 不支持 POST，我们需要使用 fetch + ReadableStream
    const controller = new AbortController()
    controllerRef.current = controller

    const connectSSE = async () => {
      try {
        console.log('Starting SSE connection:', { url, bodyString, connectionId: connectionIdRef.current })
        setIsConnected(true)
        setError(null)

        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        }

        const apiKey = localStorage.getItem('apiKey')
        if (apiKey) {
          headers['X-API-Key'] = apiKey
        }

        const response = await fetch(url, {
          method: 'POST',
          headers,
          body: bodyString,
          signal: controller.signal,
        })

        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.detail || 'SSE 连接失败')
        }

        const reader = response.body?.getReader()
        const decoder = new TextDecoder()

        if (!reader) {
          throw new Error('无法读取响应流')
        }

        let buffer = ''

        while (true) {
          // 检查是否被取消
          if (controller.signal.aborted) {
            break
          }

          const { done, value } = await reader.read()

          if (done) {
            break
          }

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          let currentEvent: string | null = null
          let dataLines: string[] = []

          // 处理消息的函数
          const processMessage = () => {
            if (dataLines.length > 0) {
              const dataStr = dataLines.join('')
              try {
                const data = JSON.parse(dataStr)
                
                console.log('SSE message parsed:', { event: currentEvent, data })

                // 根据 event 类型或数据内容处理消息
                if (currentEvent === 'plan' || data.steps) {
                  // Plan 消息（分析计划）
                  console.log('Plan received:', { steps: data.steps })
                  options.onPlan?.(data.steps || [])
                } else if (currentEvent === 'progress' || (data.message && data.progress !== undefined)) {
                  // Progress 消息
                  console.log('Progress update:', { 
                    event: currentEvent, 
                    message: data.message, 
                    progress: data.progress, 
                    step: data.step,
                    progressType: typeof data.progress 
                  })
                  // 确保 progress 是数字类型，如果是字符串则转换
                  const progressValue = typeof data.progress === 'number' 
                    ? data.progress 
                    : parseFloat(String(data.progress)) || 0
                  console.log('Calling onProgress with:', { message: data.message, progress: progressValue, step: data.step })
                  options.onProgress?.(data.message, progressValue, data.step)
                } else if (currentEvent === 'result' || (data.root_cause || data.suggestions)) {
                  // Result 消息
                  console.log('Result received:', data)
                  options.onResult?.(data)
                } else if (currentEvent === 'error' || data.error) {
                  // Error 消息
                  console.log('Error received:', data.error)
                  options.onError?.(data.error)
                  setError(data.error)
                } else if (currentEvent === 'done' || data.message === 'Analysis completed') {
                  // Done 消息
                  console.log('Done received')
                  options.onDone?.()
                } else {
                  // 未知消息类型，尝试根据数据内容推断
                  console.warn('Unknown SSE message type:', { event: currentEvent, data })
                }
              } catch (e) {
                // JSON 解析错误
                console.error('Failed to parse SSE data:', { 
                  event: currentEvent, 
                  dataStr, 
                  error: e,
                  lines: dataLines,
                  rawLines: lines
                })
              }
            }
            // 重置状态，准备下一个消息
            currentEvent = null
            dataLines = []
          }

          for (const line of lines) {
            const trimmedLine = line.trim()
            
            // 调试：打印每一行
            if (trimmedLine && (trimmedLine.includes('event:') || trimmedLine.includes('data:'))) {
              console.log('SSE raw line:', trimmedLine)
            }
            
            if (trimmedLine === '') {
              // 空行表示消息结束，处理累积的数据
              if (currentEvent || dataLines.length > 0) {
                processMessage()
              }
              continue
            }

            // 处理 EventSourceResponse 可能在每行前加 "data: " 的情况
            // 格式可能是: "data: event: progress" 或 "data: data: {...}"
            let actualLine = trimmedLine
            if (trimmedLine.startsWith('data: ')) {
              actualLine = trimmedLine.substring(6).trim()
            } else if (trimmedLine.startsWith('data:')) {
              actualLine = trimmedLine.substring(5).trim()
            }

            // 现在处理实际的内容行
            if (actualLine.startsWith('event: ')) {
              // 如果遇到新的 event，先处理之前的消息
              if (dataLines.length > 0) {
                processMessage()
              }
              currentEvent = actualLine.substring(7).trim()
              console.log('SSE event set:', currentEvent)
              continue
            }

            if (actualLine.startsWith('data: ')) {
              // 嵌套的 data: 前缀（EventSourceResponse 加的）
              const dataLine = actualLine.substring(6)
              dataLines.push(dataLine)
              console.log('SSE data line added:', dataLine.substring(0, 100))
            } else if (actualLine && !actualLine.startsWith('event:')) {
              // 如果 actualLine 不是 event，且不为空，可能是数据行
              // 可能是 JSON 数据（没有 "data: " 前缀）
              dataLines.push(actualLine)
              console.log('SSE data line added (direct):', actualLine.substring(0, 100))
            }
          }
          
          // 处理缓冲区中剩余的不完整消息（如果有 event 和 data，但没有空行）
          // 如果还有未处理的消息，处理它
          if (currentEvent || dataLines.length > 0) {
            processMessage()
          }
        }

        // 注意：不在流结束时自动调用 onDone，只有在收到明确的 done 消息时才调用
        // options.onDone?.()
      } catch (err) {
        // 如果是主动取消，不显示错误
        if (err instanceof Error && err.name === 'AbortError') {
          console.log('SSE connection aborted')
          return
        }
        const errorMessage = err instanceof Error ? err.message : 'SSE 连接错误'
        setError(errorMessage)
        options.onError?.(errorMessage)
      } finally {
        console.log('SSE connection closed')
        setIsConnected(false)
        // 注意：不清空 bodyStringRef，保留它以便下次可以检测是否需要重新连接
        // 但清空 controllerRef，确保下次可以创建新连接
        controllerRef.current = null
      }
    }

    connectSSE()

    return () => {
      console.log('useSSE cleanup - aborting connection')
      if (controllerRef.current) {
        controllerRef.current.abort()
        controllerRef.current = null
      }
      setIsConnected(false)
    }
    // 只依赖 url 和 body 的字符串表示，不依赖 options（因为 options 中的回调函数应该用 useCallback 稳定）
    // 使用 bodyStringRef 来跟踪 body 的变化，避免因为对象引用不同而重新连接
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, body ? JSON.stringify(body) : null])

  return {
    isConnected,
    error,
  }
}

