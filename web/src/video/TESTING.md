# 视频测试指南

本文档说明如何测试 Remotion 视频的预览和导出功能。

## 测试清单

### 1. 预览功能测试

#### 启动 Remotion Studio

```bash
cd web
npm run video:dev
```

**验证步骤：**
- [ ] Studio 在浏览器中正常打开（http://localhost:3001）
- [ ] 视频预览窗口显示正常
- [ ] 可以播放/暂停视频
- [ ] 时间轴可以拖动
- [ ] 场景列表显示正确（PromoVideo）

#### 热重载测试

1. 修改任意场景组件（如 `Scene1Intro.tsx`）
2. 保存文件
3. **验证：** Studio 自动刷新，更改立即生效

#### 场景切换测试

在 Studio 中：
- [ ] 拖动时间轴，验证场景正确切换
- [ ] 每个场景显示正确的内容
- [ ] 场景过渡动画流畅

### 2. 导出功能测试

#### 基本导出测试

```bash
cd web
npm run video:render
```

**验证步骤：**
- [ ] 导出过程无错误
- [ ] 输出文件 `web/out/video.mp4` 存在
- [ ] 文件大小合理（约 20-50MB）
- [ ] 视频可以正常播放

#### 视频质量检查

使用视频播放器（如 VLC、QuickTime）打开导出的视频：

- [ ] 视频分辨率正确（1920x1080）
- [ ] 帧率流畅（30fps）
- [ ] 文字清晰可读
- [ ] 颜色准确（无偏色）
- [ ] 动画过渡自然
- [ ] 无卡顿或跳帧

#### 不同格式导出测试

```bash
cd web

# 测试 WebM 格式
npx remotion render PromoVideo out/test.webm --codec=vp9

# 验证 WebM 文件可以播放
```

### 3. 场景内容测试

#### 场景1：项目介绍

- [ ] Logo 正确显示
- [ ] Logo 动画流畅
- [ ] 标题文字正确
- [ ] 副标题文字正确
- [ ] 文字淡入动画正常

#### 场景2：核心功能

- [ ] 4 个功能卡片都显示
- [ ] 卡片动画依次出现
- [ ] 图标和文字正确
- [ ] 卡片样式美观

#### 场景3：工作流程

- [ ] 4 个步骤都显示
- [ ] 步骤编号正确
- [ ] 步骤文字正确
- [ ] 步骤之间的连接线显示

#### 场景4：技术栈

- [ ] 3 个技术栈卡片都显示
- [ ] 每个卡片的内容正确
- [ ] 卡片动画依次出现

#### 场景5：行动号召

- [ ] 标题显示正确
- [ ] 副标题显示正确
- [ ] CTA 按钮显示正确
- [ ] 缩放动画流畅

### 4. 性能测试

#### 渲染时间测试

```bash
cd web
time npx remotion render PromoVideo out/test.mp4
```

**记录：**
- 渲染总时间
- 平均每帧渲染时间
- 内存使用峰值

**预期：**
- 60 秒视频（1800 帧）应在 5-15 分钟内完成
- 内存使用不超过系统限制

#### 并发渲染测试

```bash
# 测试不同并发数
npx remotion render PromoVideo out/test.mp4 --concurrency=4
npx remotion render PromoVideo out/test.mp4 --concurrency=8
```

**比较：**
- 不同并发数的渲染时间
- 内存使用情况
- 选择最优并发数

### 5. 跨平台测试

#### 在不同操作系统测试

- [ ] Windows：预览和导出正常
- [ ] macOS：预览和导出正常
- [ ] Linux：预览和导出正常（如果适用）

#### 在不同浏览器测试 Studio

- [ ] Chrome：预览正常
- [ ] Firefox：预览正常
- [ ] Safari：预览正常（macOS）
- [ ] Edge：预览正常

### 6. 错误处理测试

#### 测试无效配置

```bash
# 测试无效的 composition ID
npx remotion render InvalidID out/test.mp4
# 应该显示错误信息
```

#### 测试资源缺失

1. 临时删除一个资源文件
2. 尝试渲染
3. **验证：** 显示清晰的错误信息

## 自动化测试脚本

创建测试脚本 `web/scripts/test-video.sh`：

```bash
#!/bin/bash
# web/scripts/test-video.sh

set -e

cd "$(dirname "$0")/.."

echo "=== 测试视频预览 ==="
echo "启动 Remotion Studio..."
echo "请在浏览器中验证预览功能，然后按 Enter 继续"
read

echo "=== 测试视频导出 ==="
echo "导出测试视频..."
npx remotion render PromoVideo out/test.mp4 --log=info

if [ -f "out/test.mp4" ]; then
    echo "✅ 导出成功！文件大小: $(du -h out/test.mp4 | cut -f1)"
else
    echo "❌ 导出失败！"
    exit 1
fi

echo "=== 测试完成 ==="
```

Windows PowerShell 版本 `web/scripts/test-video.ps1`：

```powershell
# web/scripts/test-video.ps1

Set-Location $PSScriptRoot\..

Write-Host "=== 测试视频预览 ==="
Write-Host "启动 Remotion Studio..."
Write-Host "请在浏览器中验证预览功能，然后按 Enter 继续"
Read-Host

Write-Host "=== 测试视频导出 ==="
Write-Host "导出测试视频..."
npx remotion render PromoVideo out/test.mp4 --log=info

if (Test-Path "out/test.mp4") {
    $fileSize = (Get-Item "out/test.mp4").Length / 1MB
    Write-Host "✅ 导出成功！文件大小: $([math]::Round($fileSize, 2)) MB"
} else {
    Write-Host "❌ 导出失败！"
    exit 1
}

Write-Host "=== 测试完成 ==="
```

## 问题排查

### Studio 无法启动

1. 检查端口是否被占用：`netstat -an | findstr 3001`
2. 检查依赖是否安装：`npm install`
3. 检查配置文件：`remotion.config.ts`

### 导出失败

1. 检查内存是否充足
2. 检查磁盘空间
3. 查看详细日志：`--log=verbose`
4. 尝试降低并发数：`--concurrency=2`

### Chrome Headless Shell 下载失败或浏览器启动失败

如果遇到 `ECONNRESET` 或 "Old Headless mode has been removed" 错误，说明：

1. **网络问题**：无法从 Google 服务器下载 Chrome Headless Shell
2. **浏览器版本问题**：本地 Chrome 版本太新，已移除旧的 Headless 模式

#### 方案 1：手动下载 Chrome Headless Shell（推荐）

**步骤：**

1. **确定平台和架构**
   ```bash
   # macOS ARM64 (Apple Silicon)
   uname -m  # 应该显示 arm64
   
   # macOS x64 (Intel)
   uname -m  # 应该显示 x86_64
   ```

2. **下载对应版本**
   - 访问：https://googlechromelabs.github.io/chrome-for-testing/
   - 或直接下载链接（macOS ARM64）：
     ```
     https://storage.googleapis.com/chrome-for-testing-public/134.0.6998.35/mac-arm64/chrome-headless-shell-mac-arm64.zip
     ```
   - 或使用国内镜像（如果可用）

3. **解压并放置到正确位置**
   ```bash
   cd web
   
   # 创建目录
   mkdir -p node_modules/.remotion/chrome-headless-shell/mac-arm64
   
   # 解压下载的 zip 文件
   unzip ~/Downloads/chrome-headless-shell-mac-arm64.zip -d /tmp/
   
   # 复制到正确位置
   cp -r /tmp/chrome-headless-shell-mac-arm64/* node_modules/.remotion/chrome-headless-shell/mac-arm64/
   
   # 确保可执行权限
   chmod +x node_modules/.remotion/chrome-headless-shell/mac-arm64/chrome-headless-shell
   ```

4. **验证安装**
   ```bash
   ls -la node_modules/.remotion/chrome-headless-shell/mac-arm64/chrome-headless-shell
   ```

#### 方案 2：使用代理下载

如果使用代理，设置环境变量：

```bash
# 设置代理（根据你的代理配置调整）
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890

# 然后重试
npx remotion browser ensure
```

#### 方案 3：使用 VPN 或更换网络

网络连接问题可能是暂时的，可以：
1. 使用 VPN 连接
2. 更换网络环境（如使用手机热点）
3. 多次重试命令

#### 方案 4：使用详细日志调试

```bash
npx remotion render PromoVideo out/video.mp4 --log=verbose
```

这会显示更详细的错误信息，帮助定位问题。

#### 方案 5：检查浏览器路径配置

如果手动下载后仍然失败，检查 `remotion.config.ts` 配置：

```typescript
// 如果手动下载了 chrome-headless-shell，可以指定路径
Config.setBrowserExecutable(
  './node_modules/.remotion/chrome-headless-shell/mac-arm64/chrome-headless-shell'
)
```

### 视频质量问题

1. 检查 CRF 值（较低值 = 更高质量）
2. 检查分辨率设置
3. 检查编码格式

## 测试报告模板

```
# 视频测试报告

## 测试日期
2026-01-23

## 测试环境
- 操作系统：Windows 10
- Node.js 版本：v18.x
- Remotion 版本：4.0.409

## 测试结果

### 预览功能
- [x] Studio 启动正常
- [x] 视频预览正常
- [x] 热重载正常

### 导出功能
- [x] 基本导出成功
- [x] 视频质量良好
- [x] 文件大小合理

### 场景内容
- [x] 所有场景显示正确
- [x] 动画流畅
- [x] 文字清晰

### 性能
- 渲染时间：8 分钟
- 内存使用：2GB
- 文件大小：35MB

## 问题
无

## 建议
可以进一步优化动画效果
```

## 参考资源

- [Remotion 测试指南](https://www.remotion.dev/docs/testing)
- [Remotion 故障排查](https://www.remotion.dev/docs/troubleshooting)
