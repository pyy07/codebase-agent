# 桌面应用开发和使用指南

本文档介绍如何开发、构建和使用 Codebase Agent 桌面应用。

## 概述

Codebase Agent 桌面应用使用 Electron 框架，将 Web 应用打包为原生桌面应用。桌面应用会自动启动和管理 Python 后端服务，用户无需手动启动服务即可使用。

## 系统要求

### 开发环境

- **Node.js**: >= 18.0.0
- **Python**: >= 3.11
- **npm**: >= 9.0.0

### 运行环境

- **操作系统**: Windows 10+, macOS 10.15+, Linux (Ubuntu 20.04+)
- **Python**: >= 3.11（需要系统安装）

## 开发

### 安装依赖

```bash
cd web
npm install
```

### 开发模式运行

开发模式下，应用会同时启动前端开发服务器和 Electron 窗口：

```bash
cd web
npm run electron:dev
```

这会：
1. 启动 Vite 开发服务器（http://localhost:3000）
2. 等待前端服务器就绪
3. 启动 Electron 窗口
4. 自动启动 Python 后端服务

### 开发特性

- **热重载**: 前端代码修改会自动刷新
- **开发者工具**: 自动打开 Chrome DevTools
- **后端日志**: 后端日志输出到 Electron 控制台

## 构建

### 构建前端

首先构建前端静态文件：

```bash
cd web
npm run build
```

### 打包桌面应用

#### 使用 npm 脚本

```bash
cd web

# 打包当前平台
npm run electron:build

# 打包特定平台（需要对应平台环境）
npm run electron:build -- --win    # Windows
npm run electron:build -- --mac    # macOS
npm run electron:build -- --linux  # Linux
```

#### 使用构建脚本

```bash
# 从项目根目录运行
./scripts/build-desktop.sh [platform]

# platform 可选: win, mac, linux
# 默认: 当前平台
```

### 打包输出

打包后的文件位于 `web/release/` 目录：

- **Windows**: `Codebase Agent Setup X.X.X.exe` (NSIS 安装程序)
- **macOS**: `Codebase Agent-X.X.X.dmg` (磁盘镜像)
- **Linux**: `Codebase Agent-X.X.X.AppImage` (可执行文件)

## 应用图标

应用图标文件应放在 `web/build/` 目录：

- `icon.ico` - Windows 图标
- `icon.icns` - macOS 图标
- `icon.png` - Linux 图标

如果没有图标文件，electron-builder 会使用默认图标。

## 配置

### Python 路径

桌面应用会自动检测系统 Python 环境。如果检测失败，可以通过环境变量指定：

```bash
# Windows
set PYTHON_PATH=C:\Python311\python.exe

# macOS/Linux
export PYTHON_PATH=/usr/bin/python3
```

### 后端配置

后端配置通过环境变量管理，与 Web 版本相同。在桌面应用中：

1. **系统环境变量**: 继续支持系统级环境变量
2. **应用内配置**: 未来版本可能支持应用内配置界面

## 使用

### 启动应用

1. **Windows**: 双击安装程序，安装后从开始菜单或桌面快捷方式启动
2. **macOS**: 打开 DMG 文件，将应用拖到 Applications 文件夹，然后启动
3. **Linux**: 下载 AppImage，添加执行权限后运行：
   ```bash
   chmod +x Codebase-Agent-X.X.X.AppImage
   ./Codebase-Agent-X.X.X.AppImage
   ```

### 首次启动

首次启动时，应用会：
1. 检测 Python 环境
2. 启动后端服务
3. 打开主窗口

如果 Python 未安装或版本不符合要求，会显示错误提示。

### 配置 API Key

在应用界面中配置 LLM API Key（与 Web 版本相同）。

## 故障排除

### Python 未找到

**问题**: 应用提示 "Python 3.11+ not found"

**解决方案**:
1. 安装 Python 3.11 或更高版本
2. 确保 Python 在系统 PATH 中
3. 或设置 `PYTHON_PATH` 环境变量

### 后端启动失败

**问题**: 后端服务无法启动

**解决方案**:
1. 检查 Python 依赖是否安装：`pip install -r requirements.txt`
2. 检查端口 8000 是否被占用
3. 查看 Electron 控制台的错误信息

### 前端无法连接后端

**问题**: 前端显示连接错误

**解决方案**:
1. 确认后端服务已启动（检查控制台日志）
2. 检查防火墙设置
3. 确认端口 8000 未被其他程序占用

### 打包失败

**问题**: electron-builder 打包失败

**解决方案**:
1. 确保已安装所有依赖：`npm install`
2. 确保前端已构建：`npm run build`
3. 检查磁盘空间是否充足
4. 查看详细错误信息：`npm run electron:build -- --debug`

## 架构说明

### 进程结构

```
Electron 主进程
├── BrowserWindow (渲染进程)
│   └── React 前端应用
└── BackendManager
    └── Python 后端进程 (独立进程)
```

### 文件结构

```
web/
├── electron/
│   ├── main.js          # Electron 主进程
│   ├── preload.js       # 预加载脚本
│   └── backend.js       # 后端进程管理器
├── build/               # 应用图标和资源
└── release/             # 打包输出目录
```

## 开发注意事项

1. **进程隔离**: 前端运行在渲染进程，后端运行在独立进程
2. **安全**: 使用 `contextIsolation` 和 `nodeIntegration: false` 确保安全
3. **资源路径**: 生产环境使用相对路径，开发环境使用绝对路径
4. **后端管理**: 确保后端进程在应用关闭时正确清理

## 未来改进

- [ ] 应用内配置界面
- [ ] 自动更新机制
- [ ] 系统托盘支持
- [ ] 打包 Python 运行时（无需系统 Python）
- [ ] 应用签名（macOS/Windows）

## 参考资源

- [Electron 文档](https://www.electronjs.org/docs)
- [electron-builder 文档](https://www.electron.build/)
- [Vite 文档](https://vitejs.dev/)
