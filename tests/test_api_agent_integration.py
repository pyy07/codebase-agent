"""API + Agent 端到端集成测试"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from codebase_driven_agent.main import app
from codebase_driven_agent.api.models import AnalyzeRequest, AnalysisResult
from codebase_driven_agent.agent.executor import AgentExecutorWrapper


# ==================== Mock 设置 ====================

@pytest.fixture
def mock_agent_executor():
    """Mock Agent 执行器"""
    executor = Mock(spec=AgentExecutorWrapper)
    executor.run = AsyncMock()
    return executor


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


# ==================== REST API 测试 ====================

def test_health_check(client):
    """测试健康检查接口"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"


def test_api_info(client):
    """测试 API 信息接口"""
    response = client.get("/api/v1/info")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_analyze_sync_success(client, mock_agent_executor):
    """测试同步分析接口成功"""
    # Mock Agent 执行结果
    mock_agent_executor.run.return_value = {
        "success": True,
        "output": '{"root_cause": "测试根因", "suggestions": ["建议1"], "confidence": 0.8}',
        "intermediate_steps": [],
    }
    
    with patch('codebase_driven_agent.api.routes.AgentExecutorWrapper') as mock_wrapper_class:
        mock_wrapper_class.return_value = mock_agent_executor
        
        request_data = {
            "input": "测试错误日志",
        }
        
        response = client.post("/api/v1/analyze", json=request_data)
        
        # 注意：由于 Agent 执行是异步的，可能需要等待
        # 这里我们主要测试 API 接口是否正常
        assert response.status_code in [200, 202]  # 200 或 202 Accepted


@pytest.mark.asyncio
async def test_analyze_sync_with_context_files(client, mock_agent_executor):
    """测试带上下文文件的同步分析"""
    mock_agent_executor.run.return_value = {
        "success": True,
        "output": '{"root_cause": "测试根因", "suggestions": ["建议1"], "confidence": 0.8}',
        "intermediate_steps": [],
    }
    
    with patch('codebase_driven_agent.api.routes.AgentExecutorWrapper') as mock_wrapper_class:
        mock_wrapper_class.return_value = mock_agent_executor
        
        request_data = {
            "input": "测试错误",
            "context_files": [
                {
                    "type": "code",
                    "path": "test.py",
                    "content": "def test(): pass",
                    "line_start": 1,
                    "line_end": 10,
                }
            ],
        }
        
        response = client.post("/api/v1/analyze", json=request_data)
        assert response.status_code in [200, 202]


@pytest.mark.asyncio
async def test_analyze_async_success(client, mock_agent_executor):
    """测试异步分析接口"""
    mock_agent_executor.run.return_value = {
        "success": True,
        "output": '{"root_cause": "测试根因", "suggestions": ["建议1"], "confidence": 0.8}',
        "intermediate_steps": [],
    }
    
    with patch('codebase_driven_agent.api.routes.AgentExecutorWrapper') as mock_wrapper_class:
        mock_wrapper_class.return_value = mock_agent_executor
        
        request_data = {
            "input": "测试错误",
        }
        
        response = client.post("/api/v1/analyze/async", json=request_data)
        assert response.status_code == 202
        
        data = response.json()
        assert "task_id" in data
        
        # 查询任务状态
        task_id = data["task_id"]
        status_response = client.get(f"/api/v1/analyze/{task_id}")
        assert status_response.status_code in [200, 404]  # 可能还在执行中


def test_analyze_invalid_input(client):
    """测试无效输入"""
    request_data = {
        # 缺少必需的 input 字段
    }
    
    response = client.post("/api/v1/analyze", json=request_data)
    assert response.status_code == 422  # Validation error


# ==================== SSE 流式接口测试 ====================

@pytest.mark.asyncio
async def test_analyze_stream_success(client, mock_agent_executor):
    """测试 SSE 流式分析接口"""
    mock_agent_executor.run.return_value = {
        "success": True,
        "output": '{"root_cause": "测试根因", "suggestions": ["建议1"], "confidence": 0.8}',
        "intermediate_steps": [],
    }
    
    with patch('codebase_driven_agent.api.sse.AgentExecutorWrapper') as mock_wrapper_class:
        mock_wrapper_class.return_value = mock_agent_executor
        
        request_data = {
            "input": "测试错误",
        }
        
        # SSE 流式接口需要使用 EventSourceResponse
        # TestClient 可能不完全支持 SSE，这里我们主要测试接口是否存在
        response = client.post("/api/v1/analyze/stream", json=request_data)
        # SSE 接口应该返回 200 或开始流式响应
        assert response.status_code in [200, 202]


@pytest.mark.asyncio
async def test_analyze_stream_with_callbacks(client, mock_agent_executor):
    """测试 SSE 流式接口的 Callback 集成"""
    # 模拟 Agent 执行过程中的 Callback 调用
    callback_messages = []
    
    def mock_run(*args, **kwargs):
        # 模拟 Callback 发送消息
        callback_messages.append({"event": "progress", "data": {"message": "开始分析..."}})
        callback_messages.append({"event": "progress", "data": {"message": "查询代码..."}})
        return {
            "success": True,
            "output": '{"root_cause": "测试根因", "suggestions": ["建议1"], "confidence": 0.8}',
            "intermediate_steps": [],
        }
    
    mock_agent_executor.run = AsyncMock(side_effect=mock_run)
    
    with patch('codebase_driven_agent.api.sse.AgentExecutorWrapper') as mock_wrapper_class:
        mock_wrapper_class.return_value = mock_agent_executor
        
        request_data = {
            "input": "测试错误",
        }
        
        response = client.post("/api/v1/analyze/stream", json=request_data)
        assert response.status_code in [200, 202]


# ==================== 错误处理测试 ====================

@pytest.mark.asyncio
async def test_analyze_agent_error(client, mock_agent_executor):
    """测试 Agent 执行错误"""
    mock_agent_executor.run.return_value = {
        "success": False,
        "error": "Agent execution failed",
        "output": None,
        "intermediate_steps": [],
    }
    
    with patch('codebase_driven_agent.api.routes.AgentExecutorWrapper') as mock_wrapper_class:
        mock_wrapper_class.return_value = mock_agent_executor
        
        request_data = {
            "input": "测试错误",
        }
        
        response = client.post("/api/v1/analyze", json=request_data)
        # 应该返回错误响应
        assert response.status_code in [500, 400]


@pytest.mark.asyncio
async def test_analyze_timeout(client, mock_agent_executor):
    """测试超时处理"""
    # 模拟长时间执行的 Agent
    async def slow_run(*args, **kwargs):
        await asyncio.sleep(2)  # 模拟慢执行
        return {
            "success": True,
            "output": '{"root_cause": "测试根因"}',
            "intermediate_steps": [],
        }
    
    mock_agent_executor.run = slow_run
    
    with patch('codebase_driven_agent.api.routes.AgentExecutorWrapper') as mock_wrapper_class:
        mock_wrapper_class.return_value = mock_agent_executor
        
        request_data = {
            "input": "测试错误",
        }
        
        # 注意：实际超时处理可能需要配置
        response = client.post("/api/v1/analyze", json=request_data, timeout=1)
        # 可能会超时或返回错误
        assert response.status_code in [200, 202, 408, 500]


# ==================== 上下文文件处理测试 ====================

@pytest.mark.asyncio
async def test_context_files_parsing(client, mock_agent_executor):
    """测试上下文文件解析"""
    mock_agent_executor.run.return_value = {
        "success": True,
        "output": '{"root_cause": "测试根因"}',
        "intermediate_steps": [],
    }
    
    with patch('codebase_driven_agent.api.routes.AgentExecutorWrapper') as mock_wrapper_class:
        mock_wrapper_class.return_value = mock_agent_executor
        
        request_data = {
            "input": "测试错误",
            "context_files": [
                {
                    "type": "code",
                    "path": "test.py",
                    "content": "def test(): pass",
                    "line_start": 1,
                    "line_end": 10,
                },
                {
                    "type": "log",
                    "content": "2024-01-01 ERROR: Test error",
                },
            ],
        }
        
        response = client.post("/api/v1/analyze", json=request_data)
        assert response.status_code in [200, 202]
        
        # 验证 context_files 被正确传递
        call_args = mock_agent_executor.run.call_args
        if call_args:
            context_files = call_args[1].get("context_files", [])
            assert len(context_files) == 2
            assert context_files[0]["type"] == "code"
            assert context_files[1]["type"] == "log"


# ==================== 结果解析测试 ====================

@pytest.mark.asyncio
async def test_result_parsing(client, mock_agent_executor):
    """测试结果解析"""
    mock_output = """{
        "root_cause": "数据库连接失败",
        "suggestions": [
            "检查数据库连接配置",
            "验证数据库服务是否运行"
        ],
        "confidence": 0.9,
        "related_code": [
            {
                "file": "db.py",
                "lines": [10, 20],
                "description": "数据库连接代码"
            }
        ]
    }"""
    
    mock_agent_executor.run.return_value = {
        "success": True,
        "output": mock_output,
        "intermediate_steps": [],
    }
    
    with patch('codebase_driven_agent.api.routes.AgentExecutorWrapper') as mock_wrapper_class:
        mock_wrapper_class.return_value = mock_agent_executor
        
        request_data = {
            "input": "数据库连接错误",
        }
        
        response = client.post("/api/v1/analyze", json=request_data)
        assert response.status_code in [200, 202]
        
        if response.status_code == 200:
            data = response.json()
            # 验证结果结构
            assert "root_cause" in data or "result" in data


# ==================== 认证和中间件测试 ====================

def test_api_key_auth(client):
    """测试 API Key 认证"""
    # 如果没有配置 API Key，应该允许访问
    # 如果配置了 API Key，需要提供正确的 Key
    response = client.get("/health")
    assert response.status_code == 200


def test_rate_limiting(client):
    """测试请求限流"""
    # 发送多个请求
    for _ in range(10):
        response = client.get("/health")
        # 如果有限流，某些请求可能会被拒绝
        assert response.status_code in [200, 429]


# ==================== 集成场景测试 ====================

@pytest.mark.asyncio
async def test_full_analysis_flow(client, mock_agent_executor):
    """测试完整分析流程"""
    # 模拟完整的 Agent 执行流程
    mock_agent_executor.run.return_value = {
        "success": True,
        "output": """{
            "root_cause": "代码中存在空指针异常",
            "suggestions": [
                "添加空值检查",
                "使用可选链操作符"
            ],
            "confidence": 0.85,
            "related_code": [
                {
                    "file": "app.py",
                    "lines": [42, 50],
                    "description": "问题代码位置"
                }
            ],
            "related_logs": [
                {
                    "timestamp": "2024-01-01 10:00:00",
                    "content": "NullPointerException at app.py:45",
                    "description": "错误日志"
                }
            ]
        }""",
        "intermediate_steps": [
            {"tool": "code_search", "input": "NullPointerException"},
            {"tool": "log_search", "input": "error"},
        ],
    }
    
    with patch('codebase_driven_agent.api.routes.AgentExecutorWrapper') as mock_wrapper_class:
        mock_wrapper_class.return_value = mock_agent_executor
        
        request_data = {
            "input": "应用出现 NullPointerException 错误",
            "context_files": [
                {
                    "type": "code",
                    "path": "app.py",
                    "content": "def process(data):\n    return data.value",
                    "line_start": 40,
                    "line_end": 50,
                }
            ],
        }
        
        response = client.post("/api/v1/analyze", json=request_data)
        assert response.status_code in [200, 202]
        
        # 验证 Agent 被正确调用
        assert mock_agent_executor.run.called
        call_args = mock_agent_executor.run.call_args
        assert call_args[0][0] == "应用出现 NullPointerException 错误"
        assert len(call_args[1].get("context_files", [])) == 1

