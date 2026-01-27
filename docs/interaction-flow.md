# Codebase Agent 交互流程说明

## 整体架构图

```
用户输入
    ↓
[Plan 节点]
    ├─→ 需要用户输入？ ──→ [Request User Input 节点] ──→ 等待用户回复 ──→ 用户回复 API ──→ 继续执行
    │                           ↓
    │                       发送 user_input_request 事件
    │                           ↓
    │                       前端显示对话框
    │                           ↓
    │                       用户提交回复
    │                           ↓
    │                       后端接收回复
    │                           ↓
    │                       标记用户输入步骤为 completed
    │                           ↓
    │                       继续执行流程
    │
    └─→ 不需要用户输入 ──→ [Execute Step 节点] ──→ [Decide 节点]
                                                          ├─→ continue ──→ [Execute Step]
                                                          ├─→ request_input ──→ [Request User Input]
                                                          ├─→ synthesize ──→ [Synthesize 节点] ──→ 结束
                                                          └─→ adjust_plan ──→ [Plan 节点]
```

## 详细流程说明

### 1. 初始阶段：用户提交问题

```
用户 → POST /api/v1/analyze/stream
    ↓
创建 GraphExecutor
    ↓
初始化状态：
- messages: []
- plan_steps: []
- current_step: 0
- step_results: []
    ↓
启动 SSE 流
    ↓
进入 Plan 节点
```

### 2. Plan 节点流程

```
Plan 节点
    ↓
调用 LLM 生成计划
    ↓
解析 LLM 响应
    ├─→ action == "request_input"
    │       ↓
    │   创建用户交互步骤：
    │   {
    │     step: 1,
    │     action: "请求用户输入",
    │     tool_name: "user_input",
    │     tool_params: { question, context }
    │   }
    │       ↓
    │   添加到 plan_steps
    │       ↓
    │   返回 decision="request_input"
    │       ↓
    │   跳转到 Request User Input 节点
    │
    └─→ action == "continue"
            ↓
        解析 next_steps
            ↓
        添加到 plan_steps
            ↓
        返回 plan_steps
            ↓
        跳转到 Execute Step 节点
```

### 3. Execute Step 节点流程

```
Execute Step 节点
    ↓
获取当前步骤：plan_steps[current_step]
    ↓
检查 tool_name
    ├─→ tool_name == "user_input"
    │       ↓
    │   跳过工具调用
    │       ↓
    │   返回 decision="request_input"
    │       ↓
    │   跳转到 Request User Input 节点
    │
    └─→ tool_name != "user_input"
            ↓
        调用工具：_call_tool_directly(tool_name, tool_params)
            ↓
        保存结果到 step_results
            ↓
        发送 step_execution 事件到前端
            ↓
        更新 current_step = current_step + 1
            ↓
        跳转到 Decide 节点
```

### 4. Decide 节点流程

```
Decide 节点
    ↓
调用 LLM 决策下一步
    ↓
解析 LLM 响应
    ├─→ action == "continue"
    │       ↓
    │   解析 next_steps
    │       ↓
    │   扩展 plan_steps
    │       ↓
    │   发送 plan 更新事件到前端
    │       ↓
    │   返回 should_continue=True
    │       ↓
    │   跳转到 Execute Step 节点
    │
    ├─→ action == "request_input"
    │       ↓
    │   创建用户交互步骤：
    │   {
    │     step: len(plan_steps) + 1,
    │     action: "请求用户输入",
    │     tool_name: "user_input",
    │     tool_params: { question, context }
    │   }
    │       ↓
    │   添加到 plan_steps
    │       ↓
    │   返回 decision="request_input"
    │       ↓
    │   跳转到 Request User Input 节点
    │
    └─→ action == "synthesize"
            ↓
        返回 should_continue=False
            ↓
        跳转到 Synthesize 节点
```

### 5. Request User Input 节点流程

```
Request User Input 节点
    ↓
生成 request_id (UUID)
    ↓
保存会话状态到 SessionManager
    ↓
发送 user_input_request 事件到消息队列
    ↓
前端接收事件
    ↓
显示对话框（UserInputModal）
    ↓
等待用户输入...
    ↓
[工作流程暂停]
```

### 6. 用户回复流程

```
用户提交回复
    ↓
POST /api/v1/analyze/reply
    ↓
查找会话（通过 request_id）
    ↓
添加用户回复到 messages
    ↓
标记用户输入步骤为 completed
    ↓
发送 step_execution 事件（status=completed）
    ↓
发送 user_reply 事件到前端
    ↓
更新 current_step = current_step + 1（用户交互步骤已完成）
    ↓
手动执行后续节点（因为 LangGraph 不支持从中间节点继续）
    ↓
检查是否还有未执行的步骤：
    ├─→ 如果 current_step < len(plan_steps)
    │       ↓
    │   执行 _execute_step_node() ──→ 执行下一个步骤
    │       ↓
    │   然后执行 _decision_node() ──→ 决策下一步
    │       ↓
    │   根据决策继续执行或结束
    │
    └─→ 如果 current_step >= len(plan_steps)
            ↓
        执行 _decision_node() ──→ 基于用户回复和已有结果重新决策
            ↓
        检查 next_action：
            ├─→ continue ──→ 如果有新步骤，执行 _execute_step_node()
            ├─→ request_input ──→ _request_user_input_node()
            └─→ synthesize ──→ _synthesize_node()
    ↓
继续循环直到完成或再次请求用户输入
```

### 7. Synthesize 节点流程

```
Synthesize 节点
    ↓
收集所有 step_results
    ↓
调用 LLM 生成最终分析结果
    ↓
解析结果（root_cause, suggestions, etc.）
    ↓
发送 result 事件到前端
    ↓
发送 done 事件到前端
    ↓
结束流程
```

## 关键数据结构

### AgentState

```python
{
    "messages": List[Message],           # 对话历史
    "plan_steps": List[PlanStep],        # 计划步骤列表
    "current_step": int,                 # 当前步骤索引
    "step_results": List[StepResult],    # 步骤执行结果
    "should_continue": bool,             # 是否继续执行
    "original_input": str,               # 原始用户输入
    "context_files": List[Dict],         # 上下文文件
    "decision": str,                     # 决策结果：continue/synthesize/request_input
    "user_input_question": str,          # 用户输入请求的问题
    "user_input_context": str,          # 用户输入请求的上下文
    "request_id": str,                   # 用户输入请求的 ID
}
```

### PlanStep

```python
{
    "step": int,                         # 步骤编号（从1开始）
    "action": str,                      # 操作描述（中文）
    "tool_name": str,                   # 工具名称（如 "read", "code_search", "user_input"）
    "tool_params": Dict,                # 工具参数
}
```

### 用户交互步骤（特殊）

```python
{
    "step": 1,                          # 步骤编号
    "action": "请求用户输入",
    "tool_name": "user_input",          # 特殊标识
    "tool_params": {
        "question": "请提供...",
        "context": "上下文信息"
    }
}
```

## 前端显示逻辑

### UnifiedStepsBlock 组件

1. **接收数据**：
   - `planSteps`: 计划步骤列表（来自后端）
   - `executionSteps`: 执行步骤列表（来自后端）
   - `userInputRequests`: 用户输入请求列表（来自 SSE 事件）
   - `userReplies`: 用户回复列表（来自 SSE 事件）

2. **步骤合并逻辑**：
   ```typescript
   planSteps.forEach(planStep => {
     if (planStep.tool_name === "user_input") {
       // 用户交互步骤：查找对应的 userInputRequest 和 userReply
       const matchingRequest = userInputRequests.find(...)
       const matchingReply = userReplies.find(...)
       // 创建用户交互步骤
     } else {
       // 普通步骤：合并 planStep 和 executionStep
     }
   })
   ```

3. **显示顺序**：
   - 严格按照 `plan_steps` 的顺序显示
   - 如果第一个步骤是用户交互，显示为步骤1
   - 不需要额外的排序或插入逻辑

## 事件流

### SSE 事件类型

1. **progress**: 进度更新
2. **plan**: 计划更新（包含 plan_steps）
3. **step_execution**: 步骤执行结果
4. **user_input_request**: 用户输入请求
5. **user_reply**: 用户回复
6. **result**: 最终分析结果
7. **done**: 分析完成

### 消息队列处理

```
后端节点 → message_queue.put_nowait(event)
    ↓
SSE 流循环读取消息队列
    ↓
发送到前端（SSE 格式）
    ↓
前端接收并处理事件
    ↓
更新 UI 状态
```

## 关键设计决策

1. **用户交互作为步骤**：
   - 用户交互步骤添加到 `plan_steps` 中（`tool_name: "user_input"`）
   - 前端按照 `plan_steps` 的顺序显示，无需额外排序

2. **工作流程暂停**：
   - `request_user_input` 节点后直接跳转到 END
   - 用户回复后，手动执行后续节点（因为 LangGraph 不支持从中间节点继续）

3. **状态管理**：
   - 使用 SessionManager 保存会话状态
   - 用户回复后，从保存的状态恢复执行

4. **事件驱动**：
   - 所有状态更新通过消息队列发送事件
   - 前端通过 SSE 流接收事件并更新 UI
