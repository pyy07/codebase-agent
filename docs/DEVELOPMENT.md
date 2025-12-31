# 开发者扩展文档

本文档介绍如何扩展 Codebase Driven Agent 的功能，包括添加新的工具、自定义 Agent 行为等。

## 架构概述

Codebase Driven Agent 采用模块化架构：

```
┌─────────────────────────────────────┐
│         FastAPI Application         │
│  (REST API, SSE, Middleware)        │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Agent Executor                 │
│  (LangChain AgentExecutor)          │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         Tools Layer                 │
│  - CodeTool                         │
│  - LogTool                          │
│  - DatabaseTool                     │
│  - YourCustomTool                   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Data Source Layer              │
│  - Code Repository                  │
│  - Log System                       │
│  - Database                         │
│  - Your Data Source                 │
└─────────────────────────────────────┘
```

## 添加新工具

### 1. 创建工具类

所有工具都应该继承自 `BaseCodebaseTool`，它提供了统一的接口和通用功能。

**示例：创建一个服务器状态检查工具**

```python
# codebase_driven_agent/tools/server_tool.py
from typing import Optional
from pydantic import BaseModel, Field

from codebase_driven_agent.tools.base import BaseCodebaseTool, ToolResult
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.tools.server")


class ServerToolInput(BaseModel):
    """服务器工具输入参数"""
    action: str = Field(..., description="操作类型：'status'（检查状态）或 'metrics'（获取指标）")
    host: Optional[str] = Field(None, description="服务器地址（可选，默认使用配置）")


class ServerTool(BaseCodebaseTool):
    """服务器状态检查工具"""
    
    name: str = "server_status"
    description: str = """
    用于检查服务器状态和获取服务器指标。
    
    功能：
    - 检查服务器运行状态
    - 获取服务器资源使用情况（CPU、内存、磁盘等）
    - 检查服务可用性
    
    使用示例：
    - action: "status", host: "example.com" - 检查服务器状态
    - action: "metrics", host: "example.com" - 获取服务器指标
    """
    args_schema = ServerToolInput
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.max_output_length = kwargs.get("max_output_length", 5000)
    
    def _execute(
        self,
        action: str,
        host: Optional[str] = None,
    ) -> ToolResult:
        """执行服务器操作"""
        try:
            if action == "status":
                return self._check_status(host)
            elif action == "metrics":
                return self._get_metrics(host)
            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown action: {action}. Use 'status' or 'metrics'"
                )
        
        except Exception as e:
            logger.error(f"Server tool error: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Server operation failed: {str(e)}"
            )
    
    def _check_status(self, host: Optional[str]) -> ToolResult:
        """检查服务器状态"""
        # 实现服务器状态检查逻辑
        # 例如：ping、HTTP 健康检查等
        try:
            # 示例实现
            status = "healthy"  # 实际应该调用检查逻辑
            return ToolResult(
                success=True,
                data=f"Server {host or 'default'} is {status}",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to check server status: {str(e)}"
            )
    
    def _get_metrics(self, host: Optional[str]) -> ToolResult:
        """获取服务器指标"""
        # 实现指标获取逻辑
        try:
            # 示例实现
            metrics = {
                "cpu_usage": "45%",
                "memory_usage": "60%",
                "disk_usage": "70%",
            }
            
            result_text = f"Server {host or 'default'} metrics:\n"
            for key, value in metrics.items():
                result_text += f"  {key}: {value}\n"
            
            return ToolResult(
                success=True,
                data=result_text,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to get server metrics: {str(e)}"
            )
```

### 2. 注册工具

在 `codebase_driven_agent/agent/executor.py` 的 `get_tools()` 函数中注册新工具：

```python
def get_tools() -> List:
    """获取所有工具列表"""
    tools = []
    
    # ... 现有工具 ...
    
    # 新工具
    try:
        from codebase_driven_agent.tools.server_tool import ServerTool
        server_tool = ServerTool()
        tools.append(server_tool)
    except Exception as e:
        logger.warning(f"Failed to initialize ServerTool: {str(e)}")
    
    return tools
```

### 3. 更新工具导出

在 `codebase_driven_agent/tools/__init__.py` 中导出新工具：

```python
from codebase_driven_agent.tools.server_tool import ServerTool

__all__ = [
    # ... 现有工具 ...
    "ServerTool",
]
```

## BaseCodebaseTool 接口说明

### 必需实现的方法

- `_execute(**kwargs) -> ToolResult`: 执行工具的主要逻辑

### 可选重写的方法

- `_truncate_data(data: str) -> Tuple[str, bool]`: 自定义数据截断逻辑
- `_generate_summary(data: str) -> str`: 自定义摘要生成逻辑

### ToolResult 结构

```python
class ToolResult:
    success: bool  # 是否成功
    data: Optional[str] = None  # 结果数据（字符串）
    error: Optional[str] = None  # 错误信息
    truncated: bool = False  # 是否被截断
    summary: Optional[str] = None  # 数据摘要
```

## 自定义 Agent Prompt

### 修改系统提示

编辑 `codebase_driven_agent/agent/prompt.py` 中的 `generate_system_prompt()` 函数：

```python
def generate_system_prompt(tools_description: str = "", schema_info: str = "") -> str:
    base_prompt = """你是一个基于代码库驱动的智能分析 Agent。
    
    ## 新增能力
    - 服务器状态检查：可以检查服务器运行状态和资源使用情况
    
    # ... 其他内容 ...
    """
    
    # ... 其他代码 ...
    
    return base_prompt
```

### 添加 Few-Shot 示例

在 `generate_system_prompt()` 中添加工具使用示例：

```python
def generate_system_prompt(tools_description: str = "", schema_info: str = "") -> str:
    # ... 基础提示 ...
    
    # 添加工具使用示例
    examples = """
## 工具使用示例

### 服务器状态检查
当需要检查服务器状态时，使用 server_status 工具：
- action: "status" - 检查服务器是否在线
- action: "metrics" - 获取服务器资源使用情况
"""
    
    base_prompt += examples
    
    return base_prompt
```

## 添加新的数据源适配器

### 日志查询适配器示例

如果需要添加新的日志系统支持，实现 `LogQueryInterface`：

```python
# codebase_driven_agent/utils/log_query.py

class CustomLogQuery(LogQueryInterface):
    """自定义日志查询实现"""
    
    def __init__(self, config: dict):
        self.config = config
    
    async def query(
        self,
        query: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> LogQueryResult:
        """执行日志查询"""
        # 实现查询逻辑
        pass
    
    def validate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """验证查询语句"""
        # 实现验证逻辑
        pass
```

然后在 `LogQueryFactory` 中注册：

```python
def get_log_query() -> LogQueryInterface:
    if settings.log_query_type == "custom":
        return CustomLogQuery(config={...})
    # ... 其他实现 ...
```

## 自定义 Agent 行为

### 修改 Agent 执行器

编辑 `codebase_driven_agent/agent/executor.py`：

```python
def create_agent_executor(
    memory: Optional[AgentMemory] = None,
    max_iterations: Optional[int] = None,
    max_execution_time: Optional[int] = None,
) -> AgentExecutor:
    # ... 现有代码 ...
    
    # 自定义 Agent 配置
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=max_iterations or settings.agent_max_iterations,
        max_execution_time=max_execution_time or settings.agent_max_execution_time,
        handle_parsing_errors=True,
        return_intermediate_steps=True,
        # 添加自定义回调
        callbacks=[YourCustomCallback()],
    )
    
    return executor
```

### 添加自定义回调

```python
from langchain.callbacks.base import BaseCallbackHandler

class CustomCallback(BaseCallbackHandler):
    """自定义回调处理器"""
    
    def on_tool_start(self, serialized: dict, input_str: str, **kwargs):
        """工具开始执行时调用"""
        logger.info(f"Tool {serialized['name']} started with input: {input_str}")
    
    def on_tool_end(self, output: str, **kwargs):
        """工具执行结束时调用"""
        logger.info(f"Tool ended with output: {output[:100]}...")
    
    def on_tool_error(self, error: Exception, **kwargs):
        """工具执行错误时调用"""
        logger.error(f"Tool error: {str(error)}")
```

## 添加新的 API 端点

### 创建新的路由

```python
# codebase_driven_agent/api/custom_routes.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/custom", tags=["custom"])

class CustomRequest(BaseModel):
    param: str

@router.post("/endpoint")
async def custom_endpoint(request: CustomRequest):
    """自定义端点"""
    # 实现逻辑
    return {"result": "success"}
```

### 注册路由

在 `codebase_driven_agent/main.py` 中注册：

```python
from codebase_driven_agent.api.custom_routes import router as custom_router

app.include_router(custom_router)
```

## 配置管理

### 添加新配置项

在 `codebase_driven_agent/config.py` 中添加：

```python
class Settings(BaseSettings):
    # ... 现有配置 ...
    
    # 新配置
    custom_config: Optional[str] = None
    custom_timeout: int = 30
```

### 使用配置

```python
from codebase_driven_agent.config import settings

if settings.custom_config:
    # 使用配置
    pass
```

## 测试

### 编写工具测试

```python
# tests/tools/test_server_tool.py
import pytest
from codebase_driven_agent.tools.server_tool import ServerTool

def test_server_tool_status():
    tool = ServerTool()
    result = tool._execute(action="status", host="example.com")
    assert result.success
    assert "status" in result.data.lower()

def test_server_tool_metrics():
    tool = ServerTool()
    result = tool._execute(action="metrics", host="example.com")
    assert result.success
    assert "cpu" in result.data.lower() or "memory" in result.data.lower()
```

### 运行测试

```bash
pytest tests/tools/test_server_tool.py -v
```

## 最佳实践

1. **工具设计原则**:
   - 单一职责：每个工具只负责一个特定的功能
   - 错误处理：妥善处理异常，返回清晰的错误信息
   - 数据截断：对于大量数据，自动截断并生成摘要
   - 日志记录：记录关键操作和错误

2. **代码组织**:
   - 工具文件放在 `codebase_driven_agent/tools/` 目录
   - 数据源适配器放在 `codebase_driven_agent/utils/` 目录
   - API 路由放在 `codebase_driven_agent/api/` 目录

3. **文档**:
   - 为工具编写清晰的文档字符串
   - 在工具描述中提供使用示例
   - 更新相关文档（API 文档、使用指南等）

4. **测试**:
   - 为每个新功能编写测试
   - 测试正常情况和异常情况
   - 确保测试覆盖率

5. **配置**:
   - 使用环境变量或配置文件管理配置
   - 提供合理的默认值
   - 验证配置的有效性

## 示例：完整的工具实现

查看以下文件了解完整的工具实现示例：
- `codebase_driven_agent/tools/code_tool.py` - 代码工具
- `codebase_driven_agent/tools/log_tool.py` - 日志工具
- `codebase_driven_agent/tools/database_tool.py` - 数据库工具

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/your-feature`)
3. 提交更改 (`git commit -am 'Add some feature'`)
4. 推送到分支 (`git push origin feature/your-feature`)
5. 创建 Pull Request

## 问题反馈

如果遇到问题或有建议，请：
1. 查看现有文档和示例
2. 搜索已有的 Issue
3. 创建新的 Issue 描述问题

