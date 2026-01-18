# Project Context

## Purpose

**Codebase Driven Agent** 是一个基于代码库驱动的通用 AI Agent 平台。项目的核心目标是构建一个能够深度理解代码库、自主调用多种工具、解决各类开发问题的智能助手。

当前版本（v0.1.0）专注于**问题分析和错误排查**功能，未来将扩展到：
- 代码理解和文档生成
- 测试用例生成和优化
- 代码重构建议
- 代码质量分析
- 性能优化建议
- API 文档生成

## Tech Stack

### Backend (Python 3.11+)
- **Framework**: FastAPI (异步 Web 框架)
- **AI/LLM**: LangChain 1.2+, LangGraph 0.2+, langchain-openai, langchain-anthropic
- **Database**: SQLAlchemy 2.0+, PyMySQL, psycopg2-binary
- **Configuration**: pydantic-settings (环境变量管理)
- **HTTP**: requests, sse-starlette (SSE 流式响应)
- **Caching**: Redis (可选)
- **Utilities**: GitPython, python-dotenv, sqlparse

### Frontend (TypeScript/React)
- **Framework**: React 18 + TypeScript 5
- **Build Tool**: Vite 5
- **Styling**: Tailwind CSS 4 + CSS Variables (HSL color system)
- **UI Components**: shadcn/ui (基于 Radix UI)
- **Markdown**: react-markdown + react-syntax-highlighter
- **State Management**: React Hooks (useState, useCallback, useRef)
- **HTTP**: Axios, native fetch
- **Theme**: next-themes (dark/light mode)

### DevOps
- **Container**: Docker, docker-compose
- **Testing**: pytest (backend), vitest (frontend)
- **Linting**: Black, Ruff, mypy (Python); ESLint (TypeScript)
- **Package Manager**: pip/setuptools (backend), npm (frontend)

## Project Conventions

### Code Style

#### Python (Backend)
- **Formatter**: Black (line-length: 100)
- **Linter**: Ruff + mypy
- **Naming**:
  - 类名: `PascalCase` (如 `AgentExecutorWrapper`, `BaseCodebaseTool`)
  - 函数/变量: `snake_case` (如 `create_llm`, `context_files`)
  - 常量: `UPPER_SNAKE_CASE` (如 `API_KEY`, `MAX_ITERATIONS`)
  - 私有方法: 下划线前缀 `_method_name`
- **Docstrings**: 中文注释，简洁明了
- **Type Hints**: 推荐使用，但不强制 (`disallow_untyped_defs = false`)
- **Imports**: 分组排序（标准库 → 第三方 → 本地模块）

#### TypeScript (Frontend)
- **Target**: ES2020
- **Strict Mode**: 启用
- **Path Aliases**: `@/*` 映射到 `./src/*`
- **Naming**:
  - 组件: `PascalCase` (如 `AnalysisForm.tsx`)
  - hooks: `camelCase` with `use` prefix (如 `useSSE.ts`)
  - 类型/接口: `PascalCase` (如 `AnalysisResult`, `PlanStep`)
  - 变量/函数: `camelCase`

### Architecture Patterns

#### Backend
- **Agent Pattern**: 基于 LangChain 的 Agent 架构，支持自主工具调用
- **Tool Registry**: 可扩展的工具注册系统，支持动态注册
- **Factory Pattern**: `create_llm()`, `create_agent_executor()` 工厂函数
- **Base Class Pattern**: `BaseCodebaseTool` 统一工具接口
- **Configuration**: pydantic-settings 单例配置 (`settings`)
- **Layered Architecture**:
  - `api/` - HTTP 路由和模型定义
  - `agent/` - Agent 核心逻辑
  - `tools/` - LangChain 工具实现
  - `utils/` - 通用工具函数

#### Frontend
- **Component-based**: 功能组件化，每个组件独立 CSS
- **Custom Hooks**: 复用逻辑封装为 hooks (如 `useSSE`)
- **Theme Provider**: 支持 dark/light 主题切换
- **SSE Streaming**: 实时流式响应显示进度

### Testing Strategy

#### Backend Testing
- **Framework**: pytest + pytest-asyncio
- **Coverage**: pytest-cov
- **Test Location**: `tests/` 目录
- **Naming**: `test_*.py` 文件, `test_*` 函数, `Test*` 类
- **Async Mode**: auto (asyncio_mode = "auto")

#### Frontend Testing
- **Framework**: vitest + @testing-library/react
- **Coverage**: vitest --coverage
- **Test Location**: `src/components/__tests__/`, `src/hooks/__tests__/`
- **Naming**: `*.test.tsx` / `*.test.ts`

### Git Workflow

- **Branching**: Feature branches → main
- **Commit Messages**: 中文或英文，清晰描述变更内容
- **OpenSpec Integration**: 重大变更需先创建 proposal

## Domain Context

### Core Concepts
- **Agent**: 基于 LLM 的智能助手，能够自主决策和调用工具
- **Tool**: Agent 可调用的能力单元（代码搜索、日志查询、数据库查询）
- **日志易 (Logyi)**: 企业日志分析平台，支持 SPL 查询语言
- **SPL**: Search Processing Language，日志易的查询语言
- **SSE**: Server-Sent Events，用于实时流式通信

### Key Workflows
1. **分析请求**: 用户提交问题 → Agent 规划 → 工具调用 → 结果汇总
2. **流式响应**: 后端通过 SSE 推送进度、计划步骤、中间结果
3. **工具执行**: Agent 自主选择工具，可多次迭代调用

## Important Constraints

### Technical Constraints
- Python 版本: >= 3.11
- 必须配置至少一个 LLM API Key (OpenAI / Anthropic / Custom)
- 数据库工具仅在配置 `DATABASE_URL` 时可用
- 日志查询支持日志易或本地文件两种模式

### Performance Constraints
- Agent 最大迭代次数: 默认 15 次
- Agent 最大执行时间: 默认 300 秒
- 工具输出最大长度: 默认 5000 字符（可截断）
- 任务 TTL: 默认 3600 秒

### Security Constraints
- API Key 认证（可选，通过 `X-API-Key` header）
- 数据库查询为只读操作
- 敏感配置通过环境变量管理

## External Dependencies

### Required
- **LLM Provider**: OpenAI API / Anthropic API / 兼容 OpenAI 的自定义 API

### Optional
- **日志易 (Logyi)**: 企业日志查询服务
  - 配置: `LOGYI_BASE_URL`, `LOGYI_USERNAME`, `LOGYI_APIKEY`
- **MySQL/PostgreSQL**: 数据库查询
  - 配置: `DATABASE_URL`
- **Redis**: 任务存储（生产环境推荐）
  - 配置: `REDIS_URL`
- **代码仓库**: 本地代码库路径
  - 配置: `CODE_REPO_PATH`
