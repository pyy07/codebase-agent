## MODIFIED Requirements

### Requirement: 用户输入处理
系统 SHALL 接收用户提供的输入（错误日志、问题描述、疑问等），并解析其中的关键信息（错误类型、堆栈跟踪、时间戳、相关标识符、关键词等）。系统 SHALL 支持 Agent 在执行过程中主动请求用户提供额外信息，以帮助完成更准确的分析。

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

#### Scenario: Agent 请求用户输入
- **WHEN** Agent 在执行过程中发现信息不足或需要用户协助
- **THEN** Agent 暂停执行，通过 SSE 发送 `user_input_request` 事件，包含询问内容和请求 ID
- **WHEN** 用户通过 API 提交回复
- **THEN** 系统将用户回复添加到 Agent 的消息历史中，恢复 Agent 执行流程
- **WHEN** Agent 收到用户回复
- **THEN** Agent 基于新信息继续分析，可以再次请求用户输入或得出结论

#### Scenario: 多次交互支持
- **WHEN** Agent 需要多次请求用户输入
- **THEN** 系统支持多次交互循环，每次交互都有独立的请求 ID
- **WHEN** 用户回复后 Agent 继续执行
- **THEN** 系统保持完整的对话上下文，包括所有用户回复和 Agent 询问

#### Scenario: 会话状态管理
- **WHEN** Agent 请求用户输入后
- **THEN** 系统保存 Agent 执行状态（包括消息历史、计划步骤、当前步骤等）
- **WHEN** 用户提交回复
- **THEN** 系统根据请求 ID 恢复对应的 Agent 状态，继续执行
- **WHEN** 会话超过保留时间（如 30 分钟）
- **THEN** 系统自动清理过期会话，释放资源

## ADDED Requirements

### Requirement: Agent 主动交互能力
Agent SHALL 能够在分析过程中主动识别信息不足的情况，并请求用户提供额外信息。

#### Scenario: 识别信息不足
- **WHEN** Agent 发现用户输入缺少关键信息（如错误发生时间、环境配置、相关操作步骤等）
- **THEN** Agent 识别信息缺失，决定请求用户输入
- **WHEN** Agent 发现多个可能的原因但无法确定
- **THEN** Agent 请求用户提供更多上下文信息以缩小范围

#### Scenario: 生成询问内容
- **WHEN** Agent 决定请求用户输入
- **THEN** Agent 生成清晰的询问内容，说明需要什么信息以及为什么需要
- **WHEN** Agent 需要多个信息
- **THEN** Agent 可以一次询问多个问题，或分多次询问

#### Scenario: 基于用户回复继续分析
- **WHEN** Agent 收到用户回复
- **THEN** Agent 将用户回复整合到分析上下文中
- **WHEN** Agent 基于新信息继续分析
- **THEN** Agent 可以调用工具、调整计划、或直接得出结论

### Requirement: 用户回复 API
系统 SHALL 提供 API 端点，允许用户回复 Agent 的询问。

#### Scenario: 提交用户回复
- **WHEN** 用户通过 `POST /api/v1/analyze/reply` 提交回复
- **THEN** 系统验证请求 ID 的有效性，将回复添加到对应的 Agent 会话中
- **WHEN** 请求 ID 无效或会话已过期
- **THEN** 系统返回错误信息，提示用户重新开始分析

#### Scenario: 回复后继续执行
- **WHEN** 用户提交有效回复
- **THEN** 系统恢复 Agent 执行，继续通过 SSE 发送后续事件
- **WHEN** Agent 完成分析
- **THEN** 系统通过 SSE 发送最终结果，关闭连接

### Requirement: Web UI 用户交互界面
Web UI SHALL 支持显示 Agent 的询问并允许用户回复。

#### Scenario: 显示 Agent 询问
- **WHEN** Web UI 收到 `user_input_request` SSE 事件
- **THEN** UI 显示 Agent 的询问内容，并提供输入框供用户回复
- **WHEN** 询问包含上下文信息
- **THEN** UI 同时显示上下文信息，帮助用户理解为什么需要这个信息

#### Scenario: 用户提交回复
- **WHEN** 用户在输入框中输入回复并提交
- **THEN** UI 调用回复 API，显示"正在处理..."状态
- **WHEN** 回复提交成功
- **THEN** UI 显示用户的回复内容，等待 Agent 继续执行
- **WHEN** 回复提交失败
- **THEN** UI 显示错误信息，允许用户重试

#### Scenario: 多次交互显示
- **WHEN** Agent 多次请求用户输入
- **THEN** UI 在消息流中按顺序显示所有询问和回复
- **WHEN** 用户查看历史对话
- **THEN** UI 清晰展示完整的交互流程，包括 Agent 询问和用户回复
