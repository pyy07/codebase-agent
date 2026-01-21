# Change: 添加 Agent 与用户交互机制

## Why

当前 Agent 的工作流程是单向的：用户输入问题 → Agent 分析 → 返回结果。但在实际使用中，Agent 经常会遇到以下情况：

1. **问题信息不完整**：用户提供的问题描述缺少关键信息（如错误发生的时间、环境、相关配置等）
2. **需要用户确认**：Agent 发现了多个可能的原因，需要用户提供更多上下文来缩小范围
3. **需要用户协助**：Agent 需要访问用户本地环境的信息，或需要用户执行某些操作来验证假设

在这些情况下，Agent 应该能够暂停执行，主动向用户询问额外信息，然后基于用户的回复继续分析，而不是基于不完整的信息给出可能不准确的结论。

## What Changes

- **新增交互节点**：在 LangGraph 工作流中添加"请求用户输入"节点，Agent 可以在执行过程中暂停并请求用户输入
- **SSE 事件扩展**：新增 `user_input_request` 事件类型，通过 SSE 向前端发送询问信息
- **用户回复处理**：新增 API 端点接收用户的回复，并继续执行 Agent 分析流程
- **前端交互界面**：在 Web UI 中添加显示 Agent 询问和用户回复的界面组件
- **状态管理**：支持 Agent 执行状态的暂停和恢复，确保用户回复后能够正确继续执行

## Impact

- **受影响的规范**：`error-analysis-agent` capability（修改）
- **受影响的代码**：
  - `codebase_driven_agent/agent/graph_executor.py` - 添加交互节点和状态管理
  - `codebase_driven_agent/api/sse.py` - 添加 `user_input_request` 事件
  - `codebase_driven_agent/api/routes.py` - 添加用户回复处理端点
  - `codebase_driven_agent/api/models.py` - 添加用户回复请求模型
  - `web/src/App.tsx` - 添加用户回复处理逻辑
  - `web/src/components/` - 添加用户交互组件
  - `web/src/types.ts` - 添加用户交互相关的类型定义
  - `web/src/hooks/useSSE.ts` - 添加 `user_input_request` 事件处理

- **向后兼容性**：完全兼容，现有功能不受影响。如果 Agent 不需要用户输入，工作流程与之前完全相同。
