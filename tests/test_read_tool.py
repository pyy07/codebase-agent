"""测试文件读取工具"""
import pytest
import tempfile
import shutil
from pathlib import Path
from codebase_driven_agent.tools.read_tool import ReadTool, ReadToolInput
from codebase_driven_agent.tools.base import ToolResult


@pytest.fixture
def temp_repo():
    """创建临时代码仓库用于测试"""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)
    
    # 创建测试文件
    test_file = repo_path / "test.py"
    test_file.write_text("""line 1
line 2
line 3
line 4
line 5
line 6
line 7
line 8
line 9
line 10
""")
    
    # 创建二进制文件
    binary_file = repo_path / "binary.bin"
    binary_file.write_bytes(b'\x00\x01\x02\x03')
    
    yield repo_path
    
    # 清理
    shutil.rmtree(temp_dir)


@pytest.fixture
def read_tool(temp_repo, monkeypatch):
    """创建 ReadTool 实例"""
    monkeypatch.setenv("CODE_REPO_PATH", str(temp_repo))
    from codebase_driven_agent.config import settings
    settings.code_repo_path = str(temp_repo)
    return ReadTool()


def test_read_full_file(read_tool, temp_repo):
    """测试读取完整文件"""
    result = read_tool._execute("test.py")
    
    assert result.success is True
    assert "文件: test.py" in result.data
    assert "总行数: 10" in result.data
    assert "line 1" in result.data
    assert "line 10" in result.data


def test_read_with_offset(read_tool, temp_repo):
    """测试从指定行号开始读取"""
    result = read_tool._execute("test.py", offset=5)
    
    assert result.success is True
    assert "显示范围: 第 5 行 - 第 10 行" in result.data
    assert "line 5" in result.data
    assert "line 10" in result.data
    # 验证第5行之前的内容不在结果中（通过检查行号）
    lines = result.data.split('\n')
    content_lines = [l for l in lines if '|' in l]
    # 第一行应该是第5行
    assert any('5 |' in line for line in content_lines)
    # 不应该有第4行
    assert not any('4 |' in line for line in content_lines)


def test_read_with_limit(read_tool, temp_repo):
    """测试读取指定行数"""
    result = read_tool._execute("test.py", limit=3)
    
    assert result.success is True
    assert "显示范围: 第 1 行 - 第 3 行" in result.data
    assert "line 1" in result.data
    assert "line 3" in result.data
    assert "line 4" not in result.data


def test_read_with_offset_and_limit(read_tool, temp_repo):
    """测试读取指定范围"""
    result = read_tool._execute("test.py", offset=3, limit=3)
    
    assert result.success is True
    assert "显示范围: 第 3 行 - 第 5 行" in result.data
    assert "line 3" in result.data
    assert "line 5" in result.data
    assert "line 2" not in result.data
    assert "line 6" not in result.data


def test_read_nonexistent_file(read_tool, temp_repo):
    """测试读取不存在的文件"""
    result = read_tool._execute("nonexistent.py")
    
    assert result.success is False
    assert "文件不存在" in result.error


def test_read_binary_file(read_tool, temp_repo):
    """测试读取二进制文件"""
    result = read_tool._execute("binary.bin")
    
    assert result.success is False
    assert "二进制文件" in result.error


def test_read_invalid_offset(read_tool, temp_repo):
    """测试无效的起始行号"""
    result = read_tool._execute("test.py", offset=0)
    
    assert result.success is False
    assert "起始行号必须 >= 1" in result.error


def test_read_invalid_limit(read_tool, temp_repo):
    """测试无效的读取行数"""
    result = read_tool._execute("test.py", limit=0)
    
    assert result.success is False
    assert "读取行数必须 >= 1" in result.error


def test_read_path_traversal(read_tool, temp_repo, monkeypatch):
    """测试路径遍历攻击防护"""
    # 设置代码仓库路径
    monkeypatch.setenv("CODE_REPO_PATH", str(temp_repo))
    from codebase_driven_agent.config import settings
    settings.code_repo_path = str(temp_repo)
    
    # 尝试访问仓库外的文件
    result = read_tool._execute("../../etc/passwd")
    
    assert result.success is False
    assert "超出代码仓库范围" in result.error


def test_read_directory(read_tool, temp_repo):
    """测试读取目录（应该失败）"""
    # 创建一个目录
    (temp_repo / "test_dir").mkdir()
    
    result = read_tool._execute("test_dir")
    
    assert result.success is False
    assert "路径不是文件" in result.error
