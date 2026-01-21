"""测试网络搜索工具"""
import pytest
from unittest.mock import Mock, patch
from codebase_driven_agent.tools.websearch_tool import WebSearchTool, WebSearchToolInput
from codebase_driven_agent.tools.base import ToolResult


@pytest.fixture
def websearch_tool():
    """创建 WebSearchTool 实例"""
    return WebSearchTool()


@patch('codebase_driven_agent.tools.websearch_tool.httpx')
@patch('codebase_driven_agent.tools.websearch_tool.HTTPX_AVAILABLE', True)
def test_websearch_success(mock_httpx, websearch_tool, monkeypatch):
    """测试成功搜索"""
    # Mock httpx Client
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {
                "title": "Test Result 1",
                "url": "https://example.com/1",
                "snippet": "This is a test snippet"
            },
            {
                "title": "Test Result 2",
                "url": "https://example.com/2",
                "snippet": "Another test snippet"
            }
        ]
    }
    mock_response.raise_for_status = Mock()
    mock_client.__enter__.return_value.post.return_value = mock_response
    mock_httpx.Client.return_value = mock_client
    
    # 设置 API Key
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    from codebase_driven_agent.config import settings
    settings.exa_api_key = "test-key"
    
    result = websearch_tool._execute("test query")
    
    assert result.success is True
    assert "Test Result 1" in result.data
    assert "https://example.com/1" in result.data


def test_websearch_no_api_key(websearch_tool, monkeypatch):
    """测试没有 API Key"""
    # 清除 API Key
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    from codebase_driven_agent.config import settings
    settings.exa_api_key = None
    
    result = websearch_tool._execute("test query")
    
    assert result.success is False
    assert "API Key" in result.error or "配置" in result.error


@patch('codebase_driven_agent.tools.websearch_tool.httpx')
@patch('codebase_driven_agent.tools.websearch_tool.HTTPX_AVAILABLE', True)
def test_websearch_max_results(mock_httpx, websearch_tool, monkeypatch):
    """测试限制结果数量"""
    # Mock 返回多个结果
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {"title": f"Result {i}", "url": f"https://example.com/{i}", "snippet": f"Snippet {i}"}
            for i in range(20)
        ]
    }
    mock_response.raise_for_status = Mock()
    mock_client.__enter__.return_value.post.return_value = mock_response
    mock_httpx.Client.return_value = mock_client
    
    monkeypatch.setenv("EXA_API_KEY", "test-key")
    from codebase_driven_agent.config import settings
    settings.exa_api_key = "test-key"
    
    result = websearch_tool._execute("test query", max_results=5)
    
    assert result.success is True
    # 应该只返回前 5 个结果
    assert result.data.count("Result") <= 5
