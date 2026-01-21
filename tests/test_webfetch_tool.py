"""测试网页获取工具"""
import pytest
from unittest.mock import Mock, patch
from codebase_driven_agent.tools.webfetch_tool import WebFetchTool, WebFetchToolInput
from codebase_driven_agent.tools.base import ToolResult


@pytest.fixture
def webfetch_tool():
    """创建 WebFetchTool 实例"""
    return WebFetchTool()


@patch('codebase_driven_agent.tools.webfetch_tool.httpx')
@patch('codebase_driven_agent.tools.webfetch_tool.HTTPX_AVAILABLE', True)
def test_webfetch_success_httpx(mock_httpx, webfetch_tool):
    """测试成功获取网页（使用 httpx）"""
    # Mock httpx Client
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<html><body><h1>Test</h1><p>Content</p></body></html>"
    mock_response.headers = {"Content-Type": "text/html"}
    mock_client.__enter__.return_value.get.return_value = mock_response
    mock_httpx.Client.return_value = mock_client
    
    result = webfetch_tool._execute("https://example.com")
    
    assert result.success is True
    assert "Test" in result.data
    assert "Content" in result.data


def test_webfetch_invalid_url(webfetch_tool):
    """测试无效 URL"""
    result = webfetch_tool._execute("not-a-valid-url")
    
    assert result.success is False
    assert "无效的 URL" in result.error or "必须以 http" in result.error


@patch('codebase_driven_agent.tools.webfetch_tool.httpx')
@patch('codebase_driven_agent.tools.webfetch_tool.HTTPX_AVAILABLE', True)
def test_webfetch_text_extraction(mock_httpx, webfetch_tool):
    """测试文本提取"""
    html_content = """
    <html>
    <head><title>Test Page</title></head>
    <body>
        <h1>Heading</h1>
        <p>Paragraph with <strong>bold</strong> text.</p>
        <script>console.log('ignore');</script>
    </body>
    </html>
    """
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = html_content
    mock_response.headers = {"Content-Type": "text/html"}
    mock_client.__enter__.return_value.get.return_value = mock_response
    mock_httpx.Client.return_value = mock_client
    
    result = webfetch_tool._execute("https://example.com")
    
    assert result.success is True
    # 应该提取文本内容，去除 HTML 标签
    assert "Heading" in result.data or "Test Page" in result.data
    assert "Paragraph" in result.data or "bold" in result.data
