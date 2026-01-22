import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import UserReply from '../UserReply'
import type { UserReply as UserReplyType } from '../../types'

describe('UserReply', () => {
  const mockReply: UserReplyType = {
    request_id: 'test-request-id',
    reply: '错误信息：Connection refused，发生在数据库连接时'
  }

  it('应该渲染用户回复内容', () => {
    render(<UserReply reply={mockReply} />)

    expect(screen.getByText('错误信息：Connection refused，发生在数据库连接时')).toBeInTheDocument()
  })

  it('应该显示回复标签', () => {
    render(<UserReply reply={mockReply} />)

    // 检查是否有"用户回复"或类似的标签
    expect(screen.getByText(/用户回复|您的回复/i)).toBeInTheDocument()
  })

  it('应该处理空回复', () => {
    const emptyReply = {
      ...mockReply,
      reply: ''
    }
    render(<UserReply reply={emptyReply} />)

    // 空回复应该仍然渲染，可能显示占位文本
    expect(screen.getByText(/用户回复|您的回复/i)).toBeInTheDocument()
  })

  it('应该处理长回复', () => {
    const longReply = {
      ...mockReply,
      reply: '这是一个很长的回复内容。'.repeat(100)
    }
    render(<UserReply reply={longReply} />)

    expect(screen.getByText(longReply.reply)).toBeInTheDocument()
  })
})
