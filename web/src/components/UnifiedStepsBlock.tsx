import { useState, Fragment } from 'react'
import { CheckCircle2, Loader2, XCircle, Circle, ListChecks, ChevronDown, ChevronRight, AlertTriangle, Lightbulb } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { PlanStep, StepExecutionData, DecisionReasoningData } from '../types'
import './UnifiedStepsBlock.css'

interface UnifiedStep extends PlanStep {
  result?: string
  result_truncated?: boolean
  error?: string
  timestamp?: Date
  isNew?: boolean
}

interface UnifiedStepsBlockProps {
  planSteps: PlanStep[]
  executionSteps: StepExecutionData[]
  decisionReasonings?: DecisionReasoningData[]  // 支持多个推理原因
}

export default function UnifiedStepsBlock({ planSteps, executionSteps, decisionReasonings = [] }: UnifiedStepsBlockProps) {
  const [expanded, setExpanded] = useState(true)
  // 默认全部收起，用户需要点击才能展开查看结果
  const [expandedResults, setExpandedResults] = useState<Set<number>>(new Set())
  
  // 合并计划和执行步骤
  const unifiedSteps: UnifiedStep[] = planSteps.map(planStep => {
    const executionStep = executionSteps.find(es => es.step === planStep.step)
    const mergedStep = {
      ...planStep,
      // 优先使用执行步骤的状态和结果
      status: executionStep?.status || planStep.status,
      result: executionStep?.result,
      result_truncated: executionStep?.result_truncated,
      error: executionStep?.error,
      timestamp: executionStep?.timestamp,
    }
    // 调试日志：检查步骤结果
    if (mergedStep.status === 'completed') {
      console.log(`[UnifiedStepsBlock] Step ${mergedStep.step}:`, {
        status: mergedStep.status,
        hasResult: !!mergedStep.result,
        hasError: !!mergedStep.error,
        resultLength: mergedStep.result?.length || 0,
        resultPreview: mergedStep.result?.substring(0, 100) || 'N/A',
        executionStep: executionStep ? {
          step: executionStep.step,
          hasResult: !!executionStep.result,
          hasError: !!executionStep.error
        } : 'not found'
      })
    }
    return mergedStep
  })
  
  // 调试日志：检查推理原因
  console.log('[UnifiedStepsBlock] Props:', {
    planStepsCount: planSteps.length,
    executionStepsCount: executionSteps.length,
    decisionReasoningsCount: decisionReasonings.length,
    decisionReasonings: decisionReasonings
  })
  
  const completedCount = unifiedSteps.filter(s => s.status === 'completed').length
  const totalCount = unifiedSteps.length
  const progressPercent = Math.round((completedCount / totalCount) * 100)
  const runningStep = unifiedSteps.find(s => s.status === 'running')
  const hasNewSteps = unifiedSteps.some(s => s.isNew)
  
  const toggleResult = (stepNumber: number) => {
    setExpandedResults(prev => {
      const newSet = new Set(prev)
      const wasExpanded = newSet.has(stepNumber)
      if (wasExpanded) {
        newSet.delete(stepNumber)
        console.log(`[UnifiedStepsBlock] Collapsing step ${stepNumber}, expandedResults:`, Array.from(newSet))
      } else {
        newSet.add(stepNumber)
        console.log(`[UnifiedStepsBlock] Expanding step ${stepNumber}, expandedResults:`, Array.from(newSet))
      }
      return newSet
    })
  }
  
  if (unifiedSteps.length === 0) {
    return null
  }
  
  return (
    <div className="unified-steps-block">
      {/* Header */}
      <button className="unified-header clickable" onClick={() => setExpanded(!expanded)}>
        <div className="unified-header-left">
          <ListChecks size={18} className="unified-icon" />
          <span className="unified-title">分析步骤</span>
          {hasNewSteps && (
            <Badge variant="outline" className="new-steps-badge">动态调整中</Badge>
          )}
          {runningStep && (
            <Badge variant="outline" className="running-badge">
              正在执行: 步骤 {runningStep.step}
            </Badge>
          )}
        </div>
        <div className="unified-header-right">
          <Badge variant="outline" className="progress-badge">
            {completedCount}/{totalCount}
          </Badge>
          <div className="mini-progress-bar">
            <div 
              className="mini-progress-fill" 
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </div>
      </button>
      
      {expanded && (
        <div className="unified-content">
          <ol className="unified-steps-list">
            {unifiedSteps.map((step, index) => {
              const isResultExpanded = expandedResults.has(step.step)
              const hasResult = step.status === 'completed' || step.status === 'failed'
              
              // 查找在当前步骤之前显示的推理原因
              // 推理原因应该显示在 after_step 之后，before_steps 的第一个步骤之前
              // 只在该推理原因关联的第一个新步骤之前显示一次
              const reasoningBeforeThisStep = decisionReasonings.find(r => {
                if (!r.reasoning || r.after_step === undefined || !r.before_steps || r.before_steps.length === 0) {
                  return false
                }
                // 检查当前步骤是否是该推理原因关联的第一个新步骤
                const firstNewStep = Math.min(...r.before_steps)
                return r.after_step < step.step && step.step === firstNewStep
              })
              
              // 调试日志
              if (hasResult && (step.result || step.error)) {
                console.log(`[UnifiedStepsBlock] Step ${step.step}: isResultExpanded=${isResultExpanded}, hasResult=${hasResult}, resultLength=${step.result?.length || step.error?.length || 0}`)
              }
              if (reasoningBeforeThisStep) {
                console.log(`[UnifiedStepsBlock] Showing reasoning before step ${step.step}:`, reasoningBeforeThisStep)
              }
              
              return (
                <Fragment key={step.step}>
                  {/* 在当前步骤之前显示推理原因（只在第一个新步骤之前显示） */}
                  {reasoningBeforeThisStep && (
                    <li className="decision-reasoning-item">
                      <div className="decision-reasoning-section">
                        <div className="reasoning-header">
                          <Lightbulb size={16} className="reasoning-icon" />
                          <span className="reasoning-title">
                            {reasoningBeforeThisStep.action === 'continue' ? '继续分析原因' : '结束分析原因'}
                          </span>
                        </div>
                        <div className="reasoning-content">
                          {reasoningBeforeThisStep.reasoning}
                        </div>
                      </div>
                    </li>
                  )}
                  <li 
                    className={`unified-step-item step-${step.status} ${step.isNew ? 'new-step' : ''}`}
                  >
                    {/* Status Icon with Connector */}
                    <div className="step-status-column">
                    {step.status === 'completed' && (
                      <CheckCircle2 size={20} className="status-icon completed" />
                    )}
                    {step.status === 'running' && (
                      <Loader2 size={20} className="status-icon running spinning" />
                    )}
                    {step.status === 'failed' && (
                      <XCircle size={20} className="status-icon failed" />
                    )}
                    {step.status === 'pending' && (
                      <Circle size={20} className="status-icon pending" />
                    )}
                    {/* Connector line */}
                    {index < unifiedSteps.length - 1 && (
                      <div className={`step-connector ${step.status === 'completed' ? 'completed' : ''}`} />
                    )}
                  </div>
                  
                  {/* Step Content */}
                  <div className="step-content-column">
                    {/* Step Header */}
                    <div className="step-header">
                      <div className="step-header-left">
                        <span className="step-number">步骤 {step.step}</span>
                        {step.isNew && <Badge variant="outline" className="new-badge">新增</Badge>}
                        <span className="step-action">{step.action}</span>
                      </div>
                      <Badge 
                        variant="outline" 
                        className={`status-badge ${step.status}`}
                      >
                        {step.status === 'completed' && '已完成'}
                        {step.status === 'running' && '执行中'}
                        {step.status === 'failed' && '失败'}
                        {step.status === 'pending' && '等待中'}
                      </Badge>
                    </div>
                    
                    {/* Step Target */}
                    {step.target && (
                      <div className="step-target">
                        <span className="target-arrow">→</span>
                        <code className="target-code">{step.target}</code>
                      </div>
                    )}
                    
                    {/* Step Result - 总是显示结果预览，可展开查看完整内容 */}
                    {hasResult && (step.result || step.error) && (
                      <div className="step-result-section">
                        {step.error ? (
                          <div className="step-error-container">
                            <button 
                              className="result-toggle-button"
                              onClick={() => toggleResult(step.step)}
                            >
                              {isResultExpanded ? (
                                <ChevronDown size={14} />
                              ) : (
                                <ChevronRight size={14} />
                              )}
                              <AlertTriangle size={14} className="error-icon" />
                              <span className="result-label">错误信息</span>
                            </button>
                            {/* 展开时显示完整错误，收起时不显示任何内容 */}
                            {isResultExpanded && (
                              <pre className="error-content">{step.error}</pre>
                            )}
                          </div>
                        ) : step.result ? (
                          <div className="step-result-container">
                            <button 
                              className="result-toggle-button"
                              onClick={() => toggleResult(step.step)}
                            >
                              {isResultExpanded ? (
                                <ChevronDown size={14} />
                              ) : (
                                <ChevronRight size={14} />
                              )}
                              <span className="result-label">执行结果</span>
                              {step.result_truncated && (
                                <Badge variant="outline" className="truncated-badge">已截断</Badge>
                              )}
                            </button>
                            {/* 展开时显示完整内容，收起时不显示任何内容 */}
                            {isResultExpanded && (
                              <pre className="result-content">{step.result}</pre>
                            )}
                          </div>
                        ) : null}
                      </div>
                    )}
                  </div>
                  </li>
                </Fragment>
              )
            })}
          </ol>
        </div>
      )}
    </div>
  )
}
