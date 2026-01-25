/**
 * 获取 API 基础 URL
 * 在 Electron 环境中，使用 electronAPI 提供的 URL
 * 在浏览器环境中，使用相对路径（由 Vite 代理处理）
 */
export function getApiBaseURL(): string {
  // 检查是否在 Electron 环境中
  if (typeof window !== 'undefined') {
    const electronAPI = (window as any).electronAPI
    if (electronAPI?.apiBaseURL) {
      console.log('[API] Using Electron API base URL:', electronAPI.apiBaseURL)
      return electronAPI.apiBaseURL
    }
    // 调试：检查 electronAPI 是否存在
    if (electronAPI) {
      console.log('[API] electronAPI exists but no apiBaseURL:', electronAPI)
    } else {
      console.log('[API] electronAPI not available, using relative path')
    }
  }
  
  // 浏览器环境：使用相对路径，由 Vite 代理处理
  return ''
}

/**
 * 构建完整的 API URL
 */
export function buildApiUrl(path: string): string {
  const baseURL = getApiBaseURL()
  // 确保 path 以 / 开头
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const fullUrl = baseURL + normalizedPath
  console.log('[API] Building URL:', { path, baseURL, fullUrl })
  return fullUrl
}
