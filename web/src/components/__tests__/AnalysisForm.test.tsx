import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AnalysisForm from '../AnalysisForm'

describe('AnalysisForm', () => {
  const mockOnSubmit = vi.fn()

  beforeEach(() => {
    mockOnSubmit.mockClear()
    localStorage.clear()
  })

  it('应该渲染表单元素', () => {
    render(<AnalysisForm onSubmit={mockOnSubmit} loading={false} />)

    expect(screen.getByLabelText(/问题描述或错误日志/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/上下文文件/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /开始分析/i })).toBeInTheDocument()
  })

  it('应该允许用户输入文本', async () => {
    const user = userEvent.setup()
    render(<AnalysisForm onSubmit={mockOnSubmit} loading={false} />)

    const textarea = screen.getByLabelText(/问题描述或错误日志/i)
    await user.type(textarea, '测试问题描述')

    expect(textarea).toHaveValue('测试问题描述')
  })

  it('应该在提交时调用 onSubmit', async () => {
    const user = userEvent.setup()
    render(<AnalysisForm onSubmit={mockOnSubmit} loading={false} />)

    const textarea = screen.getByLabelText(/问题描述或错误日志/i)
    await user.type(textarea, '测试问题')

    const submitButton = screen.getByRole('button', { name: /开始分析/i })
    await user.click(submitButton)

    expect(mockOnSubmit).toHaveBeenCalledTimes(1)
    expect(mockOnSubmit).toHaveBeenCalledWith('测试问题', [], true)
  })

  it('应该在输入为空时阻止提交', async () => {
    const user = userEvent.setup()
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})

    render(<AnalysisForm onSubmit={mockOnSubmit} loading={false} />)

    const textarea = screen.getByLabelText(/问题描述或错误日志/i)
    // 确保 textarea 为空
    await user.clear(textarea)

    const submitButton = screen.getByRole('button', { name: /开始分析/i })
    
    // 由于 textarea 有 required 属性，浏览器会阻止表单提交
    // 我们需要移除 required 属性来测试我们的自定义验证逻辑
    textarea.removeAttribute('required')
    
    // 现在可以触发提交
    await user.click(submitButton)

    // 等待 alert 被调用
    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalledWith('请输入问题描述')
    })
    
    expect(mockOnSubmit).not.toHaveBeenCalled()

    alertSpy.mockRestore()
  })

  it('应该允许用户上传文件', async () => {
    const user = userEvent.setup()
    render(<AnalysisForm onSubmit={mockOnSubmit} loading={false} />)

    const fileInput = screen.getByLabelText(/上下文文件/i)
    const file = new File(['文件内容'], 'test.py', { type: 'text/plain' })

    await user.upload(fileInput, file)

    // 等待状态更新
    await waitFor(() => {
      expect(screen.getByText(/已选择文件/i)).toBeInTheDocument()
      expect(screen.getByText('test.py')).toBeInTheDocument()
    })
  })

  it('应该保存和读取 API Key', async () => {
    const user = userEvent.setup()
    render(<AnalysisForm onSubmit={mockOnSubmit} loading={false} />)

    const apiKeyInput = screen.getByLabelText(/API Key/i)
    await user.type(apiKeyInput, 'test-api-key')

    expect(localStorage.getItem('apiKey')).toBe('test-api-key')
  })

  it('应该在加载时禁用提交按钮', () => {
    render(<AnalysisForm onSubmit={mockOnSubmit} loading={true} />)

    const submitButton = screen.getByRole('button', { name: /分析中/i })
    expect(submitButton).toBeDisabled()
  })

  it('应该允许切换流式接口', async () => {
    const user = userEvent.setup()
    render(<AnalysisForm onSubmit={mockOnSubmit} loading={false} />)

    const checkbox = screen.getByLabelText(/使用流式接口/i)
    expect(checkbox).toBeChecked()

    await user.click(checkbox)
    expect(checkbox).not.toBeChecked()

    const textarea = screen.getByLabelText(/问题描述或错误日志/i)
    await user.type(textarea, '测试问题')

    const submitButton = screen.getByRole('button', { name: /开始分析/i })
    await user.click(submitButton)

    expect(mockOnSubmit).toHaveBeenCalledWith('测试问题', [], false)
  })
})

