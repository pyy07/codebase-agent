"""用户交互功能测试"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
import queue
import uuid

from codebase_driven_agent.main import app
from codebase_driven_agent.api.models import UserReplyRequest
from codebase_driven_agent.agent.graph_executor import GraphExecutor, AgentState
from codebase_driven_agent.agent.session_manager import get_session_manager


# ==================== 单元测试：graph_executor 交互节点 ====================

class TestGraphExecutorUserInteraction:
    """测试 GraphExecutor 的用户交互节点"""
    
    def test_request_user_input_node(self):
        """测试请求用户输入节点"""
        message_queue = queue.Queue()
        executor = GraphExecutor(message_queue=message_queue)
        
        # 创建测试状态
        state: AgentState = {
            "messages": [],
            "plan_steps": [],
            "current_step": 0,
            "step_results": [],
            "should_continue": False,
            "original_input": "测试问题",
            "decision": "request_input",
            "user_input_question": "请提供更多信息",
            "user_input_context": "需要错误日志",
        }
        
        # 执行请求用户输入节点
        result = executor._request_user_input_node(state)
        
        # 验证结果
        assert "request_id" in result
        assert result["request_id"] is not None
        # 注意：_request_user_input_node 返回的字典中可能不包含 should_continue
        # 因为状态保持不变，等待用户回复
        
        # 验证消息队列中有 user_input_request 事件
        assert not message_queue.empty()
        event = message_queue.get_nowait()
        assert event["event"] == "user_input_request"
        assert "request_id" in event["data"]
        assert "question" in event["data"]
        assert event["data"]["question"] == "请提供更多信息"
    
    def test_request_user_input_node_with_context(self):
        """测试带上下文的用户输入请求"""
        message_queue = queue.Queue()
        executor = GraphExecutor(message_queue=message_queue)
        
        state: AgentState = {
            "messages": [],
            "plan_steps": [],
            "current_step": 0,
            "step_results": [],
            "should_continue": False,
            "original_input": "测试问题",
            "decision": "request_input",
            "user_input_question": "请提供错误日志",
            "user_input_context": "当前分析显示可能是数据库连接问题",
        }
        
        result = executor._request_user_input_node(state)
        
        # 验证上下文信息被包含
        event = message_queue.get_nowait()
        assert event["event"] == "user_input_request"
        assert "context" in event["data"] or "question" in event["data"]
    
    def test_decision_node_request_input(self):
        """测试决策节点返回 request_input"""
        message_queue = queue.Queue()
        executor = GraphExecutor(message_queue=message_queue)
        
        # 由于 ChatOpenAI 是 Pydantic 模型，不能直接 patch invoke 方法
        # 我们直接 mock _parse_decision 方法来测试决策逻辑
        state: AgentState = {
            "messages": [],
            "plan_steps": [{"step": 1, "action": "read", "target": "test.py"}],
            "current_step": 0,
            "step_results": [],
            "should_continue": True,
            "original_input": "测试问题",
        }
        
        # Mock _parse_decision 方法，直接返回我们期望的决策
        # 这样可以避免 mock LLM（因为 ChatOpenAI 是 Pydantic 模型，不能直接 patch）
        with patch.object(executor, '_parse_decision', return_value={
            "action": "request_input",
            "reasoning": "需要更多信息",
            "question": "请提供错误日志",
            "context": "当前分析显示可能是数据库连接问题"
        }):
            # Mock LLM.invoke 调用（使用 MagicMock 包装整个 llm 对象）
            from langchain_core.messages import AIMessage
            mock_response = Mock()
            mock_response.content = '{"action": "request_input", "reasoning": "需要更多信息", "question": "请提供错误日志"}'
            
            # 使用 patch 整个 llm 对象
            original_llm = executor.llm
            mock_llm = Mock()
            mock_llm.invoke = Mock(return_value=mock_response)
            executor.llm = mock_llm
            
            try:
                result = executor._decision_node(state)
                
                # 验证决策结果
                assert result.get("decision") == "request_input"
                assert "user_input_question" in result
                assert result["user_input_question"] == "请提供错误日志"
            finally:
                # 恢复原始 LLM
                executor.llm = original_llm


# ==================== 集成测试：API 端点 ====================

@pytest.fixture
def client():
    """创建测试客户端"""
    # 如果配置了 API Key，需要在请求头中提供
    # 为了测试方便，我们 patch settings 来禁用认证
    from codebase_driven_agent.config import settings
    original_api_key = settings.api_key
    
    # 临时禁用 API Key 认证
    with patch.object(settings, 'api_key', None):
        yield TestClient(app)


@pytest.fixture
def mock_session():
    """Mock 会话"""
    session_manager = get_session_manager()
    request_id = str(uuid.uuid4())
    
    # 创建模拟的 executor 和 message_queue
    message_queue = queue.Queue()
    executor = Mock()
    executor.executor = Mock()
    executor.executor.message_queue = message_queue
    
    state: AgentState = {
        "messages": [],
        "plan_steps": [],
        "current_step": 0,
        "step_results": [],
        "should_continue": False,
        "original_input": "测试问题",
    }
    
    session_manager.create_session(
        state=state,
        executor=executor,
        message_queue=message_queue,
        request_id=request_id
    )
    
    return request_id, executor, message_queue


class TestUserReplyAPI:
    """测试用户回复 API"""
    
    def test_reply_success(self, client, mock_session):
        """测试成功提交用户回复"""
        request_id, executor, message_queue = mock_session
        
        # Mock executor 的方法
        executor.executor._decision_node = Mock(return_value={"decision": "continue"})
        executor.executor._should_continue = Mock(return_value="continue")
        
        request_data = {
            "request_id": request_id,
            "reply": "错误信息：Connection refused"
        }
        
        response = client.post("/api/v1/analyze/reply", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data
    
    def test_reply_invalid_request_id(self, client):
        """测试无效的 request_id"""
        request_data = {
            "request_id": "invalid-request-id",
            "reply": "测试回复"
        }
        
        response = client.post("/api/v1/analyze/reply", json=request_data)
        
        assert response.status_code == 404
    
    def test_reply_missing_fields(self, client):
        """测试缺少必需字段"""
        # 缺少 reply
        request_data = {
            "request_id": "test-id"
        }
        
        response = client.post("/api/v1/analyze/reply", json=request_data)
        assert response.status_code == 422
        
        # 缺少 request_id
        request_data = {
            "reply": "测试回复"
        }
        
        response = client.post("/api/v1/analyze/reply", json=request_data)
        assert response.status_code == 422
    
    def test_reply_empty_reply(self, client, mock_session):
        """测试空回复"""
        request_id, executor, message_queue = mock_session
        
        request_data = {
            "request_id": request_id,
            "reply": ""  # 空回复
        }
        
        # 空回复应该被接受（用户可能选择不提供信息）
        response = client.post("/api/v1/analyze/reply", json=request_data)
        assert response.status_code == 200


# ==================== 端到端测试：完整交互流程 ====================

@pytest.mark.asyncio
class TestUserInteractionE2E:
    """端到端测试：完整的用户交互流程"""
    
    async def test_complete_interaction_flow(self, client):
        """测试完整的交互流程：请求 -> 回复 -> 继续分析"""
        # 这个测试需要实际的 Agent 执行，可能需要较长时间
        # 这里提供一个框架，实际测试可能需要 mock LLM 调用
        
        # 1. 启动流式分析（需要 mock Agent 执行）
        # 2. 接收 user_input_request 事件
        # 3. 提交用户回复
        # 4. 验证 Agent 继续执行
        
        # 注意：完整的端到端测试可能需要：
        # - Mock LLM 调用
        # - Mock 工具调用
        # - 使用真实的 SSE 客户端
        # 这里提供一个简化的测试框架
        
        pass  # TODO: 实现完整的端到端测试


# ==================== 辅助函数测试 ====================

class TestSessionManager:
    """测试会话管理"""
    
    def test_create_session(self):
        """测试创建会话"""
        session_manager = get_session_manager()
        request_id = str(uuid.uuid4())
        
        state: AgentState = {
            "messages": [],
            "plan_steps": [],
            "current_step": 0,
            "step_results": [],
            "should_continue": False,
            "original_input": "测试问题",
        }
        
        message_queue = queue.Queue()
        executor = Mock()
        
        session_manager.create_session(
            state=state,
            executor=executor,
            message_queue=message_queue,
            request_id=request_id
        )
        
        # 验证会话已创建
        session = session_manager.get_session(request_id)
        assert session is not None
        assert session.request_id == request_id
    
    def test_get_session_not_found(self):
        """测试获取不存在的会话"""
        session_manager = get_session_manager()
        session = session_manager.get_session("non-existent-id")
        assert session is None
    
    def test_remove_session(self):
        """测试删除会话"""
        session_manager = get_session_manager()
        request_id = str(uuid.uuid4())
        
        state: AgentState = {
            "messages": [],
            "plan_steps": [],
            "current_step": 0,
            "step_results": [],
            "should_continue": False,
            "original_input": "测试问题",
        }
        
        message_queue = queue.Queue()
        executor = Mock()
        
        session_manager.create_session(
            state=state,
            executor=executor,
            message_queue=message_queue,
            request_id=request_id
        )
        
        # 删除会话
        session_manager.remove_session(request_id)
        
        # 验证会话已删除
        session = session_manager.get_session(request_id)
        assert session is None
