const { spawn, execSync, exec } = require('child_process')
const path = require('path')
const fs = require('fs')
const http = require('http')
const { promisify } = require('util')
const { app } = require('electron')

const execAsync = promisify(exec)

class BackendManager {
  constructor() {
    this.process = null
    this.backendPort = 8000
    this.pythonPath = null
    this.backendReady = false
    this.isStopping = false // 防止重复调用 stop
  }

  /**
   * 检测系统 Python 环境
   */
  detectPython() {
    const platform = process.platform
    
    // 首先检查打包的虚拟环境（优先级最高）
    const isPackaged = app ? app.isPackaged : false
    const resourcesPath = app ? (isPackaged ? process.resourcesPath : app.getAppPath()) : __dirname
    
    if (isPackaged) {
      // 打包后的应用：检查 resources 目录下的虚拟环境
      const packagedVenvPython = platform === 'win32' 
        ? path.join(resourcesPath, 'venv', 'Scripts', 'python.exe')
        : path.join(resourcesPath, 'venv', 'bin', 'python3')
      
      if (fs.existsSync(packagedVenvPython)) {
        try {
          const env = {
            ...process.env,
            PATH: process.env.PATH || (platform === 'win32' ? process.env.Path || process.env.PATH || '' : '/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin')
          }
          const result = execSync(
            `"${packagedVenvPython}" --version`,
            { encoding: 'utf-8', stdio: 'pipe', timeout: 5000, env, shell: platform === 'win32' }
          )
          const versionMatch = result.match(/Python (\d+)\.(\d+)/)
          if (versionMatch) {
            const major = parseInt(versionMatch[1])
            const minor = parseInt(versionMatch[2])
            if (major > 3 || (major === 3 && minor >= 11)) {
              console.log(`[detectPython] Using packaged virtual environment: ${packagedVenvPython}`)
              return packagedVenvPython
            }
          }
        } catch (error) {
          console.warn(`[detectPython] Packaged venv Python found but verification failed: ${error.message}`)
        }
      }
    } else {
      // 开发模式：检查项目根目录下的虚拟环境
      const devVenvPython = platform === 'win32'
        ? path.join(__dirname, '../../../venv-packaged/Scripts/python.exe')
        : path.join(__dirname, '../../../venv-packaged/bin/python3')
      
      if (fs.existsSync(devVenvPython)) {
        try {
          const env = {
            ...process.env,
            PATH: process.env.PATH || (platform === 'win32' ? process.env.Path || process.env.PATH || '' : '/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin')
          }
          const result = execSync(
            `"${devVenvPython}" --version`,
            { encoding: 'utf-8', stdio: 'pipe', timeout: 5000, env, shell: platform === 'win32' }
          )
          const versionMatch = result.match(/Python (\d+)\.(\d+)/)
          if (versionMatch) {
            const major = parseInt(versionMatch[1])
            const minor = parseInt(versionMatch[2])
            if (major > 3 || (major === 3 && minor >= 11)) {
              console.log(`[detectPython] Using development virtual environment: ${devVenvPython}`)
              return devVenvPython
            }
          }
        } catch (error) {
          console.warn(`[detectPython] Dev venv Python found but verification failed: ${error.message}`)
        }
      }
    }
    
    // 其次检查环境变量
    if (process.env.PYTHON_PATH) {
      const pythonPath = process.env.PYTHON_PATH
      // 验证环境变量指定的 Python 是否存在且版本正确
      try {
        const env = {
          ...process.env,
          PATH: process.env.PATH || (platform === 'win32' ? process.env.Path || process.env.PATH || '' : '/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin')
        }
        const result = execSync(
          `"${pythonPath}" --version`,
          { encoding: 'utf-8', stdio: 'pipe', timeout: 5000, env, shell: platform === 'win32' }
        )
        const versionMatch = result.match(/Python (\d+)\.(\d+)/)
        if (versionMatch) {
          const major = parseInt(versionMatch[1])
          const minor = parseInt(versionMatch[2])
            if (major > 3 || (major === 3 && minor >= 11)) {
              return pythonPath
            }
        }
      } catch (error) {
        console.warn(`[detectPython] PYTHON_PATH environment variable points to invalid Python: ${pythonPath}`)
      }
    }
    
    const possiblePaths = []

    if (platform === 'win32') {
      // Windows: 检测 python.exe 或 python3.exe
      possiblePaths.push('python.exe', 'python3.exe')
      // 也检查常见安装路径
      const commonPaths = [
        'C:\\Python311\\python.exe',
        'C:\\Python312\\python.exe',
        'C:\\Python313\\python.exe',
        process.env.LOCALAPPDATA + '\\Programs\\Python\\Python311\\python.exe',
        process.env.LOCALAPPDATA + '\\Programs\\Python\\Python312\\python.exe',
      ]
      possiblePaths.push(...commonPaths)
    } else if (platform === 'darwin') {
      // macOS: 检测 python3，并检查常见安装路径
      possiblePaths.push('python3', 'python3.11', 'python3.12', 'python3.13')
      // macOS 常见 Python 安装路径
      const macPaths = [
        '/usr/local/bin/python3',
        '/usr/local/bin/python3.11',
        '/usr/local/bin/python3.12',
        '/usr/local/bin/python3.13',
        '/opt/homebrew/bin/python3',
        '/opt/homebrew/bin/python3.11',
        '/opt/homebrew/bin/python3.12',
        '/opt/homebrew/bin/python3.13',
        '/Library/Frameworks/Python.framework/Versions/3.11/bin/python3',
        '/Library/Frameworks/Python.framework/Versions/3.12/bin/python3',
        '/Library/Frameworks/Python.framework/Versions/3.13/bin/python3',
        process.env.HOME + '/Library/Frameworks/Python.framework/Versions/3.11/bin/python3',
        process.env.HOME + '/Library/Frameworks/Python.framework/Versions/3.12/bin/python3',
        process.env.HOME + '/Library/Frameworks/Python.framework/Versions/3.13/bin/python3',
      ]
      possiblePaths.push(...macPaths)
    } else {
      // Linux: 检测 python3
      possiblePaths.push('python3', 'python3.11', 'python3.12', 'python3.13')
      // Linux 常见路径
      const linuxPaths = [
        '/usr/bin/python3',
        '/usr/bin/python3.11',
        '/usr/bin/python3.12',
        '/usr/bin/python3.13',
        '/usr/local/bin/python3',
        '/usr/local/bin/python3.11',
        '/usr/local/bin/python3.12',
        '/usr/local/bin/python3.13',
      ]
      possiblePaths.push(...linuxPaths)
    }

    // 尝试查找 Python
    for (const pythonPath of possiblePaths) {
      try {
        // 对于绝对路径，直接使用；对于相对路径，使用 which/where 查找
        let command = pythonPath
        if (!path.isAbsolute(pythonPath)) {
          // 相对路径：使用 which (Unix) 或 where (Windows) 查找
          if (platform === 'win32') {
            // Windows: 使用 where 命令查找
            try {
              // 确保使用系统 PATH
              const env = {
                ...process.env,
                PATH: process.env.Path || process.env.PATH || ''
              }
              const whereResult = execSync(
                `where ${pythonPath}`,
                { encoding: 'utf-8', stdio: 'pipe', timeout: 2000, shell: true, env }
              )
              // where 可能返回多行，取第一行
              const foundPath = whereResult.trim().split('\n')[0].trim()
              if (foundPath) {
                // Windows Store 的 Python 快捷方式可能不存在于文件系统中，但可以执行
                // 尝试执行 --version 来验证是否可用
                try {
                  const testResult = execSync(
                    `"${foundPath}" --version`,
                    { encoding: 'utf-8', stdio: 'pipe', timeout: 2000, shell: true, env }
                  )
                  command = foundPath
                } catch (testError) {
                  // 验证失败，继续尝试下一个路径
                  continue
                }
              } else {
                continue
              }
            } catch (error) {
              // where 找不到，尝试直接使用 pythonPath（可能在 PATH 中）
              // 先检查是否是有效的命令
              try {
                const testResult = execSync(
                  `"${pythonPath}" --version`,
                  { encoding: 'utf-8', stdio: 'pipe', timeout: 2000, shell: true, env: { ...process.env, PATH: process.env.Path || process.env.PATH || '' } }
                )
                // 如果能执行，说明 pythonPath 在 PATH 中
                command = pythonPath
              } catch (testError) {
                // 直接执行也失败，继续尝试下一个路径
                continue
              }
            }
          } else {
            // Unix: 使用 which 命令查找
            const env = {
              ...process.env,
              PATH: process.env.PATH || '/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin'
            }
            try {
              const whichResult = execSync(
                `which ${pythonPath}`,
                { encoding: 'utf-8', stdio: 'pipe', timeout: 2000, env }
              )
              command = whichResult.trim()
              if (!command || !fs.existsSync(command)) continue
            } catch (error) {
              continue
            }
          }
        } else {
          // 绝对路径：直接检查文件是否存在
          if (!fs.existsSync(command)) {
            continue
          }
        }
        
        // 确保 PATH 包含常见路径（macOS 应用打包后 PATH 可能受限）
        // Windows: 保持系统 PATH，Electron 应用应该能访问系统 PATH
        // Unix: 添加常见路径
        const env = {
          ...process.env,
          PATH: process.env.PATH || (platform === 'win32' ? process.env.Path || process.env.PATH || '' : '/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin')
        }
        
        // 执行 Python 版本检查
        const result = execSync(
          `"${command}" --version`,
          { encoding: 'utf-8', stdio: 'pipe', timeout: 5000, env, shell: platform === 'win32' }
        )
        if (result) {
          // 检查版本是否符合要求 (>= 3.11)
          const versionMatch = result.match(/Python (\d+)\.(\d+)/)
          if (versionMatch) {
            const major = parseInt(versionMatch[1])
            const minor = parseInt(versionMatch[2])
            if (major > 3 || (major === 3 && minor >= 11)) {
              // 返回实际找到的 Python 路径（command），而不是原始路径（pythonPath）
              return command
            }
          }
        }
      } catch (error) {
        // 继续尝试下一个路径
        continue
      }
    }

    return null
  }

  /**
   * 检查后端服务是否已运行
   */
  async isBackendRunning() {
    return new Promise((resolve) => {
      const req = http.get(`http://localhost:${this.backendPort}/health`, (res) => {
        resolve(res.statusCode === 200)
      })
      req.on('error', () => {
        resolve(false)
      })
      req.setTimeout(2000, () => {
        req.destroy()
        resolve(false)
      })
    })
  }

  /**
   * 等待后端服务就绪
   */
  async waitForBackendReady(maxAttempts = 30, interval = 1000) {
    for (let i = 0; i < maxAttempts; i++) {
      if (await this.isBackendRunning()) {
        this.backendReady = true
        return true
      }
      await new Promise((resolve) => setTimeout(resolve, interval))
    }
    return false
  }

  /**
   * 启动后端进程
   */
  async start() {
    // 检查后端是否已运行
    if (await this.isBackendRunning()) {
      console.log('Backend is already running')
      this.backendReady = true
      return
    }

    // 检测 Python 环境
    this.pythonPath = this.detectPython()
    if (!this.pythonPath) {
      throw new Error(
        'Python 3.11+ not found. Please install Python 3.11 or later.\n' +
        'Download: https://www.python.org/downloads/\n' +
        'Or set PYTHON_PATH environment variable to specify Python path.'
      )
    }

    console.log(`Using Python: ${this.pythonPath}`)

    // 获取后端脚本路径
    const isPackaged = app ? app.isPackaged : false
    const resourcesPath = app ? (isPackaged ? process.resourcesPath : app.getAppPath()) : __dirname
    
    let backendScript
    let backendDir
    
    if (isPackaged) {
      // 打包后的应用：从 resources 目录读取
      backendScript = path.join(resourcesPath, 'run_backend.py')
      backendDir = resourcesPath
      // 检查 .env 文件是否存在
      const envFile = path.join(resourcesPath, '.env')
      if (fs.existsSync(envFile)) {
        console.log(`[Backend] Found .env file at: ${envFile}`)
      } else {
        console.warn(`[Backend] .env file not found at: ${envFile}`)
      }
    } else {
      // 开发模式：从项目根目录读取
      backendScript = path.join(__dirname, '../../run_backend.py')
      backendDir = path.join(__dirname, '../..')
      // 检查 .env 文件是否存在
      const envFile = path.join(backendDir, '.env')
      if (fs.existsSync(envFile)) {
        console.log(`[Backend] Found .env file at: ${envFile}`)
      } else {
        console.warn(`[Backend] .env file not found at: ${envFile}`)
      }
    }
    
    console.log(`[Backend] Backend script: ${backendScript}`)
    console.log(`[Backend] Backend directory: ${backendDir}`)

    // 启动后端进程
    console.log('Starting backend process...')
    
    // 设置环境变量，确保虚拟环境的 Python 使用自己的库
    const platform = process.platform
    const venvDir = path.dirname(path.dirname(this.pythonPath))
    const venvScriptsDir = path.dirname(this.pythonPath)
    
    // 检查是否是虚拟环境的 Python
    const isVenvPython = this.pythonPath.includes('venv') || this.pythonPath.includes('venv-packaged')
    
    let env = {
      ...process.env,
      PYTHONUNBUFFERED: '1',
    }
    
    if (isVenvPython) {
      // 虚拟环境的 Python：设置正确的环境变量
      const venvLibDir = platform === 'win32' 
        ? path.join(venvDir, 'Lib')
        : path.join(venvDir, 'lib', `python${process.versions.node ? '3' : '3.11'}`)
      const venvSitePackagesDir = path.join(venvLibDir, 'site-packages')
      
      // 构建 PATH，优先使用虚拟环境的 Scripts/bin 目录
      const pythonPath = platform === 'win32'
        ? `${venvScriptsDir};${process.env.PATH || process.env.Path || ''}`
        : `${venvScriptsDir}:${process.env.PATH || '/usr/local/bin:/usr/bin:/bin'}`
      
      // 设置 PYTHONPATH，确保 Python 能找到虚拟环境的包
      const pythonPathEnv = fs.existsSync(venvSitePackagesDir) 
        ? venvSitePackagesDir 
        : ''
      
      env = {
        ...env,
        PATH: pythonPath,
        PYTHONPATH: pythonPathEnv,
        // Windows 特定：确保使用虚拟环境的 Python
        ...(platform === 'win32' ? { Path: pythonPath } : {})
      }
      
      console.log(`[Backend] Using venv Python, venvDir: ${venvDir}`)
      console.log(`[Backend] PYTHONPATH: ${pythonPathEnv}`)
    } else {
      // 系统 Python：保持原有逻辑
      env.PATH = (process.env.PATH || '') + (platform === 'win32' ? '' : ':/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin')
    }
    // 使用 detached: false 确保子进程随父进程退出
    // 在 Windows 上，使用 detached: false 和 createNoWindow: true
    // 在 Unix 上，确保进程在同一个进程组中
    const spawnOptions = {
      cwd: backendDir,
      stdio: 'pipe',
      env,
      detached: false, // 确保子进程随父进程退出
    }

    // Windows 特定选项
    if (process.platform === 'win32') {
      spawnOptions.windowsHide = true
    }

    this.process = spawn(this.pythonPath, [backendScript], spawnOptions)

    // 处理 stdout
    this.process.stdout.on('data', (data) => {
      const output = data.toString()
      console.log(`[Backend] ${output}`)
    })

    // 处理 stderr
    this.process.stderr.on('data', (data) => {
      const output = data.toString()
      console.error(`[Backend Error] ${output}`)
    })

    // 处理进程错误
    this.process.on('error', (error) => {
      console.error('Failed to start backend process:', error)
      this.backendReady = false
    })

    // 处理进程退出
    this.process.on('exit', (code, signal) => {
      console.log(`Backend process exited with code ${code} and signal ${signal}`)
      this.backendReady = false
      this.process = null
    })

    // 等待后端就绪
    const ready = await this.waitForBackendReady()
    if (!ready) {
      throw new Error(
        'Backend failed to start within timeout period. ' +
        'Please check the console for error messages.'
      )
    }

    console.log('Backend is ready')
  }

  /**
   * 通过端口查找并终止后端进程
   */
  async killProcessByPort(port) {
    const platform = process.platform
    let command

    if (platform === 'win32') {
      // Windows: 使用 netstat 和 taskkill
      command = `netstat -ano | findstr :${port} | findstr LISTENING`
      try {
        const { stdout } = await execAsync(command)
        const lines = stdout.trim().split('\n')
        const pids = new Set()
        for (const line of lines) {
          const parts = line.trim().split(/\s+/)
          if (parts.length > 0) {
            const pid = parts[parts.length - 1]
            if (pid && !isNaN(pid)) {
              pids.add(pid)
            }
          }
        }
        for (const pid of pids) {
          try {
            // 使用 /T 参数终止进程树（包括子进程）
            await execAsync(`taskkill /F /T /PID ${pid}`)
            console.log(`Killed process ${pid} (and its children) on port ${port}`)
          } catch (error) {
            // 如果进程已经退出，忽略错误
            if (!error.message.includes('not found') && !error.message.includes('不存在')) {
              console.error(`Error killing process ${pid}:`, error.message)
            }
          }
        }
      } catch (error) {
        // 如果没有找到进程，忽略错误
        if (!error.message.includes('findstr')) {
          console.error('Error finding process by port:', error.message)
        }
      }
    } else {
      // macOS/Linux: 使用 lsof 或 netstat
      try {
        // 尝试使用 lsof
        const { stdout } = await execAsync(`lsof -ti :${port}`)
        const pids = stdout.trim().split('\n').filter(pid => pid)
        for (const pid of pids) {
          try {
            // 先尝试 SIGTERM
            await execAsync(`kill -TERM ${pid}`)
            console.log(`Sent SIGTERM to process ${pid} on port ${port}`)
            
            // 等待一下，如果还没退出就强制杀死
            await new Promise(resolve => setTimeout(resolve, 1000))
            try {
              await execAsync(`kill -0 ${pid}`) // 检查进程是否还存在
              // 进程还存在，强制杀死
              await execAsync(`kill -KILL ${pid}`)
              console.log(`Force killed process ${pid} on port ${port}`)
            } catch (e) {
              // 进程已经退出，很好
            }
          } catch (error) {
            console.error(`Error killing process ${pid}:`, error.message)
          }
        }
      } catch (error) {
        // 如果没有找到进程，忽略错误
        if (!error.message.includes('lsof')) {
          console.error('Error finding process by port:', error.message)
        }
      }
    }
  }

  /**
   * 停止后端进程
   */
  async stop() {
    // 防止重复调用
    if (this.isStopping) {
      console.log('Backend stop already in progress')
      return
    }

    this.isStopping = true
    this.backendReady = false

    try {
      // 1. 如果有直接管理的进程，先停止它
      if (this.process) {
        const processToStop = this.process
        this.process = null // 立即清空引用

        console.log('Stopping managed backend process...')

        // 检查进程是否已经退出
        if (!processToStop.killed && processToStop.exitCode === null) {
          try {
            const platform = process.platform
            const pid = processToStop.pid
            
            if (platform === 'win32') {
              // Windows: 直接使用 taskkill 终止进程树（包括所有子进程）
              try {
                console.log(`Terminating process tree for PID ${pid} on Windows...`)
                await execAsync(`taskkill /F /T /PID ${pid}`)
                console.log(`Successfully terminated process tree for PID ${pid}`)
              } catch (taskkillError) {
                // 如果 taskkill 失败，尝试使用 Node.js 的 kill 方法
                console.warn(`taskkill failed, trying Node.js kill method: ${taskkillError.message}`)
                processToStop.kill('SIGTERM')
              }
            } else {
              // Unix: 先尝试优雅退出（SIGTERM）
              processToStop.kill('SIGTERM')
            }

            // 等待进程退出，最多等待 3 秒
            await new Promise((resolve) => {
              const pidForTimeout = pid // 保存 PID 用于超时回调
              const platformForTimeout = platform // 保存平台信息
              const timeout = setTimeout(() => {
                // 超时后强制杀死进程
                try {
                  if (!processToStop.killed && processToStop.exitCode === null) {
                    console.log('Force killing managed backend process (timeout)...')
                    if (platformForTimeout === 'win32') {
                      // Windows: 再次尝试 taskkill
                      execAsync(`taskkill /F /T /PID ${pidForTimeout}`).catch(() => {})
                    } else {
                      processToStop.kill('SIGKILL')
                    }
                  }
                } catch (error) {
                  console.error('Error force killing process:', error)
                }
                resolve()
              }, 3000)

              // 监听进程退出事件
              const onExit = () => {
                clearTimeout(timeout)
                processToStop.removeListener('exit', onExit)
                processToStop.removeListener('error', onError)
                resolve()
              }

              // 监听进程错误事件
              const onError = (error) => {
                clearTimeout(timeout)
                processToStop.removeListener('exit', onExit)
                processToStop.removeListener('error', onError)
                console.error('Error stopping backend process:', error)
                resolve() // 即使出错也继续
              }

              processToStop.once('exit', onExit)
              processToStop.once('error', onError)

              // 如果进程已经退出，立即解析
              if (processToStop.killed || processToStop.exitCode !== null) {
                clearTimeout(timeout)
                processToStop.removeListener('exit', onExit)
                processToStop.removeListener('error', onError)
                resolve()
              }
            })
          } catch (error) {
            console.error('Error stopping managed process:', error)
          }
        }
      }

      // 2. 无论是否有直接管理的进程，都尝试通过端口查找并终止后端进程
      // 这样可以处理后端进程不是当前实例启动的情况
      console.log('Killing backend process by port...')
      await this.killProcessByPort(this.backendPort)

      console.log('Backend process stopped')
    } catch (error) {
      console.error('Error stopping backend process:', error)
    } finally {
      this.isStopping = false
    }
  }

  /**
   * 检查后端是否就绪
   */
  isReady() {
    return this.backendReady
  }
}

module.exports = BackendManager
