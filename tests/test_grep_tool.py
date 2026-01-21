"""测试内容搜索工具"""
import pytest
import tempfile
import shutil
from pathlib import Path
from codebase_driven_agent.tools.grep_tool import GrepTool, GrepToolInput
from codebase_driven_agent.tools.base import ToolResult


@pytest.fixture
def temp_repo():
    """创建临时代码仓库用于测试"""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)
    
    # 创建测试文件
    (repo_path / "main.py").write_text("""def main():
    print("Hello World")
    process_data()

def process_data():
    return True
""")
    
    (repo_path / "utils.py").write_text("""def helper():
    pass

def process_data():
    pass
""")
    
    (repo_path / "config.json").write_text('{"key": "value"}')
    
    yield repo_path
    
    # 清理
    shutil.rmtree(temp_dir)


@pytest.fixture
def grep_tool(temp_repo, monkeypatch):
    """创建 GrepTool 实例"""
    monkeypatch.setenv("CODE_REPO_PATH", str(temp_repo))
    from codebase_driven_agent.config import settings
    settings.code_repo_path = str(temp_repo)
    return GrepTool()


def test_grep_simple_pattern(grep_tool, temp_repo):
    """测试简单模式搜索"""
    result = grep_tool._execute("def main")
    
    assert result.success is True
    assert "main.py" in result.data
    assert "def main" in result.data


def test_grep_multiple_matches(grep_tool, temp_repo):
    """测试多个匹配"""
    result = grep_tool._execute("process_data")
    
    assert result.success is True
    assert "main.py" in result.data
    assert "utils.py" in result.data
    assert "process_data" in result.data


def test_grep_with_include(grep_tool, temp_repo):
    """测试文件类型过滤"""
    result = grep_tool._execute("def", include="*.py")
    
    assert result.success is True
    assert "main.py" in result.data
    assert "utils.py" in result.data
    assert "config.json" not in result.data


def test_grep_with_path(grep_tool, temp_repo):
    """测试在指定路径搜索"""
    result = grep_tool._execute("def", path="main.py")
    
    assert result.success is True
    assert "main.py" in result.data
    assert "utils.py" not in result.data


def test_grep_regex_pattern(grep_tool, temp_repo):
    """测试正则表达式模式"""
    result = grep_tool._execute("def \\w+")
    
    assert result.success is True
    assert "def main" in result.data or "def helper" in result.data


def test_grep_no_matches(grep_tool, temp_repo):
    """测试无匹配结果"""
    result = grep_tool._execute("nonexistent_pattern_xyz")
    
    assert result.success is True
    assert "匹配数: 0" in result.data


def test_grep_nonexistent_path(grep_tool, temp_repo):
    """测试不存在的搜索路径"""
    result = grep_tool._execute("def", path="nonexistent.py")
    
    assert result.success is False
    assert "搜索路径不存在" in result.error
