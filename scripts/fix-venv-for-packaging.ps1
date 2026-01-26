# 修复虚拟环境配置，使其在打包后能正常工作
# 用法: .\scripts\fix-venv-for-packaging.ps1

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$VenvDir = Join-Path $ProjectRoot "venv-packaged"

if (-not (Test-Path $VenvDir)) {
    Write-Host "Error: Virtual environment not found at $VenvDir" -ForegroundColor Red
    Write-Host "Please run prepare-venv.ps1 first" -ForegroundColor Yellow
    exit 1
}

Write-Host "Fixing virtual environment for packaging..." -ForegroundColor Green

# 修复 pyvenv.cfg：将 base-prefix 和 base-exec-prefix 设置为相对路径
$pyvenvCfg = Join-Path $VenvDir "pyvenv.cfg"
if (Test-Path $pyvenvCfg) {
    Write-Host "Updating pyvenv.cfg..." -ForegroundColor Yellow
    $content = Get-Content $pyvenvCfg -Raw
    # 将绝对路径替换为相对路径（使用 .. 表示相对于虚拟环境目录）
    $content = $content -replace 'base-prefix\s*=\s*.*', 'base-prefix = .'
    $content = $content -replace 'base-exec-prefix\s*=\s*.*', 'base-exec-prefix = .'
    $content = $content -replace 'base-python\s*=\s*.*', 'base-python = python.exe'
    Set-Content $pyvenvCfg -Value $content -NoNewline
    Write-Host "pyvenv.cfg updated" -ForegroundColor Green
} else {
    Write-Host "Warning: pyvenv.cfg not found" -ForegroundColor Yellow
}

Write-Host "Virtual environment fixed for packaging!" -ForegroundColor Green
