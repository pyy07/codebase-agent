import { CheckCircle2, Loader2, XCircle, Circle, ListChecks, ChevronDown, ChevronRight } from "lucide-react"
import { useState } from "react"
import './PlanSteps.css'

interface PlanStep {
  step: number
  action: string
  target: string
  status: "pending" | "running" | "completed" | "failed"
  result?: string
  result_truncated?: boolean
  error?: string
}

interface PlanStepsProps {
  steps: PlanStep[]
}

export default function PlanSteps({ steps }: PlanStepsProps) {
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set())
  
  if (!steps || steps.length === 0) {
    return null
  }

  const completedCount = steps.filter(s => s.status === 'completed').length
  const totalCount = steps.length
  const progressPercent = Math.round((completedCount / totalCount) * 100)
  
  // 检查是否有新增的步骤
  const hasNewSteps = steps.some((s: any) => s.isNew)
  
  const toggleStep = (stepNumber: number) => {
    setExpandedSteps(prev => {
      const newSet = new Set(prev)
      if (newSet.has(stepNumber)) {
        newSet.delete(stepNumber)
      } else {
        newSet.add(stepNumber)
      }
      return newSet
    })
  }

  return (
    <div className="plan-steps">
      {/* Header */}
      <div className="plan-header">
        <div className="plan-title">
          <ListChecks size={18} className="plan-icon" />
          <span>分析计划</span>
          {hasNewSteps && (
            <span className="plan-badge new-steps">动态调整中</span>
          )}
        </div>
        <div className="plan-progress">
          <span className="progress-text">{completedCount}/{totalCount}</span>
          <div className="mini-progress-bar">
            <div 
              className="mini-progress-fill" 
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* Steps List */}
      <div className="plan-content">
        <ol className="steps-list">
          {steps.map((step, index) => {
            const isNewStep = (step as any).isNew
            return (
              <li 
                key={index} 
                className={`step-item step-${step.status} ${isNewStep ? 'new-step' : ''}`}
              >
                {/* Status Icon */}
                <div className="step-status">
                  {step.status === "completed" && (
                    <CheckCircle2 size={18} className="status-icon completed" />
                  )}
                  {step.status === "running" && (
                    <Loader2 size={18} className="status-icon running" />
                  )}
                  {step.status === "failed" && (
                    <XCircle size={18} className="status-icon failed" />
                  )}
                  {step.status === "pending" && (
                    <Circle size={18} className="status-icon pending" />
                  )}
                  {/* Connector line */}
                  {index < steps.length - 1 && (
                    <div className={`step-connector ${step.status === 'completed' ? 'completed' : ''}`} />
                  )}
                </div>

                {/* Step Content */}
                <div className="step-content">
                  <div className="step-action">
                    <span className="step-number">步骤 {step.step}</span>
                    {isNewStep && <span className="new-badge">新增</span>}
                    <span className="step-text">{step.action}</span>
                  </div>
                  {step.target && (
                    <div className="step-target">
                      <span className="target-arrow">→</span>
                      <span className="target-text">{step.target}</span>
                    </div>
                  )}
                  
                  {/* 执行结果 */}
                  {(step.status === 'completed' || step.status === 'failed') && (step.result || step.error) && (
                    <div className="step-result-container">
                      <button 
                        className="step-result-toggle"
                        onClick={() => toggleStep(step.step)}
                      >
                        {expandedSteps.has(step.step) ? (
                          <ChevronDown size={16} />
                        ) : (
                          <ChevronRight size={16} />
                        )}
                        <span className="step-result-label">
                          {step.status === 'failed' ? '错误信息' : '执行结果'}
                        </span>
                        {step.result_truncated && (
                          <span className="result-truncated-badge">已截断</span>
                        )}
                      </button>
                      {expandedSteps.has(step.step) && (
                        <div className="step-result-content">
                          {step.status === 'failed' && step.error ? (
                            <pre className="step-error">{step.error}</pre>
                          ) : step.result ? (
                            <pre className="step-result">{step.result}</pre>
                          ) : null}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </li>
            )
          })}
        </ol>
      </div>
    </div>
  )
}
