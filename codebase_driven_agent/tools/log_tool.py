"""日志查询工具实现"""
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from codebase_driven_agent.tools.base import BaseCodebaseTool, ToolResult
from codebase_driven_agent.utils.log_query import get_log_query_instance
from codebase_driven_agent.config import settings
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.tools.log")


class LogToolInput(BaseModel):
    """日志工具输入参数"""
    query: str = Field(..., description="查询语句（关键词、SPL 语句等）")
    appname: Optional[str] = Field(None, description="项目名称（可选，默认使用配置的 appname）")
    start_time: Optional[str] = Field(None, description="开始时间（ISO 格式，如 2024-01-01T10:00:00）")
    end_time: Optional[str] = Field(None, description="结束时间（ISO 格式）")
    limit: int = Field(50, description="返回记录数限制（默认 50）")
    offset: int = Field(0, description="偏移量（用于分页）")


class LogTool(BaseCodebaseTool):
    """日志查询工具"""
    
    name: str = "log_search"
    description: str = """
    用于查询和分析日志。
    
    功能：
    - 根据关键词搜索日志
    - 按时间范围查询日志
    - 支持 SPL（Search Processing Language）查询（日志易）
    - 支持文件日志查询
    - 分页查询支持
    
    使用示例：
    - query: "error" - 搜索包含 error 的日志
    - query: "appname:myapp error" - 在指定项目中搜索错误日志
    - query: "level=ERROR" - 查询错误级别日志
    - appname: "my-project" - 指定项目名称（必需，如果未配置 LOGYI_APPNAME）
    - start_time: "2024-01-01T10:00:00" - 指定开始时间
    - limit: 100 - 限制返回记录数
    
    重要提示：
    - appname 参数是必需的。如果用户没有提供，请询问用户要查询哪个项目/应用的日志
    - 如果配置了 LOGYI_APPNAME，可以不提供 appname 参数
    - 所有查询都会自动包含 appname 过滤
    - SPL 查询会自动验证语法安全性
    - 结果会自动截断，避免返回过多数据
    """
    args_schema: type[LogToolInput] = LogToolInput
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 使用 object.__setattr__ 绕过 Pydantic V2 的字段验证
        object.__setattr__(self, "log_query", get_log_query_instance())
        object.__setattr__(self, "default_appname", settings.logyi_appname)
    
    def _parse_time(self, time_str: Optional[str]) -> Optional[datetime]:
        """解析时间字符串"""
        if not time_str:
            return None
        
        try:
            # 尝试解析 ISO 格式
            return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        except Exception as e:
            logger.warning(f"Failed to parse time string '{time_str}': {str(e)}")
            return None
    
    def _execute(
        self,
        query: str,
        appname: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ToolResult:
        """执行日志查询"""
        # 检查全局停止标志
        from codebase_driven_agent.utils.log_query import _shutdown_event
        if _shutdown_event.is_set():
            logger.warning("LogTool execution cancelled due to server shutdown")
            return ToolResult(
                success=False,
                error="Server is shutting down, log query cancelled."
            )
        
        try:
            # 使用默认 appname 如果未提供
            if not appname:
                appname = self.default_appname or ""
            
            # 如果没有 appname，返回提示让 Agent 询问用户
            if not appname:
                return ToolResult(
                    success=False,
                    error=(
                        "Appname is required for log queries. "
                        "Please ask the user to provide the project/app name (appname) "
                        "that they want to query logs for. "
                        "For example: 'Which project/app should I query logs for?'"
                    )
                )
            
            # 解析时间
            start_dt = self._parse_time(start_time)
            end_dt = self._parse_time(end_time)
            
            # 如果没有指定时间范围，默认查询最近1小时
            # 注意：LogyiLogQuery 会自动检测这种自动生成的时间范围，并在缓存键中忽略它
            if not start_dt and not end_dt:
                end_dt = datetime.now()
                start_dt = end_dt - timedelta(hours=1)
            
            # 验证查询
            is_valid, error_msg = self.log_query.validate_query(query)
            if not is_valid:
                return ToolResult(
                    success=False,
                    error=f"Invalid query: {error_msg}"
                )
            
            # 执行查询
            logger.info("=" * 80)
            logger.info("LogTool Query Request:")
            logger.info(f"  Appname: {appname}")
            logger.info(f"  Query: {query}")
            logger.info(f"  Start Time: {start_dt}")
            logger.info(f"  End Time: {end_dt}")
            logger.info(f"  Limit: {limit}, Offset: {offset}")
            logger.info("=" * 80)
            
            result = self.log_query.query(
                appname=appname,
                query=query,
                start_time=start_dt,
                end_time=end_dt,
                limit=limit,
                offset=offset,
            )
            
            # 打印查询结果摘要
            logger.info("=" * 80)
            logger.info("LogTool Query Result:")
            logger.info(f"  Total: {result.total}")
            logger.info(f"  Logs Count: {len(result.logs)}")
            logger.info(f"  Has More: {result.has_more}")
            logger.info(f"  Final SPL Query: {result.query}")
            # 打印前几条日志的预览（仅打印 raw_message）
            if result.logs:
                logger.info("  Sample Logs (first 3, raw_message only):")
                for i, log_entry in enumerate(result.logs[:3], 1):
                    # 仅打印 raw_message 字段
                    raw_message = log_entry.get('raw_message', '')
                    if raw_message:
                        logger.info(f"    [{i}] {raw_message}")
                    else:
                        # 如果没有 raw_message，打印 message 作为后备
                        message = log_entry.get('message', '')
                        if message:
                            logger.info(f"    [{i}] {message}")
                        else:
                            logger.info(f"    [{i}] (no raw_message or message field)")
            logger.info("=" * 80)
            
            # 格式化结果
            if not result.logs:
                return ToolResult(
                    success=True,
                    data="No logs found matching the query.",
                )
            
            # 构建结果文本
            # 检查是否是缓存结果
            is_cached = getattr(result, '_from_cache', False)
            cache_note = "\n[⚠️ 注意：这是缓存的结果，避免重复查询相同的日志]\n" if is_cached else ""
            
            result_text = f"Found {result.total} log entries (showing {len(result.logs)}):\n\n"
            result_text += f"Query: {result.query}\n"
            if is_cached:
                result_text += cache_note
            if result.has_more:
                result_text += f"[Note: More results available, use offset={offset+limit} to get next page]\n"
            result_text += "\n" + "="*80 + "\n\n"
            
            for i, log_entry in enumerate(result.logs, 1):
                result_text += f"[{i}] {log_entry.get('timestamp', 'N/A')} "
                result_text += f"[{log_entry.get('level', 'INFO')}] "
                result_text += f"{log_entry.get('message', '')}\n"
                
                # 添加文件信息（如果有）
                if 'file' in log_entry:
                    result_text += f"    File: {log_entry['file']}"
                    if 'line' in log_entry:
                        result_text += f":{log_entry['line']}"
                    result_text += "\n"
                
                result_text += "\n"
            
            # 截断和摘要
            truncated_data, is_truncated = self._truncate_data(result_text)
            summary = None
            if is_truncated:
                summary = f"Found {result.total} log entries, showing first {len(result.logs)} entries"
            
            return ToolResult(
                success=True,
                data=truncated_data,
                truncated=is_truncated,
                summary=summary,
            )
        
        except Exception as e:
            logger.error(f"Log query error: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Error querying logs: {str(e)}"
            )

