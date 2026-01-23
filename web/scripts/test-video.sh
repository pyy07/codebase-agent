#!/bin/bash
# 视频测试脚本

set -e

cd "$(dirname "$0")/.."

echo "=== Remotion 视频测试 ==="
echo ""

echo "1. 检查依赖..."
if ! command -v npx &> /dev/null; then
    echo "❌ 错误: 未找到 npx，请先安装 Node.js"
    exit 1
fi

echo "✅ 依赖检查通过"
echo ""

echo "2. 测试视频导出..."
echo "   导出测试视频到 out/test.mp4"
npx remotion render PromoVideo out/test.mp4 --log=info

if [ -f "out/test.mp4" ]; then
    FILE_SIZE=$(du -h out/test.mp4 | cut -f1)
    echo "✅ 导出成功！"
    echo "   文件大小: $FILE_SIZE"
    echo "   文件路径: $(pwd)/out/test.mp4"
else
    echo "❌ 导出失败！"
    exit 1
fi

echo ""
echo "3. 测试完成！"
echo ""
echo "下一步："
echo "  - 使用视频播放器打开 out/test.mp4 检查视频质量"
echo "  - 运行 'npm run video:dev' 启动 Remotion Studio 进行预览"
echo ""
