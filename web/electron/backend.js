const { spawn, execSync } = require('child_process')
const path = require('path')
const http = require('http')

class BackendManager {
  constructor() {
    this.process = null
    this.backendPort = 8000
    this.pythonPath = null
    this.backendReady = false
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
    this.process = spawn(this.pythonPath, [backendScript], {
      cwd: backendDir,
      stdio: 'pipe',
      env,
    })

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
   * 停止后端进程
   */
  async stop() {
    if (this.process) {
      console.log('Stopping backend process...')
      this.process.kill('SIGTERM')

      // 等待进程退出，最多等待 5 秒
      await new Promise((resolve) => {
        if (!this.process) {
          resolve()
          return
        }

        const timeout = setTimeout(() => {
          if (this.process) {
            console.log('Force killing backend process...')
            this.process.kill('SIGKILL')
          }
          resolve()
        }, 5000)

        this.process.on('exit', () => {
          clearTimeout(timeout)
          resolve()
        })
      })

      this.process = null
      this.backendReady = false
      console.log('Backend process stopped')
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
