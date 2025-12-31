## Context
本项目旨在构建一个**基于代码库驱动的通用 AI Agent 平台**。平台的核心思想是通过深度理解代码库，结合多种数据源（代码、日志、数据库等），为开发者提供智能化的辅助能力。

**当前阶段**：以**问题分析和错误排查**作为切入点，实现一个能够自动分析问题原因并提供应急处理建议的智能 Agent。

**长期目标**：构建一个可扩展的平台，未来可支持更多代码库驱动场景，如代码理解、文档生成、测试生成、代码重构、性能优化等。

这是一个跨系统的集成项目，涉及多个数据源的访问和分析，需要提供标准化的服务接口供外部应用调用。平台架构需要具备良好的扩展性，支持未来添加新的工具和应用场景。

## Goals / Non-Goals

### Goals

**平台级目标**：
- 构建基于代码库驱动的通用 AI Agent 平台架构
- 设计可扩展的工具系统，支持代码、日志、数据库等多种数据源
- 实现统一的 Agent 执行框架，支持自主工具选择和结果分析
- 提供标准化的服务接口（REST API、SSE），支持外部应用集成
- 设计良好的扩展机制，支持未来添加新的工具和应用场景

**第一阶段目标（问题分析和错误排查）**：
- 提供统一的问题分析入口，接收用户输入（错误日志、疑问、问题描述等）并返回分析结果
- 支持代码仓库、日志、数据库三种核心数据源的查询和分析
- 生成结构化的错误分析报告，包括根因分析和应急处理建议
- 提供 Web UI，方便用户直接使用系统进行问题分析

**未来扩展场景**（非当前阶段目标，但架构需支持）：
- 代码理解和文档生成
- 测试用例生成和优化
- 代码重构建议
- 代码质量分析
- 性能优化建议
- API 文档生成

### Non-Goals
- 不实现自动修复功能（仅提供建议和分析）
- 不实现实时监控和告警（专注于按需分析）
- 不实现历史错误模式学习和预测（专注于单次分析）
- 不实现代码自动生成和修改（仅提供建议和示例）

## Decisions

### Decision: 采用 Python 作为主要开发语言
**理由**: 
- Python 在 AI/ML 领域生态丰富，有大量成熟的 LLM SDK（OpenAI, Anthropic, LangChain 等）
- 代码分析工具丰富（AST 解析、静态分析工具）
- 数据库驱动完善（支持多种数据库）
- 文件处理和文本分析能力强
- 社区活跃，易于扩展和维护

**替代方案**: 
- Node.js/TypeScript: LLM SDK 相对较少，代码分析工具不如 Python 丰富
- Go: 性能好但 AI 生态相对薄弱，开发效率较低
- Java: 生态丰富但语言复杂度高，不适合快速迭代

### Decision: 使用 FastAPI 作为 Web 框架
**理由**:
- 高性能，基于 ASGI 标准，支持异步处理
- 自动生成 OpenAPI/Swagger 文档
- 类型提示支持好，代码可读性强
- 易于集成 WebSocket
- 生态丰富，中间件和插件多

**替代方案**:
- Flask: 同步框架，性能不如 FastAPI，需要额外配置异步支持
- Django: 功能过于庞大，不适合轻量级 API 服务
- Tornado: 性能好但生态相对较小

### Decision: 使用 LangChain Agent 框架实现核心 Agent 逻辑
**理由**:
- **标准化 Agent 模式**: LangChain 提供了 ReAct、Plan-and-Execute 等标准 Agent 模式，符合行业最佳实践
- **工具化架构**: 将数据源（代码、日志、数据库）封装为 LangChain Tools，Agent 可以自主选择和调用工具
- **统一接口**: 支持多种 LLM 模型（OpenAI, Anthropic, 本地模型等），切换模型无需修改 Agent 逻辑
- **工具链管理**: LangChain 提供工具注册、调用链追踪、错误处理等标准化功能
- **可观测性**: 内置回调机制，支持工具调用过程的监控和调试
- **流式输出**: LangChain Callbacks 可以轻松集成到 SSE 流式输出，实时推送 Agent 思考过程和工具调用结果
- **文档完善**: 社区活跃，有大量示例和最佳实践

**Agent 架构设计**:
- 使用 `langchain.agents.AgentExecutor` 作为 Agent 执行引擎
- 将代码检索、日志检索、数据库查询封装为 LangChain Tools
- Agent 根据错误信息自主决定调用哪些工具，以及调用顺序
- 使用 ReAct 模式，Agent 可以观察工具结果并决定下一步行动
- 支持多轮对话和上下文记忆（通过 LangChain Memory）

**替代方案**:
- 直接使用 OpenAI SDK: 需要自研工具调用逻辑，开发成本高，不符合标准化实践
- 自研 Agent 框架: 开发成本极高，维护负担重，难以跟上行业标准
- 简单 LLM 调用: 无法实现自主工具选择和调用，灵活性差

### Decision: 提供 REST API + Streamable HTTP (SSE) 双接口
**理由**:
- REST API: 简单通用，适合同步请求-响应场景，易于集成
- Streamable HTTP (Server-Sent Events): 支持流式返回分析结果，适合长时间分析任务，提供实时进度反馈

**为什么选择 SSE 而不是 WebSocket**:
- **单向数据流**: Agent 分析过程主要是服务器向客户端推送进度和结果，不需要客户端频繁发送数据
- **更简单**: SSE 基于标准 HTTP，无需维护连接状态，自动重连机制，实现和维护成本低
- **RESTful 风格**: 更符合 REST API 的设计理念，易于理解和集成
- **HTTP 兼容性**: 可以复用 HTTP 认证、限流等中间件，无需额外实现
- **LangChain 支持**: LangChain Callbacks 可以轻松集成到 SSE 流式输出中
- **资源消耗**: SSE 比 WebSocket 更轻量，适合长时间连接场景

**API 设计**:
- REST API: `POST /api/v1/analyze` - 同步分析接口
- REST API: `POST /api/v1/analyze/async` - 异步分析接口（返回任务ID）
- REST API: `GET /api/v1/analyze/{task_id}` - 查询异步任务结果
- Streamable HTTP: `POST /api/v1/analyze/stream` - 流式分析接口（使用 SSE）

**请求 Body 设计**:
```json
{
  "input": "错误日志或问题描述",
  "context_files": [
    {
      "type": "code",
      "path": "src/main.py",
      "content": "代码片段内容",
      "line_start": 10,
      "line_end": 50
    },
    {
      "type": "log",
      "content": "日志片段内容"
    }
  ]
}
```
- `input`: 用户输入（错误日志、问题描述等），必需
- `context_files`: 辅助上下文文件列表，可选
  - 允许用户手动上传或指定特定的代码片段/日志片段
  - 减少 Agent 的搜索盲目性，提高分析效率
  - 支持代码片段（指定文件路径和行号范围）和日志片段

**SSE 流式接口设计**:
- 请求: `POST /api/v1/analyze/stream`，Body 包含用户输入和可选的 context_files
- 响应: `Content-Type: text/event-stream`，流式返回 JSON 格式的分析进度和结果
- 消息格式: 使用 SSE 标准格式 `data: {...}\n\n`，每个消息包含进度或结果片段
- 错误处理: 通过 SSE 消息发送错误信息，连接断开时客户端自动重连

**替代方案对比**:
- **WebSocket**: 
  - 优点: 双向通信，适合需要客户端频繁交互的场景
  - 缺点: 需要维护连接状态、心跳机制，实现复杂，资源消耗高
  - 结论: 对于单向流式推送场景，SSE 更合适
- **仅 REST API**: 
  - 缺点: 无法提供实时进度反馈，用户体验差
- **gRPC Stream**: 
  - 缺点: 需要生成客户端代码，集成复杂度高，HTTP/2 依赖

### Decision: 提供 Web UI 界面
**理由**:
- **用户体验**: Web UI 提供直观的交互界面，降低使用门槛
- **实时反馈**: Web UI 可以实时展示分析进度和结果，提升用户体验
- **易于使用**: 用户无需编写代码或使用 API 工具，直接在浏览器中使用
- **SSE 集成**: Web UI 可以很好地利用 SSE 流式输出，实时显示分析过程

**Web UI 设计**:
- **技术栈**: 使用现代前端框架（React/Vue）构建单页应用
- **主要功能**:
  - 用户输入界面（支持文本输入、文件上传、context_files 上传等）
  - 实时分析进度显示（利用 SSE 流式输出）
  - 分析结果展示（结构化展示根因分析、应急建议等）
  - 思考过程展示（折叠显示，类似 ChatGPT 的 "Show work"）
  - 历史记录查看（可选功能）
- **UI 交互设计**:
  - **思考过程折叠**: 
    - Agent 的思考过程（Agent Thought Trace）是非结构化的文本
    - 默认折叠显示，用户可点击展开查看详细思考过程
    - 重点展示最终结论（根因分析、应急建议），提升用户体验
    - 思考过程包括：工具调用记录、中间推理步骤、错误修正过程等
  - **结果结构化展示**:
    - 根因分析：清晰展示问题原因
    - 应急处理建议：分步骤展示
    - 相关代码和日志引用：可点击查看详情
    - 置信度评分：可视化展示
- **部署方式**: 
  - 开发环境：前后端分离，独立部署
  - 生产环境：前端静态文件可通过 FastAPI 静态文件服务提供，或使用 CDN
- **API 集成**: Web UI 通过 REST API 和 SSE 接口与后端交互

**替代方案**:
- 仅提供 API: 使用门槛高，需要用户编写代码或使用 API 工具
- 命令行工具: 交互性差，不适合非技术用户

### Decision: 将数据源封装为 LangChain Tools
**理由**: 
- **标准化工具接口**: LangChain Tools 提供统一的工具接口规范，符合 Agent 调用标准
- **自动工具发现**: Agent 可以自动发现可用工具，无需硬编码工具列表
- **工具描述和参数**: LangChain Tools 支持工具描述和参数定义，Agent 可以理解工具用途
- **错误处理**: LangChain 提供标准化的工具调用错误处理机制
- **可扩展性**: 新增数据源只需实现 LangChain Tool 接口，Agent 自动识别
- **测试友好**: 工具可以独立测试，Mock 工具用于单元测试

**工具设计**:
- `CodeTool`: 代码检索和分析工具
- `LogTool`: 日志检索和分析工具（抽象接口，日志易作为实现）
- `DatabaseTool`: 数据库工具
- 每个工具实现 `langchain.tools.BaseTool` 接口
- 工具描述包含使用场景和参数说明，帮助 Agent 选择合适的工具

**替代方案**: 
- 统一的数据访问层: 不同数据源的差异太大，强行统一会导致接口过于复杂
- 直接函数调用: 无法利用 LangChain 的工具管理和 Agent 协调能力

### Decision: 日志查询抽象化接口，支持多种实现方式
**理由**:
- **抽象化设计**: 定义抽象的日志查询接口，支持多种日志系统实现
- **多种实现方式**: 支持日志易（API查询）和文件日志（本地文件查询）两种实现
- **灵活配置**: 通过配置选择使用哪种日志实现方式
- **易于扩展**: 后续可以轻松添加其他日志系统实现

**日志查询架构**:
```
LogTool (LangChain Tool)
    ↓
LogQueryInterface (抽象接口)
    ├── LogyiLogQuery (日志易实现 - API查询)
    ├── FileLogQuery (文件日志实现 - 本地文件查询)
    └── OtherLogQuery (未来其他日志系统实现)
```

**日志易集成**:
- 使用日志易 API 进行日志查询
- 通过 SPL 语句构建查询条件（时间范围、关键词、过滤条件等）
- 支持认证（API Key + Username）
- **权限管控**: 日志易以应用作为权限管控的粒度，查询时必须明确项目名称
- 配置项：`LOGYI_BASE_URL`, `LOGYI_USERNAME`, `LOGYI_APIKEY`, `LOGYI_APPNAME`（必需）

**SPL 查询要求**:
- 所有 SPL 查询语句必须包含 `appname:<项目名称>` 作为过滤条件
- 这是日志易权限管控的要求，确保用户只能查询有权限的应用日志

**SPL 查询示例**（假设项目名称为 `my-project`）:
- 时间范围查询: `appname:my-project | where _time >= "2024-01-01 00:00:00" AND _time <= "2024-01-01 23:59:59"`
- 关键词搜索: `appname:my-project | search "error" OR "exception"`
- 字段过滤: `appname:my-project | where status >= 500`
- 关联查询: `appname:my-project | join type=left request_id [[ appname:my-project | stats count() by request_id ]]`

**抽象接口设计**:
```python
class LogQueryInterface(ABC):
    """日志查询抽象接口
    
    所有实现必须支持以下方法，appname 参数的含义：
    - 日志易实现：项目名称，用于权限管控和 SPL 查询过滤
    - 文件日志实现：项目标识，用于确定日志文件路径或目录
    """
    
    @abstractmethod
    def query_by_time_range(self, appname: str, start_time: str, end_time: str, keywords: List[str]) -> List[Dict]:
        """按时间范围查询日志
        
        Args:
            appname: 项目名称/标识（必需）
                - 日志易：项目名称，用于权限管控
                - 文件日志：项目标识，用于定位日志文件路径
            start_time: 开始时间（ISO 8601 格式）
            end_time: 结束时间（ISO 8601 格式）
            keywords: 关键词列表（可选）
        
        Returns:
            日志记录列表，每个记录为字典格式
        """
        pass
    
    @abstractmethod
    def query_by_keywords(self, appname: str, keywords: List[str], limit: int = 100) -> List[Dict]:
        """按关键词查询日志
        
        Args:
            appname: 项目名称/标识（必需）
            keywords: 关键词列表
            limit: 返回结果数量限制
        
        Returns:
            日志记录列表，每个记录为字典格式
        """
        pass
    
    @abstractmethod
    def query_by_request_id(self, appname: str, request_id: str) -> List[Dict]:
        """按请求ID查询日志
        
        Args:
            appname: 项目名称/标识（必需）
            request_id: 请求ID
        
        Returns:
            日志记录列表，每个记录为字典格式
        """
        pass
```

**替代方案**:
- 直接使用日志易 SDK: 耦合度高，难以切换其他日志系统
- 统一日志格式: 不同日志系统的格式差异大，统一成本高

**日志易实现（LogyiLogQuery）**:
- `LOGYI_APPNAME` 配置项是必需的，不能为空
- 所有 SPL 查询语句构建时，必须在开头添加 `appname:<项目名称>` 过滤条件
- 如果配置了 `LOGYI_APPNAME`，实现应该自动在所有查询中添加该过滤条件
- 查询时如果传入的 `appname` 参数与配置不一致，应该使用参数值（允许动态指定项目）
- **SPL 查询验证**: 
  - 在发送 SPL 查询前，增加 `validate_query` 步骤
  - 验证 SPL 语句的语法正确性和安全性
  - 防止 Agent 生成非法的 SPL 语句（LLM 对专有查询语言 SPL 的掌握通常不如 SQL）
  - 使用 Few-Shot Prompting 在 Agent Prompt 中提供 SPL 查询示例
  - 验证失败时，返回错误信息给 Agent，让其修正查询语句

**文件日志实现（FileLogQuery）**:
- 支持查询本地文件系统中的日志文件
- `appname` 参数在文件日志中表示项目标识，用于定位日志文件路径或目录
- 配置项：`LOG_FILE_BASE_PATH`（日志文件基础路径，可选）
- 支持多种日志格式：文本日志、JSON 日志、结构化日志等
- 支持日志文件扫描和解析
- 支持基于时间范围和关键词的文件内容搜索
- 实现方式：
  - 根据 `appname` 确定日志文件路径（如：`{LOG_FILE_BASE_PATH}/{appname}/*.log`）
  - 使用文件系统 API 扫描和读取日志文件
  - 使用正则表达式或 JSON 解析器解析日志内容
  - 支持时间范围过滤（基于文件修改时间或日志内容中的时间戳）
  - 支持关键词搜索（全文搜索或字段匹配）

**实现选择策略**:
- 通过配置项 `LOG_QUERY_TYPE` 选择实现方式：`logyi`（日志易）或 `file`（文件日志）
- 如果未配置，默认使用日志易实现
- 两种实现可以同时存在，但同一时间只能使用一种

### Decision: 使用异步并行查询策略
**理由**: 多个数据源的查询可以并行执行，提高响应速度。

**替代方案**: 串行查询
- 缺点：响应时间过长，影响用户体验

### Decision: 使用 LangChain Agent 进行智能分析和推理
**理由**: 
- **自主工具选择**: Agent 根据错误信息自主决定调用哪些工具，无需预设流程
- **多轮推理**: Agent 可以观察工具结果，进行多轮思考和工具调用，逐步深入分析
- **上下文理解**: LangChain Memory 机制让 Agent 记住之前的分析结果，进行关联分析
- **结构化输出**: 使用 LangChain Output Parsers 确保分析结果格式统一
- **规则辅助**: 在工具层面使用规则引擎处理结构化数据（如代码位置、日志时间戳）
- **LLM 推理**: Agent 使用 LLM 进行根因分析和建议生成

**Agent 工作流程**:
1. 接收用户输入（错误日志、问题描述等），解析关键信息
2. Agent 分析用户输入，决定需要查询哪些数据源
3. Agent 调用相应的 Tools（代码、日志、数据库）
4. Agent 观察工具返回结果，进行推理
5. 如果需要更多信息，Agent 继续调用工具
6. Agent 综合分析所有信息，生成根因分析和建议
7. 使用 Output Parser 格式化最终结果

**替代方案**: 
- 纯规则引擎: 难以处理复杂的语义分析和多数据源关联
- 纯 LLM 调用: 无法自主调用工具，需要手动编排数据源查询
- 固定流程: 灵活性差，无法根据错误类型动态调整分析策略

### Decision: 用户输入格式支持多种类型
**理由**: 用户输入可能是错误日志、问题描述、疑问等多种形式，不同系统和框架的错误日志格式也不同，需要灵活解析。

**替代方案**: 强制统一格式
- 缺点：限制了使用场景

### Decision: 数据库支持通过连接字符串配置
**理由**: 不同环境使用不同数据库，需要灵活配置。

**支持数据库类型**:
- MySQL/MariaDB（优先支持）
- PostgreSQL
- SQLite（用于测试）
- 其他数据库通过 SQLAlchemy 适配器支持

**替代方案**: 固定数据库类型
- 缺点：限制了使用场景

### Decision: Tool 返回数据的截断和摘要机制
**理由**: 
- **Context Window 限制**: 代码文件、数据库查询结果、日志文件通常非常大，直接返回会撑爆 LLM 的 Context Window
- **Token 消耗**: 即使是大模型（如 GPT-4-128k）也会因为大量数据导致成本高、响应慢
- **信息密度**: Agent 通常只需要关键信息，而非全部原始数据

**实现策略**:
- **代码 Tool**: 
  - 返回代码片段而非整个文件（如前100行、包含错误的关键片段）
  - 提供代码摘要功能（函数签名、关键逻辑说明）
  - 支持按需读取：Agent 可以先查看目录结构，再读取特定文件
- **日志 Tool**: 
  - 支持分页机制（limit 参数），Agent 可以先看第一页，需要时再翻页
  - 返回包含错误的关键片段，而非全部日志
  - 提供日志摘要（错误统计、时间分布等）
- **数据库 Tool**: 
  - 限制返回行数（默认最多 100 行）
  - 返回关键字段，而非所有字段
  - 提供查询结果摘要（统计信息、关键数据点）

**RAG 支持**（未来扩展）:
- 对于代码库，引入简单的向量索引
- Agent 可以先进行语义搜索，再按需读取相关文件
- 避免一次性读取整个代码库

**替代方案**: 
- 直接返回原始数据: 会导致 Context Window 溢出，成本高、速度慢
- 固定截断长度: 可能丢失关键信息，不够灵活

### Decision: 数据库 Schema 发现机制
**理由**: 
- **Schema 认知**: Agent 要生成 SQL 查询，必须先知道表结构（字段名、类型、关系等）
- **避免幻觉**: 没有 Schema 信息时，Agent 容易编造不存在的字段
- **动态适配**: 不同项目的数据库 Schema 不同，需要动态获取

**实现策略**:
- **Schema Tool**: 提供 `get_schema_info` Tool，让 Agent 在写 SQL 之前先查询表结构
- **System Prompt 注入**: 在 Agent System Prompt 中动态注入精简版的 Schema 信息
  - 仅包含表名、字段名、字段类型、主键、外键等关键信息
  - 不包含示例数据，避免占用过多 Token
- **按需加载**: Agent 可以根据查询需求，只加载相关表的 Schema
- **Schema 缓存**: 缓存 Schema 信息，避免重复查询

**Schema 信息格式**:
```python
{
    "table_name": "users",
    "columns": [
        {"name": "id", "type": "int", "primary_key": True},
        {"name": "username", "type": "varchar(50)"},
        {"name": "email", "type": "varchar(100)"}
    ],
    "foreign_keys": [...]
}
```

**替代方案**: 
- 硬编码 Schema: 不灵活，难以适配不同项目
- 不提供 Schema: Agent 会编造字段，导致查询失败

### Decision: 安全性防护机制
**理由**: 
- **Prompt Injection**: 用户可能在"问题描述"中输入恶意指令，试图操控 Agent
- **SQL Injection**: Agent 生成的 SQL 可能包含用户输入，存在注入风险
- **数据泄露**: 查询结果可能包含敏感信息（密码、密钥等）

**实现策略**:
- **数据库只读权限**: 
  - DatabaseTool 连接的数据库账号只有 SELECT 权限
  - 严禁 UPDATE、DELETE、DROP 等写操作
  - 使用专门的只读数据库账号
- **敏感数据脱敏**: 
  - 在 Tool 返回结果给 Agent 之前，增加中间件过滤敏感字段
  - 过滤规则：password, secret, key, token, credential 等关键词
  - 敏感字段替换为 `[REDACTED]` 或完全移除
- **SQL 验证**: 
  - 检查生成的 SQL 是否包含危险操作（DROP, DELETE, UPDATE 等）
  - 拒绝执行包含写操作的 SQL
  - 记录所有 SQL 查询日志，便于审计
- **输入验证**: 
  - 对用户输入进行基本验证和清理
  - 限制输入长度，防止超长恶意输入
  - 检测并拒绝明显的 Prompt Injection 模式

**替代方案**: 
- 完全信任 Agent: 风险高，可能导致数据泄露或破坏
- 完全禁止数据库查询: 功能受限，无法完成分析任务

### Decision: 异步任务状态管理
**理由**: 
- **任务持久化**: 异步任务需要存储状态，支持客户端查询
- **状态追踪**: 需要记录任务创建时间、状态、结果等
- **资源清理**: 需要定期清理过期任务，释放存储空间

**实现策略**:
- **存储介质**: 
  - **默认使用内存存储**（Python 字典或内存缓存），简单高效，无需外部依赖
  - 使用线程安全的数据结构（如 `threading.Lock` + `dict`）存储任务状态
  - 未来可扩展支持 Redis 或数据库存储（通过配置选择）
- **任务状态**: 
  - `pending`: 等待执行
  - `running`: 正在执行
  - `completed`: 已完成
  - `failed`: 执行失败
  - `cancelled`: 已取消
- **任务元数据**: 
  - 任务ID、创建时间、状态、进度百分比
  - 错误信息（如果失败）
  - 结果存储位置或结果摘要
- **任务清理**: 
  - 已完成任务保留 24 小时（可配置）
  - 失败任务保留 7 天（可配置）
  - 定期清理过期任务（后台线程定期扫描）
- **内存管理**: 
  - 限制最大任务数量（如 1000 个），防止内存溢出
  - 超过限制时，优先清理最旧的任务
  - 服务重启时任务状态会丢失（这是可接受的权衡）

**替代方案**: 
- Redis 存储: 需要外部依赖，增加部署复杂度，但支持分布式和持久化
- 数据库存储: 性能较差，增加数据库负担，但支持持久化
- 文件存储: 实现复杂，性能一般，不推荐

### Decision: 错误处理和自修正机制
**理由**: 
- **工具执行错误**: LLM 生成的 SQL 或代码搜索参数经常报错（语法错误、参数错误）
- **自修正能力**: LangChain Agent 具备自修正能力，但需要显式配置
- **提高成功率**: 通过错误反馈和重试，提高任务成功率

**实现策略**:
- **错误信息回传**: 
  - 当 Tool 执行报错时，将完整的错误信息（Error Message）回传给 Agent
  - 错误信息包含：错误类型、错误位置、错误原因、建议修复方向
- **Agent 自修正**: 
  - 配置 LangChain Agent 的错误处理回调
  - Agent 根据错误信息修正指令并重试（最多重试 3 次）
  - 记录每次重试的修正过程，便于调试
- **错误分类处理**: 
  - **可重试错误**: SQL 语法错误、参数错误等，Agent 可以修正
  - **不可重试错误**: 权限错误、连接错误等，直接返回错误
- **重试限制**: 
  - 每个工具调用最多重试 3 次
  - 避免无限重试导致资源浪费
  - 超过重试次数后，返回最后一次错误信息

**LangChain 配置**:
```python
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    max_iterations=15,  # 最大迭代次数
    max_execution_time=300,  # 最大执行时间
    handle_parsing_errors=True,  # 处理解析错误
    return_intermediate_steps=True,  # 返回中间步骤
)
```

**替代方案**: 
- 不重试: 错误率高，用户体验差
- 无限重试: 可能导致资源浪费和死循环

## Technology Stack

### 核心框架
- **Python 3.11+**: 后端主要开发语言
- **FastAPI**: Web 框架，提供 REST API、SSE (Server-Sent Events) 支持和静态文件服务
- **Pydantic**: 数据验证和序列化
- **Uvicorn**: ASGI 服务器

### 前端框架
- **React** 或 **Vue.js**: 前端框架（推荐 React，生态更丰富）
- **TypeScript**: 类型安全的 JavaScript
- **Vite** 或 **Webpack**: 构建工具
- **Tailwind CSS** 或 **Ant Design**: UI 组件库
- **EventSource API**: 用于接收 SSE 流式数据

### AI/LLM 相关
- **LangChain**: Agent 框架和 LLM 集成
  - `langchain.agents`: Agent 执行引擎（AgentExecutor）
  - `langchain.tools`: 工具接口和工具管理
  - `langchain.memory`: 上下文记忆管理
  - `langchain.chains`: 链式调用支持
  - `langchain.callbacks`: 回调机制（用于监控和流式输出）
- **LangChain OpenAI**: OpenAI 模型集成
- **LangChain Anthropic**: Claude 模型集成
- **LangChain Ollama** (可选): 本地模型集成
- **LangChain Output Parsers**: 结构化输出解析

### 代码分析
- **ast**: Python 标准库，解析 Python 代码
- **tree-sitter** (可选): 多语言代码解析
- **ripgrep** (rg): 快速代码搜索
- **gitpython**: Git 仓库操作

### 数据库访问
- **SQLAlchemy**: ORM 和数据库抽象层
- **aiomysql**: MySQL 异步驱动（优先支持）
- **asyncpg**: PostgreSQL 异步驱动
- **aiosqlite**: SQLite 异步驱动

### 日志处理
- **日志易 (Logyi)**: 日志查询系统（默认实现）
  - 通过 HTTP API 调用日志易服务
  - 使用 SPL (Search Processing Language) 查询语句
  - 支持时间范围、关键词、字段过滤等查询
- **文件日志**: 日志查询系统（第二种实现）
  - 从本地文件系统读取日志文件
  - 支持文本、JSON、结构化日志格式
  - 支持文件扫描、时间范围过滤、关键词搜索
- **抽象接口**: 定义日志查询抽象接口，支持多种日志系统实现
- **python-logging**: 标准日志库（用于应用自身日志）
- **loguru** (可选): 增强日志功能
- **正则表达式**: 日志解析和模式匹配
- **aiofiles**: 异步文件操作（用于文件日志读取）

### 工具库
- **httpx**: 异步 HTTP 客户端（用于调用外部 API，包括日志易 API）
- **aiofiles**: 异步文件操作
- **python-dotenv**: 环境变量管理
- **pydantic-settings**: 配置管理
- **sqlparse**: SQL 解析和验证
- **threading**: Python 标准库，用于线程安全的任务状态管理（内存存储）

### 开发和测试
- **pytest**: 测试框架
- **pytest-asyncio**: 异步测试支持
- **black**: 代码格式化
- **mypy**: 类型检查
- **ruff**: 代码检查和格式化

## LangChain Agent 架构设计

### Agent 工作模式
采用 **ReAct (Reasoning + Acting)** 模式，Agent 可以：
1. **思考 (Reasoning)**: 分析用户输入（错误日志、问题描述等），决定需要查询哪些信息
2. **行动 (Acting)**: 调用相应的 Tools 获取数据
3. **观察 (Observing)**: 分析工具返回的结果
4. **迭代**: 根据观察结果决定是否需要调用更多工具或得出结论

### Tool 设计模式
每个数据源封装为一个 LangChain Tool：

```python
class CodeTool(BaseTool):
    name = "code_search"
    description = "搜索代码，查找相关代码文件和函数"
    
    def _run(self, query: str) -> str:
        # 实现代码搜索逻辑
        pass
```

**Tool 职责**:
- 接收 Agent 的查询请求
- 执行数据源查询（代码/日志/数据库）
- 返回结构化的查询结果
- 处理查询错误和异常

### Agent Prompt 设计
Agent Prompt 包含：
- **系统角色**: 定义 Agent 为问题分析专家（能够分析错误、疑问、问题等）
- **工具列表**: 列出所有可用工具及其用途
- **工作流程**: 说明分析用户输入的步骤
- **输出格式**: 指定最终结果的格式要求

### Memory 机制
使用 LangChain Memory 保存：
- **对话历史**: 记录 Agent 的思考过程和工具调用
- **上下文信息**: 保存已查询的数据源结果
- **中间结论**: 记录分析过程中的发现

### 执行流程示例
```
1. 用户输入问题或错误信息（可能是错误日志、疑问、问题描述等）
   ↓
2. Agent 解析输入内容，识别关键信息（错误类型、文件位置、时间戳、关键词等）
   ↓
3. Agent 决定调用 CodeTool 查询相关代码
   ↓
4. Agent 观察代码查询结果，发现潜在问题
   ↓
5. Agent 决定调用 LogTool 查询相关日志
   ↓
6. Agent 观察日志结果，关联代码和日志信息
   ↓
7. Agent 决定调用 DatabaseTool 查询相关数据
   ↓
8. Agent 综合分析所有结果，生成根因分析和建议
   ↓
9. Output Parser 格式化最终结果
```

### 优势总结
- **标准化**: 遵循 LangChain 标准模式，易于维护和扩展
- **灵活性**: Agent 可以根据错误类型动态调整分析策略
- **可观测性**: LangChain Callbacks 提供完整的执行追踪
- **可扩展性**: 新增数据源只需实现 Tool 接口
- **可测试性**: Tools 可以独立测试，Agent 可以使用 Mock Tools

## Service Architecture

### API 服务层
```
┌─────────────────────────────────────┐
│      External Applications          │
│      Web UI (Browser)               │
└──────────────┬──────────────────────┘
               │
       ┌───────┴────────┐
       │                │
   REST API      Streamable HTTP (SSE)
       │                │
       └───────┬────────┘
               │
    ┌──────────┴──────────┐
    │   FastAPI Server     │
    │  - Request Handler   │
    │  - Auth Middleware   │
    │  - Rate Limiting     │
    │  - SSE Streaming     │
    │  - Static Files      │
    └──────────┬───────────┘
               │
    ┌──────────┴───────────┐
    │   LangChain Agent     │
    │  - AgentExecutor      │
    │  - ReAct Agent        │
    │  - Memory & Context   │
    │  - Output Parser      │
    └──────────┬───────────┘
               │
    ┌──────────┴───────────┐
    │   LangChain Tools     │
    │  - CodeTool           │
    │  - LogTool            │
    │  - DatabaseTool       │
    └──────────┬───────────┘
               │
    ┌──────────┴───────────┐
    │   Data Source Layer  │
    │  - Code Repository   │
    │  - Log System        │
    │  - Database          │
    └──────────────────────┘
```

### 服务部署方式
1. **独立服务**: 作为独立的微服务部署，通过 HTTP/WebSocket 提供服务
2. **容器化**: 提供 Docker 镜像，支持 Docker Compose 或 Kubernetes 部署
3. **配置管理**: 通过环境变量或配置文件管理数据源连接信息

### API 认证和授权
- **API Key**: 简单场景使用 API Key 认证
- **JWT Token**: 支持 JWT 令牌认证（未来扩展）
- **OAuth 2.0**: 支持 OAuth 2.0（未来扩展）

### 服务发现和注册
- **健康检查**: `GET /health` 端点
- **服务信息**: `GET /api/v1/info` 端点
- **指标监控**: 集成 Prometheus 指标（未来扩展）

## Risks / Trade-offs

### 风险：数据源访问权限和安全性
**缓解措施**: 
- 实现细粒度的权限控制
- 敏感信息（如数据库密码）使用环境变量或密钥管理
- 查询结果中过滤敏感信息（敏感字段脱敏）
- API 请求支持认证和授权
- 数据库使用只读账号，禁止写操作
- SQL 验证和日志记录，防止 SQL Injection
- 输入验证，防止 Prompt Injection

### 风险：多数据源查询的性能问题
**缓解措施**:
- 实现查询超时机制
- 实现结果缓存（对于相同错误）
- 支持查询优先级和取消机制
- 使用异步并发查询

### 风险：分析结果的准确性
**缓解措施**:
- 提供置信度评分
- 支持人工反馈和结果改进
- 记录分析过程，便于审计和优化
- Agent 自修正机制，根据错误信息重试
- 数据库 Schema 发现，避免字段幻觉

### 风险：Context Window 溢出和 Token 消耗
**缓解措施**:
- Tool 返回数据截断和摘要机制
- 日志查询支持分页
- 代码查询返回关键片段而非整个文件
- 数据库查询限制返回行数
- 未来引入 RAG 机制，优化代码检索

### 风险：LLM API 调用成本和限流
**缓解措施**:
- 支持本地模型部署
- 实现请求缓存和去重
- 支持多 LLM 提供商切换
- 实现请求限流和重试机制

### 权衡：实时性 vs 准确性
- 快速响应：优先返回部分结果，后续补充
- 完整分析：等待所有数据源返回，可能较慢

**决策**: 默认采用完整分析，但提供快速模式选项

### 权衡：同步 vs 异步 API
- 同步 API: 简单但可能超时
- 异步 API: 复杂但支持长时间任务

**决策**: 同时提供两种模式，根据任务复杂度选择

## Migration Plan
这是一个新功能，不需要迁移现有代码。但需要考虑：
- 如何与现有系统集成（如果有）
- 如何部署和配置数据源连接
- 如何逐步启用和验证功能
- 如何向后兼容 API 版本变更

## Open Questions
- LLM 模型选择（本地部署 vs API调用）？→ 建议支持两者，通过配置选择
- 是否需要支持多语言代码仓库？→ 第一阶段支持 Python，后续扩展
- 数据库连接池和连接管理策略？→ 使用 SQLAlchemy 连接池
- 用户输入的存储和检索策略（是否需要建立索引）？→ 第一阶段不存储，后续扩展
- API 版本管理策略？→ 使用 URL 路径版本控制（/api/v1/）
- 日志易 SPL 查询语句的复杂度？→ 参考 docs/spl_reference，支持常用查询模式
- 其他日志系统的对接优先级？→ 第一阶段专注日志易，后续根据需求扩展

