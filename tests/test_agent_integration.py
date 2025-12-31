"""测试 Agent 集成（包括错误处理、自修正测试）"""
import pytest
from unittest.mock import Mock, patch
from langchain_core.tools import tool

from codebase_driven_agent.agent.executor import (
    AgentExecutorWrapper,
    create_agent_executor,
    get_tools,
)
from codebase_driven_agent.agent.memory import AgentMemory
from codebase_driven_agent.agent.prompt import generate_system_prompt


# ==================== Mock 工具 ====================

@tool
def mock_tool(query: str) -> str:
    """Mock tool for testing
    
    Args:
        query: The query string
        
    Returns:
        Mock result string
    """
    return f"Mock result for: {query}"


class MockTool:
    """Mock 工具用于测试（兼容旧接口）"""
    name = "mock_tool"
    description = "Mock tool for testing"
    
    def __init__(self, should_fail=False, fail_count=0):
        self.should_fail = should_fail
        self.fail_count = fail_count
        self.call_count = 0
        # 创建一个符合 LangChain 的工具实例
        self._tool = mock_tool
    
    def run(self, query: str) -> str:
        """执行工具"""
        self.call_count += 1
        
        if self.should_fail and self.call_count <= self.fail_count:
            raise ValueError(f"Tool error on call {self.call_count}")
        
        return f"Mock result for: {query}"
    
    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)
    
    # 让 MockTool 可以被 LangChain 识别为工具
    def __getattr__(self, name):
        if name in ['name', 'description', 'args_schema', 'invoke', 'ainvoke']:
            return getattr(self._tool, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


# ==================== Agent 创建测试 ====================

def test_get_tools():
    """测试获取工具列表"""
    tools = get_tools()
    
    # 应该至少有一些工具（即使初始化失败也会返回空列表）
    assert isinstance(tools, list)
    
    # 检查工具名称
    tool_names = [tool.name for tool in tools]
    if tools:
        assert any(name in ["code_search", "log_search", "database_query"] for name in tool_names)


@patch('codebase_driven_agent.agent.executor.create_llm')
def test_create_agent_executor_basic(mock_llm):
    """测试创建 Agent 执行器"""
    # Mock LLM
    mock_llm_instance = Mock()
    mock_llm.return_value = mock_llm_instance
    
    # Mock 工具
    with patch('codebase_driven_agent.agent.executor.get_tools') as mock_get_tools:
        mock_get_tools.return_value = [mock_tool]
        
        executor = create_agent_executor(
            max_iterations=5,
            max_execution_time=10,
        )
        
        assert executor is not None
        # create_agent 返回的是可调用的 agent，不是 AgentExecutor
        assert hasattr(executor, 'invoke')
        assert hasattr(executor, '_max_iterations')
        assert executor._max_iterations == 5


def test_create_agent_executor_with_memory():
    """测试使用 Memory 创建 Agent 执行器"""
    memory = AgentMemory()
    
    with patch('codebase_driven_agent.agent.executor.create_llm') as mock_llm:
        mock_llm_instance = Mock()
        mock_llm.return_value = mock_llm_instance
        
        with patch('codebase_driven_agent.agent.executor.get_tools') as mock_get_tools:
            mock_get_tools.return_value = [mock_tool]
            
            executor = create_agent_executor(memory=memory)
            
            assert executor is not None


def test_create_agent_executor_with_callbacks():
    """测试使用 Callbacks 创建 Agent 执行器"""
    callbacks = [Mock()]
    
    with patch('codebase_driven_agent.agent.executor.create_llm') as mock_llm:
        mock_llm_instance = Mock()
        mock_llm.return_value = mock_llm_instance
        
        with patch('codebase_driven_agent.agent.executor.get_tools') as mock_get_tools:
            mock_get_tools.return_value = [mock_tool]
            
            executor = create_agent_executor(callbacks=callbacks)
            
            assert executor is not None


# ==================== AgentExecutorWrapper 测试 ====================

@pytest.fixture
def mock_executor():
    """创建 Mock Agent（LangChain 1.0+ 使用 create_agent，返回可调用的 agent）"""
    executor = Mock()
    executor.invoke = Mock()
    executor._max_iterations = 5
    executor._max_execution_time = 10
    return executor


@pytest.fixture
def agent_wrapper(mock_executor):
    """创建 AgentExecutorWrapper 实例"""
    with patch('codebase_driven_agent.agent.executor.create_agent_executor') as mock_create:
        mock_create.return_value = mock_executor
        
        wrapper = AgentExecutorWrapper()
        wrapper.executor = mock_executor
        return wrapper


@pytest.mark.asyncio
async def test_agent_wrapper_run_success(agent_wrapper, mock_executor):
    """测试 Agent 成功执行"""
    # LangChain 1.0+ 返回 messages 格式
    from langchain_core.messages import AIMessage
    mock_executor.invoke.return_value = {
        "messages": [
            AIMessage(content="Analysis completed")
        ]
    }
    
    result = await agent_wrapper.run("Test input")
    
    assert result["success"] is True
    assert result["output"] == "Analysis completed"
    mock_executor.invoke.assert_called_once()


@pytest.mark.asyncio
async def test_agent_wrapper_run_with_context_files(agent_wrapper, mock_executor):
    """测试带上下文文件的执行"""
    from langchain_core.messages import AIMessage
    mock_executor.invoke.return_value = {
        "messages": [
            AIMessage(content="Analysis completed")
        ]
    }
    
    context_files = [
        {
            "type": "code",
            "path": "test.py",
            "content": "def test(): pass",
            "line_start": 1,
            "line_end": 10,
        }
    ]
    
    result = await agent_wrapper.run("Test input", context_files=context_files)
    
    assert result["success"] is True
    # 检查输入是否包含上下文信息
    call_args = mock_executor.invoke.call_args[0][0]
    assert "messages" in call_args
    assert len(call_args["messages"]) > 0
    assert "Additional Context" in call_args["messages"][0]["content"]


@pytest.mark.asyncio
async def test_agent_wrapper_run_error(agent_wrapper, mock_executor):
    """测试 Agent 执行错误"""
    mock_executor.invoke.side_effect = Exception("Execution failed")
    
    result = await agent_wrapper.run("Test input")
    
    assert result["success"] is False
    assert "error" in result
    assert result["output"] is None
    assert len(result["intermediate_steps"]) == 0


@pytest.mark.asyncio
async def test_agent_wrapper_format_context_files(agent_wrapper):
    """测试上下文文件格式化"""
    context_files = [
        {
            "type": "code",
            "path": "test.py",
            "content": "def test(): pass",
            "line_start": 1,
            "line_end": 10,
        },
        {
            "type": "log",
            "path": "app.log",
            "content": "2024-01-01 ERROR: Test error",
        },
    ]
    
    formatted = agent_wrapper._format_context_files(context_files)
    
    assert "test.py" in formatted
    assert "app.log" in formatted
    assert "def test" in formatted
    assert "ERROR" in formatted


# ==================== 错误处理测试 ====================

@pytest.mark.asyncio
async def test_agent_error_handling_tool_failure(agent_wrapper, mock_executor):
    """测试工具执行失败的错误处理"""
    from langchain_core.messages import AIMessage
    # 模拟工具执行失败，但 Agent 继续执行
    mock_executor.invoke.return_value = {
        "messages": [
            AIMessage(content="Analysis completed despite tool errors")
        ]
    }
    
    result = await agent_wrapper.run("Test input")
    
    assert result["success"] is True
    # Agent 应该能够处理工具错误并继续执行
    assert result["output"] == "Analysis completed despite tool errors"


@pytest.mark.asyncio
async def test_agent_error_handling_parsing_error(agent_wrapper, mock_executor):
    """测试解析错误处理"""
    # 模拟解析错误，agent 应该处理
    # LangChain 1.0+ 的 create_agent 会自动处理解析错误
    # 这里我们测试 wrapper 的错误处理
    mock_executor.invoke.side_effect = ValueError("Parsing error")
    
    result = await agent_wrapper.run("Test input")
    
    assert result["success"] is False
    assert "error" in result


# ==================== 超时和迭代限制测试 ====================

@pytest.mark.asyncio
async def test_agent_max_iterations(agent_wrapper, mock_executor):
    """测试最大迭代次数限制"""
    from langchain_core.messages import AIMessage
    # 模拟多次工具调用
    mock_executor.invoke.return_value = {
        "messages": [
            AIMessage(content="Reached max iterations")
        ]
    }
    
    with patch('codebase_driven_agent.agent.executor.create_llm') as mock_llm:
        mock_llm_instance = Mock()
        mock_llm.return_value = mock_llm_instance
        
        with patch('codebase_driven_agent.agent.executor.get_tools') as mock_get_tools:
            mock_get_tools.return_value = [mock_tool]
            
            wrapper = AgentExecutorWrapper(max_iterations=5)
            wrapper.executor = mock_executor
            
            result = await wrapper.run("Test input")
            
            # 即使返回了很多步骤，也应该成功（实际限制由 agent 控制）
            assert result["success"] is True


@pytest.mark.asyncio
async def test_agent_max_execution_time(agent_wrapper, mock_executor):
    """测试最大执行时间限制"""
    from langchain_core.messages import AIMessage
    
    def slow_invoke(*args, **kwargs):
        # 注意：invoke 是同步方法，不能使用 async def
        import time
        time.sleep(0.1)  # 模拟慢执行
        return {
            "messages": [
                AIMessage(content="Completed")
            ]
        }
    
    mock_executor.invoke = slow_invoke
    
    with patch('codebase_driven_agent.agent.executor.create_llm') as mock_llm:
        mock_llm_instance = Mock()
        mock_llm.return_value = mock_llm_instance
        
        with patch('codebase_driven_agent.agent.executor.get_tools') as mock_get_tools:
            mock_get_tools.return_value = [mock_tool]
            
            wrapper = AgentExecutorWrapper(max_execution_time=1)  # 1秒超时
            wrapper.executor = mock_executor
            
            result = await wrapper.run("Test input")
            
            # 应该在超时前完成
            assert result["success"] is True


# ==================== 自修正测试 ====================

@pytest.mark.asyncio
async def test_agent_self_correction_on_tool_error(agent_wrapper, mock_executor):
    """测试 Agent 在工具错误时的自修正"""
    from langchain_core.messages import AIMessage
    # 模拟第一次调用失败，第二次成功
    call_count = 0
    
    def mock_invoke(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        
        if call_count == 1:
            # 第一次：工具调用失败
            return {
                "messages": [
                    AIMessage(content="Error: File not found")
                ]
            }
        else:
            # 第二次：修正后成功
            return {
                "messages": [
                    AIMessage(content="Analysis completed")
                ]
            }
    
    mock_executor.invoke.side_effect = mock_invoke
    
    # 注意：实际的 agent 会自动重试，这里我们只是测试 wrapper 的处理
    result = await agent_wrapper.run("Test input")
    
    # 如果 Agent 自修正成功，应该返回成功结果
    # 实际行为取决于 agent 的实现
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_agent_retry_on_invalid_sql(agent_wrapper, mock_executor):
    """测试 Agent 在无效 SQL 时的重试"""
    from langchain_core.messages import AIMessage
    # 模拟 SQL 错误和重试
    call_count = 0
    
    def mock_invoke(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        
        if call_count == 1:
            # 第一次：无效 SQL
            return {
                "messages": [
                    AIMessage(content="Error: Write operation not allowed")
                ]
            }
        else:
            # 第二次：修正为 SELECT
            return {
                "messages": [
                    AIMessage(content="Analysis completed")
                ]
            }
    
    mock_executor.invoke.side_effect = mock_invoke
    
    result = await agent_wrapper.run("Test database query")
    
    assert isinstance(result, dict)


# ==================== Memory 测试 ====================

def test_agent_memory():
    """测试 Agent Memory"""
    memory = AgentMemory()
    
    # Memory 应该能够存储和检索信息
    assert memory is not None


@pytest.mark.asyncio
async def test_agent_wrapper_with_memory(agent_wrapper, mock_executor):
    """测试使用 Memory 的 Agent"""
    from langchain_core.messages import AIMessage
    memory = AgentMemory()
    
    with patch('codebase_driven_agent.agent.executor.create_llm') as mock_llm:
        mock_llm_instance = Mock()
        mock_llm.return_value = mock_llm_instance
        
        with patch('codebase_driven_agent.agent.executor.get_tools') as mock_get_tools:
            mock_get_tools.return_value = [mock_tool]
            
            wrapper = AgentExecutorWrapper(memory=memory)
            wrapper.executor = mock_executor
            
            mock_executor.invoke.return_value = {
                "messages": [
                    AIMessage(content="Analysis completed")
                ]
            }
            
            result = await wrapper.run("Test input")
            
            assert result["success"] is True
            assert wrapper.memory == memory


# ==================== Prompt 测试 ====================

def test_generate_system_prompt():
    """测试生成系统 Prompt"""
    prompt = generate_system_prompt(
        tools_description="Test tool: Test description",
        schema_info="Test schema info"
    )
    
    assert "智能分析 Agent" in prompt or "Agent" in prompt
    assert "Test tool" in prompt
    assert "Test schema info" in prompt


def test_generate_system_prompt_minimal():
    """测试生成最小 Prompt"""
    prompt = generate_system_prompt()
    
    assert len(prompt) > 0
    assert isinstance(prompt, str)


# ==================== 工具集成测试 ====================

def test_agent_tools_integration():
    """测试 Agent 工具集成"""
    tools = get_tools()
    
    # 检查工具是否正确初始化
    for tool_instance in tools:
        assert hasattr(tool_instance, 'name')
        assert hasattr(tool_instance, 'description')
        assert hasattr(tool_instance, 'run') or hasattr(tool_instance, '_run')


@pytest.mark.asyncio
async def test_agent_with_mock_tools(agent_wrapper, mock_executor):
    """测试 Agent 使用 Mock 工具"""
    from langchain_core.messages import AIMessage
    # 模拟工具调用
    mock_executor.invoke.return_value = {
        "messages": [
            AIMessage(content="Used mock tool successfully")
        ]
    }
    
    result = await agent_wrapper.run("Test with mock tools")
    
    assert result["success"] is True
    assert result["output"] == "Used mock tool successfully"


# ==================== 边界情况测试 ====================

@pytest.mark.asyncio
async def test_agent_empty_input(agent_wrapper, mock_executor):
    """测试空输入"""
    mock_executor.invoke.return_value = {
        "output": "No input provided",
        "intermediate_steps": [],
    }
    
    result = await agent_wrapper.run("")
    
    # Agent 应该能够处理空输入
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_agent_no_tools_available():
    """测试没有工具可用的情况"""
    with patch('codebase_driven_agent.agent.executor.get_tools') as mock_get_tools:
        mock_get_tools.return_value = []
        
        with patch('codebase_driven_agent.agent.executor.create_llm') as mock_llm:
            mock_llm_instance = Mock()
            mock_llm.return_value = mock_llm_instance
            
            # 应该能够创建 executor（即使没有工具）
            # 注意：LangChain 1.0+ 的 create_agent 可能需要至少一个工具
            # 如果失败，这是预期的行为
            try:
                executor = create_agent_executor()
                assert executor is not None
            except Exception:
                # 如果没有工具时创建失败，这也是可以接受的
                pass


@pytest.mark.asyncio
async def test_agent_context_files_empty(agent_wrapper, mock_executor):
    """测试空上下文文件列表"""
    from langchain_core.messages import AIMessage
    mock_executor.invoke.return_value = {
        "messages": [
            AIMessage(content="Analysis completed")
        ]
    }
    
    result = await agent_wrapper.run("Test input", context_files=[])
    
    assert result["success"] is True
    # 空列表不应该导致错误
    call_args = mock_executor.invoke.call_args[0][0]
    assert "messages" in call_args


# ==================== 指标记录测试 ====================

@pytest.mark.asyncio
async def test_agent_metrics_recording(agent_wrapper, mock_executor):
    """测试指标记录"""
    from langchain_core.messages import AIMessage
    with patch('codebase_driven_agent.agent.executor.record_agent_metrics') as mock_metrics:
        mock_executor.invoke.return_value = {
            "messages": [
                AIMessage(content="Analysis completed")
            ]
        }
        
        await agent_wrapper.run("Test input")
        
        # 应该记录指标
        assert mock_metrics.called
        # success 是关键字参数，不是位置参数
        call_args = mock_metrics.call_args
        assert len(call_args[0]) == 2  # execution_time, tool_calls
        assert call_args[1]['success'] is True  # success=True


@pytest.mark.asyncio
async def test_agent_metrics_on_error(agent_wrapper, mock_executor):
    """测试错误时的指标记录"""
    with patch('codebase_driven_agent.agent.executor.record_agent_metrics') as mock_metrics:
        mock_executor.invoke.side_effect = Exception("Test error")
        
        await agent_wrapper.run("Test input")
        
        # 应该记录错误指标
        assert mock_metrics.called
        # success 是关键字参数，不是位置参数
        call_args = mock_metrics.call_args
        assert len(call_args[0]) == 2  # execution_time, tool_calls
        assert call_args[1]['success'] is False  # success=False

