import { User, Bot, Sparkles } from 'lucide-react'
import { ChatMessage } from '../types'
import AgentMessage from './AgentMessage'
import './MessageList.css'

interface MessageListProps {
  messages: ChatMessage[]
  onSubmitUserReply?: (requestId: string, reply: string) => Promise<void>
}

export default function MessageList({ messages, onSubmitUserReply }: MessageListProps) {
  if (messages.length === 0) {
    return (
      <div className="empty-chat">
        <div className="empty-icon">
          <Sparkles size={40} />
        </div>
        <h2>Codebase Agent</h2>
        <p>AI 驱动的代码分析助手</p>
        <div className="suggestions">
          <span>分析错误日志</span>
          <span className="dot">·</span>
          <span>排查代码问题</span>
          <span className="dot">·</span>
          <span>查询数据库</span>
        </div>
      </div>
    )
  }

  return (
    <div className="message-list">
      {messages.map((message) => (
        <div 
          key={message.id} 
          className={`message-item ${message.role}`}
        >
          {/* Avatar */}
          <div className="message-avatar">
            {message.role === 'user' ? (
              <div className="avatar user-avatar">
                <User size={18} />
              </div>
            ) : (
              <div className="avatar assistant-avatar">
                <Bot size={18} />
              </div>
            )}
          </div>

          {/* Content */}
          <div className="message-content">
            {message.role === 'user' ? (
              <UserMessageContent message={message} />
            ) : (
              <AgentMessage message={message} onSubmitUserReply={onSubmitUserReply} />
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

// User message content renderer
function UserMessageContent({ message }: { message: ChatMessage }) {
  return (
    <div className="user-message-content">
      {message.content.map((content, index) => {
        if (content.type === 'text') {
          // Check if it's an image attachment info
          if (typeof content.data === 'object' && content.data.type === 'image') {
            return (
              <div key={index} className="attached-image">
                <img src={content.data.preview} alt={content.data.name} />
                <span className="image-name">{content.data.name}</span>
              </div>
            )
          }
          // Regular text
          return (
            <p key={index} className="user-text">{content.data}</p>
          )
        }
        return null
      })}
    </div>
  )
}

