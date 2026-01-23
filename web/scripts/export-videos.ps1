# web/scripts/export-videos.ps1
# 批量导出视频脚本（Windows PowerShell）

$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot\..

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "开始批量导出视频..." -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 创建输出目录
if (-not (Test-Path "out")) {
    New-Item -ItemType Directory -Path "out" | Out-Null
}

# 1. 高质量 MP4（CRF 18，适合最终发布）
Write-Host ""
Write-Host "[1/4] 导出高质量 MP4 (CRF 18)..." -ForegroundColor Yellow
npx remotion render PromoVideo out/promo-hq.mp4 `
  --codec=h264 `
  --crf=18 `
  --pixel-format=yuv420p `
  --log=info

# 2. 中等质量 MP4（CRF 23，平衡质量和文件大小）
Write-Host ""
Write-Host "[2/4] 导出中等质量 MP4 (CRF 23)..." -ForegroundColor Yellow
npx remotion render PromoVideo out/promo-medium.mp4 `
  --codec=h264 `
  --crf=23 `
  --pixel-format=yuv420p `
  --log=info

# 3. 低质量 MP4（CRF 28，文件更小，适合快速预览）
Write-Host ""
Write-Host "[3/4] 导出低质量 MP4 (CRF 28)..." -ForegroundColor Yellow
npx remotion render PromoVideo out/promo-low.mp4 `
  --codec=h264 `
  --crf=28 `
  --pixel-format=yuv420p `
  --log=info

# 4. WebM 格式（VP9 编码，现代浏览器，文件更小）
Write-Host ""
Write-Host "[4/4] 导出 WebM 格式 (VP9)..." -ForegroundColor Yellow
npx remotion render PromoVideo out/promo.webm `
  --codec=vp9 `
  --crf=30 `
  --log=info

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "导出完成！" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

# 显示输出文件信息
Write-Host "输出文件：" -ForegroundColor Cyan
Get-ChildItem -Path "out" -Filter "*.mp4","*.webm" -ErrorAction SilentlyContinue | 
    ForEach-Object {
        $sizeMB = [math]::Round($_.Length / 1MB, 2)
        Write-Host "  $($_.Name) - $sizeMB MB" -ForegroundColor White
    }

Write-Host ""
