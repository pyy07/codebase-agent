import { useState } from 'react'
import { MessageSquare, Send, Loader2 } from 'lucide-react'
import { UserInputRequestData } from '../types'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import './UserInputRequest.css'

interface UserInputRequestProps {
  request: UserInputRequestData
  onSubmit: (requestId: string, reply: string) => Promise<void>
}

export default function UserInputRequest({ request, onSubmit }: UserInputRequestProps) {
  const [reply, setReply] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!reply.trim() || isSubmitting) {
      return
    }

    setIsSubmitting(true)
    try {
      await onSubmit(request.request_id, reply.trim())
      setReply('') // 清空输入框
    } catch (error) {
      console.error('Error submitting reply:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="user-input-request">
      <div className="request-header">
        <MessageSquare size={18} className="request-icon" />
        <span className="request-title">Agent 需要您的帮助</span>
      </div>
      
      <div className="request-content">
        <div className="request-question">
          <strong>问题：</strong>
          <p>{request.question}</p>
        </div>
        
        {request.context && (
          <div className="request-context">
            <strong>上下文：</strong>
            <p>{request.context}</p>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="reply-form">
        <Textarea
          value={reply}
          onChange={(e) => setReply(e.target.value)}
          placeholder="请输入您的回复..."
          className="reply-input"
          rows={3}
          disabled={isSubmitting}
        />
        <Button
          type="submit"
          disabled={!reply.trim() || isSubmitting}
          className="reply-submit-button"
        >
          {isSubmitting ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              提交中...
            </>
          ) : (
            <>
              <Send size={16} />
              提交回复
            </>
          )}
        </Button>
      </form>
    </div>
  )
}
