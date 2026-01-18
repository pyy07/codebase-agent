import { CheckCircle2, Loader2, XCircle, Circle, ListChecks } from "lucide-react"
import './PlanSteps.css'

interface PlanStep {
  step: number
  action: string
  target: string
  status: "pending" | "running" | "completed" | "failed"
}

interface PlanStepsProps {
  steps: PlanStep[]
}

export default function PlanSteps({ steps }: PlanStepsProps) {
  if (!steps || steps.length === 0) {
    return null
  }

  const completedCount = steps.filter(s => s.status === 'completed').length
  const totalCount = steps.length
  const progressPercent = Math.round((completedCount / totalCount) * 100)

  return (
    <div className="plan-steps">
      {/* Header */}
      <div className="plan-header">
        <div className="plan-title">
          <ListChecks size={18} className="plan-icon" />
          <span>分析计划</span>
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
          {steps.map((step, index) => (
            <li 
              key={index} 
              className={`step-item step-${step.status}`}
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
                  <span className="step-text">{step.action}</span>
                </div>
                {step.target && (
                  <div className="step-target">
                    <span className="target-arrow">→</span>
                    <span className="target-text">{step.target}</span>
                  </div>
                )}
              </div>
            </li>
          ))}
        </ol>
      </div>
    </div>
  )
}
