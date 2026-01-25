const { spawn, execSync, exec } = require('child_process')
const path = require('path')
const http = require('http')
const { promisify } = require('util')

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

    // 首先检查环境变量
    if (process.env.PYTHON_PATH) {
      return process.env.PYTHON_PATH
    }

    // 尝试查找 Python
    for (const pythonPath of possiblePaths) {
      try {
        // 对于绝对路径，直接使用；对于相对路径，使用 which 查找
        let command = pythonPath
        if (!path.isAbsolute(pythonPath)) {
          // 相对路径：使用 which 查找，确保 PATH 包含常见路径
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
            if (!command) continue
          } catch (error) {
            continue
          }
        }
        
        // 确保 PATH 包含常见路径（macOS 应用打包后 PATH 可能受限）
        const env = {
          ...process.env,
          PATH: (process.env.PATH || '') + ':/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin'
        }
        
        const result = execSync(
          `"${command}" --version`,
          { encoding: 'utf-8', stdio: 'pipe', timeout: 5000, env }
        )
        if (result) {
          // 检查版本是否符合要求 (>= 3.11)
          const versionMatch = result.match(/Python (\d+)\.(\d+)/)
          if (versionMatch) {
            const major = parseInt(versionMatch[1])
            const minor = parseInt(versionMatch[2])
            if (major > 3 || (major === 3 && minor >= 11)) {
              return pythonPath
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
    const backendScript = path.join(__dirname, '../../run_backend.py')
    const backendDir = path.join(__dirname, '../..')

    // 启动后端进程
    console.log('Starting backend process...')
    // 确保 PATH 包含常见路径（macOS 应用打包后 PATH 可能受限）
    const env = {
      ...process.env,
      PYTHONUNBUFFERED: '1',
      PATH: (process.env.PATH || '') + ':/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin',
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
            await execAsync(`taskkill /F /PID ${pid}`)
            console.log(`Killed process ${pid} on port ${port}`)
          } catch (error) {
            console.error(`Error killing process ${pid}:`, error.message)
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
            // 先尝试优雅退出（SIGTERM）
            processToStop.kill('SIGTERM')

            // 等待进程退出，最多等待 3 秒
            await new Promise((resolve) => {
              const timeout = setTimeout(() => {
                // 超时后强制杀死进程
                try {
                  if (!processToStop.killed && processToStop.exitCode === null) {
                    console.log('Force killing managed backend process (timeout)...')
                    processToStop.kill('SIGKILL')
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
