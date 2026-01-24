# Change: 添加桌面应用打包功能

## Why

当前项目是一个 Web 应用，需要用户手动启动后端服务和前端服务，并通过浏览器访问。为了提升用户体验和降低使用门槛，需要支持将项目打包成桌面应用，让用户能够：

1. **简化部署和使用**：用户无需手动启动服务，一键启动桌面应用即可使用
2. **更好的用户体验**：桌面应用提供原生窗口体验，无需打开浏览器
3. **离线使用**：所有服务都在本地运行，不依赖外部服务器
4. **跨平台支持**：支持 Windows、macOS、Linux 三大主流桌面平台
5. **保持架构不变**：不改变现有的后端和前端架构，只是增加打包能力

## What Changes

- **新增 Electron 桌面应用支持**：
  - 集成 Electron 框架，将 Web 应用包装为桌面应用
  - 创建 Electron 主进程和预加载脚本
  - 实现后端进程自动启动和管理
  - 实现前端窗口管理和生命周期控制

- **后端进程管理**：
  - 在 Electron 中自动检测和启动 Python 后端服务
  - 管理后端进程的生命周期（启动、停止、重启）
  - 处理后端服务异常和自动恢复
  - 支持后端日志输出和错误处理

- **打包配置和脚本**：
  - 配置 electron-builder 进行应用打包
  - 支持 Windows (NSIS)、macOS (DMG)、Linux (AppImage) 打包
  - 包含 Python 运行时和依赖的打包策略
  - 创建应用图标和元数据

- **开发工具和文档**：
  - 提供桌面应用开发命令
  - 提供打包命令和脚本
  - 更新文档说明如何构建和分发桌面应用

## Impact

- **受影响的规范**：`desktop-app-packaging` capability（新增）
- **受影响的代码**：
  - `web/electron/` - 新增 Electron 相关文件（新建目录）
    - `main.js` - Electron 主进程
    - `preload.js` - 预加载脚本
    - `backend.js` - 后端进程管理器
  - `web/package.json` - 新增 Electron 相关依赖和脚本
  - `web/vite.config.ts` - 可能需要调整构建配置
  - `web/build/` - 应用图标和资源（新建目录）
  - `scripts/build-desktop.sh` - 桌面应用构建脚本（新建）
  - `README.md` - 更新文档说明桌面应用构建
  - `.gitignore` - 添加桌面应用构建产物忽略规则

- **向后兼容性**：完全兼容，不影响现有功能。桌面应用打包功能作为可选功能，不影响现有的 Web 部署方式。

- **新增依赖**：
  - `electron` - Electron 核心库
  - `electron-builder` - Electron 应用打包工具
  - `concurrently` - 并发运行多个命令（开发时使用）
  - `wait-on` - 等待服务启动（开发时使用）

- **技术选择**：
  - **Electron**：选择 Electron 而非 Tauri 或其他方案，因为：
    - 项目已有完整的 React 前端，Electron 集成成本最低
    - Electron 生态成熟，文档和社区支持丰富
    - 可以复用现有的 Web 代码，无需重写
    - 虽然体积较大，但对于桌面应用来说可接受
