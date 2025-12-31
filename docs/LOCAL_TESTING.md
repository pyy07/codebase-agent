# 本地测试指南

本文档提供详细的本地测试步骤，帮助你快速上手 Codebase Driven Agent 项目。

## 前置要求

- Python 3.11+ 
- pip 或 conda
- （可选）Node.js 16+ 和 npm（用于前端开发）
- （可选）Docker 和 Docker Compose（用于容器化部署）

## 快速开始

### 1. 克隆项目（如果还没有）

```bash
cd codebase-agent
```

### 2. 安装 Python 依赖

```bash
# 方式 1: 使用 pip（推荐）
pip install -e ".[dev]"

# 方式 2: 使用 requirements.txt
pip install -r requirements.txt

# 方式 3: 使用 conda
conda create -n codebase-agent python=3.11
conda activate codebase-agent
pip install -r requirements.txt
```

### 3. 配置环境变量

创建 `.env` 文件（在项目根目录）：

```bash
# ========== 必需配置 ==========
# 至少配置一个 LLM API Key
OPENAI_API_KEY=sk-your-openai-api-key-here
# 或
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here

# LLM 模型配置（可选）
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=4000

# ========== 可选配置 ==========
# API 认证（可选，如果设置了，API 请求需要提供 X-API-Key 头）
API_KEY=your-secret-api-key

# 代码仓库路径（可选，如果想让 Agent 分析本地代码）
# Windows 示例（推荐使用正斜杠）:
CODE_REPO_PATH=F:/gf/code/algorithm
# 或使用双反斜杠:
# CODE_REPO_PATH=F:\\gf\\code\\algorithm
# Linux/Mac 示例:
# CODE_REPO_PATH=/home/user/codebase
# 相对路径示例:
# CODE_REPO_PATH=./codebase

# 日志易配置（可选，如果使用日志易）
LOGYI_BASE_URL=https://your-logyi-instance.com
LOGYI_USERNAME=your-username
LOGYI_APIKEY=your-api-key
# LOGYI_APPNAME 可以不配置，Agent 会在需要时询问用户
# LOGYI_APPNAME=your-project-name

# 使用其他供应商的大模型（可选）
# 方式 1: 使用 OPENAI_BASE_URL
# OPENAI_BASE_URL=https://your-custom-api-endpoint.com/v1
# OPENAI_API_KEY=your-api-key

# 方式 2: 使用通用配置
# LLM_BASE_URL=https://your-custom-api-endpoint.com/v1
# LLM_API_KEY=your-api-key
# LLM_MODEL=your-model-name

# 文件日志配置（可选，如果使用文件日志）
LOG_FILE_BASE_PATH=./logs
LOG_QUERY_TYPE=file  # 或 "logyi"

# 数据库配置（可选，如果使用数据库查询）
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/dbname
# 或 PostgreSQL
# DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# 缓存配置（可选）
CACHE_ENABLED=true
CACHE_TTL=3600  # 缓存过期时间（秒）
CACHE_MAX_SIZE=1000  # 最大缓存条目数
```

**最小配置示例**（仅用于测试）：

```bash
# .env
OPENAI_API_KEY=sk-your-key-here
```

### 4. 验证安装

```bash
# 测试导入
python -c "from codebase_driven_agent.main import app; print('✅ 安装成功')"

# 检查配置
python -c "from codebase_driven_agent.config import settings; print(f'LLM Model: {settings.llm_model}')"
```

### 5. 启动后端服务

```bash
# 方式 1: 使用 uvicorn（推荐，支持热重载）
uvicorn codebase_driven_agent.main:app --reload --host 0.0.0.0 --port 8000

# 方式 2: 直接运行
python -m codebase_driven_agent.main

# 方式 3: 使用脚本（如果有）
python scripts/start.py
```

服务启动后，你应该看到类似输出：

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 6. 访问 API 文档

打开浏览器访问：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health

## 测试 API

### 1. 健康检查

```bash
curl http://localhost:8000/health
```

预期响应：
```json
{"status": "healthy"}
```

### 2. 服务信息

```bash
curl http://localhost:8000/api/v1/info
```

### 3. 同步分析接口

```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "应用出现 NullPointerException 错误，请帮我分析原因"
  }'
```

如果配置了 API Key：

```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key" \
  -d '{
    "input": "应用出现 NullPointerException 错误，请帮我分析原因"
  }'
```

### 4. 带上下文文件的分析

```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "这段代码有什么问题？",
    "context_files": [
      {
        "type": "code",
        "path": "app.py",
        "content": "def process(data):\n    return data.value",
        "line_start": 10,
        "line_end": 20
      }
    ]
  }'
```

### 5. SSE 流式接口

使用 curl 测试 SSE（Server-Sent Events）：

```bash
curl -N -X POST "http://localhost:8000/api/v1/analyze/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "请分析这个错误"
  }'
```

### 6. 异步分析接口

```bash
# 1. 提交异步任务
curl -X POST "http://localhost:8000/api/v1/analyze/async" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "分析错误"
  }'

# 响应示例：
# {"task_id": "123e4567-e89b-12d3-a456-426614174000", "status": "pending"}

# 2. 查询任务状态（替换 task_id）
curl "http://localhost:8000/api/v1/analyze/123e4567-e89b-12d3-a456-426614174000"
```

### 7. 缓存管理

```bash
# 查看缓存统计
curl http://localhost:8000/api/v1/cache/stats

# 清空缓存
curl -X POST http://localhost:8000/api/v1/cache/clear
```

### 8. 工具管理

```bash
# 列出所有工具
curl http://localhost:8000/api/v1/tools

# 启用工具
curl -X POST http://localhost:8000/api/v1/tools/code_search/enable

# 禁用工具
curl -X POST http://localhost:8000/api/v1/tools/code_search/disable
```

## 使用 Web UI

### 1. 安装前端依赖

```bash
cd web
npm install
```

### 2. 启动前端开发服务器

```bash
npm run dev
```

前端服务默认运行在 **http://localhost:3000**（Vite 配置的端口）

### 3. 确保后端服务已启动

Web UI 需要后端服务运行在 http://localhost:8000。如果后端运行在不同端口，需要修改配置：

**方式 1: 修改 vite.config.ts**

编辑 `web/vite.config.ts`，修改 proxy 配置：

```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8000',  // 修改为实际的后端地址
    changeOrigin: true,
  },
}
```

**方式 2: 使用环境变量**

创建 `web/.env` 文件：

```bash
VITE_API_BASE_URL=http://localhost:8000
```

### 4. 访问 Web UI

打开浏览器访问：**http://localhost:3000**

### 5. 配置 API Key（如果后端需要）

如果后端配置了 `API_KEY`，在 Web UI 界面的 API Key 输入框中输入对应的值。

详细说明请查看 [Web UI 启动指南](WEB_UI.md)

## Python 测试脚本示例

创建一个测试脚本 `test_api.py`：

```python
"""API 测试脚本"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """测试健康检查"""
    response = requests.get(f"{BASE_URL}/health")
    print(f"Health Check: {response.json()}")

def test_analyze():
    """测试分析接口"""
    data = {
        "input": "应用出现 NullPointerException 错误，请帮我分析原因"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/analyze",
        json=data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

def test_analyze_with_context():
    """测试带上下文的分析"""
    data = {
        "input": "这段代码有什么问题？",
        "context_files": [
            {
                "type": "code",
                "path": "test.py",
                "content": "def process(data):\n    return data.value",
                "line_start": 1,
                "line_end": 10
            }
        ]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/analyze",
        json=data
    )
    
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    print("=== 测试健康检查 ===")
    test_health()
    
    print("\n=== 测试分析接口 ===")
    test_analyze()
    
    print("\n=== 测试带上下文的分析 ===")
    test_analyze_with_context()
```

运行测试：

```bash
python test_api.py
```

## 常见问题排查

### 1. 服务无法启动

**问题**: `ModuleNotFoundError` 或导入错误

**解决**:
```bash
# 确保安装了所有依赖
pip install -r requirements.txt

# 检查 Python 版本
python --version  # 应该是 3.11+

# 检查是否在正确的虚拟环境中
which python
```

### 2. LLM API Key 错误

**问题**: `ValueError: No LLM API Key configured`

**解决**:
- 检查 `.env` 文件是否存在
- 确认 `OPENAI_API_KEY` 或 `ANTHROPIC_API_KEY` 已正确设置
- 验证 API Key 是否有效

### 3. 端口被占用

**问题**: `Address already in use`

**解决**:
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9

# 或使用其他端口
uvicorn codebase_driven_agent.main:app --port 8001
```

### 4. 工具初始化失败

**问题**: `Failed to initialize CodeTool` 等警告

**解决**:
- 检查相关配置（如 `CODE_REPO_PATH`）
- 查看日志了解具体错误
- 工具初始化失败不会阻止服务启动，只是该工具不可用

### 5. 数据库连接失败

**问题**: 数据库工具无法连接

**解决**:
- 检查 `DATABASE_URL` 格式是否正确
- 确认数据库服务正在运行
- 验证数据库账号权限（需要只读权限）

### 6. 日志易连接失败

**问题**: 日志查询工具无法连接日志易

**解决**:
- 检查日志易配置是否正确
- 确认网络连接正常
- 验证 API Key 和权限

### 7. 前端无法连接后端

**问题**: CORS 错误或连接失败

**解决**:
- 检查后端是否正在运行
- 确认前端配置的 API 地址正确
- 检查后端 CORS 配置（默认允许所有来源）

## 测试不同场景

### 场景 1: 仅使用代码工具

```bash
# 配置代码仓库路径
CODE_REPO_PATH=./your-codebase

# 测试
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{"input": "查找处理用户登录的代码"}'
```

### 场景 2: 使用文件日志

```bash
# 配置
LOG_QUERY_TYPE=file
LOG_FILE_BASE_PATH=./logs

# 测试
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{"input": "查询最近的错误日志"}'
```

### 场景 3: 使用数据库查询

```bash
# 配置数据库
DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/dbname

# 测试
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{"input": "查询用户表中的数据"}'
```

## 性能测试

### 使用 Apache Bench (ab)

```bash
# 安装 ab（如果还没有）
# Ubuntu/Debian: sudo apt-get install apache2-utils
# Mac: brew install httpd

# 测试同步接口
ab -n 100 -c 10 -p request.json -T application/json \
  http://localhost:8000/api/v1/analyze
```

### 使用 wrk

```bash
# 安装 wrk
# Ubuntu/Debian: sudo apt-get install wrk
# Mac: brew install wrk

# 测试
wrk -t4 -c100 -d30s -s test.lua http://localhost:8000/api/v1/analyze
```

## 下一步

完成本地测试后，你可以：

1. 查看 [API 文档](API.md) 了解完整的 API 接口
2. 查看 [使用指南](USAGE.md) 了解使用场景
3. 查看 [配置说明](CONFIG.md) 了解详细配置选项
4. 查看 [扩展文档](EXTENDING.md) 了解如何扩展功能
5. 查看 [部署指南](../DEPLOYMENT.md) 了解生产环境部署

## 获取帮助

如果遇到问题：

1. 查看日志：服务启动时会输出详细日志
2. 检查配置：确认 `.env` 文件配置正确
3. 查看文档：参考项目文档了解详细说明
4. 提交 Issue：在 GitHub 上提交问题报告

