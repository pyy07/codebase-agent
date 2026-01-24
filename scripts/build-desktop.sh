#!/bin/bash

# 桌面应用构建脚本
# 用法: ./scripts/build-desktop.sh [platform]
# platform: win, mac, linux (默认: 当前平台)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WEB_DIR="$PROJECT_ROOT/web"

cd "$WEB_DIR"

# 检查参数
PLATFORM="${1:-$(uname | tr '[:upper:]' '[:lower:]')}"

echo "Building desktop application for platform: $PLATFORM"
echo "Project root: $PROJECT_ROOT"
echo "Web directory: $WEB_DIR"

# 检查依赖
if ! command -v npm &> /dev/null; then
    echo "Error: npm is not installed"
    exit 1
fi

# 安装依赖（如果需要）
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# 构建前端
echo "Building frontend..."
npm run build

# 根据平台构建
case "$PLATFORM" in
    win|windows)
        echo "Building for Windows..."
        npm run electron:build -- --win
        ;;
    mac|darwin)
        echo "Building for macOS..."
        npm run electron:build -- --mac
        ;;
    linux)
        echo "Building for Linux..."
        npm run electron:build -- --linux
        ;;
    *)
        echo "Building for current platform..."
        npm run electron:build
        ;;
esac

echo "Build completed! Output files are in: $WEB_DIR/release/"
