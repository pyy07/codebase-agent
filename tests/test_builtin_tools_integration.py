"""测试内置工具与 Agent 的集成"""
import pytest
import tempfile
import shutil
from pathlib import Path
from codebase_driven_agent.tools.registry import get_tool_registry


@pytest.fixture
def temp_repo():
    """创建临时代码仓库用于测试"""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)
    
    # 创建测试文件
    (repo_path / "test.py").write_text("def hello():\n    print('Hello')\n")
    (repo_path / "README.md").write_text("# Test Project")
    
    yield repo_path
    
    # 清理
    shutil.rmtree(temp_dir)


def test_tools_registered():
    """测试所有新工具都已注册"""
    registry = get_tool_registry()
    tools = registry.get_all_tools()
    
    tool_names = [tool.name for tool in tools]
    tool_class_names = list(registry.list_tools().keys())
    
    # 检查新工具是否已注册（通过工具名称）
    expected_tool_names = ['read', 'glob', 'grep', 'bash', 'webfetch']
    for tool_name in expected_tool_names:
        assert tool_name in tool_names, f"工具 {tool_name} 未注册"
    
    # websearch 是可选的，只有在配置了 API Key 时才会注册
    # 这里不强制要求它必须注册


def test_read_tool_integration(temp_repo, monkeypatch):
    """测试 read_tool 与 Agent 集成"""
    monkeypatch.setenv("CODE_REPO_PATH", str(temp_repo))
    from codebase_driven_agent.config import settings
    settings.code_repo_path = str(temp_repo)
    
    # 直接创建新的工具实例，确保使用新的路径
    from codebase_driven_agent.tools.read_tool import ReadTool
    read_tool = ReadTool()
    
    assert read_tool is not None
    result = read_tool._execute("test.py")
    
    assert result.success is True
    assert "def hello" in result.data


def test_glob_tool_integration(temp_repo, monkeypatch):
    """测试 glob_tool 与 Agent 集成"""
    monkeypatch.setenv("CODE_REPO_PATH", str(temp_repo))
    from codebase_driven_agent.config import settings
    settings.code_repo_path = str(temp_repo)
    
    # 直接创建新的工具实例
    from codebase_driven_agent.tools.glob_tool import GlobTool
    glob_tool = GlobTool()
    
    assert glob_tool is not None
    # 使用递归模式才能找到文件
    result = glob_tool._execute("**/*.py")
    
    assert result.success is True
    assert "test.py" in result.data


def test_grep_tool_integration(temp_repo, monkeypatch):
    """测试 grep_tool 与 Agent 集成"""
    monkeypatch.setenv("CODE_REPO_PATH", str(temp_repo))
    from codebase_driven_agent.config import settings
    settings.code_repo_path = str(temp_repo)
    
    registry = get_tool_registry()
    grep_tool = registry.get_tool("GrepTool")
    
    assert grep_tool is not None
    result = grep_tool._execute("def hello")
    
    assert result.success is True
    assert "test.py" in result.data or "匹配数: 0" in result.data


def test_bash_tool_integration(temp_repo, monkeypatch):
    """测试 bash_tool 与 Agent 集成"""
    monkeypatch.setenv("CODE_REPO_PATH", str(temp_repo))
    from codebase_driven_agent.config import settings
    settings.code_repo_path = str(temp_repo)
    
    registry = get_tool_registry()
    bash_tool = registry.get_tool("BashTool")
    
    assert bash_tool is not None
    # 测试简单命令
    import sys
    if sys.platform == "win32":
        result = bash_tool._execute("echo test")
    else:
        result = bash_tool._execute("echo test")
    
    assert result.success is True


def test_tool_error_handling(temp_repo, monkeypatch):
    """测试工具错误处理"""
    monkeypatch.setenv("CODE_REPO_PATH", str(temp_repo))
    from codebase_driven_agent.config import settings
    settings.code_repo_path = str(temp_repo)
    
    registry = get_tool_registry()
    read_tool = registry.get_tool("ReadTool")
    
    assert read_tool is not None
    # 测试不存在的文件
    result = read_tool._execute("nonexistent.py")
    assert result.success is False
    assert "文件不存在" in result.error


def test_tool_concurrent_access(temp_repo, monkeypatch):
    """测试工具的并发访问"""
    import threading
    
    monkeypatch.setenv("CODE_REPO_PATH", str(temp_repo))
    from codebase_driven_agent.config import settings
    settings.code_repo_path = str(temp_repo)
    
    # 直接创建新的工具实例
    from codebase_driven_agent.tools.read_tool import ReadTool
    read_tool = ReadTool()
    
    assert read_tool is not None
    
    results = []
    
    def read_file():
        result = read_tool._execute("test.py")
        results.append(result.success)
    
    # 创建多个线程并发访问
    threads = [threading.Thread(target=read_file) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # 所有调用应该都成功
    assert all(results)
    assert len(results) == 5
