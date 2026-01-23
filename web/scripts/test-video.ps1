# 视频测试脚本 (PowerShell)

Set-Location $PSScriptRoot\..

Write-Host "=== Remotion 视频测试 ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "1. 检查依赖..." -ForegroundColor Yellow
try {
    $null = Get-Command npx -ErrorAction Stop
    Write-Host "✅ 依赖检查通过" -ForegroundColor Green
} catch {
    Write-Host "❌ 错误: 未找到 npx，请先安装 Node.js" -ForegroundColor Red
    exit 1
}

Write-Host ""

Write-Host "2. 测试视频导出..." -ForegroundColor Yellow
Write-Host "   导出测试视频到 out/test.mp4"
npx remotion render PromoVideo out/test.mp4 --log=info

if (Test-Path "out/test.mp4") {
    $file = Get-Item "out/test.mp4"
    $fileSizeMB = [math]::Round($file.Length / 1MB, 2)
    Write-Host "✅ 导出成功！" -ForegroundColor Green
    Write-Host "   文件大小: $fileSizeMB MB"
    Write-Host "   文件路径: $($file.FullName)"
} else {
    Write-Host "❌ 导出失败！" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "3. 测试完成！" -ForegroundColor Green
Write-Host ""
Write-Host "下一步：" -ForegroundColor Cyan
Write-Host "  - 使用视频播放器打开 out/test.mp4 检查视频质量"
Write-Host "  - 运行 'npm run video:dev' 启动 Remotion Studio 进行预览"
Write-Host ""
