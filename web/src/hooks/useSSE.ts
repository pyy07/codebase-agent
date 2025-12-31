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
}

export function useSSE(url: string, body: any, options: UseSSEOptions = {}) {
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const controllerRef = useRef<AbortController | null>(null)
  const bodyStringRef = useRef<string | null>(null)

  useEffect(() => {
    if (!url || !body) {
      setIsConnected(false)
      return
    }

    // 稳定化 body 的字符串表示，避免因为对象引用不同而重新连接
    const bodyString = JSON.stringify(body)
    
    // 如果 body 内容没有变化，不重新连接
    if (bodyStringRef.current === bodyString && controllerRef.current && !controllerRef.current.signal.aborted) {
      return
    }
    
    // 如果之前有连接，先断开
    if (controllerRef.current) {
      controllerRef.current.abort()
    }

    bodyStringRef.current = bodyString

    // 使用 POST 请求发送 SSE
    // 注意：标准 EventSource 不支持 POST，我们需要使用 fetch + ReadableStream
    const controller = new AbortController()
    controllerRef.current = controller

    const connectSSE = async () => {
      try {
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
          let inMessage = false

          for (const line of lines) {
            if (line.trim() === '') {
              // 空行表示消息结束，处理累积的数据
              if (inMessage && dataLines.length > 0) {
                const dataStr = dataLines.join('')
                try {
                  const data = JSON.parse(dataStr)

                  // 处理不同类型的消息
                  if (data.message && data.progress !== undefined) {
                    // Progress 消息
                    console.log('Progress update:', data)
                    options.onProgress?.(data.message, data.progress, data.step)
                  } else if (data.root_cause || data.suggestions) {
                    // Result 消息
                    console.log('Result received:', data)
                    options.onResult?.(data)
                  } else if (data.error) {
                    // Error 消息
                    console.log('Error received:', data.error)
                    options.onError?.(data.error)
                    setError(data.error)
                  } else if (data.message === 'Analysis completed') {
                    // Done 消息
                    console.log('Done received')
                    options.onDone?.()
                  }
                } catch (e) {
                  // 忽略 JSON 解析错误
                  console.warn('Failed to parse SSE data:', dataStr, e)
                }
              }
              // 重置状态
              currentEvent = null
              dataLines = []
              inMessage = false
              continue
            }

            if (line.startsWith('event: ')) {
              currentEvent = line.substring(7).trim()
              inMessage = true
              continue
            }

            if (line.startsWith('data: ')) {
              // 累积多行的 data 字段
              const dataLine = line.substring(6)
              dataLines.push(dataLine)
              inMessage = true
            }
          }
        }

        options.onDone?.()
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
        setIsConnected(false)
      }
    }

    connectSSE()

    return () => {
      if (controllerRef.current) {
        controllerRef.current.abort()
        controllerRef.current = null
      }
      setIsConnected(false)
    }
    // 只依赖 url 和 body 的字符串表示，不依赖 options（因为 options 中的回调函数应该用 useCallback 稳定）
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, body ? JSON.stringify(body) : null])

  return {
    isConnected,
    error,
  }
}

