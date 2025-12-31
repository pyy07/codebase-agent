# 测试指南

## 前置条件

1. Python 3.11+ 已安装
2. 已安装项目依赖

## 安装依赖

### 方式 1: 使用 pip 安装（推荐）

```bash
pip install -r requirements.txt
```

### 方式 2: 使用 pip 安装核心依赖（最小化）

```bash
pip install fastapi uvicorn pydantic pydantic-settings
```

## 运行基础测试

### 1. 测试代码导入

```bash
python -c "from codebase_driven_agent.main import app; print('✅ FastAPI app imported successfully')"
```

### 2. 测试配置加载

```bash
python -c "from codebase_driven_agent.config import settings; print(f'✅ Config loaded: API key header = {settings.api_key_header}')"
```

### 3. 运行单元测试

```bash
# 安装测试依赖
pip install pytest httpx

# 运行测试
python test_basic.py
```

### 4. 启动服务并测试

```bash
# 启动服务
python -m codebase_driven_agent.main

# 在另一个终端测试
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/info
```

或者使用 uvicorn:

```bash
uvicorn codebase_driven_agent.main:app --reload
```

然后访问:
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health
- 服务信息: http://localhost:8000/api/v1/info

## 预期结果

### 健康检查接口 (`GET /health`)

```json
{
  "status": "healthy"
}
```

### 服务信息接口 (`GET /api/v1/info`)

```json
{
  "name": "Codebase Driven Agent",
  "version": "0.1.0",
  "status": "running"
}
```

## 故障排查

### 问题: ModuleNotFoundError

**原因**: 依赖未安装

**解决**: 
```bash
pip install -r requirements.txt
```

### 问题: 端口被占用

**原因**: 8000 端口已被使用

**解决**: 
```bash
# 使用其他端口
uvicorn codebase_driven_agent.main:app --port 8001
```

### 问题: 配置加载失败

**原因**: `.env` 文件格式错误或路径不正确

**解决**: 
- 检查 `.env` 文件是否存在
- 检查 `.env` 文件格式是否正确
- 配置会使用默认值，不影响基础功能测试

