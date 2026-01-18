import { Loader2 } from 'lucide-react'
import './ProgressIndicator.css'

interface ProgressIndicatorProps {
  message: string
  progress: number
  step?: string
}

export function ProgressIndicator({ message, progress, step }: ProgressIndicatorProps) {
  const progressValue = Math.max(0, Math.min(1, progress))
  const percentage = Math.round(progressValue * 100)
  
  return (
    <div className="progress-indicator">
      <div className="progress-header">
        <div className="progress-title">
          <Loader2 size={16} className="progress-spinner" />
          <span className="progress-message">{message}</span>
        </div>
        <span className="progress-percentage">{percentage}%</span>
      </div>
      
      <div className="progress-bar-wrapper">
        <div className="progress-bar-track">
          <div 
            className="progress-bar-fill" 
            style={{ width: `${percentage}%` }}
          />
          <div 
            className="progress-bar-glow" 
            style={{ left: `${percentage}%` }}
          />
        </div>
      </div>
      
      {step && (
        <div className="progress-step">
          <span className="step-label">当前步骤:</span>
          <span className="step-value">{step}</span>
        </div>
      )}
    </div>
  )
}
