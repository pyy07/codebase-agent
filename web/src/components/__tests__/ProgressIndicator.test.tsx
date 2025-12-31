import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ProgressIndicator from '../ProgressIndicator'

describe('ProgressIndicator', () => {
  it('应该渲染进度消息和百分比', () => {
    render(
      <ProgressIndicator
        message="正在分析..."
        progress={0.5}
        step="analyzing"
      />
    )

    expect(screen.getByText('正在分析...')).toBeInTheDocument()
    expect(screen.getByText('50%')).toBeInTheDocument()
  })

  it('应该显示进度条', () => {
    const { container } = render(
      <ProgressIndicator
        message="处理中"
        progress={0.75}
      />
    )

    const progressBar = container.querySelector('.progress-bar')
    expect(progressBar).toBeInTheDocument()
    expect(progressBar).toHaveStyle({ width: '75%' })
  })

  it('应该显示步骤信息（如果提供）', () => {
    render(
      <ProgressIndicator
        message="处理中"
        progress={0.5}
        step="searching_code"
      />
    )

    expect(screen.getByText('searching_code')).toBeInTheDocument()
  })

  it('应该正确计算百分比', () => {
    render(
      <ProgressIndicator
        message="测试"
        progress={0.333}
      />
    )

    expect(screen.getByText('33%')).toBeInTheDocument()
  })
})

