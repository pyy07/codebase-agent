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
  const [planSteps, setPlanSteps] = useState<Array<{step: number, action: string, target: string, status: string}>>([])
  const [useStreaming, setUseStreaming] = useState(true)
  const [sseBody, setSseBody] = useState<any>(null)
  const timeoutTimerRef = useRef<NodeJS.Timeout | null>(null)

  // 使用 useCallback 稳定回调函数，避免 useSSE 的 useEffect 重复执行
  const handleProgress = useCallback((message: string, progress: number, step?: string) => {
    console.log('handleProgress called:', { message, progress, step, progressType: typeof progress })
    // 确保 progress 是数字类型
    const progressValue = typeof progress === 'number' ? progress : parseFloat(String(progress)) || 0
    console.log('Setting progress state:', { message, progress: progressValue, step })
    setProgress({ message, progress: progressValue, step })
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
    console.log('handleError called:', errorMsg)
    setError(errorMsg)
    setLoading(false)
    setProgress(null)
    // 注意：不清空 sseBody 和 useStreaming，让 useSSE 自己处理清理
    // 这样可以在错误后重新连接
    if (timeoutTimerRef.current) {
      clearTimeout(timeoutTimerRef.current)
      timeoutTimerRef.current = null
    }
  }, [])

  const handleDone = useCallback(() => {
    console.log('handleDone called - analysis completed')
    // 注意：不要在这里清空 progress，因为可能还有结果要显示
    // 只有在收到 result 时才清空 progress
    setLoading(false)
    // 不清空 progress，让用户看到最终状态
    // setProgress(null)
    if (timeoutTimerRef.current) {
      clearTimeout(timeoutTimerRef.current)
      timeoutTimerRef.current = null
    }
  }, [])

  const handlePlan = useCallback((steps: Array<{step: number, action: string, target: string, status: string}>) => {
    console.log('handlePlan called:', steps)
    setPlanSteps(steps)
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
      onPlan: handlePlan,
    }
  )

  const handleAnalysis = async (input: string, contextFiles: File[], streaming: boolean = true) => {
    console.log('handleAnalysis called:', { input, contextFiles: contextFiles.length, streaming })
    
    // 先清空之前的状态，确保可以重新发起请求
    setError(null)
    setResult(null)
    setProgress(null)
    setPlanSteps([])
    
    // 清除之前的超时定时器
    if (timeoutTimerRef.current) {
      clearTimeout(timeoutTimerRef.current)
      timeoutTimerRef.current = null
    }
    
    // 设置加载状态和初始进度
    setLoading(true)
    setProgress({ message: '准备开始分析...', progress: 0, step: 'preparing' })

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
        // 先重置流式状态，然后设置 sseBody
        // 使用双 requestAnimationFrame 确保状态重置完成后再设置新值
        setUseStreaming(false)
        setSseBody(null)
        
        // 使用双 requestAnimationFrame 确保状态重置完成后再设置新值
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            console.log('Setting SSE body:', requestBody)
            setUseStreaming(true)
            setSseBody(requestBody)
          })
        })
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
        
        {planSteps.length > 0 && (
          <div className="plan-steps" style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#f5f5f5', borderRadius: '8px' }}>
            <h3 style={{ marginTop: 0, marginBottom: '10px' }}>分析计划</h3>
            <ol style={{ margin: 0, paddingLeft: '20px' }}>
              {planSteps.map((step, index) => (
                <li key={index} style={{ 
                  marginBottom: '8px',
                  color: step.status === 'completed' ? '#28a745' : 
                         step.status === 'running' ? '#007bff' : 
                         step.status === 'failed' ? '#dc3545' : '#666'
                }}>
                  <strong>步骤 {step.step}:</strong> {step.action}
                  {step.target && <span> - {step.target}</span>}
                  {step.status === 'completed' && <span> ✓</span>}
                  {step.status === 'running' && <span> ⟳</span>}
                  {step.status === 'failed' && <span> ✗</span>}
                </li>
              ))}
            </ol>
          </div>
        )}
        
        {progress && <ProgressIndicator {...progress} />}
        
        {result && <AnalysisResult result={result} />}
      </main>
    </div>
  )
}

export default App

