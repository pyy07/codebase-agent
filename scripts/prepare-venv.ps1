# 准备虚拟环境用于打包
# 用法: .\scripts\prepare-venv.ps1

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$VenvDir = Join-Path $ProjectRoot "venv-packaged"

Write-Host "Preparing virtual environment for packaging..." -ForegroundColor Green
Write-Host "Project root: $ProjectRoot"
Write-Host "Virtual environment directory: $VenvDir"

# 检查 Python 是否安装
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python version: $pythonVersion" -ForegroundColor Cyan
} catch {
    Write-Host "Error: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.11+ from https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# 检查 Python 版本
$versionOutput = python --version 2>&1
if ($versionOutput -match "Python (\d+)\.(\d+)") {
    $major = [int]$matches[1]
    $minor = [int]$matches[2]
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
        Write-Host "Error: Python 3.11+ is required, but found Python $major.$minor" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Warning: Could not parse Python version" -ForegroundColor Yellow
}

# 删除旧的虚拟环境（如果存在）
if (Test-Path $VenvDir) {
    Write-Host "Removing existing virtual environment..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $VenvDir -ErrorAction SilentlyContinue
}

# 创建新的虚拟环境（使用 --copies 确保完全独立，不依赖系统 Python）
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
python -m venv $VenvDir --copies

# 激活虚拟环境并安装依赖
Write-Host "Installing dependencies..." -ForegroundColor Yellow
$activateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
& $activateScript
pip install --upgrade pip
pip install -r (Join-Path $ProjectRoot "requirements.txt")

Write-Host "Virtual environment prepared successfully!" -ForegroundColor Green
Write-Host "Location: $VenvDir" -ForegroundColor Cyan
