"""测试日志查询工具"""
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from codebase_driven_agent.utils.log_query import (
    LogQueryInterface,
    LogQueryResult,
    LogyiLogQuery,
    FileLogQuery,
    get_log_query_instance,
)
from codebase_driven_agent.tools.log_tool import LogTool, LogToolInput


# ==================== 抽象接口测试 ====================

def test_log_query_interface_abstract():
    """测试 LogQueryInterface 是抽象类"""
    with pytest.raises(TypeError):
        LogQueryInterface()


def test_log_query_result_model():
    """测试 LogQueryResult 模型"""
    result = LogQueryResult(
        logs=[{"message": "test"}],
        total=1,
        has_more=False,
        query="test query"
    )
    
    assert result.total == 1
    assert result.has_more is False
    assert len(result.logs) == 1


# ==================== 日志易实现测试 ====================

@pytest.fixture
def logyi_query(monkeypatch):
    """创建 LogyiLogQuery 实例"""
    monkeypatch.setenv("LOGYI_BASE_URL", "http://test.logyi.com")
    monkeypatch.setenv("LOGYI_USERNAME", "testuser")
    monkeypatch.setenv("LOGYI_APIKEY", "testkey")
    monkeypatch.setenv("LOGYI_APPNAME", "testapp")
    
    from codebase_driven_agent.config import settings
    settings.logyi_base_url = "http://test.logyi.com"
    settings.logyi_username = "testuser"
    settings.logyi_apikey = "testkey"
    settings.logyi_appname = "testapp"
    
    return LogyiLogQuery()


def test_logyi_build_spl_query(logyi_query):
    """测试 SPL 查询构建"""
    # 测试自动添加 appname
    spl = logyi_query._build_spl_query("testapp", "error")
    assert "appname:testapp" in spl
    assert "error" in spl
    
    # 测试已有 appname 的情况
    spl2 = logyi_query._build_spl_query("testapp", "appname:other error")
    assert "appname:testapp" in spl2 or "appname:other" in spl2
    
    # 测试时间范围
    start_time = datetime(2024, 1, 1, 10, 0, 0)
    end_time = datetime(2024, 1, 1, 11, 0, 0)
    spl3 = logyi_query._build_spl_query("testapp", "error", start_time, end_time)
    assert "time>=" in spl3 or "time<=" in spl3


def test_logyi_validate_query(logyi_query):
    """测试查询验证"""
    # 有效查询
    is_valid, error = logyi_query.validate_query("error")
    assert is_valid is True
    assert error is None
    
    # 空查询
    is_valid, error = logyi_query.validate_query("")
    assert is_valid is False
    assert error is not None
    
    # 危险关键词
    is_valid, error = logyi_query.validate_query("delete all")
    assert is_valid is False
    assert "dangerous" in error.lower() or "delete" in error.lower()


@patch('requests.get')
def test_logyi_query_success(mock_get, logyi_query):
    """测试日志易查询成功"""
    # Mock API 响应
    mock_response = Mock()
    mock_response.json.return_value = {
        "data": [
            {
                "time": "2024-01-01T10:00:00",
                "level": "ERROR",
                "message": "Test error message"
            }
        ],
        "total": 1
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    result = logyi_query.query(
        appname="testapp",
        query="error",
        limit=10
    )
    
    assert result.total == 1
    assert len(result.logs) == 1
    assert result.logs[0]["level"] == "ERROR"
    assert "appname:testapp" in result.query.lower()


@patch('requests.get')
def test_logyi_query_api_error(mock_get, logyi_query):
    """测试日志易 API 错误处理"""
    # Mock API 错误
    mock_get.side_effect = Exception("Connection error")
    
    result = logyi_query.query(
        appname="testapp",
        query="error"
    )
    
    assert result.total == 0
    assert len(result.logs) == 0


@patch('requests.get')
def test_logyi_query_invalid_response(mock_get, logyi_query):
    """测试无效的 API 响应"""
    mock_response = Mock()
    mock_response.json.return_value = "invalid format"
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    result = logyi_query.query(
        appname="testapp",
        query="error"
    )
    
    # 应该优雅处理无效响应
    assert isinstance(result, LogQueryResult)


def test_logyi_query_no_appname(logyi_query):
    """测试没有 appname 的情况"""
    result = logyi_query.query(
        appname="",
        query="error"
    )
    
    assert result.total == 0
    assert len(result.logs) == 0


def test_logyi_query_invalid_query(logyi_query):
    """测试无效查询"""
    result = logyi_query.query(
        appname="testapp",
        query="delete all"  # 危险关键词
    )
    
    assert result.total == 0


# ==================== 文件日志实现测试 ====================

@pytest.fixture
def temp_log_dir():
    """创建临时日志目录"""
    temp_dir = tempfile.mkdtemp()
    log_dir = Path(temp_dir) / "logs"
    log_dir.mkdir()
    
    # 创建测试日志文件
    (log_dir / "testapp.log").write_text("""2024-01-01 10:00:00 [INFO] Application started
2024-01-01 10:01:00 [ERROR] Database connection failed
2024-01-01 10:02:00 [WARN] Retrying connection...
2024-01-01 10:03:00 [INFO] Connection restored
""")
    
    (log_dir / "testapp-error.log").write_text("""2024-01-01 10:01:00 [ERROR] Critical error occurred
2024-01-01 10:01:30 [ERROR] Stack trace: File "app.py", line 42
""")
    
    yield log_dir
    
    shutil.rmtree(temp_dir)


@pytest.fixture
def file_log_query(temp_log_dir, monkeypatch):
    """创建 FileLogQuery 实例"""
    monkeypatch.setenv("LOG_FILE_BASE_PATH", str(temp_log_dir))
    
    from codebase_driven_agent.config import settings
    settings.log_file_base_path = str(temp_log_dir)
    
    return FileLogQuery()


def test_file_log_find_log_files(file_log_query):
    """测试查找日志文件"""
    files = file_log_query._find_log_files("testapp")
    
    assert len(files) > 0
    assert any("testapp" in f for f in files)


def test_file_log_validate_query(file_log_query):
    """测试文件日志查询验证"""
    # 有效查询
    is_valid, error = file_log_query.validate_query("error")
    assert is_valid is True
    
    # 空查询
    is_valid, error = file_log_query.validate_query("")
    assert is_valid is False


def test_file_log_query(file_log_query):
    """测试文件日志查询"""
    result = file_log_query.query(
        appname="testapp",
        query="error",
        limit=10
    )
    
    assert result.total > 0
    assert len(result.logs) > 0
    assert any("error" in log.get("message", "").lower() for log in result.logs)


def test_file_log_query_pagination(file_log_query):
    """测试文件日志分页"""
    # 第一页
    result1 = file_log_query.query(
        appname="testapp",
        query="",
        limit=2,
        offset=0
    )
    
    # 第二页
    result2 = file_log_query.query(
        appname="testapp",
        query="",
        limit=2,
        offset=2
    )
    
    assert len(result1.logs) <= 2
    assert len(result2.logs) <= 2
    # 确保结果不同
    if result1.logs and result2.logs:
        assert result1.logs[0] != result2.logs[0]


def test_file_log_query_no_files(file_log_query):
    """测试没有日志文件的情况"""
    result = file_log_query.query(
        appname="nonexistent",
        query="error"
    )
    
    assert result.total == 0
    assert len(result.logs) == 0


def test_file_log_parse_log_line(file_log_query):
    """测试日志行解析"""
    line = "2024-01-01 10:00:00 [ERROR] Test error message"
    parsed = file_log_query._parse_log_line(line, "test.log", 1)
    
    assert parsed is not None
    assert parsed["level"] == "ERROR"
    assert "error" in parsed["message"].lower()


# ==================== LogTool 集成测试 ====================

@pytest.fixture
def log_tool_file(monkeypatch, temp_log_dir):
    """创建使用文件日志的 LogTool"""
    monkeypatch.setenv("LOG_FILE_BASE_PATH", str(temp_log_dir))
    monkeypatch.setenv("LOG_QUERY_TYPE", "file")
    monkeypatch.setenv("LOGYI_APPNAME", "testapp")
    
    from codebase_driven_agent.config import settings
    settings.log_file_base_path = str(temp_log_dir)
    settings.log_query_type = "file"
    settings.logyi_appname = "testapp"
    
    return LogTool()


def test_log_tool_execute(log_tool_file):
    """测试 LogTool 执行"""
    result = log_tool_file._execute(
        query="error",
        appname="testapp",
        limit=10
    )
    
    assert result.success is True
    assert "error" in result.data.lower() or "found" in result.data.lower()


def test_log_tool_pagination(log_tool_file):
    """测试 LogTool 分页"""
    # 使用非空查询进行分页测试
    result1 = log_tool_file._execute(
        query=".*",  # 匹配所有日志
        appname="testapp",
        limit=2,
        offset=0
    )
    
    result2 = log_tool_file._execute(
        query=".*",  # 匹配所有日志
        appname="testapp",
        limit=2,
        offset=2
    )
    
    assert result1.success is True
    assert result2.success is True


def test_log_tool_time_range(log_tool_file):
    """测试 LogTool 时间范围查询"""
    start_time = (datetime.now() - timedelta(hours=2)).isoformat()
    end_time = datetime.now().isoformat()
    
    result = log_tool_file._execute(
        query="error",
        appname="testapp",
        start_time=start_time,
        end_time=end_time,
        limit=10
    )
    
    assert result.success is True


def test_log_tool_no_appname(log_tool_file):
    """测试 LogTool 没有 appname"""
    # 清除默认 appname 以测试没有 appname 的情况
    original_appname = log_tool_file.default_appname
    object.__setattr__(log_tool_file, "default_appname", None)
    
    try:
        result = log_tool_file._execute(
            query="error",
            appname=""
        )
        
        assert result.success is False
        assert "appname" in result.error.lower()
    finally:
        # 恢复原始 appname
        object.__setattr__(log_tool_file, "default_appname", original_appname)


def test_log_tool_invalid_query(log_tool_file):
    """测试 LogTool 无效查询"""
    result = log_tool_file._execute(
        query="",
        appname="testapp"
    )
    
    # 空查询应该被拒绝或返回空结果
    assert result.success is False or "no logs" in result.data.lower()


def test_log_tool_truncation(log_tool_file):
    """测试 LogTool 结果截断"""
    # 创建一个会产生大量结果的查询
    result = log_tool_file._execute(
        query="",
        appname="testapp",
        limit=1000  # 大限制
    )
    
    # 如果结果被截断，应该有 summary
    if result.truncated:
        assert result.summary is not None


def test_log_tool_format_result(log_tool_file):
    """测试 LogTool 结果格式化"""
    result = log_tool_file._execute(
        query="error",
        appname="testapp",
        limit=5
    )
    
    assert result.success is True
    formatted = log_tool_file._format_result(result)
    
    assert isinstance(formatted, str)
    assert len(formatted) > 0


# ==================== 工厂方法测试 ====================

def test_get_log_query_instance_file(monkeypatch):
    """测试获取文件日志实例"""
    monkeypatch.setenv("LOG_QUERY_TYPE", "file")
    
    from codebase_driven_agent.config import settings
    settings.log_query_type = "file"
    
    instance = get_log_query_instance()
    assert isinstance(instance, FileLogQuery)


def test_get_log_query_instance_logyi(monkeypatch):
    """测试获取日志易实例"""
    monkeypatch.setenv("LOG_QUERY_TYPE", "logyi")
    
    from codebase_driven_agent.config import settings
    settings.log_query_type = "logyi"
    
    instance = get_log_query_instance()
    assert isinstance(instance, LogyiLogQuery)


def test_get_log_query_instance_default(monkeypatch):
    """测试默认实例"""
    monkeypatch.setenv("LOG_QUERY_TYPE", "unknown")
    
    from codebase_driven_agent.config import settings
    settings.log_query_type = "unknown"
    
    instance = get_log_query_instance()
    # 应该回退到 FileLogQuery
    assert isinstance(instance, FileLogQuery)


# ==================== LogToolInput 测试 ====================

def test_log_tool_input_validation():
    """测试 LogToolInput 参数验证"""
    # 有效输入
    input_data = LogToolInput(
        query="error",
        appname="testapp",
        limit=50,
        offset=0
    )
    
    assert input_data.query == "error"
    assert input_data.limit == 50
    
    # 测试默认值
    minimal_input = LogToolInput(query="error")
    assert minimal_input.limit == 50
    assert minimal_input.offset == 0

