# 桌面应用构建脚本 (Windows PowerShell)
# 用法: .\scripts\build-desktop.ps1 [platform]
# platform: win, mac, linux (默认: win)

param(
    [string]$Platform = "win"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$WebDir = Join-Path $ProjectRoot "web"

Set-Location $WebDir

Write-Host "Building desktop application for platform: $Platform" -ForegroundColor Green
Write-Host "Project root: $ProjectRoot"
Write-Host "Web directory: $WebDir"

# 检查 npm 是否安装
try {
    $npmVersion = npm --version
    Write-Host "npm version: $npmVersion" -ForegroundColor Cyan
} catch {
    Write-Host "Error: npm is not installed" -ForegroundColor Red
    exit 1
}

# 安装依赖（如果需要）
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    npm install
}

# 准备虚拟环境（如果不存在）
$VenvDir = Join-Path $ProjectRoot "venv-packaged"
if (-not (Test-Path $VenvDir)) {
    Write-Host "Virtual environment not found, preparing..." -ForegroundColor Yellow
    & (Join-Path $ProjectRoot "scripts\prepare-venv.ps1")
} else {
    Write-Host "Using existing virtual environment: $VenvDir" -ForegroundColor Cyan
}

# 修复虚拟环境配置以适配打包
Write-Host "Fixing virtual environment for packaging..." -ForegroundColor Yellow
& (Join-Path $ProjectRoot "scripts\fix-venv-for-packaging.ps1")

# 清理之前的构建（如果存在）
if (Test-Path "release") {
    Write-Host "Cleaning previous build..." -ForegroundColor Yellow
    
    # 先尝试关闭可能占用文件的进程
    $processesToKill = Get-Process | Where-Object { 
        $_.Path -like "*release\win-unpacked\CodebaseAgent.exe*" -or 
        $_.Path -like "*release\win-unpacked\electron.exe*" -or
        ($_.ProcessName -eq "python" -and $_.Path -like "*release\*")
    }
    
    if ($processesToKill) {
        Write-Host "Stopping processes that may be using files..." -ForegroundColor Yellow
        $processesToKill | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
    
    # 等待一下确保文件释放
    Start-Sleep -Seconds 2
    
    # 尝试多次删除，处理可能被锁定的文件
    $maxRetries = 3
    $retryCount = 0
    $removed = $false
    
    while (-not $removed -and $retryCount -lt $maxRetries) {
        try {
            # 先尝试删除可能被锁定的文件（.pyd, .dll, .exe）
            $lockedFiles = Get-ChildItem -Path "release" -Recurse -File -ErrorAction SilentlyContinue | 
                Where-Object { $_.Extension -in @(".pyd", ".dll", ".exe") }
            
            if ($lockedFiles) {
                Write-Host "Removing locked files..." -ForegroundColor Yellow
                $lockedFiles | ForEach-Object {
                    try {
                        Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
                    } catch {
                        # 忽略单个文件删除失败
                    }
                }
                Start-Sleep -Seconds 1
            }
            
            # 然后删除整个目录
            Remove-Item -Recurse -Force "release" -ErrorAction Stop
            $removed = $true
            Write-Host "Successfully removed release directory" -ForegroundColor Green
        } catch {
            $retryCount++
            if ($retryCount -lt $maxRetries) {
                Write-Host "Retry ${retryCount}/${maxRetries}: Waiting for files to be released..." -ForegroundColor Yellow
                Start-Sleep -Seconds 3
            } else {
                Write-Host "Warning: Could not fully remove release directory after $maxRetries attempts" -ForegroundColor Yellow
                Write-Host "Continuing build... electron-builder's beforePack hook will attempt to clean up." -ForegroundColor Yellow
                Write-Host "If build fails, manually delete the release directory:" -ForegroundColor Yellow
                Write-Host "  Remove-Item -Recurse -Force '$WebDir\release'" -ForegroundColor Cyan
            }
        }
    }
}

# 构建前端
Write-Host "Building frontend..." -ForegroundColor Yellow
npm run build

# 根据平台构建
switch ($Platform.ToLower()) {
    { $_ -in "win", "windows" } {
        Write-Host "Building for Windows..." -ForegroundColor Yellow
        Write-Host "Enable debug logging with: `$env:DEBUG='electron-builder*'" -ForegroundColor Cyan
        # 禁用代码签名以避免下载 winCodeSign
        $env:CSC_IDENTITY_AUTO_DISCOVERY = "false"
        $env:WIN_CERT_FILE = ""
        npm run electron:pack -- --win
    }
    { $_ -in "mac", "darwin", "macos" } {
        Write-Host "Building for macOS..." -ForegroundColor Yellow
        npm run electron:pack -- --mac
    }
    "linux" {
        Write-Host "Building for Linux..." -ForegroundColor Yellow
        npm run electron:pack -- --linux
    }
    default {
        Write-Host "Building for current platform (Windows)..." -ForegroundColor Yellow
        $env:CSC_IDENTITY_AUTO_DISCOVERY = "false"
        $env:WIN_CERT_FILE = ""
        npm run electron:pack -- --win
    }
}

Write-Host "Build completed! Output files are in: $WebDir\release\" -ForegroundColor Green
