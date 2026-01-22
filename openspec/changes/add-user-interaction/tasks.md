## 1. 后端：Agent 交互节点实现

- [x] 1.1 在 `graph_executor.py` 中添加 `request_user_input` 节点
- [x] 1.2 修改 `_decision_node`，支持返回 `request_input` 动作
- [x] 1.3 实现用户输入请求的 prompt 生成逻辑
- [x] 1.4 添加用户回复处理逻辑，将用户回复添加到消息历史
- [x] 1.5 更新图结构，添加从 `request_user_input` 到 `execute_step` 的边
- [x] 1.6 实现执行状态的暂停和恢复机制

## 2. 后端：SSE 事件扩展

- [x] 2.1 在 `sse.py` 中添加 `user_input_request` 事件类型
- [x] 2.2 实现 `user_input_request` 事件的格式化函数
- [x] 2.3 在 `graph_executor.py` 中发送 `user_input_request` 事件到消息队列
- [x] 2.4 确保事件包含询问内容、请求 ID 等信息

## 3. 后端：API 端点实现

- [x] 3.1 在 `models.py` 中添加 `UserReplyRequest` 模型（包含 request_id, reply）
- [x] 3.2 在 `routes.py` 中添加 `POST /api/v1/analyze/reply` 端点
- [x] 3.3 实现用户回复的验证和处理逻辑
- [x] 3.4 将用户回复添加到对应的 Agent 执行上下文中
- [x] 3.5 恢复 Agent 执行流程

## 4. 后端：状态管理

- [x] 4.1 实现执行会话的状态存储（内存或 Redis）
- [x] 4.2 支持会话的暂停和恢复
- [x] 4.3 实现会话超时和清理机制
- [x] 4.4 确保多个用户回复请求的正确处理

## 5. 前端：类型定义

- [x] 5.1 在 `types.ts` 中添加 `UserInputRequest` 类型
- [x] 5.2 添加 `user_input_request` 到 `MessageContentType`
- [x] 5.3 添加用户回复相关的状态类型

## 6. 前端：SSE 事件处理

- [x] 6.1 在 `useSSE.ts` 中添加 `onUserInputRequest` 回调
- [x] 6.2 实现 `user_input_request` 事件的解析和处理
- [x] 6.3 在 `App.tsx` 中添加 `handleUserInputRequest` 处理函数

## 7. 前端：交互组件

- [x] 7.1 创建 `UserInputRequest.tsx` 组件，显示 Agent 的询问
- [x] 7.2 创建 `UserReply.tsx` 组件，显示用户的回复
- [x] 7.3 在 `AgentMessage.tsx` 中集成用户交互组件
- [x] 7.4 实现用户回复的输入框和提交逻辑

## 8. 前端：API 集成

- [x] 8.1 实现调用 `POST /api/v1/analyze/reply` 的函数
- [x] 8.2 处理用户回复的提交和错误处理
- [x] 8.3 确保回复后能够继续接收 SSE 事件

## 9. 测试

- [x] 9.1 编写后端单元测试（graph_executor 交互节点）
- [x] 9.2 编写后端集成测试（API 端点）
- [x] 9.3 编写前端组件测试
- [x] 9.4 编写端到端测试（完整交互流程）

## 10. 文档更新

- [x] 10.1 更新 `docs/API.md`，添加用户回复 API 文档
- [x] 10.2 更新 `docs/USAGE.md`，说明用户交互功能
- [x] 10.3 更新 `README.md`，添加用户交互功能说明
