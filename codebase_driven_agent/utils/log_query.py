"""日志查询抽象接口和实现"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

from codebase_driven_agent.config import settings
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.utils.log_query")


class LogQueryResult(BaseModel):
    """日志查询结果"""
    logs: List[Dict[str, Any]] = Field(..., description="日志条目列表")
    total: int = Field(..., description="总记录数")
    has_more: bool = Field(False, description="是否还有更多记录")
    query: str = Field(..., description="执行的查询语句")


class LogQueryInterface(ABC):
    """日志查询抽象接口
    
    所有日志查询实现都必须实现此接口，确保统一的查询方式。
    所有方法都必须包含 appname 参数，用于权限控制。
    """
    
    @abstractmethod
    def query(
        self,
        appname: str,
        query: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> LogQueryResult:
        """
        执行日志查询
        
        Args:
            appname: 项目名称（必需，用于权限控制）
            query: 查询语句（SPL 或关键词）
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回记录数限制
            offset: 偏移量
        
        Returns:
            日志查询结果
        """
        pass
    
    @abstractmethod
    def validate_query(self, query: str) -> tuple[bool, Optional[str]]:
        """
        验证查询语句
        
        Args:
            query: 查询语句
        
        Returns:
            (is_valid, error_message)
        """
        pass


class LogyiLogQuery(LogQueryInterface):
    """日志易查询实现"""
    
    def __init__(self):
        self.base_url = settings.logyi_base_url
        self.username = settings.logyi_username
        self.api_key = settings.logyi_apikey
        self.default_appname = settings.logyi_appname
        
        if not self.base_url or not self.username or not self.api_key:
            logger.warning("Logyi configuration incomplete, LogyiLogQuery may not work properly")
    
    def _build_spl_query(
        self,
        appname: str,
        base_query: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> str:
        """构建 SPL 查询语句，确保包含 appname 过滤"""
        # 确保 appname 在查询开头
        if not base_query.strip().startswith("appname:"):
            spl_query = f"appname:{appname} {base_query}"
        else:
            # 如果已有 appname，替换为指定的 appname
            spl_query = base_query
            if f"appname:{appname}" not in spl_query:
                # 移除旧的 appname，添加新的
                import re
                spl_query = re.sub(r'appname:\w+', f'appname:{appname}', spl_query)
        
        # 注意：时间范围不在 SPL 查询中直接添加，而是在 API 请求的 time_range 参数中传递
        # 这样可以保持 SPL 查询的简洁性
        return spl_query
    
    def validate_query(self, query: str) -> tuple[bool, Optional[str]]:
        """验证 SPL 查询语句"""
        if not query or not query.strip():
            return False, "Query cannot be empty"
        
        # 基本语法检查
        # 检查是否包含危险操作（如删除、更新等）
        dangerous_keywords = ["delete", "drop", "update", "remove", "truncate"]
        query_lower = query.lower()
        for keyword in dangerous_keywords:
            if keyword in query_lower:
                return False, f"Dangerous keyword '{keyword}' detected in query"
        
        # 检查 appname 是否存在（虽然不是强制，但建议有）
        if "appname:" not in query_lower:
            logger.warning("Query does not contain appname filter, it will be added automatically")
        
        return True, None
    
    def query(
        self,
        appname: str,
        query: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> LogQueryResult:
        """执行日志易查询"""
        # 使用默认 appname 如果未提供
        if not appname:
            appname = self.default_appname or ""
        
        if not appname:
            return LogQueryResult(
                logs=[],
                total=0,
                has_more=False,
                query=query,
            )
        
        # 验证查询
        is_valid, error_msg = self.validate_query(query)
        if not is_valid:
            logger.error(f"Invalid SPL query: {error_msg}")
            return LogQueryResult(
                logs=[],
                total=0,
                has_more=False,
                query=query,
            )
        
        # 构建完整的 SPL 查询
        spl_query = self._build_spl_query(appname, query, start_time, end_time)
        
        # 打印查询详情（用于调试）
        logger.info("=" * 80)
        logger.info("Logyi Query Details:")
        logger.info(f"  Appname: {appname}")
        logger.info(f"  Original Query: {query}")
        logger.info(f"  Built SPL Query: {spl_query}")
        logger.info(f"  Start Time: {start_time}")
        logger.info(f"  End Time: {end_time}")
        logger.info(f"  Limit: {limit}")
        logger.info(f"  Offset: {offset}")
        logger.info(f"  Base URL: {self.base_url}")
        logger.info(f"  API Key: {self.api_key[:10]}...{self.api_key[-4:] if self.api_key and len(self.api_key) > 14 else '***'}")
        logger.info("=" * 80)
        
        # 实现日志易 API 调用（使用异步轮询方式）
        try:
            import requests
            import time
            from requests.adapters import HTTPAdapter
            from requests.packages.urllib3.util.retry import Retry
            
            # 验证配置完整性
            if not self.base_url or not self.api_key or not self.username:
                error_msg = "Logyi configuration incomplete: missing base_url, api_key, or username"
                logger.error(error_msg)
                return LogQueryResult(
                    logs=[],
                    total=0,
                    has_more=False,
                    query=spl_query,
                )
            
            # 步骤1: 提交搜索任务，获取 sid
            sid = self._submit_search(spl_query, start_time, end_time, limit)
            if not sid:
                return LogQueryResult(
                    logs=[],
                    total=0,
                    has_more=False,
                    query=spl_query,
                )
            
            # 步骤2: 轮询获取搜索结果（异步）
            # 由于 query 方法是同步的，但我们需要异步轮询，使用线程池来运行异步代码
            import asyncio
            import concurrent.futures
            import threading
            
            def run_async_polling():
                """在新的事件循环中运行异步轮询"""
                try:
                    # 创建新的事件循环（在单独的线程中）
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(
                            self._fetch_search_results(sid, limit, offset, max_wait_time=60000, poll_interval=1000)
                        )
                    finally:
                        loop.close()
                except KeyboardInterrupt:
                    logger.warning("  Log query interrupted by user")
                    return [], 0
                except Exception as e:
                    logger.error(f"  Error in async polling: {str(e)}", exc_info=True)
                    return [], 0
            
            try:
                # 使用线程池执行异步轮询，这样可以响应 KeyboardInterrupt
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(run_async_polling)
                    # 设置超时，稍长于 max_wait_time
                    logs, total = future.result(timeout=70)
            except KeyboardInterrupt:
                logger.warning("  Log query interrupted by user (KeyboardInterrupt)")
                return LogQueryResult(
                    logs=[],
                    total=0,
                    has_more=False,
                    query=spl_query,
                )
            except concurrent.futures.TimeoutError:
                logger.error("  Log query polling timeout")
                return LogQueryResult(
                    logs=[],
                    total=0,
                    has_more=False,
                    query=spl_query,
                )
            except Exception as e:
                logger.error(f"  Error in async polling: {str(e)}", exc_info=True)
                return LogQueryResult(
                    logs=[],
                    total=0,
                    has_more=False,
                    query=spl_query,
                )
            
            return LogQueryResult(
                logs=logs[:limit],
                total=total,
                has_more=total > offset + limit,
                query=spl_query,
            )
        
        except Exception as e:
            error_msg = f"Error executing Logyi query: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return LogQueryResult(
                logs=[],
                total=0,
                has_more=False,
                query=spl_query,
            )
    
    def _submit_search(
        self,
        query: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        max_lines: int = 100,
    ) -> Optional[str]:
        """
        提交搜索任务，获取搜索ID (sid)
        
        Args:
            query: SPL 查询语句
            start_time: 开始时间
            end_time: 结束时间
            max_lines: 最大返回条数
        
        Returns:
            搜索ID (sid)，如果失败返回 None
        """
        try:
            import requests
            import time
            
            # 构建查询URL
            url = f"{self.base_url.rstrip('/')}/api/v3/search/submit/"
            
            # 处理查询语句：如果查询不包含管道命令，添加 head 命令限制返回条数
            if "|" not in query:
                query_with_limit = f"{query} | head {max_lines}"
            else:
                query_with_limit = query
            
            # 处理时间范围
            if start_time and end_time:
                # 转换为时间戳（毫秒）
                start_ts = int(start_time.timestamp() * 1000)
                end_ts = int(end_time.timestamp() * 1000)
                time_range = f"{start_ts},{end_ts}"
            else:
                # 默认最近10分钟
                time_range = "-10m,now"
            
            # 构建查询参数（参考 logyi_service.py）
            params = {
                "username": self.username,
                "page": "0",
                "size": str(max_lines),
                "order": "desc",
                "datasets": "[]",
                "filters": "",
                "now": "",
                "test_mode": "false",
                "timeline": "true",
                "statsevents": "true",
                "fields": "true",
                "fromSearch": "true",
                "terminated_after_size": "",
                "searchMode": "intelligent",
                "market_day": "0",
                "highlight": "false",
                "onlySortByTimestamp": "false",
                "use_spark": "false",
                "parameters": "{}",
                "category": "search",
                "timezone": "Asia/Shanghai",
                "lang": "zh_CN",
                "_t": str(int(time.time() * 1000)),
                "version": "1",
                "query": query_with_limit,
                "time_range": time_range,
            }
            
            # 构建认证头
            headers = {
                "Accept": "application/json, text/plain, */*",
                "Authorization": f"apikey {self.api_key}",
            }
            
            logger.info(f"  Submitting search task: query={query_with_limit}, time_range={time_range}")
            
            # 发送请求
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=30,
            )
            
            logger.info(f"  Submit response status: {response.status_code}")
            
            # 检查响应
            if response.status_code != 200:
                logger.error(f"  Submit failed with status {response.status_code}: {response.text[:500]}")
                return None
            
            # 解析响应
            try:
                data = response.json()
            except Exception as e:
                logger.error(f"  Failed to parse submit response JSON: {e}, response text: {response.text[:500]}")
                return None
            
            # 检查错误
            if data.get("result") is False or data.get("error"):
                error_msg = data.get("error", {}).get("message") or data.get("message") or "未知错误"
                logger.error(f"  Submit search task failed: {error_msg}")
                return None
            
            # 获取 sid
            sid = data.get("sid") or (data.get("object") or {}).get("sid")
            if not sid:
                logger.error(f"  No sid in response: {str(data)[:500]}")
                return None
            
            logger.info(f"  Search task submitted successfully, sid: {sid}")
            return sid
            
        except Exception as e:
            logger.error(f"  Error submitting search task: {str(e)}", exc_info=True)
            return None
    
    async def _fetch_search_results(
        self,
        sid: str,
        max_lines: int = 100,
        offset: int = 0,
        max_wait_time: int = 60000,  # 毫秒
        poll_interval: int = 1000,  # 毫秒
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        轮询获取搜索结果（异步版本）
        
        Args:
            sid: 搜索ID
            max_lines: 最大返回条数
            offset: 偏移量
            max_wait_time: 最大等待时间（毫秒）
            poll_interval: 轮询间隔（毫秒）
        
        Returns:
            (logs列表, 总数)
        """
        try:
            import requests
            import asyncio
            import time
            
            url = f"{self.base_url.rstrip('/')}/api/v3/search/fetch/"
            
            # 构建认证头
            headers = {
                "Accept": "application/json, text/plain, */*",
                "Authorization": f"apikey {self.api_key}",
            }
            
            start_time = time.time() * 1000
            poll_count = 0
            
            logger.info(f"  Starting to poll search results (sid: {sid}, max_wait: {max_wait_time}ms)")
            
            def _make_request():
                """同步的 HTTP 请求函数"""
                params = {
                    "sid": sid,
                    "category": "sheets",
                    "page": str(offset // max_lines),  # 计算页码
                    "size": str(max_lines),
                    "username": self.username,
                }
                return requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=30,
                )
            
            while (time.time() * 1000 - start_time) < max_wait_time:
                poll_count += 1
                elapsed = int(time.time() * 1000 - start_time)
                
                logger.info(f"  Poll #{poll_count} (elapsed: {elapsed}ms)")
                
                try:
                    # 使用 asyncio.to_thread 将同步请求转换为异步
                    response = await asyncio.to_thread(_make_request)
                except asyncio.CancelledError:
                    logger.warning("  Polling cancelled by user")
                    raise
                except Exception as e:
                    logger.error(f"  Request failed: {str(e)}")
                    return [], 0
                
                if response.status_code != 200:
                    logger.error(f"  Fetch failed with status {response.status_code}: {response.text[:500]}")
                    return [], 0
                
                # 解析响应
                try:
                    data = response.json()
                except Exception as e:
                    logger.error(f"  Failed to parse fetch response JSON: {e}, response text: {response.text[:500]}")
                    return [], 0
                
                # 检查任务状态
                job_status = data.get("job_status") or data.get("status") or ""
                job_status_lower = job_status.lower() if job_status else ""
                
                if job_status_lower in ["running", "pending"]:
                    progress = data.get("progress", 0)
                    logger.info(f"  Search task running (status: {job_status}), progress: {progress}%")
                    # 使用异步 sleep，避免阻塞事件循环
                    try:
                        await asyncio.sleep(poll_interval / 1000)
                    except asyncio.CancelledError:
                        logger.warning("  Polling cancelled during sleep")
                        raise
                    continue
                
                if job_status_lower in ["failed", "error"]:
                    error_msg = data.get("error", {}).get("message") or data.get("message") or "搜索任务失败"
                    logger.error(f"  Search task failed: {error_msg}")
                    return [], 0
                
                # 任务完成，提取数据
                logger.info(f"  Search task completed (status: {job_status or 'unknown'})")
                return self._extract_logs_from_response(data, max_lines, offset)
            
            # 超时
            total_elapsed = int(time.time() * 1000 - start_time)
            logger.error(f"  Polling timeout after {total_elapsed}ms ({poll_count} polls)")
            return [], 0
            
        except asyncio.CancelledError:
            logger.warning("  Polling cancelled")
            raise
        except Exception as e:
            logger.error(f"  Error fetching search results: {str(e)}", exc_info=True)
            return [], 0
    
    def _extract_logs_from_response(
        self,
        response_data: Dict[str, Any],
        limit: int,
        offset: int,
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        从响应数据中提取日志
        
        Args:
            response_data: API 响应数据
            limit: 返回记录数限制
            offset: 偏移量
        
        Returns:
            (logs列表, 总数)
        """
        logs = []
        total = 0
        
        # 尝试多种可能的数据结构（参考 logyi_service.py）
        results = None
        
        if response_data.get("results"):
            results = response_data["results"]
        elif response_data.get("sheets") or response_data.get("fields") or response_data.get("data"):
            results = response_data
        elif response_data.get("object"):
            results = response_data["object"]
        
        if not results:
            logger.warning("  No results found in response")
            return [], 0
        
        # 从 sheets 中提取数据
        if results.get("sheets") and isinstance(results["sheets"], dict):
            for sheet_key, sheet in results["sheets"].items():
                logger.info(f"  Processing sheet: {sheet_key}")
                if isinstance(sheet, list):
                    logs.extend(sheet)
                elif isinstance(sheet, dict) and isinstance(sheet.get("data"), list):
                    logs.extend(sheet["data"])
        
        # 如果 sheets 为空，尝试从 fields 中提取
        if not logs and results.get("fields") and isinstance(results["fields"], list):
            for field in results["fields"]:
                if field.get("topk") and isinstance(field["topk"], list):
                    for item in field["topk"]:
                        logs.append({
                            "field": field.get("name"),
                            "value": item.get("value"),
                            "count": item.get("count"),
                        })
        
        # 获取总数
        total = results.get("total_hits", len(logs))
        
        # 格式化日志数据
        formatted_logs = []
        for log in logs:
            if isinstance(log, dict):
                formatted = {**log}
                
                # 确保时间戳字段存在
                if not formatted.get("timestamp"):
                    formatted["timestamp"] = (
                        log.get("timestamp") or
                        log.get("time") or
                        log.get("@timestamp") or
                        log.get("date") or
                        ""
                    )
                
                # 确保日志级别字段存在
                if not formatted.get("level"):
                    formatted["level"] = (
                        log.get("level") or
                        log.get("severity") or
                        log.get("log_level") or
                        "INFO"
                    )
                
                # 确保消息字段存在
                if not formatted.get("message"):
                    formatted["message"] = (
                        log.get("message") or
                        log.get("msg") or
                        log.get("content") or
                        str(log)
                    )
                
                formatted_logs.append(formatted)
            else:
                # 如果不是字典，转换为字符串
                formatted_logs.append({
                    "timestamp": "",
                    "level": "INFO",
                    "message": str(log),
                    "raw": log,
                })
        
        logger.info(f"  Extracted {len(formatted_logs)} logs, total: {total}")
        return formatted_logs, total


class FileLogQuery(LogQueryInterface):
    """文件日志查询实现"""
    
    def __init__(self):
        self.base_path = settings.log_file_base_path
        
        if not self.base_path:
            logger.warning("Log file base path not configured, FileLogQuery may not work properly")
    
    def _find_log_files(self, appname: str) -> List[str]:
        """根据 appname 查找日志文件"""
        from pathlib import Path
        
        if not self.base_path:
            return []
        
        base = Path(self.base_path)
        if not base.exists():
            return []
        
        log_files = []
        
        # 查找匹配的日志文件
        # 假设日志文件命名格式：{appname}.log 或 {appname}-*.log
        for file_path in base.rglob(f"{appname}*.log"):
            log_files.append(str(file_path))
        
        # 也查找通用日志文件
        for file_path in base.rglob("*.log"):
            if appname in str(file_path):
                if str(file_path) not in log_files:
                    log_files.append(str(file_path))
        
        return log_files
    
    def validate_query(self, query: str) -> tuple[bool, Optional[str]]:
        """验证查询语句（文件日志使用简单关键词查询）"""
        if not query or not query.strip():
            return False, "Query cannot be empty"
        
        return True, None
    
    def query(
        self,
        appname: str,
        query: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> LogQueryResult:
        """执行文件日志查询"""
        
        if not appname:
            return LogQueryResult(
                logs=[],
                total=0,
                has_more=False,
                query=query,
            )
        
        # 查找日志文件
        log_files = self._find_log_files(appname)
        
        if not log_files:
            logger.warning(f"No log files found for appname: {appname}")
            return LogQueryResult(
                logs=[],
                total=0,
                has_more=False,
                query=query,
            )
        
        # 搜索日志
        results = []
        query_lower = query.lower()
        
        for log_file in log_files[:5]:  # 限制搜索文件数量
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        if query_lower in line.lower():
                            # 尝试解析日志行
                            log_entry = self._parse_log_line(line, log_file, line_num)
                            if log_entry:
                                results.append(log_entry)
                                
                                if len(results) >= limit:
                                    break
            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {str(e)}")
                continue
            
            if len(results) >= limit:
                break
        
        return LogQueryResult(
            logs=results[offset:offset+limit],
            total=len(results),
            has_more=len(results) > offset + limit,
            query=query,
        )
    
    def _parse_log_line(self, line: str, file_path: str, line_num: int) -> Optional[Dict[str, Any]]:
        """解析日志行"""
        line = line.strip()
        if not line:
            return None
        
        # 简单的日志解析（可以根据实际格式扩展）
        import re
        
        # 尝试匹配常见日志格式：时间戳 级别 消息
        timestamp_pattern = r'(\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2})'
        level_pattern = r'\b(ERROR|WARN|INFO|DEBUG|FATAL)\b'
        
        timestamp_match = re.search(timestamp_pattern, line)
        level_match = re.search(level_pattern, line, re.IGNORECASE)
        
        return {
            "timestamp": timestamp_match.group(1) if timestamp_match else datetime.now().isoformat(),
            "level": level_match.group(1) if level_match else "INFO",
            "message": line,
            "file": file_path,
            "line": line_num,
        }


def get_log_query_instance() -> LogQueryInterface:
    """获取日志查询实例（工厂方法）"""
    query_type = settings.log_query_type.lower()
    
    if query_type == "file":
        return FileLogQuery()
    elif query_type == "logyi":
        return LogyiLogQuery()
    else:
        logger.warning(f"Unknown log query type: {query_type}, defaulting to file")
        return FileLogQuery()

