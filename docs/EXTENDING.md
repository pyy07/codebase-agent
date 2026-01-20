# 扩展性设计文档

本文档说明 Codebase Driven Agent 的扩展性设计，包括如何添加新工具、新数据源、新功能场景等。

## 扩展点概述

Codebase Driven Agent 设计了多个扩展点，方便开发者添加新功能：

1. **工具扩展** (`tools/`): 添加新的 LangChain Tools
2. **数据源扩展** (`utils/`): 添加新的数据源适配器
3. **API 扩展** (`api/`): 添加新的 API 端点
4. **Agent 扩展** (`agent/`): 自定义 Agent 行为和 Prompt

## 工具扩展流程

### 步骤 1: 实现 BaseCodebaseTool

所有工具都应该继承 `BaseCodebaseTool`，它提供了：
- 统一的接口规范
- 数据截断和摘要功能
- 错误处理机制
- LangChain Tool 集成

**完整示例**:

```python
"""示例：自定义工具实现"""
from typing import Optional
from pydantic import BaseModel, Field
from codebase_driven_agent.tools.base import BaseCodebaseTool, ToolResult
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.tools.your_tool")


class YourToolInput(BaseModel):
    """工具输入参数模型"""
    query: str = Field(..., description="查询字符串")
    limit: int = Field(10, description="返回结果数量限制", ge=1, le=100)


class YourTool(BaseCodebaseTool):
    """自定义工具示例
    
    这是一个完整的工具实现示例，展示了如何：
    1. 定义输入参数模型
    2. 实现工具执行逻辑
    3. 处理错误和异常
    4. 返回格式化的结果
    """
    
    name: str = "your_tool"
    description: str = """
    工具功能描述，Agent 会根据这个描述决定是否使用该工具。
    
    功能：
    - 功能1：描述
    - 功能2：描述
    
    使用示例：
    - query: "示例查询" - 执行查询
    - limit: 20 - 限制返回结果数
    
    注意：
    - 注意事项1
    - 注意事项2
    """
    args_schema: type[YourToolInput] = YourToolInput
    
    def __init__(self, **kwargs):
        """初始化工具"""
        super().__init__(**kwargs)
        # 在这里初始化工具所需的资源（如数据库连接、API 客户端等）
        # self.client = YourAPIClient()
    
    def _execute(
        self,
        query: str,
        limit: int = 10,
    ) -> ToolResult:
        """
        执行工具逻辑
        
        Args:
            query: 查询字符串
            limit: 结果数量限制
        
        Returns:
            ToolResult: 工具执行结果
        """
        try:
            logger.info(f"Executing {self.name} with query: {query[:50]}...")
            
            # 1. 参数验证
            if not query or not query.strip():
                return ToolResult(
                    success=False,
                    error="Query cannot be empty",
                )
            
            # 2. 执行工具逻辑
            # 这里实现你的工具核心逻辑
            results = self._perform_query(query, limit)
            
            # 3. 格式化结果
            if not results:
                return ToolResult(
                    success=True,
                    data="No results found",
                    summary="查询未找到结果",
                )
            
            # 4. 构建返回数据
            result_data = self._format_results(results)
            
            # 5. 生成摘要（如果结果很大）
            summary = None
            if len(result_data) > 500:
                summary = f"找到 {len(results)} 条结果，显示前 {limit} 条"
                result_data = result_data[:500] + "\n... (truncated)"
            
            return ToolResult(
                success=True,
                data=result_data,
                summary=summary,
                truncated=len(result_data) > 500,
            )
        
        except Exception as e:
            logger.error(f"Tool execution failed: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Tool execution failed: {str(e)}",
            )
    
    def _perform_query(self, query: str, limit: int) -> list:
        """执行实际查询（示例）"""
        # 这里实现你的查询逻辑
        # 例如：调用 API、查询数据库、搜索文件等
        return [
            {"id": 1, "content": f"Result for: {query}"},
            {"id": 2, "content": f"Another result for: {query}"},
        ]
    
    def _format_results(self, results: list) -> str:
        """格式化结果（示例）"""
        formatted = []
        for i, result in enumerate(results, 1):
            formatted.append(f"{i}. {result.get('content', str(result))}")
        return "\n".join(formatted)
```

### 步骤 2: 注册工具

有两种方式注册工具：

#### 方式 1: 使用 Tool Registry（推荐，支持动态注册）

```python
from codebase_driven_agent.tools.registry import get_tool_registry

# 获取注册表
registry = get_tool_registry()

# 注册工具类
from codebase_driven_agent.tools.your_tool import YourTool
registry.register(YourTool, enabled=True, auto_init=True)

# 或者从模块动态加载
registry.load_from_module(
    module_path="codebase_driven_agent.tools.your_tool",
    tool_class_name="YourTool"
)
```

**优势**:
- 支持运行时动态注册和卸载
- 支持启用/禁用工具（无需重启服务）
- 提供 API 接口管理工具
- 线程安全

#### 方式 2: 手动注册（向后兼容）

在 `codebase_driven_agent/agent/executor.py` 的 `get_tools()` 函数中注册：

```python
def get_tools() -> List:
    tools = []
    
    # 代码工具
    try:
        code_tool = CodeTool()
        tools.append(code_tool)
    except Exception as e:
        logger.warning(f"Failed to initialize CodeTool: {str(e)}")
    
    # 注册新工具
    try:
        from codebase_driven_agent.tools.your_tool import YourTool
        your_tool = YourTool()
        tools.append(your_tool)
        logger.info(f"Successfully registered tool: {your_tool.name}")
    except Exception as e:
        logger.warning(f"Failed to initialize YourTool: {str(e)}")
    
    return tools
```

**注意事项**:
- 使用 try-except 包裹工具初始化，避免单个工具失败影响其他工具
- 记录初始化成功和失败的日志，便于调试
- 确保工具初始化不会阻塞或抛出异常

### 步骤 3: 使用 Tool Registry API（可选）

注册后，可以通过 API 管理工具：

```bash
# 列出所有工具
GET /api/v1/tools

# 启用工具
POST /api/v1/tools/{tool_name}/enable

# 禁用工具
POST /api/v1/tools/{tool_name}/disable
```

### 步骤 3: 更新 Prompt

在 `codebase_driven_agent/agent/prompt.py` 中更新工具描述，Agent 会自动获取工具列表并注入到 Prompt 中。

## 内置工具集参考

平台提供了以下内置工具，可以作为实现参考：

### 文件操作工具

- **read**: 读取文件内容，支持行号范围
  - 参考: `codebase_driven_agent/tools/read_tool.py`
  - 特点: 二进制文件检测、路径安全验证、编码处理

- **glob**: 文件模式匹配
  - 参考: `codebase_driven_agent/tools/glob_tool.py`
  - 特点: 递归搜索、结果排序、结果限制

### 内容搜索工具

- **grep**: 正则表达式搜索
  - 参考: `codebase_driven_agent/tools/grep_tool.py`
  - 特点: ripgrep 集成、文件类型过滤、结果格式化

### 命令执行工具

- **bash**: Shell 命令执行
  - 参考: `codebase_driven_agent/tools/bash_tool.py`
  - 特点: 安全限制、超时控制、输出截断

### 网络工具

- **webfetch**: 网页内容获取
  - 参考: `codebase_driven_agent/tools/webfetch_tool.py`
  - 特点: HTML 解析、文本提取、超时处理

- **websearch**: 网络搜索（可选）
  - 参考: `codebase_driven_agent/tools/websearch_tool.py`
  - 特点: 多 API 支持、配置检查、结果格式化

详细文档请参考 [BUILTIN_TOOLS.md](BUILTIN_TOOLS.md)。

## 数据源扩展流程

### 日志查询适配器

实现 `LogQueryInterface` 接口：

```python
from codebase_driven_agent.utils.log_query import LogQueryInterface, LogQueryResult

class YourLogQuery(LogQueryInterface):
    async def query(self, query: str, ...) -> LogQueryResult:
        # 实现查询逻辑
        pass
    
    def validate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        # 实现验证逻辑
        pass
```

在 `LogQueryFactory` 中注册：

```python
def get_log_query() -> LogQueryInterface:
    if settings.log_query_type == "your_type":
        return YourLogQuery(config={...})
    # ...
```

### 数据库适配器

数据库查询通过 SQLAlchemy 支持，理论上支持所有 SQLAlchemy 支持的数据库。只需配置正确的 `DATABASE_URL`。

## API 扩展流程

### 添加新端点

1. 创建路由文件：`codebase_driven_agent/api/your_routes.py`
2. 定义 Pydantic 模型：`codebase_driven_agent/api/models.py`
3. 实现端点逻辑
4. 在 `main.py` 中注册路由

**示例**:

```python
# api/your_routes.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/your", tags=["your"])

@router.get("/endpoint")
async def your_endpoint():
    return {"message": "Hello"}
```

```python
# main.py
from codebase_driven_agent.api.your_routes import router as your_router
app.include_router(your_router)
```

## Agent 行为扩展

### 自定义 Prompt

编辑 `codebase_driven_agent/agent/prompt.py`:

```python
def generate_system_prompt(...) -> str:
    base_prompt = """你的自定义系统提示..."""
    # ...
    return base_prompt
```

### 自定义回调

```python
from langchain.callbacks.base import BaseCallbackHandler

class YourCallback(BaseCallbackHandler):
    def on_tool_start(self, ...):
        # 自定义行为
        pass
```

在 `create_agent_executor()` 中使用：

```python
executor = AgentExecutor(
    # ...
    callbacks=[YourCallback()],
)
```

## 预留扩展接口

### 服务器状态检查 Tool

设计预留接口（待实现）：

```python
class ServerTool(BaseCodebaseTool):
    """服务器状态检查工具（预留）"""
    name: str = "server_status"
    # ...
```

### 进程状态检查 Tool

设计预留接口（待实现）：

```python
class ProcessTool(BaseCodebaseTool):
    """进程状态检查工具（预留）"""
    name: str = "process_status"
    # ...
```

## 扩展场景示例

### 场景1: 添加监控系统集成

1. 创建 `MonitorTool` 继承 `BaseCodebaseTool`
2. 实现监控数据查询逻辑
3. 注册到 `get_tools()`
4. 更新 Prompt 说明新工具用途

### 场景2: 添加代码质量分析

1. 创建 `CodeQualityTool` 继承 `BaseCodebaseTool`
2. 集成代码质量分析工具（如 pylint, mypy）
3. 返回分析结果和建议
4. 注册到 Agent

### 场景3: 添加性能分析

1. 创建 `PerformanceTool` 继承 `BaseCodebaseTool`
2. 分析代码性能瓶颈
3. 提供优化建议
4. 集成到 Agent 工作流

## 扩展性设计原则

1. **接口抽象**: 使用接口和基类定义扩展点
2. **依赖注入**: 通过配置和工厂模式管理依赖
3. **插件化**: 工具可以独立开发和测试
4. **向后兼容**: 新功能不影响现有功能
5. **文档完善**: 为每个扩展点提供清晰的文档

## 工具开发检查清单

- [ ] 继承 `BaseCodebaseTool`
- [ ] 实现 `_execute()` 方法
- [ ] 定义 `name` 和 `description`
- [ ] 定义 `args_schema` (Pydantic 模型)
- [ ] 实现错误处理
- [ ] 实现数据截断（如需要）
- [ ] 添加日志记录
- [ ] 编写单元测试
- [ ] 更新文档
- [ ] 注册到 `get_tools()`

## 未来扩展方向

1. **更多数据源**:
   - 监控系统（Prometheus, Grafana）
   - 配置管理（Consul, etcd）
   - 消息队列（Kafka, RabbitMQ）

2. **更多分析能力**:
   - 代码质量分析
   - 性能分析
   - 安全漏洞扫描

3. **更多 Agent 能力**:
   - 代码生成
   - 测试用例生成
   - 文档生成

4. **更多集成**:
   - IDE 插件
   - CI/CD 集成
   - 聊天机器人集成

## 参考资源

- [LangChain Tools 文档](https://python.langchain.com/docs/modules/tools/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Pydantic 文档](https://docs.pydantic.dev/)

