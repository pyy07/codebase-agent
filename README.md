# Codebase Driven Agent

基于代码仓库驱动的通用 AI Agent 平台，通过查阅代码、日志、数据库等多种数据源，为开发者提供智能化的代码分析和问题解决能力。

## 项目愿景

**Codebase Driven Agent** 是一个基于代码库驱动的通用 AI Agent 平台。我们的目标是构建一个能够深度理解代码库、自主调用多种工具、解决各类开发问题的智能助手。

**问题分析和错误排查** 只是我们当前的切入点，未来将扩展到更多场景：
- 🔍 代码理解和文档生成
- 🧪 测试用例生成和优化
- 🔧 代码重构建议
- 📊 代码质量分析
- 🚀 性能优化建议
- 📝 API 文档生成
- 以及其他基于代码库的智能化功能

## 当前功能（第一阶段）

当前版本专注于**问题分析和错误排查**功能：

- 🤖 **智能分析**: 基于 LangGraph Agent 框架，自主调用工具分析问题
- 💬 **交互式分析**: Agent 可以在分析过程中主动请求用户提供额外信息，支持多轮交互
- 📚 **多数据源**: 支持代码仓库、日志系统（日志易）、数据库查询
- 🔍 **代码检索**: 基于错误信息智能检索相关代码
- 📋 **日志分析**: 支持日志易 SPL 查询和本地文件日志查询
- 🗄️ **数据库查询**: 支持 MySQL、PostgreSQL 等数据库
- 🛠️ **内置工具集**: 提供文件读取、文件匹配、内容搜索、命令执行、网页获取等实用工具
- 🌐 **REST API**: 提供同步、异步、流式（SSE）三种接口
- 💻 **Web UI**: 提供友好的聊天式用户界面（React + TypeScript），支持实时步骤展示和交互式对话框

## 核心能力

- 🏗️ **代码库驱动**: 深度理解代码库结构和逻辑，基于代码上下文进行智能分析
- 🔌 **工具化架构**: 可扩展的工具系统，支持代码、日志、数据库等多种数据源
- 🧠 **自主决策**: Agent 能够自主选择工具、分析结果、生成解决方案
- 💬 **交互式协作**: Agent 能够识别信息不足的情况，主动请求用户输入，实现人机协作分析
- 🔄 **持续扩展**: 架构设计支持未来添加新的工具和功能场景

## 快速开始

### 安装依赖

```bash
pip install -e ".[dev]"
```

### 配置环境变量

创建 `.env` 文件：

```bash
# LLM 配置（至少配置一个）
OPENAI_API_KEY=your-openai-api-key
# 或使用自定义 Base URL（支持其他 OpenAI 兼容的 API）
OPENAI_BASE_URL=https://your-custom-api-endpoint.com/v1
OPENAI_API_KEY=your-api-key

# 或使用通用配置（其他供应商）
# LLM_BASE_URL=https://your-custom-api-endpoint.com/v1
# LLM_API_KEY=your-api-key

# 或
ANTHROPIC_API_KEY=your-anthropic-api-key

# 日志易配置（可选）
LOGYI_BASE_URL=https://your-logyi-instance.com
LOGYI_USERNAME=your-username
LOGYI_APIKEY=your-api-key
# LOGYI_APPNAME 可以不配置，Agent 会在需要时询问用户
# LOGYI_APPNAME=your-project-name

# 代码仓库配置（可选）
# Windows 示例（推荐使用正斜杠）:
CODE_REPO_PATH=your-code-repo-path
# Linux/Mac 示例:
# CODE_REPO_PATH=/home/user/codebase

# 数据库配置（可选）
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/dbname

# API 配置
API_KEY=your-api-key-for-authentication
```

### 运行服务

#### 方式 1: Docker 部署（推荐）

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填写必要的配置

# 2. 一键启动
chmod +x scripts/start.sh
./scripts/start.sh

# 或手动启动
docker-compose up -d
```

访问 http://localhost:8000/docs 查看 API 文档。

详细部署说明请查看 [DEPLOYMENT.md](DEPLOYMENT.md)

#### 方式 2: 本地运行

```bash
uvicorn codebase_driven_agent.main:app --reload
```

后端服务运行在 http://localhost:8000

访问 http://localhost:8000/docs 查看 Swagger API 文档。

### 启动 Web UI

1. **进入 Web 目录**

```bash
cd web
```

2. **安装前端依赖**

```bash
npm install
```

3. **启动前端开发服务器**

```bash
npm run dev
```

前端服务运行在 **http://localhost:3000**

4. **访问 Web UI**

打开浏览器访问：**http://localhost:3000**

详细说明请查看 [Web UI 启动指南](docs/WEB_UI.md)

### 启动桌面应用（可选）

项目支持打包为桌面应用，提供原生桌面体验。

#### 开发模式运行桌面应用

```bash
cd web
npm install  # 如果还没安装依赖
npm run electron:dev
```

#### 构建桌面应用

```bash
# 使用构建脚本（推荐）
./scripts/build-desktop.sh [platform]

# 或使用 npm 脚本
cd web
npm run electron:build
```

支持的平台：
- Windows (NSIS 安装程序)
- macOS (DMG 磁盘镜像)
- Linux (AppImage)

详细说明请查看 [桌面应用指南](docs/DESKTOP_APP.md)

## 项目结构

```
codebase_driven_agent/
├── __init__.py
├── main.py              # FastAPI 应用入口
├── config.py            # 配置管理
├── agent/               # Agent 核心逻辑
│   ├── __init__.py
│   ├── graph_executor.py    # LangGraph 执行器（核心）
│   ├── callbacks.py         # LangChain 回调
│   ├── input_parser.py      # 输入解析器
│   ├── output_parser.py     # 输出解析器
│   ├── memory.py            # 记忆管理
│   ├── prompt.py            # Prompt 模板
│   ├── session_manager.py   # 会话管理（用户交互）
│   └── utils.py             # Agent 工具函数
├── tools/               # LangChain Tools
│   ├── __init__.py
│   ├── base.py          # 工具基类
│   ├── code_tool.py     # 代码相关工具
│   ├── log_tool.py      # 日志查询工具
│   ├── database_tool.py # 数据库查询工具
│   └── registry.py      # 工具注册表
├── api/                 # API 路由
│   ├── __init__.py
│   ├── routes.py        # API 路由定义
│   ├── models.py        # API 数据模型
│   ├── middleware.py    # 中间件
│   └── sse.py           # SSE 事件流处理
└── utils/               # 工具函数
    ├── __init__.py
    ├── cache.py          # 缓存工具
    ├── database.py       # 数据库工具
    ├── extractors.py     # 数据提取器
    ├── logger.py         # 日志工具
    ├── log_query.py      # 日志查询工具
    └── metrics.py        # 指标收集
```

## 文档

- [API 文档](docs/API.md) - 完整的 API 接口文档和使用示例
- [使用指南](docs/USAGE.md) - 快速开始和使用场景
- [配置说明](docs/CONFIG.md) - 详细的配置选项说明
- [示例场景](docs/EXAMPLES.md) - 常见问题分析场景示例
- [Web UI 启动指南](docs/WEB_UI.md) - Web UI 启动和使用说明
- [桌面应用指南](docs/DESKTOP_APP.md) - 桌面应用开发、构建和使用说明
- [开发者扩展文档](docs/DEVELOPMENT.md) - 如何扩展功能和添加新工具
- [SETUP.md](SETUP.md) - 项目设置指南
- [TESTING.md](TESTING.md) - 测试指南
- [DEPLOYMENT.md](DEPLOYMENT.md) - 部署指南

启动服务后，访问 `http://localhost:8000/docs` 查看 Swagger API 文档。

## 开发

### 代码格式化

```bash
black codebase_driven_agent tests
ruff check codebase_driven_agent tests
```

### 类型检查

```bash
mypy codebase_driven_agent
```

### 运行测试

#### 后端测试

```bash
# 安装测试依赖（如果还没安装）
pip install -e ".[dev]"

# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_user_interaction.py

# 运行特定测试类或函数
pytest tests/test_user_interaction.py::TestGraphExecutorUserInteraction
pytest tests/test_user_interaction.py::TestGraphExecutorUserInteraction::test_request_user_input_node

# 显示详细输出
pytest -v

# 显示覆盖率
pytest --cov=codebase_driven_agent --cov-report=html
```

#### 前端测试

```bash
# 进入前端目录
cd web

# 安装依赖（如果还没安装）
npm install

# 运行所有测试
npm test

# 运行测试并显示 UI（交互式）
npm run test:ui

# 运行测试并生成覆盖率报告
npm run test:coverage

# 运行特定测试文件
npm test -- UserInputRequest.test.tsx
```

#### 运行用户交互功能测试

```bash
# 后端：运行用户交互相关测试
pytest tests/test_user_interaction.py -v

# 前端：运行用户交互组件测试
cd web
npm test -- UserInputRequest UserReply UnifiedStepsBlock
```

### 生成推广视频

项目使用 Remotion 制作推广视频。视频项目位于 `web/src/video/` 目录。

#### 开发视频

```bash
cd web

# 启动 Remotion Studio（开发环境）
npm run video:dev

# Studio 会在浏览器中打开，可以实时预览和编辑视频
```

#### 导出视频

```bash
cd web

# 导出 MP4 视频（默认 1920x1080，30fps）
npm run video:render

# 视频将导出到 web/out/video.mp4
```

#### 自定义视频导出

```bash
cd web

# 使用 Remotion CLI 自定义导出参数
npx remotion render PromoVideo out/custom-video.mp4 --codec=h264 --crf=18 --pixel-format=yuv420p
```

更多 Remotion 使用说明请参考 [Remotion 文档](https://www.remotion.dev/docs)。

## 许可证

MIT License

