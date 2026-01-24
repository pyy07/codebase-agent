const { app, BrowserWindow, dialog } = require('electron')
const path = require('path')
const fs = require('fs')
const BackendManager = require('./backend')

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged

let mainWindow = null
let backendManager = null

// 设置日志文件路径
const logDir = path.join(app.getPath('userData'), 'logs')
const logFile = path.join(logDir, `app-${new Date().toISOString().split('T')[0]}.log`)

// 确保日志目录存在
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true })
}

// 保存原始的 console 方法（在重定向之前）
const originalConsole = {
  log: console.log.bind(console),
  error: console.error.bind(console),
  warn: console.warn.bind(console),
}

// 日志函数（使用原始 console，避免无限递归）
function log(message, level = 'INFO') {
  const timestamp = new Date().toISOString()
  const logMessage = `[${timestamp}] [${level}] ${message}\n`
  
  // 输出到控制台（使用原始 console，避免递归）
  originalConsole.log(logMessage.trim())
  
  // 写入日志文件
  try {
    fs.appendFileSync(logFile, logMessage)
  } catch (error) {
    originalConsole.error('Failed to write to log file:', error)
  }
}

// 重定向 console 方法（使用原始 console 输出，然后记录到日志文件）
console.log = (...args) => {
  originalConsole.log(...args)
  log(args.join(' '), 'INFO')
}

console.error = (...args) => {
  originalConsole.error(...args)
  log(args.join(' '), 'ERROR')
}

console.warn = (...args) => {
  originalConsole.warn(...args)
  log(args.join(' '), 'WARN')
}

log(`Application starting... (isDev: ${isDev}, isPackaged: ${app.isPackaged})`)
log(`Log file: ${logFile}`)

/**
 * 创建应用窗口
 */
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
    // icon: path.join(__dirname, '../build/icon.png'), // 可选：应用图标（需要时取消注释）
    show: false, // 先不显示，等后端启动后再显示
  })

  // 加载前端
  if (isDev) {
    // 开发模式：从 Vite 开发服务器加载
    log(`Loading frontend from: http://localhost:3000`)
    mainWindow.loadURL('http://localhost:3000')
    // 开发模式下打开开发者工具
    mainWindow.webContents.openDevTools()
  } else {
    // 生产模式：从打包后的文件加载
    // 使用 loadURL 配合 file:// 协议，确保资源路径正确解析
    const distPath = path.join(__dirname, '../dist/index.html')
    const fileUrl = `file://${distPath}`
    log(`Loading frontend from: ${fileUrl}`)
    
    // 检查文件是否存在
    if (!fs.existsSync(distPath)) {
      log(`ERROR: Frontend file not found: ${distPath}`, 'ERROR')
      dialog.showErrorBox(
        '启动失败',
        `前端文件未找到：\n${distPath}\n\n请重新构建应用。`
      )
      app.quit()
      return
    }
    
    // 使用 loadURL 而不是 loadFile，这样可以更好地处理资源路径
    mainWindow.loadURL(fileUrl)
    
    // 设置 webSecurity 为 false，允许加载本地文件（仅在 Electron 环境中安全）
    mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL) => {
      // 如果是资源加载失败，尝试使用相对路径重新加载
      if (errorCode === -6 && validatedURL.includes('file://')) {
        log(`Retrying with alternative path handling for: ${validatedURL}`, 'WARN')
      }
    })
  }

  // 窗口准备好后显示
  mainWindow.once('ready-to-show', () => {
    log('Window ready to show')
    if (mainWindow) {
      mainWindow.show()
      log('Window shown')
    }
  })

  // 处理窗口关闭
  mainWindow.on('closed', () => {
    log('Window closed')
    mainWindow = null
  })

  // 处理窗口加载完成
  mainWindow.webContents.on('did-finish-load', () => {
    log('Window finished loading')
  })

  // 处理窗口加载失败
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL) => {
    log(`Failed to load window: ${errorCode} - ${errorDescription} (URL: ${validatedURL})`, 'ERROR')
    
    // 显示错误对话框
    dialog.showErrorBox(
      '加载失败',
      `无法加载前端页面：\n\n错误代码: ${errorCode}\n错误描述: ${errorDescription}\nURL: ${validatedURL}\n\n日志文件: ${logFile}`
    )
  })

  // 处理渲染进程崩溃
  mainWindow.webContents.on('render-process-gone', (event, details) => {
    log(`Render process gone: ${JSON.stringify(details)}`, 'ERROR')
    dialog.showErrorBox(
      '渲染进程崩溃',
      `渲染进程意外退出：\n\n原因: ${details.reason}\n退出代码: ${details.exitCode}\n\n日志文件: ${logFile}`
    )
  })

  // 处理控制台消息（从渲染进程）
  mainWindow.webContents.on('console-message', (event, level, message) => {
    log(`[Renderer ${level}] ${message}`)
  })
}

/**
 * 启动应用
 */
async function startApp() {
  try {
    // 启动后端服务
    log('Starting backend service...')
    backendManager = new BackendManager()
    await backendManager.start()
    log('Backend service started successfully')

    // 创建前端窗口
    log('Creating frontend window...')
    createWindow()
  } catch (error) {
    log(`Failed to start application: ${error.message}\n${error.stack}`, 'ERROR')
    
    // 显示错误对话框
    dialog.showErrorBox(
      '启动失败',
      `无法启动应用：\n\n${error.message}\n\n日志文件位置：\n${logFile}\n\n请查看日志文件获取详细信息。`
    )
    
    // 退出应用
    app.quit()
  }
}

// 应用准备就绪
app.whenReady().then(() => {
  startApp()

  // macOS: 当所有窗口关闭时，应用通常继续运行
  app.on('activate', () => {
    log('App activated')
    if (BrowserWindow.getAllWindows().length === 0) {
      startApp()
    }
  })
})

// 添加快捷键打开开发者工具（生产模式也支持）
app.on('ready', () => {
  // 添加全局快捷键：Cmd+Option+I (macOS) 或 Ctrl+Shift+I (Windows/Linux)
  const { globalShortcut } = require('electron')
  globalShortcut.register('CommandOrControl+Shift+I', () => {
    if (mainWindow) {
      mainWindow.webContents.toggleDevTools()
      log('Developer tools toggled')
    }
  })
  
  // 添加快捷键显示日志文件位置
  globalShortcut.register('CommandOrControl+Shift+L', () => {
    dialog.showMessageBox(mainWindow, {
      type: 'info',
      title: '日志文件位置',
      message: '日志文件位置',
      detail: logFile,
      buttons: ['打开文件夹', '复制路径', '确定']
    }).then((result) => {
      if (result.response === 0) {
        // 打开文件夹
        const { shell } = require('electron')
        shell.showItemInFolder(logFile)
      } else if (result.response === 1) {
        // 复制路径
        const { clipboard } = require('electron')
        clipboard.writeText(logFile)
        log('Log file path copied to clipboard')
      }
    })
  })
  
  log('Global shortcuts registered: Cmd+Shift+I (DevTools), Cmd+Shift+L (Log location)')
})

// 所有窗口关闭时退出应用（Windows/Linux）
app.on('window-all-closed', () => {
  // macOS: 通常应用会继续运行
  if (process.platform !== 'darwin') {
    // 停止后端进程
    if (backendManager) {
      backendManager.stop().then(() => {
        app.quit()
      })
    } else {
      app.quit()
    }
  }
})

// 应用退出前清理
app.on('before-quit', async (event) => {
  if (backendManager) {
    event.preventDefault()
    await backendManager.stop()
    app.quit()
  }
})

// 处理未捕获的异常
process.on('uncaughtException', (error) => {
  log(`Uncaught exception: ${error.message}\n${error.stack}`, 'ERROR')
  dialog.showErrorBox(
    '未捕获的异常',
    `应用发生未捕获的异常：\n\n${error.message}\n\n日志文件: ${logFile}`
  )
})

process.on('unhandledRejection', (reason, promise) => {
  log(`Unhandled rejection: ${reason}`, 'ERROR')
  if (reason instanceof Error) {
    log(`Stack: ${reason.stack}`, 'ERROR')
  }
})
