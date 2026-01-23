#!/bin/bash
# web/scripts/export-videos.sh
# 批量导出视频脚本（Linux/Mac）

set -e  # 遇到错误立即退出

cd "$(dirname "$0")/.."

echo "=========================================="
echo "开始批量导出视频..."
echo "=========================================="

# 创建输出目录
mkdir -p out

# 1. 高质量 MP4（CRF 18，适合最终发布）
echo ""
echo "[1/4] 导出高质量 MP4 (CRF 18)..."
npx remotion render PromoVideo out/promo-hq.mp4 \
  --codec=h264 \
  --crf=18 \
  --pixel-format=yuv420p \
  --log=info

# 2. 中等质量 MP4（CRF 23，平衡质量和文件大小）
echo ""
echo "[2/4] 导出中等质量 MP4 (CRF 23)..."
npx remotion render PromoVideo out/promo-medium.mp4 \
  --codec=h264 \
  --crf=23 \
  --pixel-format=yuv420p \
  --log=info

# 3. 低质量 MP4（CRF 28，文件更小，适合快速预览）
echo ""
echo "[3/4] 导出低质量 MP4 (CRF 28)..."
npx remotion render PromoVideo out/promo-low.mp4 \
  --codec=h264 \
  --crf=28 \
  --pixel-format=yuv420p \
  --log=info

# 4. WebM 格式（VP9 编码，现代浏览器，文件更小）
echo ""
echo "[4/4] 导出 WebM 格式 (VP9)..."
npx remotion render PromoVideo out/promo.webm \
  --codec=vp9 \
  --crf=30 \
  --log=info

echo ""
echo "=========================================="
echo "导出完成！"
echo "=========================================="
echo ""
echo "输出文件："
ls -lh out/*.mp4 out/*.webm 2>/dev/null || true
echo ""
echo "文件大小："
du -h out/*.mp4 out/*.webm 2>/dev/null || true
echo ""
