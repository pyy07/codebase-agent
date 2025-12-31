import React, { useState, useCallback, useRef, useEffect } from 'react'
import AnalysisForm from './components/AnalysisForm'
import AnalysisResult from './components/AnalysisResult'
import ProgressIndicator from './components/ProgressIndicator'
import { AnalysisResult as AnalysisResultType } from './types'
import { useSSE } from './hooks/useSSE'
import './App.css'

function App() {
  const [result, setResult] = useState<AnalysisResultType | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState<{ message: string; progress: number; step?: string } | null>(null)
  const [useStreaming, setUseStreaming] = useState(true)
  const [sseBody, setSseBody] = useState<any>(null)
  const timeoutTimerRef = useRef<NodeJS.Timeout | null>(null)

  // 使用 useCallback 稳定回调函数，避免 useSSE 的 useEffect 重复执行
  const handleProgress = useCallback((message: string, progress: number, step?: string) => {
    console.log('handleProgress called:', { message, progress, step })
    setProgress({ message, progress, step })
    // 清除超时定时器（收到进度更新）
    if (timeoutTimerRef.current) {
      clearTimeout(timeoutTimerRef.current)
      timeoutTimerRef.current = null
    }
    // 设置新的超时定时器（30秒无响应则提示）
    timeoutTimerRef.current = setTimeout(() => {
      setError('分析时间较长，请耐心等待...如果长时间无响应，请检查网络连接或重试。')
    }, 30000)
  }, [])

  const handleResult = useCallback((resultData: any) => {
    setResult(resultData)
    setLoading(false)
    setProgress(null)
    if (timeoutTimerRef.current) {
      clearTimeout(timeoutTimerRef.current)
      timeoutTimerRef.current = null
    }
  }, [])

  const handleError = useCallback((errorMsg: string) => {
    setError(errorMsg)
    setLoading(false)
    setProgress(null)
    if (timeoutTimerRef.current) {
      clearTimeout(timeoutTimerRef.current)
      timeoutTimerRef.current = null
    }
  }, [])

  const handleDone = useCallback(() => {
    setLoading(false)
    setProgress(null)
    if (timeoutTimerRef.current) {
      clearTimeout(timeoutTimerRef.current)
      timeoutTimerRef.current = null
    }
  }, [])

  // 清理超时定时器
  useEffect(() => {
    return () => {
      if (timeoutTimerRef.current) {
        clearTimeout(timeoutTimerRef.current)
      }
    }
  }, [])

  // SSE 流式处理
  const { isConnected: sseConnected, error: sseError } = useSSE(
    useStreaming && sseBody ? '/api/v1/analyze/stream' : '',
    sseBody,
    {
      onProgress: handleProgress,
      onResult: handleResult,
      onError: handleError,
      onDone: handleDone,
    }
  )

  const handleAnalysis = async (input: string, contextFiles: File[], streaming: boolean = true) => {
    setLoading(true)
    setError(null)
    setResult(null)
    setProgress({ message: '准备开始分析...', progress: 0, step: 'preparing' })
    
    // 清除之前的超时定时器
    if (timeoutTimerRef.current) {
      clearTimeout(timeoutTimerRef.current)
      timeoutTimerRef.current = null
    }

    try {
      // 处理上下文文件
      const contextFilesData: any[] = []
      for (const file of contextFiles) {
        const content = await file.text()
        const type = file.name.endsWith('.log') || file.name.endsWith('.txt') ? 'log' : 'code'
        contextFilesData.push({
          type,
          path: file.name,
          content,
        })
      }

      // 构建请求体
      const requestBody: any = {
        input,
      }
      
      if (contextFilesData.length > 0) {
        requestBody.context_files = contextFilesData
      }

      if (streaming) {
        // 使用 SSE 流式接口
        setUseStreaming(true)
        setSseBody(requestBody)
        return
      }

      // 使用同步接口
      setUseStreaming(false)
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      }
      
      const apiKey = localStorage.getItem('apiKey')
      if (apiKey) {
        headers['X-API-Key'] = apiKey
      }

      const response = await fetch('/api/v1/analyze', {
        method: 'POST',
        headers,
        body: JSON.stringify(requestBody),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || '分析失败')
      }

      const data = await response.json()
      setResult(data.result)
      setLoading(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : '未知错误')
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Codebase Driven Agent</h1>
        <p>基于代码库驱动的智能问题分析平台</p>
      </header>
      
      <main className="app-main">
        <AnalysisForm onSubmit={handleAnalysis} loading={loading || sseConnected} />
        
        {(sseError || error) && (
          <div className="error-message">
            <strong>错误：</strong>{sseError || error}
          </div>
        )}
        
        {progress && <ProgressIndicator {...progress} />}
        
        {result && <AnalysisResult result={result} />}
      </main>
    </div>
  )
}

export default App

