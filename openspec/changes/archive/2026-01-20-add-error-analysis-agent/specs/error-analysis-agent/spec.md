## ADDED Requirements

### Requirement: 用户输入处理
系统 SHALL 接收用户提供的输入（错误日志、问题描述、疑问等），并解析其中的关键信息（错误类型、堆栈跟踪、时间戳、相关标识符、关键词等）。

#### Scenario: 接收错误日志
- **WHEN** 用户通过 API 提供包含堆栈跟踪的错误日志
- **THEN** 系统解析出错误类型、文件位置、行号、调用链等关键信息

#### Scenario: 接收问题描述或疑问
- **WHEN** 用户提供问题描述、疑问或简化的错误信息
- **THEN** 系统提取关键词，识别问题类型，并尝试匹配相关代码和日志

#### Scenario: 支持多种输入格式
- **WHEN** 用户提供不同格式的输入（错误日志：JSON、文本、结构化日志；问题描述：自然语言文本）
- **THEN** 系统能够正确解析并提取关键信息

#### Scenario: 接收辅助上下文文件
- **WHEN** 用户在请求中提供 context_files（代码片段或日志片段）
- **THEN** 系统将这些上下文文件作为辅助信息提供给 Agent，减少搜索盲目性，提高分析效率
- **WHEN** context_files 包含代码片段
- **THEN** 系统解析文件路径和行号范围，提取相关代码上下文
- **WHEN** context_files 包含日志片段
- **THEN** 系统解析日志内容，作为分析参考

### Requirement: REST API 接口
系统 SHALL 提供 REST API 接口，支持外部应用通过 HTTP 请求调用问题分析功能（包括错误分析、疑问解答等）。

#### Scenario: 同步分析接口
- **WHEN** 客户端发送 `POST /api/v1/analyze` 请求，包含用户输入（错误日志、问题描述等）
- **THEN** 系统返回完整的分析结果（JSON 格式）

#### Scenario: 异步分析接口
- **WHEN** 客户端发送 `POST /api/v1/analyze/async` 请求，包含用户输入（错误日志、问题描述等）
- **THEN** 系统返回任务ID，客户端可通过任务ID查询结果

#### Scenario: 查询异步任务结果
- **WHEN** 客户端发送 `GET /api/v1/analyze/{task_id}` 请求
- **THEN** 系统返回任务状态和结果（如果已完成）

#### Scenario: 异步任务状态管理
- **WHEN** 创建异步任务后
- **THEN** 系统在内存中存储任务状态（pending, running, completed, failed），使用线程安全的数据结构
- **WHEN** 任务完成后超过保留时间（如 24 小时）
- **THEN** 系统自动清理过期任务，释放内存空间
- **WHEN** 任务数量超过最大限制（如 1000 个）
- **THEN** 系统优先清理最旧的任务，保持任务数量在限制内

#### Scenario: API 认证
- **WHEN** 客户端请求包含有效的 API Key
- **THEN** 系统处理请求
- **WHEN** 客户端请求未包含 API Key 或 API Key 无效
- **THEN** 系统返回 401 未授权错误

#### Scenario: API 限流
- **WHEN** 客户端请求频率超过限制
- **THEN** 系统返回 429 请求过多错误

#### Scenario: API 文档
- **WHEN** 客户端访问 `/docs` 或 `/openapi.json`
- **THEN** 系统返回 OpenAPI/Swagger 文档

### Requirement: Streamable HTTP (SSE) 接口
系统 SHALL 提供 Server-Sent Events (SSE) 接口，支持流式返回分析结果和实时进度反馈。

#### Scenario: SSE 流式接口调用
- **WHEN** 客户端发送 `POST /api/v1/analyze/stream` 请求，包含用户输入（错误日志、问题描述等），Accept 头包含 `text/event-stream`
- **THEN** 系统返回 `Content-Type: text/event-stream` 响应，开始流式返回分析进度和结果

#### Scenario: 流式分析结果
- **WHEN** Agent 执行分析过程中产生进度更新或结果片段
- **THEN** 系统通过 SSE 格式（`data: {...}\n\n`）实时推送消息到客户端

#### Scenario: SSE 消息格式
- **WHEN** 系统发送流式消息
- **THEN** 消息使用标准 SSE 格式，包含 JSON 数据，客户端可以解析并显示进度

#### Scenario: 连接自动重连
- **WHEN** SSE 连接意外断开
- **THEN** 客户端可以自动重连（SSE 标准特性），系统继续发送后续消息

#### Scenario: 连接错误处理
- **WHEN** SSE 连接发生错误或分析失败
- **THEN** 系统通过 SSE 消息发送错误信息，然后关闭连接

### Requirement: 代码仓库检索和分析
系统 SHALL 基于错误信息检索相关代码，分析代码上下文，识别可能导致错误的代码位置和逻辑。

#### Scenario: 基于堆栈跟踪检索代码
- **WHEN** 错误日志包含文件路径和行号
- **THEN** 系统定位到对应代码文件，提取相关代码段和上下文

#### Scenario: 基于错误消息检索代码
- **WHEN** 错误日志包含错误消息但无具体位置
- **THEN** 系统在代码仓库中搜索相关关键词，找到可能相关的代码位置

#### Scenario: 分析代码上下文
- **WHEN** 定位到相关代码位置
- **THEN** 系统分析代码逻辑、依赖关系、数据流，识别潜在问题

#### Scenario: 代码查询结果截断
- **WHEN** 代码文件非常大（超过 1000 行）
- **THEN** 系统返回关键代码片段（如前 100 行或包含错误的部分），而非整个文件

#### Scenario: 代码目录结构查询
- **WHEN** Agent 需要查找代码但不确定文件位置
- **THEN** Agent 可以先查询目录结构，再按需读取特定文件

### Requirement: 日志检索和分析
系统 SHALL 基于错误信息检索相关日志，分析日志模式，识别错误发生的时间线和相关事件。

#### Scenario: 基于时间范围检索日志
- **WHEN** 错误日志包含时间戳
- **THEN** 系统通过日志查询接口检索该时间点前后的日志，分析错误发生的时间线

#### Scenario: 基于关键词检索日志
- **WHEN** 错误日志包含特定标识符（如用户ID、请求ID）
- **THEN** 系统通过日志查询接口检索包含该标识符的所有日志，分析相关操作序列

#### Scenario: 识别日志异常模式
- **WHEN** 检索到相关日志
- **THEN** 系统识别异常日志模式（如错误频率激增、特定操作失败等）

#### Scenario: 日志查询分页
- **WHEN** 日志查询结果数量很大
- **THEN** 系统支持分页机制，Agent 可以先查看第一页，需要时再查询后续页面

#### Scenario: 日志结果截断
- **WHEN** 单条日志记录非常长
- **THEN** 系统返回关键片段（包含错误的部分），而非完整日志内容

#### Scenario: 使用日志易进行日志查询
- **WHEN** 系统配置了日志易连接信息（LOGYI_BASE_URL, LOGYI_USERNAME, LOGYI_APIKEY, LOGYI_APPNAME）
- **THEN** 系统使用日志易 API 和 SPL 查询语句进行日志检索，所有查询语句都包含 `appname:<项目名称>` 过滤条件

#### Scenario: SPL 查询验证
- **WHEN** Agent 生成 SPL 查询语句
- **THEN** 系统在执行查询前验证 SPL 语句的语法正确性和安全性
- **WHEN** SPL 查询验证失败
- **THEN** 系统返回错误信息给 Agent，Agent 根据错误信息修正查询语句并重试
- **WHEN** Agent 需要生成 SPL 查询
- **THEN** 系统在 Agent Prompt 中提供 SPL 查询示例（Few-Shot Prompting），帮助 Agent 生成正确的查询

#### Scenario: 日志查询接口抽象化
- **WHEN** 需要对接其他日志系统（非日志易）
- **THEN** 系统通过实现日志查询抽象接口，可以无缝切换日志查询实现，无需修改 Agent 逻辑

#### Scenario: 使用文件日志进行日志查询
- **WHEN** 系统配置了文件日志查询方式（LOG_QUERY_TYPE=file, LOG_FILE_BASE_PATH）
- **THEN** 系统从本地文件系统读取日志文件，根据 appname 定位日志文件路径，进行日志检索和分析

#### Scenario: 日志查询实现方式选择
- **WHEN** 系统配置了 LOG_QUERY_TYPE（logyi 或 file）
- **THEN** 系统使用对应的日志查询实现（日志易或文件日志）
- **WHEN** 未配置 LOG_QUERY_TYPE
- **THEN** 系统默认使用日志易实现

### Requirement: 数据库查询和分析
系统 SHALL 基于错误信息查询数据库，检查相关数据状态，识别数据异常或关联问题。

#### Scenario: 基于错误标识符查询数据
- **WHEN** 错误日志包含数据标识符（如记录ID、用户ID）
- **THEN** 系统查询相关数据记录，检查数据状态和完整性

#### Scenario: 基于错误类型查询相关数据
- **WHEN** 错误类型与特定数据表相关（如外键约束错误）
- **THEN** 系统查询相关表，检查数据一致性和约束违反情况

#### Scenario: 分析数据异常
- **WHEN** 查询到相关数据
- **THEN** 系统分析数据状态，识别异常值、缺失数据或数据不一致问题

#### Scenario: 支持多种数据库
- **WHEN** 配置了 MySQL、PostgreSQL 或 SQLite 数据库连接
- **THEN** 系统能够正确连接并查询相应数据库

#### Scenario: 数据库 Schema 发现
- **WHEN** Agent 需要查询数据库但不知道表结构
- **THEN** Agent 可以调用 Schema 发现工具获取表结构信息，然后生成正确的 SQL 查询

#### Scenario: 数据库安全性
- **WHEN** Agent 尝试执行包含写操作的 SQL（UPDATE, DELETE, DROP 等）
- **THEN** 系统拒绝执行并返回错误信息
- **WHEN** 数据库查询结果包含敏感字段（password, secret 等）
- **THEN** 系统自动过滤或脱敏敏感字段，不返回给 Agent

### Requirement: 综合分析引擎
系统 SHALL 整合来自代码、日志、数据库的分析结果，进行根因分析，并生成应急处理建议。

#### Scenario: 多数据源结果聚合
- **WHEN** 完成所有数据源的查询和分析
- **THEN** 系统聚合所有结果，建立关联关系，形成完整的错误上下文

#### Scenario: 根因分析
- **WHEN** 获得完整的错误上下文
- **THEN** 系统分析错误的根本原因，识别最可能的触发因素和因果关系链

#### Scenario: 生成应急处理建议
- **WHEN** 完成根因分析
- **THEN** 系统生成结构化的应急处理建议，包括：
  - 立即采取的缓解措施
  - 需要检查的关键点
  - 可能的修复方向
  - 预防措施建议

#### Scenario: Agent 错误自修正
- **WHEN** Tool 执行失败（如 SQL 语法错误、参数错误）
- **THEN** Agent 接收错误信息，修正指令并重试（最多重试 3 次）
- **WHEN** 重试次数超过限制
- **THEN** 系统返回最后一次错误信息，不再重试

#### Scenario: 输出分析报告
- **WHEN** 完成分析和建议生成
- **THEN** 系统输出结构化的分析报告，包括：
  - 错误摘要
  - 数据源分析结果
  - 根因分析
  - 应急处理建议
  - 相关代码和日志引用
  - 置信度评分

### Requirement: 数据源扩展接口
系统 SHALL 提供可扩展的数据源接口，支持未来添加新的数据源类型（如服务器状态、进程状态等）。

#### Scenario: 定义数据源接口
- **WHEN** 需要添加新的数据源类型
- **THEN** 系统提供标准的数据源接口，包括查询方法、结果格式规范

#### Scenario: 注册新数据源
- **WHEN** 实现新的数据源适配器
- **THEN** 系统支持动态注册新数据源，并自动集成到分析流程中

#### Scenario: 预留服务器状态检查接口
- **WHEN** 未来需要添加服务器状态检查
- **THEN** 系统架构已预留接口，可以无缝集成服务器状态查询功能

#### Scenario: 预留进程状态检查接口
- **WHEN** 未来需要添加进程状态检查
- **THEN** 系统架构已预留接口，可以无缝集成进程状态查询功能

### Requirement: Web UI 界面
系统 SHALL 提供 Web UI 界面，方便用户直接使用系统进行问题分析。

#### Scenario: Web UI 访问
- **WHEN** 用户在浏览器中访问 Web UI 地址
- **THEN** 系统显示问题分析界面，用户可以输入问题或错误信息

#### Scenario: 用户输入和提交
- **WHEN** 用户在 Web UI 中输入问题描述或上传错误日志文件
- **THEN** 系统接收输入并开始分析，实时显示分析进度

#### Scenario: 实时进度显示
- **WHEN** Agent 执行分析过程中产生进度更新
- **THEN** Web UI 通过 SSE 实时接收并显示分析进度和中间结果

#### Scenario: 分析结果展示
- **WHEN** Agent 完成分析并返回结果
- **THEN** Web UI 以结构化方式展示根因分析、应急处理建议、相关代码和日志引用等信息

#### Scenario: 思考过程折叠显示
- **WHEN** Agent 分析过程中产生思考过程（Agent Thought Trace）
- **THEN** Web UI 默认折叠显示思考过程，用户可点击展开查看详细内容
- **WHEN** 用户查看分析结果
- **THEN** Web UI 重点展示最终结论（根因分析、应急建议），思考过程作为辅助信息折叠显示
- **WHEN** 用户需要了解分析过程
- **THEN** 用户可以展开思考过程，查看工具调用记录、中间推理步骤、错误修正过程等详细信息

### Requirement: 服务部署和配置
系统 SHALL 支持灵活的部署方式和配置管理。

#### Scenario: 容器化部署
- **WHEN** 使用 Docker 镜像部署服务
- **THEN** 系统能够正常启动并提供服务

#### Scenario: 环境变量配置
- **WHEN** 通过环境变量配置数据源连接信息
- **THEN** 系统能够读取配置并建立连接

#### Scenario: 健康检查
- **WHEN** 客户端访问 `GET /health` 端点
- **THEN** 系统返回服务健康状态

#### Scenario: 服务信息查询
- **WHEN** 客户端访问 `GET /api/v1/info` 端点
- **THEN** 系统返回服务版本、支持的功能等信息

