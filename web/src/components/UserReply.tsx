import { User } from 'lucide-react'
import { UserReplyData } from '../types'
import './UserReply.css'

interface UserReplyProps {
  reply: UserReplyData
}

export default function UserReply({ reply }: UserReplyProps) {
  return (
    <div className="user-reply">
      <div className="reply-header">
        <User size={16} className="reply-icon" />
        <span className="reply-label">您的回复</span>
      </div>
      <div className="reply-content">
        {reply.reply}
      </div>
    </div>
  )
}
