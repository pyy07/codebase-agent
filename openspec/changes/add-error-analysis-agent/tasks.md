## 1. 项目初始化和基础设施
- [x] 1.1 创建 Python 项目结构，配置 pyproject.toml 或 requirements.txt
- [x] 1.2 配置 FastAPI 项目框架和基础路由
- [x] 1.3 配置环境变量管理和配置加载
- [x] 1.4 设置日志系统和错误处理
- [x] 1.5 配置开发环境（black, mypy, pytest）

## 2. LangChain Agent 核心架构
- [x] 2.1 配置 LangChain Agent（使用 ReAct 模式）
- [x] 2.2 设计 Agent Prompt 模板（包含工具描述和使用说明）
- [x] 2.3 实现用户输入解析器（提取关键信息供 Agent 使用，支持错误日志、问题描述等多种输入）
- [x] 2.4 设计 LangChain Tools 接口规范（BaseTool 实现）
- [x] 2.6 设计 Agent Memory 机制（上下文记忆）
- [x] 2.7 设计 Output Parser（结构化输出解析）
- [x] 2.7 设计 API 请求/响应模型（使用 Pydantic）

## 3. REST API 实现
- [x] 3.1 设计 API 请求/响应模型（包含 input 和可选的 context_files 字段）
- [x] 3.2 实现同步分析接口 `POST /api/v1/analyze`（支持 context_files）
- [x] 3.3 实现异步分析接口 `POST /api/v1/analyze/async`（支持 context_files）
- [x] 3.4 实现任务查询接口 `GET /api/v1/analyze/{task_id}`
- [x] 3.5 实现异步任务状态管理（默认使用内存存储，线程安全）
- [x] 3.6 实现任务清理机制（定期清理过期任务，限制最大任务数量）
- [x] 3.7 实现健康检查接口 `GET /health`
- [x] 3.8 实现服务信息接口 `GET /api/v1/info`
- [x] 3.9 添加 API 认证中间件（API Key）
- [x] 3.10 添加请求限流中间件
- [x] 3.11 添加输入验证中间件（防止 Prompt Injection）
- [x] 3.12 实现 context_files 解析和处理（代码片段、日志片段）
- [x] 3.13 生成 OpenAPI/Swagger 文档

## 4. Streamable HTTP (SSE) 接口实现
- [x] 4.1 实现 SSE 流式接口 `POST /api/v1/analyze/stream`
- [x] 4.2 配置 FastAPI SSE 响应（Content-Type: text/event-stream）
- [x] 4.3 实现流式消息发送（分析进度和结果，使用 SSE 格式）
- [x] 4.4 集成 LangChain Callbacks 到 SSE 流式输出
- [x] 4.5 实现消息格式化和错误处理
- [x] 4.6 实现连接超时和资源清理

## 5. LangChain Tools 实现 - 代码工具
- [x] 5.1 实现 CodeTool（继承 langchain.tools.BaseTool）
- [x] 5.2 实现代码仓库扫描和索引功能
- [x] 5.3 实现基于错误信息的代码检索（关键词、堆栈跟踪等）
- [x] 5.4 实现代码上下文提取和分析
- [x] 5.5 实现代码截断和摘要机制（返回关键片段，而非整个文件）
- [x] 5.6 实现目录结构查询功能（Agent 可以先查看目录，再读取文件）
- [x] 5.7 集成 ripgrep 进行快速代码搜索
- [x] 5.8 集成 gitpython 进行 Git 操作
- [x] 5.9 编写工具描述和参数定义（供 Agent 理解工具用途）
- [x] 5.10 编写代码工具测试（包括截断、摘要功能）

## 6. LangChain Tools 实现 - 日志查询工具
- [x] 6.1 设计日志查询抽象接口（LogQueryInterface），所有方法必须包含 appname 参数
- [x] 6.2 实现日志查询工厂类（根据配置选择日志易或文件日志实现）
- [x] 6.3 实现日志易查询适配器（LogyiLogQuery，实现抽象接口）
- [x] 6.4 集成日志易配置（读取环境变量：LOGYI_BASE_URL, LOGYI_USERNAME, LOGYI_APIKEY, LOGYI_APPNAME，其中 LOGYI_APPNAME 为必需）
- [x] 6.5 实现 SPL 查询语句构建器（时间范围、关键词、字段过滤等），确保所有查询都包含 `appname:<项目名称>` 过滤条件
- [x] 6.6 实现 SPL 查询验证机制（validate_query，验证语法正确性和安全性）
- [x] 6.7 设计 SPL 查询示例（Few-Shot Prompting，供 Agent 参考）- 已在 Agent Prompt 中实现
- [x] 6.8 实现日志易 API 调用封装（HTTP 请求、认证、错误处理）- 已实现完整的 API 调用，包括重试机制和错误处理
- [x] 6.9 实现文件日志查询适配器（FileLogQuery，实现抽象接口）
- [x] 6.10 集成文件日志配置（读取环境变量：LOG_FILE_BASE_PATH, LOG_QUERY_TYPE）
- [x] 6.11 实现文件日志扫描和解析功能（支持文本、JSON、结构化日志格式）
- [x] 6.12 实现基于文件路径的日志文件定位（根据 appname 确定日志文件位置）
- [x] 6.13 实现文件日志的时间范围查询（基于文件修改时间或日志内容时间戳）
- [x] 6.14 实现文件日志的关键词搜索（全文搜索和字段匹配）
- [x] 6.15 实现日志分页机制（支持 limit 和 offset 参数）
- [x] 6.16 实现日志结果截断和摘要（返回关键片段，而非全部日志）
- [x] 6.17 实现 LogTool（继承 BaseCodebaseTool，使用抽象接口）
- [x] 6.18 实现基于时间范围和关键词的日志检索
- [ ] 6.19 实现日志模式识别和异常检测（可选功能）
- [x] 6.20 实现日志结果解析和格式化
- [x] 6.21 编写工具描述和参数定义（供 Agent 理解工具用途）
- [x] 6.22 编写日志查询抽象接口测试
- [x] 6.23 编写日志易实现测试（Mock API 响应）
- [x] 6.24 编写文件日志实现测试（Mock 文件系统）
- [x] 6.25 编写 LogTool 集成测试（包括分页、截断功能）

## 7. LangChain Tools 实现 - 数据库工具
- [x] 7.1 实现 DatabaseTool（继承 BaseCodebaseTool）
- [x] 7.2 配置 SQLAlchemy 和数据库连接池（使用只读账号）
- [x] 7.3 实现数据库连接和查询接口
- [x] 7.4 实现数据库 Schema 发现工具（get_schema_info）
- [x] 7.5 实现 Schema 信息缓存机制
- [x] 7.6 实现 SQL 验证和过滤（禁止写操作）
- [x] 7.7 实现查询结果限制和摘要（最多返回 100 行）
- [x] 7.8 实现敏感数据脱敏（过滤 password, secret 等字段）
- [ ] 7.9 实现基于错误信息的数据库查询策略（可选，Agent 可以自行决定）
- [ ] 7.10 实现查询结果分析和关联（可选，Agent 可以自行决定）
- [x] 7.11 支持 MySQL（优先）, PostgreSQL, SQLite（通过 SQLAlchemy 支持）
- [x] 7.12 编写工具描述和参数定义（供 Agent 理解工具用途）
- [x] 7.13 编写数据库工具测试（包括 Schema 发现、SQL 验证、敏感数据过滤）

## 8. LangChain Agent 集成和配置
- [x] 8.1 配置 LangChain LLM（OpenAI/Anthropic/本地模型）
- [x] 8.2 创建 AgentExecutor，注册所有 Tools
- [x] 8.3 设计 Agent Prompt（包含工具列表、使用说明、数据库 Schema 信息）
- [x] 8.4 实现动态 Schema 注入机制（在 System Prompt 中注入精简 Schema）
- [x] 8.5 配置 Agent Memory（用于上下文记忆）
- [x] 8.6 实现流式输出支持（使用 LangChain Callbacks）- 已完善 SSE 集成，Callbacks 正确传递到 Agent 执行
- [x] 8.7 实现请求缓存和去重（可选优化）- 已实现基于请求内容的缓存和去重，支持 LRU 淘汰策略
- [x] 8.8 配置 Agent 错误处理和自修正机制（handle_parsing_errors, max_iterations）
- [x] 8.9 实现工具执行错误回传和重试逻辑（通过 AgentExecutor 自动处理）
- [x] 8.10 配置 Agent 超时和重试机制（max_execution_time）
- [x] 8.11 编写 Agent 集成测试（包括错误处理、自修正测试）

## 9. Agent 执行和结果处理
- [x] 9.1 实现 Agent 执行流程（接收用户输入 → Agent 分析 → 工具调用 → 结果生成）
- [x] 9.2 实现 Output Parser（解析 Agent 输出为结构化结果）
- [x] 9.3 实现结果格式化（根因分析、应急建议、置信度评分）
- [x] 9.4 实现 Agent 调用链追踪（记录工具调用过程）
- [x] 9.5 实现错误处理和重试逻辑（工具执行错误回传、Agent 自修正）
- [x] 9.6 实现 Agent 执行超时控制
- [x] 9.7 编写 Agent 端到端测试 - 已编写完整的 Agent 集成测试（test_agent_integration.py）

## 10. API 层与 Agent 集成
- [x] 10.1 实现用户输入解析和预处理（支持错误日志、问题描述等多种输入类型）
- [x] 10.2 实现 API 层调用 Agent 的封装
- [x] 10.3 实现 Agent 执行结果的序列化
- [x] 10.4 实现流式输出集成（SSE + LangChain Callbacks）
- [x] 10.5 实现结果缓存（基于用户输入内容）- 已实现结果缓存，与请求缓存集成
- [x] 10.6 实现查询超时和取消机制
- [x] 10.7 编写 API + Agent 端到端集成测试 - 已编写完整的 API + Agent 集成测试（test_api_agent_integration.py）

## 11. 扩展性设计
- [x] 11.1 设计新 Tool 添加流程（实现 BaseTool → 注册到 Agent）- 已在 EXTENDING.md 中详细说明
- [ ] 11.2 设计服务器状态检查 Tool（预留接口）
- [ ] 11.3 设计进程状态检查 Tool（预留接口）
- [x] 11.4 编写 Tool 开发文档和示例 - 已在 EXTENDING.md 中添加完整的工具开发示例和检查清单
- [x] 11.5 实现 Tool 动态注册机制 - 已实现 ToolRegistry，支持动态注册、启用/禁用工具，并提供 API 接口

## 12. 部署和运维
- [x] 12.1 创建 Dockerfile
- [x] 12.2 创建 docker-compose.yml（包含示例配置）
- [x] 12.3 编写部署文档
- [x] 12.4 配置环境变量示例文件
- [x] 12.5 实现日志收集和监控（基础）

## 13. Web UI 实现
- [x] 13.1 搭建前端项目结构（React + TypeScript + Vite）
- [x] 13.2 实现用户输入界面（文本输入、文件上传、context_files 上传）
- [x] 13.3 实现 SSE 流式数据接收和显示（实时进度展示）
- [x] 13.4 实现分析结果展示界面（结构化展示根因分析、应急建议等）
- [x] 13.5 实现思考过程折叠显示（默认折叠，可展开查看 Agent Thought Trace）
- [x] 13.6 实现结果结构化展示组件（根因分析、应急建议、代码/日志引用、置信度评分）
- [x] 13.7 实现 API 调用封装（REST API 和 SSE，支持 context_files）
- [x] 13.8 实现错误处理和用户提示
- [x] 13.9 实现响应式布局和样式优化
- [x] 13.10 编写前端测试（Vitest + Testing Library）
- [x] 13.11 配置前端构建和部署流程

## 14. 文档和示例
- [x] 14.1 编写用户使用文档（API 文档 + 使用指南）
- [x] 14.2 编写开发者扩展文档
- [x] 14.3 创建示例问题分析场景（包括错误分析、疑问解答等）
- [x] 14.4 创建 API 调用示例（curl, Python, JavaScript）
- [x] 14.5 编写配置说明文档

