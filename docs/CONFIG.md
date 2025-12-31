# 配置说明

## 环境变量配置

所有配置通过环境变量或 `.env` 文件设置。

### API 配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `API_KEY` | string | `None` | API 认证密钥（可选） |
| `API_KEY_HEADER` | string | `X-API-Key` | API Key 请求头名称 |

### LLM 配置

至少需要配置一个 LLM API Key。

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `OPENAI_API_KEY` | string | `None` | OpenAI API Key |
| `OPENAI_BASE_URL` | string | `None` | OpenAI API Base URL（支持自定义，用于其他 OpenAI 兼容的 API） |
| `ANTHROPIC_API_KEY` | string | `None` | Anthropic API Key |
| `LLM_BASE_URL` | string | `None` | 自定义 LLM API Base URL（用于其他供应商） |
| `LLM_API_KEY` | string | `None` | 通用 LLM API Key（配合 `LLM_BASE_URL` 使用） |
| `LLM_PROVIDER` | string | `openai` | LLM 供应商类型（`openai`、`anthropic` 或 `custom`） |
| `LLM_MODEL` | string | `gpt-4` | LLM 模型名称 |
| `LLM_TEMPERATURE` | float | `0.0` | LLM 温度参数（0.0-1.0） |
| `LLM_MAX_TOKENS` | int | `4000` | LLM 最大输出 token 数 |

**使用其他供应商的大模型**：

支持使用 OpenAI 兼容接口的其他供应商（如 Azure OpenAI、本地部署的模型等）：

```bash
# 方式 1: 使用 OPENAI_BASE_URL（推荐）
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://your-custom-api-endpoint.com/v1
LLM_MODEL=your-model-name

# 方式 2: 使用通用配置
LLM_BASE_URL=https://your-custom-api-endpoint.com/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-name
```

### 日志查询配置

选择一种日志查询方式。

#### 日志易配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `LOG_QUERY_TYPE` | string | `logyi` | 日志查询类型：`logyi` 或 `file` |
| `LOGYI_BASE_URL` | string | `None` | 日志易服务地址 |
| `LOGYI_USERNAME` | string | `None` | 日志易用户名 |
| `LOGYI_APIKEY` | string | `None` | 日志易 API Key |
| `LOGYI_APPNAME` | string | `None` | 日志易项目名称（可选，如果未配置，Agent 会在需要时询问用户） |

#### 文件日志配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `LOG_QUERY_TYPE` | string | `logyi` | 日志查询类型：`logyi` 或 `file` |
| `LOG_FILE_BASE_PATH` | string | `None` | 日志文件基础路径 |

### 数据库配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `DATABASE_URL` | string | `None` | 数据库连接 URL |

**数据库 URL 格式**:
- MySQL: `mysql+pymysql://user:password@host:port/database`
- PostgreSQL: `postgresql://user:password@host:port/database`
- SQLite: `sqlite:///path/to/database.db`

**安全提示**: 数据库账号应该只有 SELECT 权限（只读），禁止 UPDATE、DELETE、INSERT 等写操作。

### Agent 配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `AGENT_MAX_ITERATIONS` | int | `15` | Agent 最大迭代次数 |
| `AGENT_MAX_EXECUTION_TIME` | int | `300` | Agent 最大执行时间（秒） |

### 任务管理配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `TASK_STORAGE_TYPE` | string | `memory` | 任务存储类型：`memory` 或 `redis` |
| `REDIS_URL` | string | `None` | Redis 连接 URL（当 `TASK_STORAGE_TYPE=redis` 时使用） |
| `TASK_TTL` | int | `3600` | 任务过期时间（秒） |
| `MAX_TASKS` | int | `1000` | 最大任务数 |

### 代码仓库配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `CODE_REPO_PATH` | string | `None` | 代码仓库路径 |

**路径格式说明**：
- **Windows**: 推荐使用正斜杠 `/` 或双反斜杠 `\\`
  - ✅ `CODE_REPO_PATH=F:/gf/code/algorithm`（推荐）
  - ✅ `CODE_REPO_PATH=F:\\gf\\code\\algorithm`
  - ✅ `CODE_REPO_PATH="F:\gf\code\algorithm"`（使用引号）
- **Linux/Mac**: 使用正斜杠 `/`
  - ✅ `CODE_REPO_PATH=/home/user/codebase`
- Python 的 `pathlib.Path` 会自动处理不同操作系统的路径格式

## 配置示例

### 最小配置（仅使用代码工具）

```bash
OPENAI_API_KEY=sk-...
CODE_REPO_PATH=/path/to/codebase
```

### 完整配置（使用所有功能）

```bash
# API 认证
API_KEY=your-secret-api-key

# LLM
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=4000

# 代码仓库
CODE_REPO_PATH=/path/to/codebase

# 日志查询（日志易）
LOG_QUERY_TYPE=logyi
LOGYI_BASE_URL=https://logyi.example.com
LOGYI_USERNAME=your-username
LOGYI_APIKEY=your-apikey
# LOGYI_APPNAME 可以不配置，Agent 会在需要时询问用户
# LOGYI_APPNAME=your-project

# 数据库
DATABASE_URL=mysql+pymysql://readonly:password@localhost:3306/mydb

# Agent
AGENT_MAX_ITERATIONS=15
AGENT_MAX_EXECUTION_TIME=300

# 任务管理（使用 Redis）
TASK_STORAGE_TYPE=redis
REDIS_URL=redis://localhost:6379/0
TASK_TTL=3600
MAX_TASKS=1000
```

### 开发环境配置

```bash
# 使用本地文件日志
LOG_QUERY_TYPE=file
LOG_FILE_BASE_PATH=./logs

# 使用内存任务存储
TASK_STORAGE_TYPE=memory

# 使用 SQLite 数据库
DATABASE_URL=sqlite:///./dev.db
```

## 配置验证

启动服务时，系统会检查必要的配置。如果缺少必需配置，会在日志中显示警告。

**必需配置**:
- 至少一个 LLM API Key（`OPENAI_API_KEY` 或 `ANTHROPIC_API_KEY`）

**可选配置**:
- `CODE_REPO_PATH`: 如果不配置，代码工具将不可用
- `LOGYI_*` 或 `LOG_FILE_BASE_PATH`: 如果不配置，日志工具将不可用
- `DATABASE_URL`: 如果不配置，数据库工具将不可用

## 安全建议

1. **API Key**: 使用强随机字符串作为 API Key，不要使用默认值。

2. **数据库账号**: 
   - 使用只读账号（只有 SELECT 权限）
   - 不要在连接字符串中硬编码密码
   - 使用环境变量或密钥管理服务

3. **日志易配置**: 
   - 保护 API Key 和用户名
   - 使用最小权限原则

4. **代码仓库**: 
   - 确保代码仓库路径安全
   - 不要暴露敏感信息

5. **环境变量**: 
   - 不要将 `.env` 文件提交到版本控制
   - 在生产环境使用环境变量或密钥管理服务

## 配置优先级

配置按以下优先级加载：

1. 环境变量
2. `.env` 文件
3. 默认值

## 配置检查

可以使用以下命令检查配置：

```python
from codebase_driven_agent.config import settings

print(f"LLM Model: {settings.llm_model}")
print(f"Code Repo Path: {settings.code_repo_path}")
print(f"Log Query Type: {settings.log_query_type}")
print(f"Database URL: {settings.database_url}")
```

