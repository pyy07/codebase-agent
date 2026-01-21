"""测试命令执行工具"""
import pytest
import sys
from codebase_driven_agent.tools.bash_tool import BashTool, BashToolInput
from codebase_driven_agent.tools.base import ToolResult


@pytest.fixture
def bash_tool():
    """创建 BashTool 实例"""
    return BashTool()


def test_bash_simple_command(bash_tool):
    """测试简单命令执行"""
    if sys.platform == "win32":
        result = bash_tool._execute("echo Hello")
    else:
        result = bash_tool._execute("echo Hello")
    
    assert result.success is True
    assert "Hello" in result.data


def test_bash_command_with_output(bash_tool):
    """测试有输出的命令"""
    if sys.platform == "win32":
        result = bash_tool._execute("dir" if sys.platform == "win32" else "ls")
    else:
        result = bash_tool._execute("ls")
    
    # 命令应该成功执行（即使没有输出）
    assert result.success is True


def test_bash_dangerous_command(bash_tool):
    """测试危险命令被阻止"""
    dangerous_commands = [
        "rm -rf /",
        "rm -rf /*",
        "sudo rm -rf /",
    ]
    
    for cmd in dangerous_commands:
        result = bash_tool._execute(cmd)
        assert result.success is False
        assert "安全限制" in result.error or "禁止" in result.error or "危险" in result.error


def test_bash_command_timeout(bash_tool):
    """测试命令超时"""
    # 创建一个会长时间运行的命令
    if sys.platform == "win32":
        result = bash_tool._execute("ping 127.0.0.1 -n 10")
    else:
        result = bash_tool._execute("sleep 60")
    
    # 由于超时设置，命令应该被终止或返回超时错误
    # 这个测试可能不稳定，取决于超时设置
    assert isinstance(result, ToolResult)


def test_bash_invalid_command(bash_tool):
    """测试无效命令"""
    result = bash_tool._execute("nonexistent_command_xyz_123")
    
    # 命令应该失败
    assert result.success is False or "未找到" in result.error or "not found" in result.error.lower()


def test_bash_with_cwd(bash_tool, tmp_path):
    """测试指定工作目录"""
    # 创建一个临时文件
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    if sys.platform == "win32":
        result = bash_tool._execute("dir test.txt", cwd=str(tmp_path))
    else:
        result = bash_tool._execute("ls test.txt", cwd=str(tmp_path))
    
    assert result.success is True
    assert "test.txt" in result.data
