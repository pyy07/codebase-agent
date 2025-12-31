"""测试信息提取器"""
from typing import Any
from codebase_driven_agent.utils.extractors import (
    extract_related_code,
    extract_related_logs,
    extract_related_data,
    extract_from_intermediate_steps,
)
from codebase_driven_agent.api.models import AnalysisResult


class MockAction:
    """模拟 AgentAction"""
    def __init__(self, tool: str, tool_input: Any = None, log: str = ""):
        self.tool = tool
        self.tool_input = tool_input
        self.log = log


def test_extract_related_code():
    """测试代码信息提取"""
    # 模拟 CodeTool 返回格式
    code_observation = """File: src/main.py

def process_data():
    # 处理数据
    pass

Line 10: def process_data():
Line 15:     pass"""
    
    intermediate_steps = [
        (MockAction("code_search", {"query": "process_data"}), code_observation),
    ]
    
    result = extract_related_code(intermediate_steps)
    
    assert result is not None
    assert len(result) > 0
    assert result[0]["file"] == "src/main.py"
    assert "lines" in result[0]


def test_extract_related_logs():
    """测试日志信息提取"""
    # 模拟 LogTool 返回格式
    log_observation = """Found 10 log entries (showing 5):

Query: appname:test AND error
================================================================================

[1] 2024-01-01 10:00:00 [ERROR] Database connection failed
    File: src/db.py:123

[2] 2024-01-01 10:01:00 [WARN] Retrying connection...
"""
    
    intermediate_steps = [
        (MockAction("log_search", {"query": "error"}), log_observation),
    ]
    
    result = extract_related_logs(intermediate_steps)
    
    assert result is not None
    assert len(result) > 0
    assert "timestamp" in result[0]
    assert "content" in result[0]


def test_extract_related_data():
    """测试数据库查询结果提取"""
    # 模拟 DatabaseTool 返回格式
    db_observation = """Query returned 5 rows:

Columns: id, name, email

Row 1:
  id: 1
  name: Test User
  email: test@example.com

Row 2:
  id: 2
  name: Another User
  email: another@example.com
"""
    
    intermediate_steps = [
        (MockAction("database_query", {"action": "query", "sql": "SELECT * FROM users LIMIT 5"}), db_observation),
    ]
    
    result = extract_related_data(intermediate_steps)
    
    assert result is not None
    assert len(result) > 0
    assert "query" in result[0]
    assert "result" in result[0]


def test_extract_from_intermediate_steps():
    """测试完整提取流程"""
    code_observation = "File: src/main.py\n\nCode content here"
    log_observation = "[1] 2024-01-01 10:00:00 [ERROR] Error message"
    db_observation = "Query returned 3 rows:\n\nColumns: id, name"
    
    intermediate_steps = [
        (MockAction("code_search"), code_observation),
        (MockAction("log_search"), log_observation),
        (MockAction("database_query", {"sql": "SELECT * FROM users"}), db_observation),
    ]
    
    result = AnalysisResult(
        root_cause="测试根因",
        suggestions=["建议1"],
        confidence=0.8,
        related_code=None,
        related_logs=None,
        related_data=None,
    )
    
    updated_result = extract_from_intermediate_steps(intermediate_steps, result)
    
    assert updated_result.related_code is not None
    assert updated_result.related_logs is not None
    assert updated_result.related_data is not None


def test_extract_empty_steps():
    """测试空步骤列表"""
    result = extract_related_code([])
    assert result is None
    
    result = extract_related_logs([])
    assert result is None
    
    result = extract_related_data([])
    assert result is None

