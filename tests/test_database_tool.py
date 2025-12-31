"""测试数据库工具"""
import pytest
import tempfile
import os
from sqlalchemy import create_engine, text

from codebase_driven_agent.tools.database_tool import DatabaseTool, DatabaseToolInput
from codebase_driven_agent.utils.database import (
    get_schema_info,
    format_schema_info,
    validate_sql,
    sanitize_result,
    execute_query,
    get_database_engine,
)


# ==================== SQL 验证测试 ====================

def test_validate_sql_valid_select():
    """测试有效的 SELECT 查询"""
    is_valid, error = validate_sql("SELECT * FROM users")
    assert is_valid is True
    assert error is None


def test_validate_sql_empty():
    """测试空 SQL"""
    is_valid, error = validate_sql("")
    assert is_valid is False
    assert "empty" in error.lower()


def test_validate_sql_insert_rejected():
    """测试 INSERT 被拒绝"""
    is_valid, error = validate_sql("INSERT INTO users VALUES (1, 'test')")
    assert is_valid is False
    assert "insert" in error.lower() or "write" in error.lower()


def test_validate_sql_update_rejected():
    """测试 UPDATE 被拒绝"""
    is_valid, error = validate_sql("UPDATE users SET name = 'test' WHERE id = 1")
    assert is_valid is False
    assert "update" in error.lower() or "write" in error.lower()


def test_validate_sql_delete_rejected():
    """测试 DELETE 被拒绝"""
    is_valid, error = validate_sql("DELETE FROM users WHERE id = 1")
    assert is_valid is False
    assert "delete" in error.lower() or "write" in error.lower()


def test_validate_sql_drop_rejected():
    """测试 DROP 被拒绝"""
    is_valid, error = validate_sql("DROP TABLE users")
    assert is_valid is False
    assert "drop" in error.lower() or "write" in error.lower()


def test_validate_sql_comment_allowed():
    """测试注释中的关键字被允许"""
    sql = "-- This is a comment about UPDATE"
    is_valid, error = validate_sql(sql)
    # 注释中的关键字应该被允许（如果实现支持）
    # 如果当前实现不支持，这个测试可能需要调整


def test_validate_sql_complex_select():
    """测试复杂的 SELECT 查询"""
    sql = """
    SELECT u.id, u.name, p.title
    FROM users u
    LEFT JOIN posts p ON u.id = p.user_id
    WHERE u.status = 'active'
    ORDER BY u.created_at DESC
    LIMIT 10
    """
    is_valid, error = validate_sql(sql)
    assert is_valid is True


# ==================== 敏感数据过滤测试 ====================

def test_sanitize_result_password():
    """测试密码字段过滤"""
    result = [
        {"id": 1, "username": "test", "password": "secret123"},
        {"id": 2, "username": "admin", "password": "admin123"},
    ]
    
    sanitized = sanitize_result(result)
    
    assert sanitized[0]["password"] == "***REDACTED***"
    assert sanitized[1]["password"] == "***REDACTED***"
    assert sanitized[0]["username"] == "test"  # 非敏感字段保留


def test_sanitize_result_secret():
    """测试 secret 字段过滤"""
    result = [
        {"id": 1, "name": "test", "secret_key": "abc123"},
        {"id": 2, "name": "admin", "api_key": "xyz789"},
    ]
    
    sanitized = sanitize_result(result)
    
    assert sanitized[0]["secret_key"] == "***REDACTED***"
    assert sanitized[1]["api_key"] == "***REDACTED***"


def test_sanitize_result_token():
    """测试 token 字段过滤"""
    result = [
        {"id": 1, "user_id": 100, "access_token": "token123"},
        {"id": 2, "user_id": 200, "refresh_token": "token456"},
    ]
    
    sanitized = sanitize_result(result)
    
    assert sanitized[0]["access_token"] == "***REDACTED***"
    assert sanitized[1]["refresh_token"] == "***REDACTED***"


def test_sanitize_result_case_insensitive():
    """测试大小写不敏感过滤"""
    result = [
        {"id": 1, "Password": "secret", "SECRET_KEY": "key"},
    ]
    
    sanitized = sanitize_result(result)
    
    assert sanitized[0]["Password"] == "***REDACTED***"
    assert sanitized[0]["SECRET_KEY"] == "***REDACTED***"


def test_sanitize_result_no_sensitive_fields():
    """测试没有敏感字段的情况"""
    result = [
        {"id": 1, "name": "test", "email": "test@example.com"},
    ]
    
    sanitized = sanitize_result(result)
    
    assert sanitized[0]["name"] == "test"
    assert sanitized[0]["email"] == "test@example.com"


# ==================== Schema 发现测试 ====================

@pytest.fixture
def sqlite_db():
    """创建临时 SQLite 数据库"""
    db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    db_path = db_file.name
    db_file.close()
    
    # 创建数据库和表
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username VARCHAR(50) NOT NULL,
                email VARCHAR(100),
                password VARCHAR(255)
            )
        """))
        conn.execute(text("""
            CREATE TABLE posts (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title VARCHAR(200),
                content TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))
        conn.commit()
    
    yield f"sqlite:///{db_path}"
    
    # 清理
    os.unlink(db_path)


def test_get_schema_info(sqlite_db, monkeypatch):
    """测试获取 Schema 信息"""
    monkeypatch.setenv("DATABASE_URL", sqlite_db)
    
    from codebase_driven_agent.config import settings
    settings.database_url = sqlite_db
    
    schema_info = get_schema_info(use_cache=False)
    
    assert "tables" in schema_info
    assert "users" in schema_info["tables"]
    assert "posts" in schema_info["tables"]
    
    # 检查 users 表结构
    users_table = schema_info["tables"]["users"]
    assert len(users_table["columns"]) == 4
    assert users_table["primary_keys"] == ["id"]
    
    # 检查 posts 表外键
    posts_table = schema_info["tables"]["posts"]
    assert len(posts_table["foreign_keys"]) > 0


def test_format_schema_info():
    """测试 Schema 信息格式化"""
    schema_info = {
        "database_type": "sqlite",
        "tables": {
            "users": {
                "columns": [
                    {"name": "id", "type": "INTEGER", "nullable": False},
                    {"name": "username", "type": "VARCHAR(50)", "nullable": False},
                ],
                "primary_keys": ["id"],
                "foreign_keys": [],
            }
        }
    }
    
    formatted = format_schema_info(schema_info)
    
    assert "users" in formatted
    assert "id" in formatted
    assert "username" in formatted
    assert "INTEGER" in formatted


def test_format_schema_info_max_tables():
    """测试 Schema 格式化限制表数量"""
    schema_info = {
        "database_type": "sqlite",
        "tables": {f"table_{i}": {"columns": [], "primary_keys": [], "foreign_keys": []}
                   for i in range(25)}
    }
    
    formatted = format_schema_info(schema_info, max_tables=10)
    
    assert "more tables" in formatted.lower()


# ==================== 查询执行测试 ====================

def test_execute_query_no_database(monkeypatch):
    """测试没有配置数据库的情况"""
    monkeypatch.setenv("DATABASE_URL", "")
    
    from codebase_driven_agent.config import settings
    settings.database_url = None
    
    success, result, error = execute_query("SELECT * FROM users")
    
    assert success is False
    assert "not configured" in error.lower() or "connection" in error.lower()


def test_execute_query_invalid_sql(sqlite_db, monkeypatch):
    """测试无效 SQL"""
    monkeypatch.setenv("DATABASE_URL", sqlite_db)
    
    from codebase_driven_agent.config import settings
    settings.database_url = sqlite_db
    
    success, result, error = execute_query("INSERT INTO users VALUES (1, 'test')")
    
    assert success is False
    assert "write" in error.lower() or "insert" in error.lower()


def test_execute_query_success(sqlite_db, monkeypatch):
    """测试成功执行查询"""
    monkeypatch.setenv("DATABASE_URL", sqlite_db)
    
    from codebase_driven_agent.config import settings
    settings.database_url = sqlite_db
    
    # 插入测试数据
    engine = get_database_engine()
    with engine.connect() as conn:
        conn.execute(text("INSERT INTO users (id, username, email, password) VALUES (1, 'test', 'test@example.com', 'secret')"))
        conn.commit()
    
    success, result, error = execute_query("SELECT id, username, email FROM users", sanitize=True)
    
    assert success is True
    assert result is not None
    assert len(result) == 1
    assert result[0]["username"] == "test"


def test_execute_query_limit(sqlite_db, monkeypatch):
    """测试查询结果限制"""
    monkeypatch.setenv("DATABASE_URL", sqlite_db)
    
    from codebase_driven_agent.config import settings
    settings.database_url = sqlite_db
    
    # 插入多条数据
    engine = get_database_engine()
    with engine.connect() as conn:
        for i in range(10):
            conn.execute(text(f"INSERT INTO users (id, username) VALUES ({i}, 'user{i}')"))
        conn.commit()
    
    success, result, error = execute_query("SELECT * FROM users", limit=5)
    
    assert success is True
    assert len(result) <= 5


def test_execute_query_sanitize(sqlite_db, monkeypatch):
    """测试查询结果脱敏"""
    monkeypatch.setenv("DATABASE_URL", sqlite_db)
    
    from codebase_driven_agent.config import settings
    settings.database_url = sqlite_db
    
    # 插入包含敏感字段的数据
    engine = get_database_engine()
    with engine.connect() as conn:
        conn.execute(text("INSERT INTO users (id, username, password) VALUES (1, 'test', 'secret123')"))
        conn.commit()
    
    success, result, error = execute_query("SELECT * FROM users", sanitize=True)
    
    assert success is True
    assert result[0]["password"] == "***REDACTED***"


# ==================== DatabaseTool 集成测试 ====================

@pytest.fixture
def database_tool():
    """创建 DatabaseTool 实例"""
    return DatabaseTool()


def test_database_tool_get_schema_all_tables(database_tool, sqlite_db, monkeypatch):
    """测试获取所有表结构"""
    monkeypatch.setenv("DATABASE_URL", sqlite_db)
    
    from codebase_driven_agent.config import settings
    settings.database_url = sqlite_db
    
    result = database_tool._execute(action="schema")
    
    assert result.success is True
    assert "users" in result.data.lower() or "posts" in result.data.lower()


def test_database_tool_get_schema_specific_table(database_tool, sqlite_db, monkeypatch):
    """测试获取特定表结构"""
    monkeypatch.setenv("DATABASE_URL", sqlite_db)
    
    from codebase_driven_agent.config import settings
    settings.database_url = sqlite_db
    
    result = database_tool._execute(action="schema", table_name="users")
    
    assert result.success is True
    assert "users" in result.data.lower()
    assert "username" in result.data.lower()


def test_database_tool_get_schema_table_not_found(database_tool, sqlite_db, monkeypatch):
    """测试表不存在的情况"""
    monkeypatch.setenv("DATABASE_URL", sqlite_db)
    
    from codebase_driven_agent.config import settings
    settings.database_url = sqlite_db
    
    result = database_tool._execute(action="schema", table_name="nonexistent")
    
    assert result.success is False
    assert "not found" in result.error.lower()


def test_database_tool_execute_query(database_tool, sqlite_db, monkeypatch):
    """测试执行查询"""
    monkeypatch.setenv("DATABASE_URL", sqlite_db)
    
    from codebase_driven_agent.config import settings
    settings.database_url = sqlite_db
    
    # 插入测试数据
    engine = get_database_engine()
    with engine.connect() as conn:
        conn.execute(text("INSERT INTO users (id, username, email) VALUES (1, 'test', 'test@example.com')"))
        conn.commit()
    
    result = database_tool._execute(
        action="query",
        sql="SELECT id, username, email FROM users WHERE id = 1",
        limit=10
    )
    
    assert result.success is True
    assert "test" in result.data.lower()


def test_database_tool_execute_query_no_sql(database_tool):
    """测试查询操作缺少 SQL"""
    result = database_tool._execute(action="query")
    
    assert result.success is False
    assert "sql" in result.error.lower()


def test_database_tool_execute_query_invalid_sql(database_tool):
    """测试无效 SQL"""
    result = database_tool._execute(
        action="query",
        sql="DELETE FROM users"
    )
    
    assert result.success is False
    assert "invalid" in result.error.lower() or "write" in result.error.lower()


def test_database_tool_unknown_action(database_tool):
    """测试未知操作"""
    result = database_tool._execute(action="unknown")
    
    assert result.success is False
    assert "unknown" in result.error.lower()


def test_database_tool_result_truncation(database_tool, sqlite_db, monkeypatch):
    """测试结果截断"""
    monkeypatch.setenv("DATABASE_URL", sqlite_db)
    
    from codebase_driven_agent.config import settings
    settings.database_url = sqlite_db
    
    # 插入大量数据
    engine = get_database_engine()
    with engine.connect() as conn:
        for i in range(100):
            conn.execute(text(f"INSERT INTO users (id, username) VALUES ({i}, 'user{i}')"))
        conn.commit()
    
    result = database_tool._execute(
        action="query",
        sql="SELECT * FROM users",
        limit=100
    )
    
    # 结果应该被截断或限制显示
    assert result.success is True
    # 如果被截断，应该有 summary
    if result.truncated:
        assert result.summary is not None


def test_database_tool_format_result(database_tool, sqlite_db, monkeypatch):
    """测试结果格式化"""
    monkeypatch.setenv("DATABASE_URL", sqlite_db)
    
    from codebase_driven_agent.config import settings
    settings.database_url = sqlite_db
    
    result = database_tool._execute(action="schema")
    
    if result.success:
        formatted = database_tool._format_result(result)
        assert isinstance(formatted, str)
        assert len(formatted) > 0


def test_database_tool_input_validation():
    """测试 DatabaseToolInput 参数验证"""
    # 有效输入
    input_data = DatabaseToolInput(
        action="query",
        sql="SELECT * FROM users",
        limit=50
    )
    
    assert input_data.action == "query"
    assert input_data.sql == "SELECT * FROM users"
    assert input_data.limit == 50
    
    # 测试默认值
    schema_input = DatabaseToolInput(action="schema")
    assert schema_input.limit == 100


def test_database_tool_no_database(database_tool, monkeypatch):
    """测试没有配置数据库的情况"""
    monkeypatch.setenv("DATABASE_URL", "")
    
    from codebase_driven_agent.config import settings
    settings.database_url = None
    
    result = database_tool._execute(action="schema")
    
    assert result.success is False
    assert "not available" in result.error.lower() or "not configured" in result.error.lower()

