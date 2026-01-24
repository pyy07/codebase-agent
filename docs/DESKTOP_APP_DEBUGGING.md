# 桌面应用调试指南

## 查看日志

### 方法 1: 日志文件（推荐）

应用会在以下位置创建日志文件：

- **macOS**: `~/Library/Application Support/Codebase Agent/logs/app-YYYY-MM-DD.log`
- **Windows**: `%APPDATA%/Codebase Agent/logs/app-YYYY-MM-DD.log`
- **Linux**: `~/.config/Codebase Agent/logs/app-YYYY-MM-DD.log`

日志文件包含：
- 应用启动信息
- 后端进程启动日志
- 错误和异常信息
- 窗口加载状态

### 方法 2: 在终端运行应用

在终端中运行应用可以看到实时日志输出：

```bash
# macOS
/Applications/Codebase\ Agent.app/Contents/MacOS/Codebase\ Agent

# 或者如果应用在 release 目录
./release/mac-arm64/Codebase\ Agent.app/Contents/MacOS/Codebase\ Agent
```

### 方法 3: 打开开发者工具

应用支持快捷键打开开发者工具：

- **macOS**: `Cmd + Shift + I`
- **Windows/Linux**: `Ctrl + Shift + I`

开发者工具可以查看：
- 前端控制台日志
- 网络请求
- 页面元素
- 性能分析

### 方法 4: 查看日志文件位置

使用快捷键查看日志文件位置：

- **macOS**: `Cmd + Shift + L`
- **Windows/Linux**: `Ctrl + Shift + L`

这会显示一个对话框，可以：
- 打开日志文件所在文件夹
- 复制日志文件路径

## 常见问题排查

### 白屏问题

如果应用打开后显示白屏，检查以下内容：

1. **查看日志文件**：检查是否有错误信息
2. **打开开发者工具**：按 `Cmd+Shift+I` 查看控制台错误
3. **检查前端文件**：确认 `dist/index.html` 文件存在
4. **检查后端状态**：确认后端服务已启动（查看日志中的后端启动信息）

### Python 未找到

如果提示 Python 未找到：

1. **检查系统 Python**：
   ```bash
   which python3
   python3 --version
   ```

2. **设置环境变量**：
   ```bash
   export PYTHON_PATH=/usr/local/bin/python3
   ```

3. **查看日志**：日志中会显示检测到的 Python 路径

### 后端启动失败

如果后端无法启动：

1. **查看日志文件**：后端错误会记录在日志中
2. **检查 Python 依赖**：
   ```bash
   pip install -r requirements.txt
   ```
3. **检查端口占用**：确认 8000 端口未被占用
4. **手动测试后端**：
   ```bash
   python3 run_backend.py
   ```

### 前端加载失败

如果前端页面无法加载：

1. **检查 dist 目录**：确认前端已构建
2. **打开开发者工具**：查看网络请求错误
3. **检查文件路径**：日志中会显示加载的文件路径

## 调试技巧

### 1. 启用详细日志

应用默认会记录所有日志。如果需要更详细的日志，可以修改 `main.js` 中的日志级别。

### 2. 检查应用数据目录

应用数据存储在：
- **macOS**: `~/Library/Application Support/Codebase Agent/`
- **Windows**: `%APPDATA%/Codebase Agent/`
- **Linux**: `~/.config/Codebase Agent/`

### 3. 重置应用

如果应用出现问题，可以删除应用数据目录重置应用（注意：这会删除所有配置和日志）。

### 4. 查看系统日志

macOS 系统日志：
```bash
log show --predicate 'process == "Codebase Agent"' --last 1h
```

## 报告问题

如果遇到问题，请提供以下信息：

1. **日志文件**：完整的日志文件内容
2. **系统信息**：
   - 操作系统版本
   - Python 版本
   - 应用版本
3. **错误截图**：如果有错误对话框
4. **复现步骤**：如何触发问题

## 开发模式调试

开发模式下，应用会自动打开开发者工具，并输出详细日志到控制台：

```bash
cd web
npm run electron:dev
```

开发模式下的日志会同时输出到：
- 终端控制台
- 日志文件
