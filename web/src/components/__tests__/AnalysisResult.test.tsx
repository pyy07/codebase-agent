import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import AnalysisResult from '../AnalysisResult'
import { AnalysisResult as AnalysisResultType } from '../../types'

describe('AnalysisResult', () => {
  const mockResult: AnalysisResultType = {
    root_cause: '测试根因分析',
    suggestions: ['建议1：测试建议', '建议2：另一个建议'],
    confidence: 0.85,
    related_code: [
      {
        file: 'test.py',
        lines: [10, 20],
        description: '相关代码说明',
      },
    ],
    related_logs: [
      {
        timestamp: '2024-01-01 10:00:00',
        content: '错误日志内容',
        description: '日志说明',
      },
    ],
  }

  it('应该渲染根因分析', () => {
    render(<AnalysisResult result={mockResult} />)

    expect(screen.getByText(/根本原因/i)).toBeInTheDocument()
    // ReactMarkdown 会将文本包装在段落中
    expect(screen.getByText(/测试根因分析/)).toBeInTheDocument()
  })

  it('应该渲染处理建议', () => {
    render(<AnalysisResult result={mockResult} />)

    expect(screen.getByText(/处理建议/i)).toBeInTheDocument()
    // ReactMarkdown 会将文本包装，使用正则表达式匹配
    expect(screen.getByText(/建议1：测试建议/)).toBeInTheDocument()
    expect(screen.getByText(/建议2：另一个建议/)).toBeInTheDocument()
  })

  it('应该显示置信度', () => {
    render(<AnalysisResult result={mockResult} />)

    expect(screen.getByText(/置信度/i)).toBeInTheDocument()
    expect(screen.getByText(/85%/i)).toBeInTheDocument()
  })

  it('应该渲染相关代码', () => {
    render(<AnalysisResult result={mockResult} />)

    // 使用 getByRole 查找标题，避免与描述文本冲突
    expect(screen.getByRole('heading', { name: /相关代码/i })).toBeInTheDocument()
    expect(screen.getByText('test.py')).toBeInTheDocument()
    // 注意：行号格式是 "行 10-20"，需要匹配完整文本
    expect(screen.getByText(/行 10-20/)).toBeInTheDocument()
  })

  it('应该渲染相关日志', () => {
    render(<AnalysisResult result={mockResult} />)

    expect(screen.getByText(/相关日志/i)).toBeInTheDocument()
    expect(screen.getByText('2024-01-01 10:00:00')).toBeInTheDocument()
    // 日志内容在 <pre> 标签中，需要查找包含该文本的元素
    expect(screen.getByText(/错误日志内容/)).toBeInTheDocument()
  })

  it('应该在没有相关代码时不显示相关代码部分', () => {
    const resultWithoutCode = {
      ...mockResult,
      related_code: undefined,
    }

    render(<AnalysisResult result={resultWithoutCode} />)

    expect(screen.queryByText(/相关代码/i)).not.toBeInTheDocument()
  })

  it('应该显示思考过程折叠按钮', () => {
    render(<AnalysisResult result={mockResult} />)

    // 按钮文本是 "显示 Agent 思考过程" 或 "隐藏 Agent 思考过程"
    expect(screen.getByRole('button', { name: /Agent 思考过程/i })).toBeInTheDocument()
  })
})

