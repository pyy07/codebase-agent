# API 文档

## 概述

Codebase Driven Agent 提供 REST API 和 Server-Sent Events (SSE) 流式接口，用于问题分析和错误排查。

## 基础信息

- **Base URL**: `http://localhost:8000`
- **API Version**: `v1`
- **Content-Type**: `application/json`

## 认证

如果配置了 API Key，需要在请求头中包含：

```
X-API-Key: your-api-key
```

## 端点列表

### 1. 健康检查

**GET** `/health`

检查服务健康状态。

**响应示例**:
```json
{
  "status": "healthy"
}
```

### 2. 服务信息

**GET** `/api/v1/info`

获取服务基本信息。

**响应示例**:
```json
{
  "name": "Codebase Driven Agent",
  "version": "0.1.0",
  "status": "running"
}
```

### 3. 指标信息

**GET** `/api/v1/metrics`

获取服务指标信息（Prometheus 格式）。

**响应示例**:
```json
{
  "counters": {
    "http_requests_total{endpoint=/api/v1/analyze,method=POST,status=200}": 10
  },
  "histograms": {
    "http_request_duration_seconds{endpoint=/api/v1/analyze,method=POST}": {
      "count": 10,
      "min": 0.5,
      "max": 3.2,
      "avg": 1.8,
      "p50": 1.6,
      "p95": 2.8,
      "p99": 3.1
    }
  },
  "gauges": {},
  "uptime_seconds": 3600
}
```

### 4. 同步分析

**POST** `/api/v1/analyze`

同步执行问题分析，等待完成后返回结果。

**请求体**:
```json
{
  "input": "用户输入的问题描述或错误日志",
  "context_files": [
    {
      "type": "code",
      "path": "path/to/file.py",
      "content": "代码内容",
      "line_start": 10,
      "line_end": 20
    },
    {
      "type": "log",
      "path": "path/to/log.txt",
      "content": "日志内容"
    }
  ]
}
```

**响应示例**:
```json
{
  "success": true,
  "result": {
    "root_cause": "问题的根本原因分析",
    "suggestions": [
      "建议1：...",
      "建议2：...",
      "建议3：..."
    ],
    "confidence": 0.85,
    "related_code": null,
    "related_logs": null,
    "related_data": null
  }
}
```

### 5. 异步分析

**POST** `/api/v1/analyze/async`

异步执行问题分析，立即返回任务 ID。

**请求体**: 同同步分析

**响应示例**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending"
}
```

### 6. 查询任务状态

**GET** `/api/v1/analyze/{task_id}`

查询异步任务的状态和结果。

**响应示例**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "result": {
    "root_cause": "问题的根本原因分析",
    "suggestions": ["建议1", "建议2"],
    "confidence": 0.85
  }
}
```

**状态值**:
- `pending`: 等待执行
- `running`: 正在执行
- `completed`: 已完成
- `failed`: 执行失败

### 7. 流式分析

**POST** `/api/v1/analyze/stream`

使用 Server-Sent Events (SSE) 流式返回分析进度和结果。

**请求体**: 同同步分析

**响应格式** (SSE):
```
event: progress
data: {"message": "开始分析...", "progress": 0.0, "step": "initializing"}

event: progress
data: {"message": "检索相关代码...", "progress": 0.4, "step": "searching_code"}

event: user_input_request
data: {"request_id": "unique-request-id", "question": "请提供具体的错误信息"}

event: result
data: {"root_cause": "...", "suggestions": [...], "confidence": 0.85}

event: done
data: {"message": "Analysis completed"}
```

**SSE 事件类型**:
- `progress`: 分析进度更新
- `user_input_request`: Agent 请求用户输入（交互式分析）
- `user_reply`: 用户回复确认
- `result`: 最终分析结果
- `done`: 分析完成

### 8. 用户回复（交互式分析）

**POST** `/api/v1/analyze/reply`

当 Agent 在分析过程中请求用户输入时，使用此端点提交用户的回复，Agent 将基于回复继续分析。

**请求体**:
```json
{
  "request_id": "请求ID（来自 user_input_request 事件）",
  "reply": "用户的回复内容"
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "回复已接收，Agent 将继续分析"
}
```

**状态码**:
- `200`: 成功
- `400`: 请求参数错误（如 request_id 无效或已过期）
- `404`: 未找到对应的会话（request_id 不存在）
- `500`: 服务器内部错误

**使用场景**:

当使用流式分析接口（`/api/v1/analyze/stream`）时，如果 Agent 需要更多信息，会发送 `user_input_request` 事件：

```json
{
  "event": "user_input_request",
  "data": {
    "request_id": "unique-request-id",
    "question": "请提供具体的错误信息或错误日志"
  }
}
```

收到此事件后，调用 `/api/v1/analyze/reply` 提交回复，Agent 将继续分析。

**示例**:

```bash
# 提交用户回复
curl -X POST http://localhost:8000/api/v1/analyze/reply \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "request_id": "unique-request-id",
    "reply": "错误发生在 2024-01-01 10:00:00，错误信息是 Connection refused"
  }'
```

```python
# Python 示例
import requests

response = requests.post(
    "http://localhost:8000/api/v1/analyze/reply",
    headers={
        "Content-Type": "application/json",
        "X-API-Key": "your-api-key"
    },
    json={
        "request_id": "unique-request-id",
        "reply": "错误发生在 2024-01-01 10:00:00，错误信息是 Connection refused"
    }
)
result = response.json()
print(result)  # {"success": true, "message": "回复已接收，Agent 将继续分析"}
```

**注意事项**:
- `request_id` 来自 `user_input_request` 事件，必须匹配
- 会话会在 30 分钟后自动过期，过期后无法提交回复
- 支持多次交互，Agent 可能会多次请求用户输入
- 如果用户无法提供信息，可以关闭对话框或等待超时，Agent 将基于已有信息继续分析

## 错误处理

所有错误响应遵循以下格式：

```json
{
  "detail": "错误描述信息"
}
```

**常见错误码**:
- `400`: 请求参数错误
- `401`: 认证失败（缺少或无效的 API Key）
- `413`: 请求体过大（超过 10MB）
- `429`: 请求频率超限
- `500`: 服务器内部错误

## 使用示例

### cURL

```bash
# 同步分析
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "input": "数据库连接失败，错误信息：Connection refused"
  }'

# 异步分析
curl -X POST http://localhost:8000/api/v1/analyze/async \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "input": "数据库连接失败"
  }'

# 查询任务状态
curl http://localhost:8000/api/v1/analyze/{task_id} \
  -H "X-API-Key: your-api-key"

# 流式分析
curl -X POST http://localhost:8000/api/v1/analyze/stream \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "input": "数据库连接失败"
  }'
```

### Python

```python
import requests

# 同步分析
response = requests.post(
    "http://localhost:8000/api/v1/analyze",
    headers={
        "Content-Type": "application/json",
        "X-API-Key": "your-api-key"
    },
    json={
        "input": "数据库连接失败，错误信息：Connection refused"
    }
)
result = response.json()
print(result)

# 异步分析
response = requests.post(
    "http://localhost:8000/api/v1/analyze/async",
    headers={
        "Content-Type": "application/json",
        "X-API-Key": "your-api-key"
    },
    json={
        "input": "数据库连接失败"
    }
)
task_id = response.json()["task_id"]

# 查询任务状态
response = requests.get(
    f"http://localhost:8000/api/v1/analyze/{task_id}",
    headers={"X-API-Key": "your-api-key"}
)
status = response.json()
print(status)

# 流式分析
import sseclient

response = requests.post(
    "http://localhost:8000/api/v1/analyze/stream",
    headers={
        "Content-Type": "application/json",
        "X-API-Key": "your-api-key"
    },
    json={
        "input": "数据库连接失败"
    },
    stream=True
)

client = sseclient.SSEClient(response)
for event in client.events():
    if event.event == "progress":
        print(f"进度: {event.data}")
    elif event.event == "result":
        print(f"结果: {event.data}")
    elif event.event == "done":
        print("完成")
        break
```

### JavaScript (Fetch API)

```javascript
// 同步分析
const response = await fetch('http://localhost:8000/api/v1/analyze', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify({
    input: '数据库连接失败，错误信息：Connection refused'
  })
});
const result = await response.json();
console.log(result);

// 异步分析
const asyncResponse = await fetch('http://localhost:8000/api/v1/analyze/async', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify({
    input: '数据库连接失败'
  })
});
const { task_id } = await asyncResponse.json();

// 查询任务状态
const statusResponse = await fetch(
  `http://localhost:8000/api/v1/analyze/${task_id}`,
  {
    headers: {
      'X-API-Key': 'your-api-key'
    }
  }
);
const status = await statusResponse.json();
console.log(status);

// 流式分析
const eventSource = new EventSource(
  'http://localhost:8000/api/v1/analyze/stream',
  {
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': 'your-api-key'
    },
    body: JSON.stringify({
      input: '数据库连接失败'
    })
  }
);

eventSource.addEventListener('progress', (event) => {
  const data = JSON.parse(event.data);
  console.log('进度:', data);
});

eventSource.addEventListener('result', (event) => {
  const data = JSON.parse(event.data);
  console.log('结果:', data);
});

eventSource.addEventListener('done', () => {
  console.log('完成');
  eventSource.close();
});
```

## 速率限制

默认速率限制为每分钟 60 次请求。超过限制将返回 `429 Too Many Requests` 错误。

## 注意事项

1. **API Key**: 如果配置了 API Key，所有请求（除了 `/health`、`/docs`、`/api/v1/info`）都需要包含有效的 API Key。

2. **请求体大小**: 请求体大小限制为 10MB。

3. **超时**: 
   - 同步分析：默认超时时间为 Agent 配置的 `max_execution_time`（默认 300 秒）
   - 异步分析：任务会在后台执行，可以通过任务 ID 查询状态

4. **上下文文件**: `context_files` 是可选的，用于提供额外的代码或日志片段作为辅助上下文，帮助 Agent 更准确地分析问题。

