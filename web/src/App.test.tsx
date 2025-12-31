import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

// Mock fetch
global.fetch = vi.fn()

// Mock useSSE hook
vi.mock('./hooks/useSSE', () => ({
  useSSE: vi.fn(() => ({
    isConnected: false,
    error: null,
  })),
}))

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('应该渲染应用标题', () => {
    render(<App />)

    expect(screen.getByText('Codebase Driven Agent')).toBeInTheDocument()
    expect(
      screen.getByText('基于代码库驱动的智能问题分析平台')
    ).toBeInTheDocument()
  })

  it('应该渲染分析表单', () => {
    render(<App />)

    expect(screen.getByLabelText(/问题描述或错误日志/i)).toBeInTheDocument()
  })

  it('应该在提交后显示结果', async () => {
    const user = userEvent.setup()

    const mockResult = {
      success: true,
      result: {
        root_cause: '测试根因',
        suggestions: ['建议1'],
        confidence: 0.8,
      },
    }

    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => mockResult,
    } as Response)

    render(<App />)

    // 取消流式接口（使用同步接口）
    const checkbox = screen.getByLabelText(/使用流式接口/i)
    await user.click(checkbox)

    const textarea = screen.getByLabelText(/问题描述或错误日志/i)
    await user.type(textarea, '测试问题')

    const submitButton = screen.getByRole('button', { name: /开始分析/i })
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/分析结果/i)).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('应该在 API 错误时显示错误消息', async () => {
    const user = userEvent.setup()

    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      json: async () => ({ detail: 'API 错误' }),
    } as Response)

    render(<App />)

    // 取消流式接口（使用同步接口）
    const checkbox = screen.getByLabelText(/使用流式接口/i)
    await user.click(checkbox)

    const textarea = screen.getByLabelText(/问题描述或错误日志/i)
    await user.type(textarea, '测试问题')

    const submitButton = screen.getByRole('button', { name: /开始分析/i })
    await user.click(submitButton)

    await waitFor(() => {
      // 使用更精确的选择器，避免匹配到 label 中的"错误日志"
      const errorMessage = screen.getByText(/API 错误/i)
      expect(errorMessage).toBeInTheDocument()
      // 验证错误消息在 error-message 容器中
      expect(errorMessage.closest('.error-message')).toBeInTheDocument()
    }, { timeout: 3000 })
  })
})

