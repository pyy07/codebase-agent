# 项目设置指南

## 快速开始

### 1. 安装 Python 依赖

```bash
# 安装所有依赖（包括开发依赖）
pip install -r requirements.txt

# 或者仅安装核心依赖
pip install fastapi uvicorn pydantic pydantic-settings python-dotenv
```

### 2. 配置环境变量（可选）

创建 `.env` 文件：

```bash
# LLM 配置（至少配置一个）
OPENAI_API_KEY=your-openai-api-key
# 或
ANTHROPIC_API_KEY=your-anthropic-api-key

# 日志易配置（可选）
LOGYI_BASE_URL=https://your-logyi-instance.com
LOGYI_USERNAME=your-username
LOGYI_APIKEY=your-api-key
LOGYI_APPNAME=your-project-name

# 数据库配置（可选）
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/dbname

# API 配置（可选）
API_KEY=your-api-key-for-authentication
```

### 3. 验证安装

```bash
# 测试导入
python -c "from codebase_driven_agent.main import app; print('✅ Success')"

# 启动服务
python -m codebase_driven_agent.main
```

访问 http://localhost:8000/docs 查看 API 文档。

## 开发环境设置

### 安装开发工具

```bash
pip install black mypy pytest pytest-asyncio pytest-cov ruff
```

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

```bash
pytest
```

## 项目结构

```
codebase_driven_agent/
├── __init__.py
├── main.py              # FastAPI 应用入口
├── config.py            # 配置管理
├── agent/               # Agent 核心逻辑（待实现）
├── tools/               # LangChain Tools（待实现）
├── api/                 # API 路由（待实现）
└── utils/               # 工具函数
    ├── __init__.py
    └── logger.py        # 日志系统
```

## 下一步

完成基础设置后，可以：

1. 查看 `TESTING.md` 了解如何测试基础功能
2. 查看 `README.md` 了解项目概述
3. 查看 `openspec/changes/add-error-analysis-agent/` 了解详细设计

