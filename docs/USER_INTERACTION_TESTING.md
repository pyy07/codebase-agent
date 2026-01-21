# 用户交互功能测试指南

本文档说明如何测试 Agent 与用户的交互功能。

## 测试方法

### 方法 1: 手动测试（推荐用于快速验证）

#### 步骤 1: 启动服务

```bash
# 启动后端
python run_backend.py

# 启动前端（另一个终端）
cd web
npm run dev
```

#### 步骤 2: 触发 Agent 请求用户输入

由于 Agent 需要在实际分析过程中判断是否需要用户输入，我们可以通过以下方式触发：

**方式 A: 使用模糊的问题描述**

在 Web UI 中输入一个信息不完整的问题，例如：
```
我的代码出错了，帮我看看
```

Agent 可能会因为缺少关键信息（如错误日志、具体错误信息等）而请求用户提供更多信息。

**方式 B: 修改 prompt 强制请求（用于测试）**

临时修改 `codebase_driven_agent/agent/graph_executor.py` 中的 `_build_adjustment_plan_prompt` 方法（约第596行），在 prompt 开头添加测试指令：

```python
prompt = f"""**测试模式：请在第1步后请求用户输入，询问"请提供具体的错误信息或错误日志"**

你是一个智能分析 Agent。请根据已执行步骤的结果，动态决定下一步。

原始问题：
{input_text}
...
```

**方式 C: 使用环境变量控制（推荐）**

在 `.env` 文件中添加：
```bash
FORCE_USER_INPUT_TEST=true
```

然后在 `_build_adjustment_plan_prompt` 中添加：
```python
from codebase_driven_agent.config import settings

# 在 prompt 开头
test_instruction = ""
if getattr(settings, 'force_user_input_test', False):
    test_instruction = "**测试模式：请在第1步后请求用户输入，询问'请提供具体的错误信息或错误日志'**\n\n"

prompt = f"""{test_instruction}你是一个智能分析 Agent...
```

#### 步骤 3: 验证交互流程

1. **观察前端界面**
   - Agent 应该显示一个询问框，包含：
     - 问题内容
     - 可选的上下文说明
     - 输入框
     - 提交按钮

2. **提交用户回复**
   - 在输入框中输入回复，例如："错误信息是 FileNotFoundError: config.json not found"
   - 点击"提交回复"按钮

3. **验证 Agent 继续执行**
   - Agent 应该收到回复后继续分析
   - 前端应该显示用户的回复内容
   - Agent 应该基于新信息继续执行步骤

#### 步骤 4: 验证多次交互

Agent 可以多次请求用户输入。验证：
- 每次请求都有独立的 `request_id`
- 用户回复后 Agent 能正确继续
- 所有交互历史都正确显示

### 方法 2: 自动化测试

#### 单元测试：会话管理

创建 `tests/test_session_manager.py`:

```python
"""测试会话管理功能"""
import pytest
from datetime import datetime, timedelta
from codebase_driven_agent.agent.session_manager import SessionManager, SessionInfo
from codebase_driven_agent.agent.graph_executor import AgentState

def test_create_session():
    """测试创建会话"""
    manager = SessionManager()
    state: AgentState = {
        "messages": [],
        "plan_steps": [],
        "current_step": 0,
        "step_results": [],
        "should_continue": True,
        "original_input": "test",
        "context_files": None,
    }
    
    request_id = manager.create_session(
        state=state,
        executor=None,
        message_queue=None
    )
    
    assert request_id is not None
    session = manager.get_session(request_id)
    assert session is not None
    assert session.request_id == request_id

def test_session_expiration():
    """测试会话过期"""
    manager = SessionManager(timeout_minutes=0)  # 立即过期
    state: AgentState = {
        "messages": [],
        "plan_steps": [],
        "current_step": 0,
        "step_results": [],
        "should_continue": True,
        "original_input": "test",
        "context_files": None,
    }
    
    request_id = manager.create_session(
        state=state,
        executor=None,
        message_queue=None
    )
    
    # 等待一小段时间确保过期
    import time
    time.sleep(0.1)
    
    session = manager.get_session(request_id)
    assert session is None  # 应该已过期

def test_cleanup_expired_sessions():
    """测试清理过期会话"""
    manager = SessionManager(timeout_minutes=0)
    state: AgentState = {
        "messages": [],
        "plan_steps": [],
        "current_step": 0,
        "step_results": [],
        "should_continue": True,
        "original_input": "test",
        "context_files": None,
    }
    
    request_id = manager.create_session(
        state=state,
        executor=None,
        message_queue=None
    )
    
    import time
    time.sleep(0.1)
    
    cleaned = manager.cleanup_expired_sessions()
    assert cleaned > 0
    
    session = manager.get_session(request_id)
    assert session is None
```

#### 集成测试：API 端点

创建 `tests/test_user_interaction_api.py`:

```python
"""测试用户交互 API"""
import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

from codebase_driven_agent.main import app
from codebase_driven_agent.api.models import UserReplyRequest
from codebase_driven_agent.agent.session_manager import get_session_manager, SessionInfo

@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)

@pytest.fixture
def mock_session():
    """创建模拟会话"""
    manager = get_session_manager()
    state = {
        "messages": [],
        "plan_steps": [],
        "current_step": 0,
        "step_results": [],
        "should_continue": True,
        "original_input": "test input",
        "context_files": None,
    }
    
    executor = Mock()
    executor._execute_step_node = Mock(return_value={})
    executor._decision_node = Mock(return_value={"should_continue": False})
    executor._should_continue = Mock(return_value="synthesize")
    executor._synthesize_node = Mock(return_value={"final_result": {}})
    
    message_queue = Mock()
    message_queue.put_nowait = Mock()
    
    request_id = manager.create_session(
        state=state,
        executor=executor,
        message_queue=message_queue
    )
    
    return request_id, executor, message_queue

def test_reply_endpoint_success(client, mock_session):
    """测试用户回复端点成功"""
    request_id, executor, message_queue = mock_session
    
    response = client.post(
        "/api/v1/analyze/reply",
        json={
            "request_id": request_id,
            "reply": "这是测试回复"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "回复已收到" in data["message"]

def test_reply_endpoint_invalid_session(client):
    """测试无效会话的回复"""
    invalid_request_id = str(uuid.uuid4())
    
    response = client.post(
        "/api/v1/analyze/reply",
        json={
            "request_id": invalid_request_id,
            "reply": "测试回复"
        }
    )
    
    assert response.status_code == 404
    data = response.json()
    assert "不存在或已过期" in data["detail"]

def test_reply_endpoint_missing_fields(client):
    """测试缺少字段的请求"""
    response = client.post(
        "/api/v1/analyze/reply",
        json={
            "request_id": "test-id"
            # 缺少 reply 字段
        }
    )
    
    assert response.status_code == 422  # Validation error
```

#### 端到端测试：完整交互流程

创建 `tests/test_user_interaction_e2e.py`:

```python
"""端到端测试：完整的用户交互流程"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from codebase_driven_agent.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_full_interaction_flow(client):
    """测试完整的交互流程"""
    # 1. 启动分析（模拟 Agent 请求用户输入）
    # 注意：这需要实际运行 Agent，可能需要 mock LLM 响应
    
    # 2. 模拟收到 user_input_request 事件
    # 3. 用户提交回复
    # 4. 验证 Agent 继续执行
    
    # 这个测试比较复杂，需要：
    # - Mock LLM 响应，让它返回 request_input 动作
    # - 启动 SSE 连接
    # - 监听 user_input_request 事件
    # - 提交回复
    # - 验证后续事件
    
    pass  # 实现细节根据实际需求调整
```

### 方法 3: 使用测试脚本

创建 `scripts/test_user_interaction.py`:

```python
"""用户交互功能测试脚本"""
import requests
import json
import time
import uuid

BASE_URL = "http://localhost:8000"

def test_user_interaction():
    """测试用户交互流程"""
    print("=" * 60)
    print("用户交互功能测试")
    print("=" * 60)
    
    # 1. 启动分析（使用模糊问题触发请求）
    print("\n1. 启动分析...")
    response = requests.post(
        f"{BASE_URL}/api/v1/analyze/stream",
        json={
            "input": "我的代码出错了，帮我看看"  # 模糊问题，可能触发请求
        },
        headers={"Content-Type": "application/json"},
        stream=True
    )
    
    print(f"  状态码: {response.status_code}")
    
    # 2. 监听 SSE 事件
    print("\n2. 监听 SSE 事件...")
    request_id = None
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('event:'):
                event_type = line_str.split(':', 1)[1].strip()
                print(f"  事件类型: {event_type}")
            elif line_str.startswith('data:'):
                data_str = line_str.split(':', 1)[1].strip()
                try:
                    data = json.loads(data_str)
                    if 'request_id' in data:
                        request_id = data['request_id']
                        print(f"  收到用户输入请求:")
                        print(f"    Request ID: {request_id}")
                        print(f"    问题: {data.get('question', 'N/A')}")
                        print(f"    上下文: {data.get('context', 'N/A')}")
                        break
                except json.JSONDecodeError:
                    pass
    
    if not request_id:
        print("  ⚠️  未收到 user_input_request 事件")
        print("  提示: Agent 可能不需要用户输入，或者需要修改 prompt 来强制触发")
        return
    
    # 3. 提交用户回复
    print(f"\n3. 提交用户回复...")
    reply_response = requests.post(
        f"{BASE_URL}/api/v1/analyze/reply",
        json={
            "request_id": request_id,
            "reply": "错误信息是 FileNotFoundError: config.json not found"
        },
        headers={"Content-Type": "application/json"}
    )
    
    print(f"  状态码: {reply_response.status_code}")
    if reply_response.status_code == 200:
        result = reply_response.json()
        print(f"  响应: {result.get('message', 'N/A')}")
        print("  ✅ 用户回复提交成功")
    else:
        print(f"  ❌ 用户回复提交失败: {reply_response.text}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_user_interaction()
```

运行测试脚本：

```bash
python scripts/test_user_interaction.py
```

## 测试检查清单

- [ ] **会话管理**
  - [ ] 创建会话成功
  - [ ] 获取会话成功
  - [ ] 会话过期清理
  - [ ] 多个会话独立管理

- [ ] **SSE 事件**
  - [ ] `user_input_request` 事件正确发送
  - [ ] 事件包含所有必需字段（request_id, question, context）
  - [ ] 前端正确接收和解析事件

- [ ] **API 端点**
  - [ ] `POST /api/v1/analyze/reply` 端点存在
  - [ ] 验证 request_id 有效性
  - [ ] 用户回复正确添加到消息历史
  - [ ] Agent 正确恢复执行

- [ ] **前端 UI**
  - [ ] Agent 询问正确显示
  - [ ] 输入框可用
  - [ ] 提交按钮可用
  - [ ] 用户回复正确显示
  - [ ] 错误处理正确

- [ ] **完整流程**
  - [ ] Agent 请求用户输入
  - [ ] 用户提交回复
  - [ ] Agent 继续执行
  - [ ] 支持多次交互

## 调试技巧

1. **查看后端日志**
   ```bash
   # 查看 GraphExecutor 日志
   tail -f logs/codebase_driven_agent.agent.graph_executor.log
   
   # 查看 API 日志
   tail -f logs/codebase_driven_agent.api.log
   ```

2. **查看前端控制台**
   - 打开浏览器开发者工具
   - 查看 Console 标签页
   - 查找 `[App] User input request received` 日志

3. **检查会话状态**
   ```python
   from codebase_driven_agent.agent.session_manager import get_session_manager
   
   manager = get_session_manager()
   sessions = manager.get_all_sessions()
   print(f"当前活跃会话数: {len(sessions)}")
   for req_id, session in sessions.items():
       print(f"  {req_id}: {session.created_at}")
   ```

4. **强制触发请求（用于测试）**
   
   临时修改 `_build_adjustment_plan_prompt`，在 prompt 开头添加：
   ```python
   prompt = f"""**测试指令：请在第1步后请求用户输入，询问"请提供具体的错误信息或日志"**
   
   你是一个智能分析 Agent...
   ```

## 常见问题

**Q: Agent 不请求用户输入？**
A: Agent 只在认为信息不足时才会请求。可以：
- 使用更模糊的问题描述
- 临时修改 prompt 强制请求（仅用于测试）

**Q: 用户回复后 Agent 不继续执行？**
A: 检查：
- 会话是否过期
- 后端日志是否有错误
- message_queue 是否正确传递

**Q: 前端不显示询问框？**
A: 检查：
- SSE 事件是否正确接收
- `handleUserInputRequest` 是否正确调用
- `UserInputRequest` 组件是否正确渲染
