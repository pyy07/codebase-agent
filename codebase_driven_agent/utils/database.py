"""数据库工具和 Schema 发现"""
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
import sqlparse

from codebase_driven_agent.config import settings
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.utils.database")

# Schema 缓存
_schema_cache: Dict[str, Dict] = {}


def get_database_engine() -> Optional[Engine]:
    """获取数据库引擎"""
    if not settings.database_url:
        logger.debug("No database URL configured")
        return None
    
    try:
        logger.debug(f"Creating database engine for: {settings.database_url[:50]}...")
        engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,  # 连接前检查
            pool_recycle=3600,   # 1小时回收连接
            echo=False,
            connect_args={"connect_timeout": 5} if "postgresql" in settings.database_url.lower() else {},  # PostgreSQL 连接超时
        )
        logger.debug("Database engine created successfully")
        return engine
    except Exception as e:
        logger.error(f"Failed to create database engine: {str(e)}")
        return None


def get_schema_info(database_url: Optional[str] = None, use_cache: bool = True) -> Dict[str, Any]:
    """
    获取数据库 Schema 信息
    
    Args:
        database_url: 数据库 URL（可选，默认使用配置）
        use_cache: 是否使用缓存
    
    Returns:
        Schema 信息字典
    """
    db_url = database_url or settings.database_url
    if not db_url:
        return {}
    
    # 检查缓存
    if use_cache and db_url in _schema_cache:
        return _schema_cache[db_url]
    
    engine = get_database_engine()
    if not engine:
        logger.debug("No database engine available, returning empty schema")
        return {}
    
    try:
        logger.debug("Inspecting database schema...")
        inspector = inspect(engine)
        schema_info = {
            "tables": {},
            "database_type": engine.dialect.name,
        }
        
        # 获取所有表名
        logger.debug("Getting table names...")
        tables = inspector.get_table_names()
        logger.debug(f"Found {len(tables)} tables")
        
        for table_name in tables:
            try:
                # 获取列信息
                columns = inspector.get_columns(table_name)
                column_info = []
                
                for col in columns:
                    column_info.append({
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col.get("nullable", True),
                        "default": str(col.get("default", "")),
                    })
                
                # 获取主键
                pk_constraint = inspector.get_pk_constraint(table_name)
                primary_keys = pk_constraint.get("constrained_columns", [])
                
                # 获取外键
                foreign_keys = inspector.get_foreign_keys(table_name)
                fk_info = []
                for fk in foreign_keys:
                    fk_info.append({
                        "columns": fk["constrained_columns"],
                        "referred_table": fk["referred_table"],
                        "referred_columns": fk["referred_columns"],
                    })
                
                schema_info["tables"][table_name] = {
                    "columns": column_info,
                    "primary_keys": primary_keys,
                    "foreign_keys": fk_info,
                }
            
            except Exception as e:
                logger.warning(f"Failed to get schema for table {table_name}: {str(e)}")
                continue
        
        # 缓存结果
        if use_cache:
            _schema_cache[db_url] = schema_info
        
        return schema_info
    
    except Exception as e:
        logger.error(f"Failed to get schema info: {str(e)}")
        return {}


def format_schema_info(schema_info: Dict[str, Any], max_tables: int = 20) -> str:
    """格式化 Schema 信息为字符串（用于 Agent Prompt）"""
    if not schema_info or not schema_info.get("tables"):
        return "No schema information available."
    
    lines = [f"Database Type: {schema_info.get('database_type', 'Unknown')}"]
    lines.append(f"Total Tables: {len(schema_info['tables'])}")
    lines.append("")
    
    tables = list(schema_info["tables"].items())[:max_tables]
    
    for table_name, table_info in tables:
        lines.append(f"Table: {table_name}")
        
        # 主键
        if table_info.get("primary_keys"):
            lines.append(f"  Primary Keys: {', '.join(table_info['primary_keys'])}")
        
        # 列信息
        lines.append("  Columns:")
        for col in table_info.get("columns", []):
            col_type = col["type"]
            nullable = "NULL" if col["nullable"] else "NOT NULL"
            default = f" DEFAULT {col['default']}" if col.get("default") else ""
            lines.append(f"    - {col['name']}: {col_type} {nullable}{default}")
        
        # 外键
        if table_info.get("foreign_keys"):
            lines.append("  Foreign Keys:")
            for fk in table_info["foreign_keys"]:
                fk_cols = ", ".join(fk["columns"])
                ref_table = fk["referred_table"]
                ref_cols = ", ".join(fk["referred_columns"])
                lines.append(f"    - {fk_cols} -> {ref_table}({ref_cols})")
        
        lines.append("")
    
    if len(schema_info["tables"]) > max_tables:
        lines.append(f"... and {len(schema_info['tables']) - max_tables} more tables")
    
    return "\n".join(lines)


def validate_sql(sql: str) -> Tuple[bool, Optional[str]]:
    """
    验证 SQL 语句
    
    Args:
        sql: SQL 语句
    
    Returns:
        (is_valid, error_message)
    """
    if not sql or not sql.strip():
        return False, "SQL query cannot be empty"
    
    # 使用 sqlparse 解析 SQL
    try:
        parsed = sqlparse.parse(sql)
        if not parsed:
            return False, "Invalid SQL syntax"
        
        # 检查是否包含写操作
        write_keywords = [
            "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
            "TRUNCATE", "REPLACE", "MERGE", "GRANT", "REVOKE",
        ]
        
        sql_upper = sql.upper()
        for keyword in write_keywords:
            if keyword in sql_upper:
                # 检查是否是注释中的关键字
                if not _is_in_comment(sql, keyword):
                    return False, f"Write operation '{keyword}' is not allowed. Only SELECT queries are permitted."
        
        return True, None
    
    except Exception as e:
        return False, f"SQL parsing error: {str(e)}"


def _is_in_comment(sql: str, keyword: str) -> bool:
    """检查关键字是否在注释中"""
    # 简单的注释检查（可以改进）
    lines = sql.split('\n')
    for line in lines:
        if keyword.upper() in line.upper():
            # 检查是否是注释行
            stripped = line.strip()
            if stripped.startswith('--') or stripped.startswith('/*'):
                return True
    return False


def sanitize_result(result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    清理查询结果，移除敏感字段
    
    Args:
        result: 查询结果列表
    
    Returns:
        清理后的结果列表
    """
    sensitive_fields = [
        "password", "passwd", "pwd",
        "secret", "secret_key", "api_key", "apikey",
        "token", "access_token", "refresh_token",
        "private_key", "privatekey",
    ]
    
    sanitized = []
    for row in result:
        sanitized_row = {}
        for key, value in row.items():
            key_lower = key.lower()
            # 检查是否是敏感字段
            is_sensitive = any(sensitive in key_lower for sensitive in sensitive_fields)
            
            if is_sensitive:
                sanitized_row[key] = "***REDACTED***"
            else:
                sanitized_row[key] = value
        
        sanitized.append(sanitized_row)
    
    return sanitized


def execute_query(
    sql: str,
    limit: int = 100,
    sanitize: bool = True,
) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    执行 SQL 查询
    
    Args:
        sql: SQL 查询语句
        limit: 结果限制
        sanitize: 是否清理敏感数据
    
    Returns:
        (success, result, error_message)
    """
    # 验证 SQL
    is_valid, error_msg = validate_sql(sql)
    if not is_valid:
        return False, None, error_msg
    
    engine = get_database_engine()
    if not engine:
        return False, None, "Database connection not configured"
    
    try:
        # 添加 LIMIT（如果还没有）
        sql_upper = sql.upper()
        if "LIMIT" not in sql_upper:
            sql = f"{sql.rstrip(';')} LIMIT {limit}"
        
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            
            # 转换为字典列表
            rows = []
            for row in result:
                row_dict = dict(row._mapping)
                rows.append(row_dict)
            
            # 清理敏感数据
            if sanitize:
                rows = sanitize_result(rows)
            
            return True, rows, None
    
    except SQLAlchemyError as e:
        error_msg = str(e)
        logger.error(f"SQL execution error: {error_msg}")
        return False, None, error_msg
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, None, error_msg

