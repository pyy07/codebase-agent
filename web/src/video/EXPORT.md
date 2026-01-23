# 视频导出指南

本文档说明如何导出和优化 Remotion 视频。

## 基本导出

### 快速导出

```bash
cd web
npm run video:render
```

这将导出默认配置的视频：
- 格式：MP4
- 分辨率：1920x1080
- 帧率：30fps
- 编码：H.264
- 输出路径：`web/out/video.mp4`

## 导出配置优化

### 高质量导出

```bash
cd web

# 高质量 MP4（CRF 18，适合最终发布）
npx remotion render PromoVideo out/promo-hq.mp4 \
  --codec=h264 \
  --crf=18 \
  --pixel-format=yuv420p

# 中等质量（CRF 23，平衡质量和文件大小）
npx remotion render PromoVideo out/promo-medium.mp4 \
  --codec=h264 \
  --crf=23 \
  --pixel-format=yuv420p

# 低质量（CRF 28，文件更小，适合快速预览）
npx remotion render PromoVideo out/promo-low.mp4 \
  --codec=h264 \
  --crf=28 \
  --pixel-format=yuv420p
```

### CRF 值说明

- **CRF 18**：高质量，文件较大（~50-100MB），适合最终发布
- **CRF 23**：中等质量，文件适中（~20-40MB），适合一般用途
- **CRF 28**：较低质量，文件较小（~10-20MB），适合快速预览或网络分享

### WebM 格式导出

```bash
cd web

# VP9 编码（现代浏览器，文件更小）
npx remotion render PromoVideo out/promo.webm \
  --codec=vp9 \
  --crf=30

# VP8 编码（兼容性更好）
npx remotion render PromoVideo out/promo-vp8.webm \
  --codec=vp8 \
  --crf=30
```

### 不同分辨率导出

```bash
cd web

# 4K (3840x2160)
npx remotion render PromoVideo out/promo-4k.mp4 \
  --scale=2

# 720p (1280x720)
npx remotion render PromoVideo out/promo-720p.mp4 \
  --scale=0.666

# 自定义分辨率
npx remotion render PromoVideo out/promo-custom.mp4 \
  --width=1280 \
  --height=720
```

### 导出特定片段

```bash
cd web

# 导出前 10 秒（0-300 帧 @ 30fps）
npx remotion render PromoVideo out/promo-segment.mp4 \
  --frames=0-300

# 导出特定场景（场景2：300-600 帧）
npx remotion render PromoVideo out/promo-scene2.mp4 \
  --frames=300-600
```

## 批量导出脚本

创建 `web/scripts/export-videos.sh`（Linux/Mac）或 `web/scripts/export-videos.ps1`（Windows）：

### Linux/Mac 脚本

```bash
#!/bin/bash
# web/scripts/export-videos.sh

cd "$(dirname "$0")/.."

echo "导出高质量视频..."
npx remotion render PromoVideo out/promo-hq.mp4 --codec=h264 --crf=18

echo "导出中等质量视频..."
npx remotion render PromoVideo out/promo-medium.mp4 --codec=h264 --crf=23

echo "导出 WebM 格式..."
npx remotion render PromoVideo out/promo.webm --codec=vp9 --crf=30

echo "导出完成！"
```

### Windows PowerShell 脚本

```powershell
# web/scripts/export-videos.ps1

Set-Location $PSScriptRoot\..

Write-Host "导出高质量视频..."
npx remotion render PromoVideo out/promo-hq.mp4 --codec=h264 --crf=18

Write-Host "导出中等质量视频..."
npx remotion render PromoVideo out/promo-medium.mp4 --codec=h264 --crf=23

Write-Host "导出 WebM 格式..."
npx remotion render PromoVideo out/promo.webm --codec=vp9 --crf=30

Write-Host "导出完成！"
```

## 性能优化建议

### 1. 并发渲染

```bash
# 使用多核渲染（默认使用所有可用核心）
npx remotion render PromoVideo out/video.mp4 --concurrency=8
```

### 2. 内存优化

如果遇到内存不足，可以：
- 减少并发数：`--concurrency=4`
- 降低分辨率：`--scale=0.5`
- 分段渲染后合并

### 3. 渲染进度

```bash
# 显示详细进度
npx remotion render PromoVideo out/video.mp4 --log=verbose
```

## 视频质量检查清单

导出后检查：

- [ ] 视频播放流畅，无卡顿
- [ ] 文字清晰可读
- [ ] 动画过渡自然
- [ ] 颜色准确（无偏色）
- [ ] 文件大小合理（根据用途）
- [ ] 在不同设备上测试播放

## 常见问题

### 导出速度慢

- 使用 `--concurrency` 增加并发数
- 降低分辨率进行快速预览
- 分段导出后合并

### 文件太大

- 增加 CRF 值（降低质量）
- 使用 WebM 格式
- 降低分辨率

### 导出失败

- 检查内存是否充足
- 检查磁盘空间
- 查看错误日志：`--log=verbose`

## 参考资源

- [Remotion 渲染文档](https://www.remotion.dev/docs/render)
- [Remotion 编码选项](https://www.remotion.dev/docs/encoding)
- [FFmpeg 编码指南](https://trac.ffmpeg.org/wiki/Encode/H.264)
