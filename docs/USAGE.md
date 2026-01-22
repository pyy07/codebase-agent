# 使用指南

## 快速开始

### 1. 安装依赖

```bash
pip install -e .
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# LLM 配置（至少配置一个）
OPENAI_API_KEY=your-openai-api-key
# 或
ANTHROPIC_API_KEY=your-anthropic-api-key

# API 认证（可选）
API_KEY=your-api-key

# 代码仓库路径
CODE_REPO_PATH=/path/to/your/codebase

# 日志查询配置（选择一种）
# 选项1：日志易
LOG_QUERY_TYPE=logyi
LOGYI_BASE_URL=https://your-logyi-instance.com
LOGYI_USERNAME=your-username
LOGYI_APIKEY=your-apikey
LOGYI_APPNAME=your-project-name

# 选项2：文件日志
LOG_QUERY_TYPE=file
LOG_FILE_BASE_PATH=/path/to/logs

# 数据库配置（可选）
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/dbname

# Agent 配置（可选）
AGENT_MAX_ITERATIONS=15
AGENT_MAX_EXECUTION_TIME=300
```

### 3. 启动服务

```bash
uvicorn codebase_driven_agent.main:app --reload
```

服务将在 `http://localhost:8000` 启动。

## 使用场景

### 场景1：错误日志分析

**输入示例**:
```
错误日志：
2024-01-01 10:00:00 ERROR [main] com.example.Service - Database connection failed
java.sql.SQLException: Connection refused
    at com.example.Database.connect(Database.java:45)
    at com.example.Service.init(Service.java:20)
```

**Agent 会**:
1. 解析错误信息，提取关键词（Database connection failed, Connection refused）
2. 搜索代码库中相关的数据库连接代码
3. 查询日志中相关的错误记录
4. 检查数据库配置和状态
5. 综合分析并给出根因分析和建议

### 场景2：问题描述分析

**输入示例**:
```
用户反馈：登录功能无法使用，点击登录按钮后页面一直加载，没有响应。
```

**Agent 会**:
1. 理解问题描述
2. 搜索登录相关的代码
3. 查询登录相关的日志
4. 检查数据库中的用户数据
5. 分析可能的原因（网络问题、代码bug、数据库问题等）

### 场景3：代码疑问

**输入示例**:
```
这段代码的作用是什么？为什么会出现性能问题？
[代码片段]
```

**Agent 会**:
1. 分析代码片段
2. 搜索相关的代码上下文
3. 查找相关的日志和性能指标

### 场景4：交互式分析（Agent 主动询问）

**使用场景**:
当 Agent 发现信息不足时，会主动暂停并请求用户提供额外信息。

**流程示例**:

1. **用户提交问题**:
```
我的代码出错了，帮我看看
```

2. **Agent 分析并发现信息不足**:
Agent 会通过 SSE 发送 `user_input_request` 事件：
```json
{
  "event": "user_input_request",
  "data": {
    "request_id": "unique-request-id",
    "question": "请提供具体的错误信息或错误日志，以便我更好地分析问题"
  }
}
```

3. **用户回复**:
通过 `/api/v1/analyze/reply` 端点提交回复：
```bash
curl -X POST http://localhost:8000/api/v1/analyze/reply \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "unique-request-id",
    "reply": "错误信息：Connection refused，发生在数据库连接时"
  }'
```

4. **Agent 继续分析**:
基于用户提供的信息，Agent 继续分析并给出结果。

**Web UI 使用**:
在 Web UI 中，当 Agent 请求用户输入时，会自动弹出对话框，用户可以直接在对话框中输入回复，无需手动调用 API。

**注意事项**:
- Agent 可能会多次请求用户输入，以获取更完整的信息
- 如果用户无法提供信息，可以关闭对话框，Agent 将基于已有信息继续分析
- 会话会在 30 分钟后自动过期
4. 提供代码解释和性能优化建议

## API 使用示例

### Python 客户端示例

```python
import requests
import json

class CodebaseAgentClient:
    def __init__(self, base_url="http://localhost:8000", api_key=None):
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json"
        }
        if api_key:
            self.headers["X-API-Key"] = api_key
    
    def analyze(self, input_text, context_files=None):
        """同步分析"""
        data = {"input": input_text}
        if context_files:
            data["context_files"] = context_files
        
        response = requests.post(
            f"{self.base_url}/api/v1/analyze",
            headers=self.headers,
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def analyze_async(self, input_text, context_files=None):
        """异步分析"""
        data = {"input": input_text}
        if context_files:
            data["context_files"] = context_files
        
        response = requests.post(
            f"{self.base_url}/api/v1/analyze/async",
            headers=self.headers,
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def get_task_status(self, task_id):
        """查询任务状态"""
        response = requests.get(
            f"{self.base_url}/api/v1/analyze/{task_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def reply_to_agent(self, request_id, reply):
        """回复 Agent 的询问（交互式分析）"""
        response = requests.post(
            f"{self.base_url}/api/v1/analyze/reply",
            headers=self.headers,
            json={
                "request_id": request_id,
                "reply": reply
            }
        )
        response.raise_for_status()
        return response.json()
    
    def analyze_stream(self, input_text, context_files=None, on_progress=None, on_user_input=None):
        """流式分析（支持交互）"""
        import sseclient
        
        data = {"input": input_text}
        if context_files:
            data["context_files"] = context_files
        
        response = requests.post(
            f"{self.base_url}/api/v1/analyze/stream",
            headers=self.headers,
            json=data,
            stream=True
        )
        response.raise_for_status()
        
        client = sseclient.SSEClient(response)
        result = None
        
        for event in client.events():
            if event.event == "progress":
                if on_progress:
                    on_progress(json.loads(event.data))
            elif event.event == "user_input_request":
                data = json.loads(event.data)
                if on_user_input:
                    reply = on_user_input(data["question"])
                    if reply:
                        self.reply_to_agent(data["request_id"], reply)
            elif event.event == "result":
                result = json.loads(event.data)
            elif event.event == "done":
                break
        
        return result

# 使用示例
client = CodebaseAgentClient(api_key="your-api-key")

# 同步分析
result = client.analyze("数据库连接失败")
print(result)

# 异步分析
task = client.analyze_async("数据库连接失败")
task_id = task["task_id"]

# 轮询查询状态
import time
while True:
    status = client.get_task_status(task_id)
    if status["status"] in ["completed", "failed"]:
        print(status)
        break
    time.sleep(1)

# 流式分析（支持交互）
def handle_user_input(question):
    """处理 Agent 的询问"""
    print(f"Agent 询问: {question}")
    reply = input("请输入回复（或按 Enter 跳过）: ")
    return reply if reply else None

result = client.analyze_stream(
    "我的代码出错了，帮我看看",
    on_progress=lambda data: print(f"进度: {data.get('progress', 0):.1%} - {data.get('message', '')}"),
    on_user_input=handle_user_input
)
print("分析结果:", result)
```

## 上下文文件使用

上下文文件可以帮助 Agent 更准确地分析问题。你可以提供：

1. **代码片段**: 相关的代码文件或代码片段
2. **日志片段**: 相关的日志内容

**示例**:

```python
context_files = [
    {
        "type": "code",
        "path": "src/database.py",
        "content": """
def connect():
    conn = mysql.connect(host='localhost', ...)
    return conn
""",
        "line_start": 10,
        "line_end": 20
    },
    {
        "type": "log",
        "path": "logs/app.log",
        "content": """
2024-01-01 10:00:00 ERROR Database connection failed
2024-01-01 10:00:01 ERROR Retrying connection...
"""
    }
]

result = client.analyze(
    "数据库连接失败",
    context_files=context_files
)
```

## 最佳实践

1. **提供清晰的输入**: 尽量详细地描述问题，包括错误信息、时间范围、相关操作等。

2. **使用上下文文件**: 如果问题涉及特定的代码或日志，提供相关的上下文文件可以提高分析准确性。

3. **异步处理长时间任务**: 对于复杂的问题分析，使用异步接口避免超时。

4. **监控指标**: 定期查看 `/api/v1/metrics` 端点，了解服务的使用情况和性能。

5. **错误处理**: 实现适当的错误处理和重试机制。

6. **速率限制**: 注意速率限制（默认每分钟 60 次请求），避免请求被拒绝。

## 常见问题

### Q: Agent 无法找到相关代码？

A: 检查 `CODE_REPO_PATH` 配置是否正确，确保路径指向正确的代码仓库。

### Q: 日志查询失败？

A: 
- 如果使用日志易，检查 `LOGYI_*` 配置是否正确，特别是 `LOGYI_APPNAME`。
- 如果使用文件日志，检查 `LOG_FILE_BASE_PATH` 配置和文件权限。

### Q: 数据库查询失败？

A: 检查 `DATABASE_URL` 配置是否正确，确保数据库账号有只读权限。

### Q: Agent 执行超时？

A: 可以增加 `AGENT_MAX_EXECUTION_TIME` 配置，或使用异步接口。

### Q: 如何提高分析准确性？

A: 
- 提供详细的输入信息
- 使用上下文文件提供相关代码和日志
- 确保代码仓库、日志、数据库配置正确

## 下一步

- 查看 [API 文档](./API.md) 了解详细的 API 接口
- 查看 [开发文档](./DEVELOPMENT.md) 了解如何扩展功能
- 查看 [配置文档](./CONFIG.md) 了解所有配置选项

