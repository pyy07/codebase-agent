import React from 'react'
import './ProgressIndicator.css'

interface ProgressIndicatorProps {
  message: string
  progress: number
  step?: string
}

const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({
  message,
  progress,
  step,
}) => {
  // 确保进度值在 0-1 之间
  const normalizedProgress = Math.max(0, Math.min(1, progress))
  
  // 调试日志
  console.log('ProgressIndicator render:', { message, progress, normalizedProgress, step })
  
  return (
    <div className="progress-indicator">
      <div className="progress-header">
        <span className="progress-message">{message}</span>
        <span className="progress-percentage">{Math.round(normalizedProgress * 100)}%</span>
      </div>
      <div className="progress-bar-container">
        <div
          className="progress-bar"
          style={{ width: `${normalizedProgress * 100}%` }}
        />
      </div>
      {step && <div className="progress-step">{step}</div>}
    </div>
  )
}

export default ProgressIndicator

