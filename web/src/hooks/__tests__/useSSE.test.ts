import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useSSE } from '../useSSE'

// Mock fetch
global.fetch = vi.fn()

describe('useSSE', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('应该在 URL 为空时不连接', async () => {
    const onProgress = vi.fn()
    const onResult = vi.fn()

    renderHook(() =>
      useSSE('', null, {
        onProgress,
        onResult,
      })
    )

    // 等待 useEffect 执行
    await new Promise(resolve => setTimeout(resolve, 100))
    expect(fetch).not.toHaveBeenCalled()
  })

  it('应该在 body 为空时不连接', async () => {
    const onProgress = vi.fn()
    const onResult = vi.fn()

    renderHook(() =>
      useSSE('/api/v1/analyze/stream', null, {
        onProgress,
        onResult,
      })
    )

    // 等待 useEffect 执行
    await new Promise(resolve => setTimeout(resolve, 100))
    expect(fetch).not.toHaveBeenCalled()
  })

  it('应该使用 API Key（如果存在）', async () => {
    localStorage.setItem('apiKey', 'test-key')

    const mockReader = {
      read: vi.fn().mockResolvedValue({ done: true }),
    }

    const mockResponse = {
      ok: true,
      body: {
        getReader: () => mockReader,
      },
    }

    vi.mocked(fetch).mockResolvedValue(mockResponse as any)

    renderHook(() =>
      useSSE('/api/v1/analyze/stream', { input: 'test' }, {})
    )

    await waitFor(() => {
      expect(fetch).toHaveBeenCalled()
    })

    const callArgs = vi.mocked(fetch).mock.calls[0]
    const headers = callArgs[1]?.headers as Record<string, string> | undefined
    expect(headers?.['X-API-Key']).toBe('test-key')
  })

  it('应该在响应错误时调用 onError', async () => {
    const onError = vi.fn()

    const mockResponse = {
      ok: false,
      json: vi.fn().mockResolvedValue({ detail: '错误信息' }),
    }

    vi.mocked(fetch).mockResolvedValue(mockResponse as any)

    renderHook(() =>
      useSSE('/api/v1/analyze/stream', { input: 'test' }, { onError })
    )

    await waitFor(() => {
      expect(onError).toHaveBeenCalled()
    }, { timeout: 2000 })
  })
})

