import { Config } from '@remotion/cli/config'
import { existsSync } from 'fs'
import { resolve } from 'path'

// Remotion 配置
// 更多配置选项请参考: https://www.remotion.dev/docs/config

// 设置入口点
Config.setEntryPoint('./src/video/remotion-entry.tsx')

// 设置 Studio 端口（避免与主应用冲突）
Config.setStudioPort(3001)

// 自动检测 Chrome Headless Shell 路径
// 动态检测平台并查找已安装的浏览器（相对于当前工作目录）
try {
  // 检测平台
  const platform = process.platform === 'darwin'
    ? (process.arch === 'arm64' ? 'mac-arm64' : 'mac-x64')
    : process.platform === 'linux'
    ? (process.arch === 'arm64' ? 'linux-arm64' : 'linux-x64')
    : process.platform === 'win32'
    ? 'win64'
    : null

  if (platform) {
    // 使用当前工作目录（通常是 web 目录）构建浏览器路径
    const browserPath = resolve(process.cwd(), `node_modules/.remotion/chrome-headless-shell/${platform}/chrome-headless-shell`)
    
    if (existsSync(browserPath)) {
      Config.setBrowserExecutable(browserPath)
    }
  }
} catch (error) {
  // 如果检测失败，让 Remotion 自动处理
  // Remotion 会自动在 node_modules/.remotion/chrome-headless-shell/ 下查找浏览器
  // 如果找不到，会尝试自动下载 Chrome Headless Shell
}
