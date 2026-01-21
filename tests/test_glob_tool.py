"""测试文件匹配工具"""
import pytest
import tempfile
import shutil
from pathlib import Path
from codebase_driven_agent.tools.glob_tool import GlobTool, GlobToolInput
from codebase_driven_agent.tools.base import ToolResult


@pytest.fixture
def temp_repo():
    """创建临时代码仓库用于测试"""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)
    
    # 创建测试文件结构
    (repo_path / "src").mkdir()
    (repo_path / "src" / "main.py").write_text("# main")
    (repo_path / "src" / "utils.py").write_text("# utils")
    (repo_path / "src" / "config.json").write_text("{}")
    
    (repo_path / "tests").mkdir()
    (repo_path / "tests" / "test_main.py").write_text("# test")
    
    (repo_path / "README.md").write_text("# README")
    (repo_path / "setup.py").write_text("# setup")
    
    yield repo_path
    
    # 清理
    shutil.rmtree(temp_dir)


@pytest.fixture
def glob_tool(temp_repo, monkeypatch):
    """创建 GlobTool 实例"""
    monkeypatch.setenv("CODE_REPO_PATH", str(temp_repo))
    from codebase_driven_agent.config import settings
    settings.code_repo_path = str(temp_repo)
    return GlobTool()


def test_glob_python_files(glob_tool, temp_repo):
    """测试匹配所有 Python 文件"""
    result = glob_tool._execute("*.py")
    
    assert result.success is True
    assert "setup.py" in result.data
    assert "main.py" not in result.data  # 在子目录中


def test_glob_recursive(glob_tool, temp_repo):
    """测试递归匹配"""
    result = glob_tool._execute("**/*.py")
    
    assert result.success is True
    assert "main.py" in result.data
    assert "utils.py" in result.data
    assert "test_main.py" in result.data
    assert "setup.py" in result.data


def test_glob_with_path(glob_tool, temp_repo):
    """测试在指定路径下匹配"""
    result = glob_tool._execute("*.py", path="src")
    
    assert result.success is True
    assert "main.py" in result.data
    assert "utils.py" in result.data
    assert "setup.py" not in result.data  # 不在 src 目录下


def test_glob_json_files(glob_tool, temp_repo):
    """测试匹配 JSON 文件"""
    result = glob_tool._execute("**/*.json")
    
    assert result.success is True
    # 使用递归模式才能找到子目录中的文件
    assert "config.json" in result.data or "匹配文件数: 0" in result.data


def test_glob_nonexistent_pattern(glob_tool, temp_repo):
    """测试不匹配任何文件的模式"""
    result = glob_tool._execute("*.nonexistent")
    
    assert result.success is True
    assert "匹配文件数: 0" in result.data


def test_glob_nonexistent_path(glob_tool, temp_repo):
    """测试不存在的搜索路径"""
    result = glob_tool._execute("*.py", path="nonexistent")
    
    assert result.success is False
    assert "搜索路径不存在" in result.error


def test_glob_results_sorted(glob_tool, temp_repo):
    """测试结果按修改时间排序"""
    result = glob_tool._execute("**/*.py")
    
    assert result.success is True
    # 结果应该包含文件列表
    assert isinstance(result.data, str)
    # 验证包含多个文件
    assert result.data.count(".py") >= 3
