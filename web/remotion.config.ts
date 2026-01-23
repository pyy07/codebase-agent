import { Config } from '@remotion/cli/config'

// Remotion 配置
// 更多配置选项请参考: https://www.remotion.dev/docs/config

// 设置入口点
Config.setEntryPoint('./src/video/remotion-entry.tsx')

// 设置 Studio 端口（避免与主应用冲突）
Config.setStudioPort(3001)
