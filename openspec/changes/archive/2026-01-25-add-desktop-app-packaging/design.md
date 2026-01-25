# Design: 桌面应用打包架构设计

## 架构概述

桌面应用采用 Electron 框架，将现有的 Web 应用包装为桌面应用。架构设计遵循以下原则：

1. **最小侵入**：不改变现有后端和前端代码，只添加 Electron 包装层
2. **进程隔离**：后端 Python 进程和前端 Electron 进程独立运行
3. **自动管理**：Electron 主进程负责自动启动和管理后端服务
4. **跨平台**：使用 electron-builder 支持多平台打包

## 架构图

```
┌─────────────────────────────────────────────────────────┐
│                    Electron 主进程                        │
│  ┌──────────────────────────────────────────────────┐   │
│  │  BrowserWindow (前端窗口)                         │   │
│  │  ┌────────────────────────────────────────────┐  │   │
│  │  │  React 前端应用 (现有代码)                  │  │   │
│  │  │  - 通过 localhost:8000 访问后端 API        │  │   │
│  │  │  - SSE 流式通信                            │  │   │
│  │  └────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  BackendManager (后端进程管理器)                 │   │
│  │  - 检测 Python 环境                              │   │
│  │  - 启动 Python 后端进程                          │   │
│  │  - 监控后端健康状态                              │   │
│  │  - 处理后端异常和重启                            │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          │
                          │ spawn
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Python 后端进程 (独立进程)                   │
│  - FastAPI 服务 (localhost:8000)                        │
│  - 现有代码无需修改                                     │
└─────────────────────────────────────────────────────────┘
```

## 核心组件设计

### 1. Electron 主进程 (main.js)

**职责**：
- 创建和管理应用窗口
- 处理应用生命周期事件（启动、关闭、激活）
- 启动和管理后端进程
- 处理系统级事件（菜单、托盘等）

**关键实现**：
```javascript
// 伪代码示例
const { app, BrowserWindow } = require('electron')
const BackendManager = require('./backend')

let mainWindow
let backendManager

app.whenReady().then(() => {
  // 启动后端服务
  backendManager = new BackendManager()
  await backendManager.start()
  
  // 创建前端窗口
  createWindow()
})

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  })
  
  // 加载前端（开发时用 localhost:3000，生产时用打包后的文件）
  if (isDev) {
    mainWindow.loadURL('http://localhost:3000')
  } else {
    mainWindow.loadFile('dist/index.html')
  }
}
```

### 2. 后端进程管理器 (backend.js)

**职责**：
- 检测系统 Python 环境
- 启动 Python 后端进程
- 监控后端服务健康状态
- 处理后端进程异常和重启
- 在应用关闭时清理后端进程

**关键实现**：
```javascript
// 伪代码示例
class BackendManager {
  constructor() {
    this.process = null
    this.backendPort = 8000
    this.pythonPath = this.detectPython()
  }
  
  async start() {
    // 检查后端是否已运行
    if (await this.isBackendRunning()) {
      return
    }
    
    // 启动后端进程
    const backendScript = path.join(__dirname, '../../run_backend.py')
    this.process = spawn(this.pythonPath, [backendScript], {
      cwd: path.join(__dirname, '../..'),
      stdio: 'pipe'
    })
    
    // 等待后端启动
    await this.waitForBackendReady()
  }
  
  async stop() {
    if (this.process) {
      this.process.kill()
      this.process = null
    }
  }
  
  detectPython() {
    // 检测系统 Python 路径
    // Windows: python.exe
    // macOS/Linux: python3
  }
  
  async isBackendRunning() {
    // 检查 localhost:8000/health 是否可访问
  }
}
```

### 3. 预加载脚本 (preload.js)

**职责**：
- 在渲染进程和主进程之间建立安全的通信桥梁
- 暴露必要的 API 给前端使用（如果需要）

**关键实现**：
```javascript
// 伪代码示例
const { contextBridge } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  // 可以暴露更多 API，如文件系统访问等
})
```

## 打包策略

### Python 后端打包

**方案选择**：
1. **方案 A：依赖系统 Python**（推荐用于开发）
   - 优点：打包体积小，启动快
   - 缺点：需要用户安装 Python 3.11+
   - 实现：检测系统 Python，如果没有则提示安装

2. **方案 B：打包 Python 运行时**（推荐用于生产）
   - 优点：用户无需安装 Python，开箱即用
   - 缺点：打包体积较大（~50-100MB）
   - 实现：使用 PyInstaller 打包 Python 后端为可执行文件

**推荐方案**：先实现方案 A，后续可扩展方案 B

### 前端打包

- 使用 Vite 构建前端为静态文件
- Electron 加载打包后的静态文件（`dist/index.html`）
- 生产环境不再需要 Vite 开发服务器

### 应用打包

- 使用 `electron-builder` 打包 Electron 应用
- 支持平台：
  - Windows: NSIS 安装程序
  - macOS: DMG 磁盘镜像
  - Linux: AppImage 可执行文件

## 配置管理

### 环境变量处理

桌面应用中，环境变量可以通过以下方式管理：
1. **应用内配置界面**：在桌面应用中提供配置界面
2. **配置文件**：使用 JSON 或 YAML 配置文件
3. **系统环境变量**：继续支持系统环境变量（向后兼容）

### 数据存储

- **用户数据**：存储在用户目录下的应用数据文件夹
  - Windows: `%APPDATA%/CodebaseAgent`
  - macOS: `~/Library/Application Support/CodebaseAgent`
  - Linux: `~/.config/CodebaseAgent`
- **配置数据**：存储 API Key、LLM 配置等敏感信息
- **会话数据**：存储历史会话和分析结果（可选）

## 安全考虑

1. **进程隔离**：前端运行在渲染进程，后端运行在独立进程
2. **上下文隔离**：启用 `contextIsolation`，防止前端直接访问 Node.js API
3. **API 限制**：只暴露必要的 API 给前端
4. **资源访问**：限制文件系统访问范围

## 性能优化

1. **启动优化**：
   - 后端启动时显示启动画面
   - 并行启动后端和前端窗口
   - 缓存后端启动状态

2. **资源优化**：
   - 使用代码分割减少初始加载时间
   - 压缩静态资源
   - 延迟加载非关键组件

3. **内存优化**：
   - 及时清理不需要的资源
   - 限制后端日志输出量
   - 优化 Electron 窗口内存使用

## 错误处理

1. **后端启动失败**：
   - 检测 Python 环境
   - 显示友好的错误提示
   - 提供解决方案链接

2. **后端进程崩溃**：
   - 自动重启后端进程
   - 记录错误日志
   - 通知用户

3. **网络错误**：
   - 检测后端连接状态
   - 显示连接错误提示
   - 提供重试机制

## 开发体验

1. **开发模式**：
   - 使用 `concurrently` 同时启动前端和后端
   - 支持热重载
   - 显示开发工具

2. **调试**：
   - 后端日志输出到控制台
   - 前端使用 Chrome DevTools
   - 支持远程调试

3. **构建**：
   - 一键构建所有平台
   - 自动化测试
   - CI/CD 集成
