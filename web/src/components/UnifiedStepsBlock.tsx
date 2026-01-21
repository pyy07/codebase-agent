import { useState, Fragment, useEffect } from 'react'
import { CheckCircle2, Loader2, XCircle, Circle, ListChecks, ChevronDown, ChevronRight, AlertTriangle, Lightbulb, MessageSquare, Send, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose } from '@/components/ui/dialog'
import { PlanStep, StepExecutionData, DecisionReasoningData, UserInputRequestData, UserReplyData } from '../types'
import './UnifiedStepsBlock.css'
import './UserInputModal.css'

interface UnifiedStep extends PlanStep {
  result?: string
  result_truncated?: boolean
  error?: string
  timestamp?: Date
  isNew?: boolean
  userInputRequest?: UserInputRequestData  // 用户输入请求
  userReply?: UserReplyData  // 用户回复
}

interface UnifiedStepsBlockProps {
  planSteps: PlanStep[]
  executionSteps: StepExecutionData[]
  decisionReasonings?: DecisionReasoningData[]  // 支持多个推理原因
  userInputRequests?: UserInputRequestData[]  // 用户输入请求列表
  userReplies?: UserReplyData[]  // 用户回复列表
  onSubmitUserReply?: (requestId: string, reply: string) => Promise<void>
  onSkipUserInput?: (requestId: string) => Promise<void>
}

export default function UnifiedStepsBlock({ 
  planSteps, 
  executionSteps, 
  decisionReasonings = [],
  userInputRequests = [],
  userReplies = [],
  onSubmitUserReply,
  onSkipUserInput
}: UnifiedStepsBlockProps) {
  const [expanded, setExpanded] = useState(true)
  // 默认全部收起，用户需要点击才能展开查看结果
  const [expandedResults, setExpandedResults] = useState<Set<number>>(new Set())
  const [openModalRequestId, setOpenModalRequestId] = useState<string | null>(null)
  
  // 自动打开未回复的用户输入请求的对话框
  useEffect(() => {
    // 查找未回复的用户输入请求
    const unrepliedRequest = userInputRequests.find(req => {
      const hasReply = userReplies.some(reply => reply.request_id === req.request_id)
      return !hasReply
    })
    
    // 如果有未回复的请求且对话框未打开，自动打开
    if (unrepliedRequest && openModalRequestId !== unrepliedRequest.request_id) {
      setOpenModalRequestId(unrepliedRequest.request_id)
    }
  }, [userInputRequests, userReplies, openModalRequestId])
  
  // 合并计划和执行步骤，并将用户交互作为独立步骤插入
  // 构建包含用户交互步骤的完整步骤列表
  const unifiedSteps: UnifiedStep[] = []
  const insertedRequestIds = new Set<string>() // 跟踪已插入的请求ID
  
  // 首先处理所有计划步骤
  planSteps.forEach((planStep, index) => {
    const executionStep = executionSteps.find(es => es.step === planStep.step)
    
    const mergedStep: UnifiedStep = {
      ...planStep,
      // 优先使用执行步骤的状态和结果
      status: executionStep?.status || planStep.status,
      result: executionStep?.result,
      result_truncated: executionStep?.result_truncated,
      error: executionStep?.error,
      timestamp: executionStep?.timestamp,
    }
    
    unifiedSteps.push(mergedStep)
    
    // 在当前步骤完成后，检查是否有用户输入请求
    // 用户输入请求应该插入在当前步骤之后，下一个步骤之前
    if (executionStep?.status === 'completed') {
      // 查找应该插入在当前步骤之后的用户输入请求
      // 简单策略：如果这是最后一个已完成的步骤，或者请求时间戳在当前步骤之后
      const currentStepTimestamp = executionStep.timestamp
      const isLastCompletedStep = !planSteps.slice(index + 1).some(ps => {
        const es = executionSteps.find(e => e.step === ps.step)
        return es?.status === 'completed'
      })
      
      // 查找未插入的用户输入请求
      const pendingRequest = userInputRequests.find(request => {
        if (insertedRequestIds.has(request.request_id)) {
          return false // 已经插入过
        }
        
        // 如果这是最后一个已完成的步骤，或者请求时间戳在当前步骤之后，则插入
        if (isLastCompletedStep) {
          return true
        }
        
        const requestTimestamp = request.timestamp
        return requestTimestamp && currentStepTimestamp && requestTimestamp >= currentStepTimestamp
      })
      
      if (pendingRequest) {
        insertedRequestIds.add(pendingRequest.request_id)
        
        // 查找对应的用户回复
        const reply = userReplies.find(r => r.request_id === pendingRequest.request_id)
        
        // 插入用户输入请求步骤（包含用户回复，如果有的话）
        const userInputStep: UnifiedStep = {
          step: planStep.step + 0.5, // 使用小数步骤号，表示这是插入的步骤
          action: reply ? '用户交互' : '请求用户输入',
          target: reply ? reply.reply : pendingRequest.question,
          status: reply ? 'completed' : 'running',
          userInputRequest: pendingRequest,
          userReply: reply,
          timestamp: pendingRequest.timestamp,
        }
        
        unifiedSteps.push(userInputStep)
      }
    }
  })
  
  // 按步骤号排序
  unifiedSteps.sort((a, b) => a.step - b.step)
  
  // 重新编号步骤，使其连续
  unifiedSteps.forEach((step, index) => {
    step.step = index + 1
  })
  
  // 调试日志：检查步骤结果
  unifiedSteps.forEach((step) => {
    if (step.status === 'completed') {
      console.log(`[UnifiedStepsBlock] Step ${step.step}:`, {
        status: step.status,
        hasResult: !!step.result,
        hasError: !!step.error,
        resultLength: step.result?.length || 0,
        resultPreview: step.result?.substring(0, 100) || 'N/A',
        isUserInteraction: !!(step.userInputRequest || step.userReply)
      })
    }
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
              // 用户交互步骤的结果就是回复内容，不需要展开/收起
              const hasResult = (!step.userInputRequest && !step.userReply) && 
                                (step.status === 'completed' || step.status === 'failed')
              
              // 查找在当前步骤之前显示的推理原因
              // 推理原因应该显示在 after_step 之后，before_steps 的第一个步骤之前
              // 但是，如果 after_step 之后有用户交互步骤，推理原因应该显示在用户交互步骤之后
              const reasoningBeforeThisStep = decisionReasonings.find(r => {
                if (!r.reasoning || r.after_step === undefined || !r.before_steps || r.before_steps.length === 0) {
                  return false
                }
                
                // 如果当前步骤是用户交互步骤，不显示推理原因
                if (step.userInputRequest || step.userReply) {
                  return false
                }
                
                // 检查 after_step 对应的原始步骤号
                const afterStepOriginalNumber = r.after_step
                
                // 查找 after_step 对应的步骤在 unifiedSteps 中的位置（非用户交互步骤）
                const afterStepIndex = unifiedSteps.findIndex((s, idx) => 
                  !s.userInputRequest && !s.userReply && s.step === afterStepOriginalNumber
                )
                
                if (afterStepIndex < 0) {
                  // 如果找不到 after_step 对应的步骤，使用原来的逻辑
                  const firstNewStep = Math.min(...r.before_steps)
                  return r.after_step < step.step && step.step === firstNewStep
                }
                
                // 检查 after_step 之后是否有用户交互步骤
                const userInteractionAfterIndex = unifiedSteps.findIndex((s, idx) => 
                  idx > afterStepIndex && s.userInputRequest && s.userReply
                )
                
                if (userInteractionAfterIndex >= 0) {
                  // 如果有用户交互步骤，推理原因应该显示在用户交互步骤之后，第一个新步骤之前
                  // 第一个新步骤是 before_steps 中的最小值
                  const firstNewStep = Math.min(...r.before_steps)
                  
                  // 检查当前步骤是否是用户交互步骤之后的第一个新步骤
                  // 当前步骤应该在用户交互步骤之后，且是第一个新步骤
                  if (index > userInteractionAfterIndex && step.step === firstNewStep) {
                    return true
                  }
                } else {
                  // 如果没有用户交互步骤，使用原来的逻辑
                  const firstNewStep = Math.min(...r.before_steps)
                  return afterStepOriginalNumber < step.step && step.step === firstNewStep
                }
                
                return false
              })
              
              // 调试日志
              if (hasResult && (step.result || step.error)) {
                console.log(`[UnifiedStepsBlock] Step ${step.step}: isResultExpanded=${isResultExpanded}, hasResult=${hasResult}, resultLength=${step.result?.length || step.error?.length || 0}`)
              }
              if (reasoningBeforeThisStep) {
                console.log(`[UnifiedStepsBlock] Showing reasoning before step ${step.step}:`, reasoningBeforeThisStep)
              }
              
              // 检查是否应该在用户交互步骤之后显示推理原因
              // 如果前一个步骤是用户交互步骤（已完成），且当前步骤是第一个新步骤，则显示推理原因
              const prevStep = index > 0 ? unifiedSteps[index - 1] : null
              const isAfterUserInteraction = prevStep?.userInputRequest && prevStep?.userReply && prevStep?.status === 'completed'
              const shouldShowReasoningAfterInteraction = isAfterUserInteraction && reasoningBeforeThisStep
              
              return (
                <Fragment key={step.step}>
                  {/* 在当前步骤之前显示推理原因（只在第一个新步骤之前显示） */}
                  {/* 如果前一个步骤是用户交互步骤，推理原因应该显示在用户交互步骤之后 */}
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
                    
                    {/* 用户输入请求步骤的特殊显示 */}
                    {step.userInputRequest && (
                      <div className="step-user-interaction-full">
                        <div className="user-interaction-header">
                          <MessageSquare size={16} className="interaction-icon" />
                          <span className="interaction-title">Agent 提问</span>
                        </div>
                        <div className="user-request-display">
                          <strong>问题：</strong>
                          <p>{step.userInputRequest.question}</p>
                          {step.userInputRequest.context && (
                            <>
                              <strong>上下文：</strong>
                              <p>{step.userInputRequest.context}</p>
                            </>
                          )}
                        </div>
                        {step.userReply && (
                          <div className="user-reply-display">
                            <strong>您的回复：</strong>
                            <p>{step.userReply.reply}</p>
                          </div>
                        )}
                      </div>
                    )}
                    
                    
                    {/* Step Target - 只在非用户交互步骤中显示 */}
                    {!step.userInputRequest && !step.userReply && step.target && (
                      <div className="step-target">
                        <span className="target-arrow">→</span>
                        <code className="target-code">{step.target}</code>
                      </div>
                    )}
                    
                    {/* Step Result - 只在非用户交互步骤中显示 */}
                    {!step.userInputRequest && !step.userReply && hasResult && (step.result || step.error) && (
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
      
      {/* User Input Modal Dialog */}
      {openModalRequestId && (() => {
        const request = userInputRequests.find(r => r.request_id === openModalRequestId)
        if (!request) return null
        
        return (
          <UserInputModal
            request={request}
            onSubmit={async (reply: string) => {
              // 立即关闭对话框
              setOpenModalRequestId(null)
              // 然后提交回复（不等待响应）
              if (onSubmitUserReply) {
                onSubmitUserReply(request.request_id, reply).catch((error) => {
                  console.error('Error submitting reply:', error)
                })
              }
            }}
            onSkip={async () => {
              // 立即关闭对话框
              setOpenModalRequestId(null)
              // 然后执行跳过（不等待响应）
              if (onSkipUserInput) {
                onSkipUserInput(request.request_id).catch((error) => {
                  console.error('Error skipping input:', error)
                })
              }
            }}
            onCancel={() => {
              // onCancel 不再使用，但保留接口兼容性
              setOpenModalRequestId(null)
            }}
          />
        )
      })()}
    </div>
  )
}

// User Input Modal Component
interface UserInputModalProps {
  request: UserInputRequestData
  onSubmit: (reply: string) => Promise<void>
  onSkip: () => Promise<void>
  onCancel: () => void
}

function UserInputModal({ request, onSubmit, onSkip, onCancel }: UserInputModalProps) {
  const [reply, setReply] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!reply.trim() || isSubmitting) return
    
    const replyText = reply.trim()
    setIsSubmitting(true)
    
    // 立即关闭对话框，不等待后端响应
    // 用户回复会立即显示在主界面，后续分析通过 SSE 流式更新
    onSubmit(replyText).catch((error) => {
      console.error('Error submitting reply:', error)
      // 错误会通过 handleError 显示，不影响对话框关闭
    })
    
    // 对话框会在 onSubmit 调用后立即关闭（因为 onSubmit 立即返回）
  }
  
  const handleClose = async () => {
    if (isSubmitting) return
    setIsSubmitting(true)
    
    // 立即关闭对话框，不等待后端响应
    // 跳过操作会在后台执行，后续分析通过 SSE 流式更新
    onSkip().catch((error) => {
      console.error('Error closing/skipping input:', error)
      // 错误会通过 handleError 显示，不影响对话框关闭
    })
    
    // 对话框会在 onSkip 调用后立即关闭（因为 onSkip 立即返回）
  }
  
  const isDark = document.documentElement.classList.contains('dark')
  
  return (
    <Dialog open={true} onOpenChange={(open) => {
      if (!open && !isSubmitting) {
        handleClose()
      }
    }}>
      <DialogContent>
        <DialogClose onClose={handleClose} />
        <div className="user-input-modal-content">
          <div className="user-input-modal-header">
            <div className="user-input-modal-title">
              <MessageSquare size={20} className="user-input-modal-title-icon" />
              <span>Agent 需要您的帮助</span>
            </div>
            <div className="user-input-modal-description">
              请提供以下信息以继续分析
            </div>
          </div>
          
          <div className="user-input-modal-section">
            <label className="user-input-modal-section-label">问题</label>
            <div className="user-input-modal-section-content">
              {request.question}
            </div>
          </div>
          
          {request.context && (
            <div className="user-input-modal-section">
              <label className="user-input-modal-section-label">上下文</label>
              <div className="user-input-modal-section-content">
                {request.context}
              </div>
            </div>
          )}
          
          <form onSubmit={handleSubmit} className="user-input-modal-form">
            <label htmlFor="reply-input" className="user-input-modal-label">
              您的回复
            </label>
            <textarea
              id="reply-input"
              value={reply}
              onChange={(e) => setReply(e.target.value)}
              placeholder="请输入您的回复..."
              className="user-input-modal-textarea"
              disabled={isSubmitting}
              rows={5}
            />
            
            <div className="user-input-modal-footer">
              <button
                type="button"
                onClick={handleClose}
                disabled={isSubmitting}
                className="user-input-modal-button user-input-modal-button-secondary"
              >
                关闭（不提供信息）
              </button>
              <button
                type="submit"
                disabled={!reply.trim() || isSubmitting}
                className="user-input-modal-button user-input-modal-button-primary"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 size={16} className="user-input-modal-button-icon user-input-modal-spinner" />
                    提交中...
                  </>
                ) : (
                  <>
                    <Send size={16} className="user-input-modal-button-icon" />
                    提交回复
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </DialogContent>
    </Dialog>
  )
}
