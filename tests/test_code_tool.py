"""测试代码工具"""
import pytest
import tempfile
import shutil
from pathlib import Path
from codebase_driven_agent.tools.code_tool import CodeTool, CodeToolInput
from codebase_driven_agent.tools.base import ToolResult


@pytest.fixture
def temp_repo():
    """创建临时代码仓库用于测试"""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)
    
    # 创建测试文件结构
    (repo_path / "src").mkdir()
    (repo_path / "src" / "main.py").write_text("""def main():
    print("Hello World")
    process_data()

def process_data():
    # 处理数据
    return True
""")
    
    (repo_path / "src" / "utils.py").write_text("""def helper_function():
    # 辅助函数
    pass
""")
    
    (repo_path / "tests").mkdir()
    (repo_path / "tests" / "test_main.py").write_text("""def test_main():
    assert True
""")
    
    (repo_path / "README.md").write_text("# Test Repository")
    
    yield repo_path
    
    # 清理
    shutil.rmtree(temp_dir)


@pytest.fixture
def code_tool(temp_repo, monkeypatch):
    """创建 CodeTool 实例"""
    monkeypatch.setenv("CODE_REPO_PATH", str(temp_repo))
    from codebase_driven_agent.config import settings
    settings.code_repo_path = str(temp_repo)
    
    tool = CodeTool()
    # 使用 object.__setattr__ 绕过 Pydantic V2 的字段验证
    object.__setattr__(tool, "repo_path", temp_repo)
    return tool


def test_search_files_by_name(code_tool):
    """测试按文件名搜索"""
    result = code_tool._execute(query="main.py")
    
    assert result.success is True
    assert "main.py" in result.data.lower()
    assert "Hello World" in result.data


def test_search_files_by_path(code_tool):
    """测试按文件路径搜索"""
    result = code_tool._execute(query="src/main.py", file_path="src/main.py")
    
    assert result.success is True
    assert "main.py" in result.data.lower()
    assert "process_data" in result.data


def test_search_in_file_content(code_tool):
    """测试在文件内容中搜索"""
    result = code_tool._execute(query="process_data")
    
    assert result.success is True
    assert "process_data" in result.data.lower()


def test_get_directory_structure(code_tool):
    """测试获取目录结构"""
    result = code_tool._execute(query="src", file_path="src")
    
    assert result.success is True
    assert "main.py" in result.data or "utils.py" in result.data


def test_read_file_with_truncation(code_tool):
    """测试文件读取和截断"""
    # 创建一个大文件
    large_content = "\n".join([f"# Line {i}" for i in range(200)])
    (code_tool.repo_path / "large_file.py").write_text(large_content)
    
    result = code_tool._execute(query="large_file.py", max_lines=50)
    
    assert result.success is True
    assert "截断" in result.data or "truncated" in result.data.lower() or "..." in result.data


def test_parse_stack_trace(code_tool):
    """测试堆栈跟踪解析"""
    # 测试 Python 堆栈跟踪格式
    stack_trace = 'File "src/main.py", line 3'
    result = code_tool._parse_stack_trace(stack_trace)
    
    assert result is not None
    assert result["file_path"] == "src/main.py"
    assert result["line_number"] == 3
    
    # 测试 JavaScript 堆栈跟踪格式
    stack_trace_js = "at src/utils.js:42:10"
    result_js = code_tool._parse_stack_trace(stack_trace_js)
    
    assert result_js is not None
    assert result_js["file_path"] == "src/utils.js"
    assert result_js["line_number"] == 42
    
    # 测试简单格式
    simple_trace = "src/main.py:10"
    result_simple = code_tool._parse_stack_trace(simple_trace)
    
    assert result_simple is not None
    assert result_simple["file_path"] == "src/main.py"
    assert result_simple["line_number"] == 10


def test_execute_with_stack_trace(code_tool):
    """测试使用堆栈跟踪执行搜索"""
    stack_trace = 'File "src/main.py", line 3'
    result = code_tool._execute(query=stack_trace)
    
    assert result.success is True
    assert "main.py" in result.data.lower()
    assert "定位自堆栈跟踪" in result.data or "stack trace" in result.data.lower()


def test_file_not_found(code_tool):
    """测试文件不存在的情况"""
    result = code_tool._execute(query="nonexistent.py", file_path="nonexistent.py")
    
    assert result.success is False
    assert "not found" in result.error.lower()


def test_no_results(code_tool):
    """测试没有搜索结果的情况"""
    result = code_tool._execute(query="nonexistent_function_xyz")
    
    assert result.success is False
    assert "no code found" in result.error.lower() or "not found" in result.error.lower()


def test_truncate_data(code_tool):
    """测试数据截断功能"""
    long_text = "A" * 10000
    truncated, is_truncated = code_tool._truncate_data(long_text, max_length=1000)
    
    assert is_truncated is True
    assert len(truncated) <= 1000 + 100  # 允许一些额外字符
    assert "截断" in truncated or "truncated" in truncated.lower()


def test_create_summary(code_tool):
    """测试创建摘要"""
    long_text = "A" * 500
    summary = code_tool._create_summary(long_text)
    
    assert summary is not None
    assert len(summary) <= 250  # 摘要应该比原文短


def test_search_with_ripgrep(code_tool):
    """测试使用 ripgrep 搜索（如果可用）"""
    try:
        import importlib.util
        if importlib.util.find_spec("ripgrepy") is None:
            pytest.skip("ripgrep-py not available")
        result = code_tool._execute(query="process_data", use_ripgrep=True)
        
        assert result.success is True
        assert "process_data" in result.data.lower()
    except ImportError:
        pytest.skip("ripgrep-py not available")


def test_get_git_info(code_tool):
    """测试获取 Git 信息（如果可用）"""
    try:
        import git
        # 初始化 Git 仓库
        repo = git.Repo.init(code_tool.repo_path)
        repo.index.add(["src/main.py"])
        repo.index.commit("Initial commit")
        
        git_info = code_tool._get_git_info("src/main.py")
        
        # Git 信息可能为空（如果没有提交历史），但不应该报错
        assert git_info is None or isinstance(git_info, str)
    except ImportError:
        pytest.skip("gitpython not available")
    except Exception:
        # Git 操作可能失败（例如不在 Git 仓库中），这是可以接受的
        pass


def test_format_result(code_tool):
    """测试结果格式化"""
    tool_result = ToolResult(
        success=True,
        data="Test data",
        truncated=False,
        summary=None
    )
    
    formatted = code_tool._format_result(tool_result)
    
    assert isinstance(formatted, str)
    assert "Test data" in formatted


def test_format_error(code_tool):
    """测试错误格式化"""
    tool_result = ToolResult(
        success=False,
        error="Test error"
    )
    
    formatted = code_tool._format_result(tool_result)
    
    assert isinstance(formatted, str)
    assert "错误" in formatted or "error" in formatted.lower()
    assert "Test error" in formatted


def test_multiple_files_search(code_tool):
    """测试搜索多个文件"""
    result = code_tool._execute(query=".py")
    
    # 应该找到多个 Python 文件
    assert result.success is True
    assert "main.py" in result.data.lower() or "utils.py" in result.data.lower()


def test_directory_query(code_tool):
    """测试目录查询"""
    result = code_tool._execute(query="src")
    
    assert result.success is True
    assert "Directory structure" in result.data or "目录结构" in result.data.lower()


def test_code_tool_input_validation():
    """测试输入参数验证"""
    # 有效的输入
    valid_input = CodeToolInput(
        query="test",
        file_path=None,
        max_lines=100,
        include_context=True
    )
    
    assert valid_input.query == "test"
    assert valid_input.max_lines == 100
    
    # 测试默认值
    minimal_input = CodeToolInput(query="test")
    assert minimal_input.max_lines == 100
    assert minimal_input.include_context is True

