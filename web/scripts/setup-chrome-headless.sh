#!/bin/bash
# web/scripts/setup-chrome-headless.sh
# 手动设置 Chrome Headless Shell 的辅助脚本

set -e

cd "$(dirname "$0")/.."

# 检测平台
ARCH=$(uname -m)
OS=$(uname -s | tr '[:upper:]' '[:lower:]')

if [[ "$OS" == "darwin" ]]; then
  if [[ "$ARCH" == "arm64" ]]; then
    PLATFORM="mac-arm64"
  else
    PLATFORM="mac-x64"
  fi
elif [[ "$OS" == "linux" ]]; then
  if [[ "$ARCH" == "aarch64" ]]; then
    PLATFORM="linux-arm64"
  else
    PLATFORM="linux-x64"
  fi
else
  echo "❌ 不支持的操作系统: $OS"
  exit 1
fi

echo "=========================================="
echo "Chrome Headless Shell 设置脚本"
echo "=========================================="
echo "平台: $PLATFORM"
echo ""

CHROME_VERSION="134.0.6998.35"
TARGET_DIR="node_modules/.remotion/chrome-headless-shell/$PLATFORM"
DOWNLOAD_URL="https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/${PLATFORM}/chrome-headless-shell-${PLATFORM}.zip"

echo "📥 下载地址:"
echo "   $DOWNLOAD_URL"
echo ""
echo "📋 手动下载步骤:"
echo "   1. 复制上面的下载地址"
echo "   2. 在浏览器中打开，或使用 curl/wget 下载"
echo "   3. 下载完成后，运行以下命令解压："
echo ""
echo "   mkdir -p $TARGET_DIR"
echo "   unzip ~/Downloads/chrome-headless-shell-${PLATFORM}.zip -d /tmp/"
echo "   cp -r /tmp/chrome-headless-shell-${PLATFORM}/* $TARGET_DIR/"
echo "   chmod +x $TARGET_DIR/chrome-headless-shell"
echo ""

# 检查是否已经安装
if [[ -f "$TARGET_DIR/chrome-headless-shell" ]]; then
  echo "✅ Chrome Headless Shell 已安装"
  echo "   路径: $TARGET_DIR/chrome-headless-shell"
  exit 0
fi

# 尝试自动下载
echo "🔄 尝试自动下载..."
if command -v curl &> /dev/null; then
  echo "   使用 curl 下载..."
  mkdir -p "$TARGET_DIR"
  TEMP_ZIP="/tmp/chrome-headless-shell-${PLATFORM}.zip"
  
  if curl -L -o "$TEMP_ZIP" "$DOWNLOAD_URL" 2>/dev/null; then
    echo "✅ 下载成功"
    unzip -q "$TEMP_ZIP" -d /tmp/
    cp -r "/tmp/chrome-headless-shell-${PLATFORM}"/* "$TARGET_DIR/"
    chmod +x "$TARGET_DIR/chrome-headless-shell"
    rm "$TEMP_ZIP"
    echo "✅ 安装完成！"
    echo "   路径: $TARGET_DIR/chrome-headless-shell"
    exit 0
  else
    echo "❌ 自动下载失败（可能是网络问题）"
    echo ""
    echo "请按照上面的手动步骤操作，或："
    echo "   1. 使用 VPN"
    echo "   2. 设置代理环境变量:"
    echo "      export HTTP_PROXY=http://127.0.0.1:7890"
    echo "      export HTTPS_PROXY=http://127.0.0.1:7890"
    echo "   3. 然后重新运行此脚本"
    exit 1
  fi
elif command -v wget &> /dev/null; then
  echo "   使用 wget 下载..."
  mkdir -p "$TARGET_DIR"
  TEMP_ZIP="/tmp/chrome-headless-shell-${PLATFORM}.zip"
  
  if wget -O "$TEMP_ZIP" "$DOWNLOAD_URL" 2>/dev/null; then
    echo "✅ 下载成功"
    unzip -q "$TEMP_ZIP" -d /tmp/
    cp -r "/tmp/chrome-headless-shell-${PLATFORM}"/* "$TARGET_DIR/"
    chmod +x "$TARGET_DIR/chrome-headless-shell"
    rm "$TEMP_ZIP"
    echo "✅ 安装完成！"
    echo "   路径: $TARGET_DIR/chrome-headless-shell"
    exit 0
  else
    echo "❌ 自动下载失败（可能是网络问题）"
    echo ""
    echo "请按照上面的手动步骤操作"
    exit 1
  fi
else
  echo "❌ 未找到 curl 或 wget，请手动下载"
  exit 1
fi
