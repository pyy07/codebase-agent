"""数据库查询工具实现"""
from typing import Optional
from pydantic import BaseModel, Field

from codebase_driven_agent.tools.base import BaseCodebaseTool, ToolResult
from codebase_driven_agent.utils.database import (
    get_schema_info,
    format_schema_info,
    execute_query,
    validate_sql,
)
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.tools.database")


class DatabaseToolInput(BaseModel):
    """数据库工具输入参数"""
    action: str = Field(
        ...,
        description="操作类型：'query'（执行查询）或 'schema'（获取表结构）"
    )
    sql: Optional[str] = Field(None, description="SQL 查询语句（action='query' 时必需）")
    table_name: Optional[str] = Field(None, description="表名（action='schema' 时可选，不提供则返回所有表）")
    limit: int = Field(100, description="查询结果限制（默认 100）")


class DatabaseTool(BaseCodebaseTool):
    """数据库查询工具"""
    
    name: str = "database_query"
    description: str = """
    用于查询和分析数据库。
    
    功能：
    - 执行 SELECT 查询（只读操作）
    - 获取数据库表结构（Schema）
    - 自动清理敏感数据（password, secret 等字段）
    - 自动限制查询结果数量
    
    使用示例：
    - action: "schema" - 获取所有表的结构信息
    - action: "schema", table_name: "users" - 获取 users 表的结构
    - action: "query", sql: "SELECT * FROM users WHERE id = 1" - 执行查询
    
    安全限制：
    - 只允许 SELECT 查询
    - 禁止 INSERT, UPDATE, DELETE, DROP 等写操作
    - 自动清理敏感字段（password, secret, token 等）
    - 查询结果自动限制为 100 行
    """
    args_schema: type[DatabaseToolInput] = DatabaseToolInput
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.max_output_length = kwargs.get("max_output_length", 5000)
    
    def _execute(
        self,
        action: str,
        sql: Optional[str] = None,
        table_name: Optional[str] = None,
        limit: int = 100,
    ) -> ToolResult:
        """执行数据库操作"""
        try:
            # 打印输入参数
            logger.info("=" * 80)
            logger.info("DatabaseTool Query Request:")
            logger.info(f"  Action: {action}")
            if action == "query":
                logger.info(f"  SQL: {sql}")
                logger.info(f"  Limit: {limit}")
            elif action == "schema":
                logger.info(f"  Table Name: {table_name or 'All tables'}")
            logger.info("=" * 80)
            
            if action == "schema":
                result = self._get_schema(table_name)
            elif action == "query":
                if not sql:
                    return ToolResult(
                        success=False,
                        error="SQL query is required for 'query' action"
                    )
                result = self._execute_query(sql, limit)
            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown action: {action}. Use 'schema' or 'query'"
                )
            
            # 打印输出结果摘要
            logger.info("=" * 80)
            logger.info("DatabaseTool Query Result:")
            logger.info(f"  Success: {result.success}")
            if result.success:
                logger.info(f"  Result Length: {len(result.data) if result.data else 0} characters")
                logger.info(f"  Truncated: {result.truncated}")
                if result.summary:
                    logger.info(f"  Summary: {result.summary}")
                # 打印结果预览（前500字符）
                if result.data:
                    preview = result.data[:500].replace('\n', '\\n')
                    logger.info(f"  Result Preview: {preview}...")
            else:
                logger.info(f"  Error: {result.error}")
            logger.info("=" * 80)
            
            return result
        
        except Exception as e:
            logger.error(f"Database tool error: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Database operation failed: {str(e)}"
            )
    
    def _get_schema(self, table_name: Optional[str] = None) -> ToolResult:
        """获取数据库 Schema"""
        try:
            schema_info = get_schema_info()
            
            if not schema_info or not schema_info.get("tables"):
                return ToolResult(
                    success=False,
                    error="No schema information available. Please check database configuration."
                )
            
            # 如果指定了表名，只返回该表的信息
            if table_name:
                tables = schema_info.get("tables", {})
                if table_name not in tables:
                    return ToolResult(
                        success=False,
                        error=f"Table '{table_name}' not found. Available tables: {', '.join(tables.keys())[:10]}"
                    )
                
                # 格式化单个表的信息
                table_info = tables[table_name]
                result_text = f"Table: {table_name}\n\n"
                result_text += "Columns:\n"
                for col in table_info.get("columns", []):
                    col_type = col["type"]
                    nullable = "NULL" if col["nullable"] else "NOT NULL"
                    result_text += f"  - {col['name']}: {col_type} {nullable}\n"
                
                if table_info.get("primary_keys"):
                    result_text += f"\nPrimary Keys: {', '.join(table_info['primary_keys'])}\n"
                
                if table_info.get("foreign_keys"):
                    result_text += "\nForeign Keys:\n"
                    for fk in table_info["foreign_keys"]:
                        fk_cols = ", ".join(fk["columns"])
                        ref_table = fk["referred_table"]
                        ref_cols = ", ".join(fk["referred_columns"])
                        result_text += f"  - {fk_cols} -> {ref_table}({ref_cols})\n"
            else:
                # 返回所有表的信息（格式化）
                result_text = format_schema_info(schema_info, max_tables=10)
            
            # 截断和摘要
            truncated_data, is_truncated = self._truncate_data(result_text)
            summary = None
            if is_truncated:
                total_tables = len(schema_info.get("tables", {}))
                summary = f"Database schema with {total_tables} tables"
            
            return ToolResult(
                success=True,
                data=truncated_data,
                truncated=is_truncated,
                summary=summary,
            )
        
        except Exception as e:
            logger.error(f"Schema retrieval error: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Failed to get schema: {str(e)}"
            )
    
    def _execute_query(self, sql: str, limit: int = 100) -> ToolResult:
        """执行 SQL 查询"""
        try:
            logger.info(f"  Executing SQL query: {sql}")
            
            # 验证 SQL
            is_valid, error_msg = validate_sql(sql)
            if not is_valid:
                logger.warning(f"  SQL validation failed: {error_msg}")
                return ToolResult(
                    success=False,
                    error=f"Invalid SQL: {error_msg}"
                )
            
            # 执行查询
            success, result, error_msg = execute_query(sql, limit=limit, sanitize=True)
            
            logger.info(f"  Query execution result: success={success}, rows={len(result) if result else 0}")
            
            if not success:
                return ToolResult(
                    success=False,
                    error=error_msg or "Query execution failed"
                )
            
            if not result:
                return ToolResult(
                    success=True,
                    data="Query executed successfully, but no results returned.",
                )
            
            # 格式化结果
            result_text = f"Query returned {len(result)} rows:\n\n"
            
            # 获取列名
            if result:
                columns = list(result[0].keys())
                result_text += "Columns: " + ", ".join(columns) + "\n\n"
                
                # 显示数据（限制显示行数）
                display_limit = min(limit, 20)  # 最多显示20行
                for i, row in enumerate(result[:display_limit], 1):
                    result_text += f"Row {i}:\n"
                    for col in columns:
                        value = row.get(col, "NULL")
                        # 限制单个字段的长度
                        if isinstance(value, str) and len(value) > 100:
                            value = value[:100] + "..."
                        result_text += f"  {col}: {value}\n"
                    result_text += "\n"
                
                if len(result) > display_limit:
                    result_text += f"... and {len(result) - display_limit} more rows\n"
            
            # 截断和摘要
            truncated_data, is_truncated = self._truncate_data(result_text)
            summary = None
            if is_truncated:
                summary = f"Query returned {len(result)} rows, showing first {display_limit} rows"
            
            return ToolResult(
                success=True,
                data=truncated_data,
                truncated=is_truncated,
                summary=summary,
            )
        
        except Exception as e:
            logger.error(f"Query execution error: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Query execution failed: {str(e)}"
            )

