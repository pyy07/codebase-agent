import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import UnifiedStepsBlock from '../UnifiedStepsBlock'
import type { PlanStep, ExecutionStep, UserInputRequest, UserReply } from '../../types'

describe('UnifiedStepsBlock - User Interaction', () => {
  const mockOnSubmitUserReply = vi.fn()
  const mockOnSkipUserInput = vi.fn()

  beforeEach(() => {
    mockOnSubmitUserReply.mockClear()
    mockOnSkipUserInput.mockClear()
  })

  it('应该显示用户输入请求步骤', () => {
    const planSteps: PlanStep[] = [
      { step: 1, action: 'read', target: 'test.py' }
    ]
    
    const executionSteps: ExecutionStep[] = [
      {
        step: 1,
        action: 'read',
        target: 'test.py',
        status: 'completed',
        result: '文件内容'
      }
    ]

    const userInputRequests: UserInputRequest[] = [
      {
        request_id: 'test-request-id',
        question: '请提供更多信息',
        context: '需要错误日志'
      }
    ]

    render(
      <UnifiedStepsBlock
        planSteps={planSteps}
        executionSteps={executionSteps}
        userInputRequests={userInputRequests}
        onSubmitUserReply={mockOnSubmitUserReply}
        onSkipUserInput={mockOnSkipUserInput}
      />
    )

    // 应该显示用户输入请求（可能在步骤内容或模态对话框中）
    const elements = screen.getAllByText('请提供更多信息')
    expect(elements.length).toBeGreaterThan(0)
  })

  it('应该显示用户回复步骤', () => {
    const planSteps: PlanStep[] = [
      { step: 1, action: 'read', target: 'test.py' }
    ]
    
    const executionSteps: ExecutionStep[] = [
      {
        step: 1,
        action: 'read',
        target: 'test.py',
        status: 'completed',
        result: '文件内容'
      }
    ]

    const userInputRequests: UserInputRequest[] = [
      {
        request_id: 'test-request-id',
        question: '请提供更多信息'
      }
    ]

    const userReplies: UserReply[] = [
      {
        request_id: 'test-request-id',
        reply: '错误信息：Connection refused'
      }
    ]

    render(
      <UnifiedStepsBlock
        planSteps={planSteps}
        executionSteps={executionSteps}
        userInputRequests={userInputRequests}
        userReplies={userReplies}
        onSubmitUserReply={mockOnSubmitUserReply}
        onSkipUserInput={mockOnSkipUserInput}
      />
    )

    // 应该显示用户回复
    expect(screen.getByText('错误信息：Connection refused')).toBeInTheDocument()
  })

  it('应该将用户交互作为独立步骤显示', () => {
    const planSteps: PlanStep[] = [
      { step: 1, action: 'read', target: 'test.py' },
      { step: 2, action: 'read', target: 'test2.py' }
    ]
    
    const executionSteps: ExecutionStep[] = [
      {
        step: 1,
        action: 'read',
        target: 'test.py',
        status: 'completed',
        result: '文件内容'
      }
    ]

    const userInputRequests: UserInputRequest[] = [
      {
        request_id: 'test-request-id',
        question: '请提供更多信息'
      }
    ]

    const userReplies: UserReply[] = [
      {
        request_id: 'test-request-id',
        reply: '错误信息'
      }
    ]

    render(
      <UnifiedStepsBlock
        planSteps={planSteps}
        executionSteps={executionSteps}
        userInputRequests={userInputRequests}
        userReplies={userReplies}
        onSubmitUserReply={mockOnSubmitUserReply}
        onSkipUserInput={mockOnSkipUserInput}
      />
    )

    // 用户交互应该作为步骤显示在流程中
    // 步骤编号应该正确（用户交互步骤应该在步骤1和步骤2之间）
    expect(screen.getByText(/用户交互/i)).toBeInTheDocument()
  })

  it('应该在用户输入请求时显示模态对话框', async () => {
    const planSteps: PlanStep[] = [
      { step: 1, action: 'read', target: 'test.py' }
    ]
    
    const executionSteps: ExecutionStep[] = [
      {
        step: 1,
        action: 'read',
        target: 'test.py',
        status: 'completed',
        result: '文件内容'
      }
    ]

    const userInputRequests: UserInputRequest[] = [
      {
        request_id: 'test-request-id',
        question: '请提供更多信息'
      }
    ]

    render(
      <UnifiedStepsBlock
        planSteps={planSteps}
        executionSteps={executionSteps}
        userInputRequests={userInputRequests}
        onSubmitUserReply={mockOnSubmitUserReply}
        onSkipUserInput={mockOnSkipUserInput}
      />
    )

    // 应该自动弹出模态对话框（文本可能在多个地方出现）
    await waitFor(() => {
      const elements = screen.getAllByText('请提供更多信息')
      expect(elements.length).toBeGreaterThan(0)
    })
  })
})
