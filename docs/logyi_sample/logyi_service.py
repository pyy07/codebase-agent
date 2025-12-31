"""
日志易服务模块
提供从日志易系统获取日志的功能
"""
import logging
import time
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..config import logyi_config

logger = logging.getLogger(__name__)


class LogyiService:
    """
    日志易服务类
    封装日志易 API 调用逻辑
    """
    
    def __init__(self, config=None):
        """
        初始化日志易服务
        
        Args:
            config: 日志易配置对象，如果不提供则使用全局配置
        """
        self.config = config or logyi_config
        self.base_url = self.config.base_url
        self.username = self.config.username
        self.apikey = self.config.apikey
        self.appname = self.config.appname
        
        logger.info(
            f"[LogyiService] 初始化 - BaseURL: {self.base_url}, "
            f"用户名: {self.username or '(未配置)'}, "
            f"API Key: {'***已配置***' if self.apikey else '(未配置)'}, "
            f"应用名称: {self.appname or '(未配置)'}"
        )
        
        if not self.config.is_configured():
            logger.warning("[LogyiService] 未配置日志易认证信息（需要 LOGYI_APIKEY 和 LOGYI_USERNAME）")
    
    def _get_auth_headers(self, include_content_type: bool = False) -> dict:
        """获取认证头"""
        return self.config.get_auth_headers(include_content_type)
    
    def submit_search(
        self,
        query: str = "*",
        time_range: Optional[Dict[str, str]] = None,
        max_lines: int = 20
    ) -> str:
        """
        提交搜索任务，获取搜索ID (sid)
        
        Args:
            query: SPL 搜索查询语句
            time_range: 时间范围 {"start": "-5m", "end": "now"} 或 {"start": "2024-01-01 00:00:00", "end": "2024-01-01 23:59:59"}
            max_lines: 最大返回条数
        
        Returns:
            搜索ID (sid)
        """
        try:
            # 如果配置了 appname，自动添加到查询中
            if self.appname:
                # 检查查询中是否已经包含 appname
                if "appname:" not in query.lower():
                    # 如果查询是 "*" 或空，直接使用 appname
                    if query.strip() == "*" or not query.strip():
                        query = f"appname:{self.appname}"
                    else:
                        # 否则在查询前添加 appname 过滤
                        query = f"appname:{self.appname} {query}"
                    logger.debug(f"[LogyiService] 自动添加 appname 过滤: appname:{self.appname}")
            
            # 构建查询URL
            url = f"{self.base_url}/api/v3/search/submit/"
            
            # 构建查询参数
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
                "version": "1"
            }
            
            # 添加查询语句
            # 根据 SPL 规范，查询必须包含管道命令（pipeCommands）
            # 如果查询为空或仅为 "*"，需要添加默认的管道命令
            if not query or query.strip() == "*":
                # 默认查询：查询所有并限制返回条数
                params["query"] = f"* | head {max_lines}"
            else:
                # 如果查询不包含管道命令，添加 head 命令限制返回条数
                query = query.strip()
                if "|" not in query:
                    # 没有管道命令，添加 head 命令
                    params["query"] = f"{query} | head {max_lines}"
                else:
                    # 已有管道命令，直接使用
                    params["query"] = query
            
            # 处理时间范围
            if time_range and time_range.get("start") and time_range.get("end"):
                start_str = str(time_range["start"])
                end_str = str(time_range["end"])
                
                # 规范化时间格式（将常见格式转换为日志易支持的格式）
                start_str = self._normalize_time(start_str)
                end_str = self._normalize_time(end_str)
                
                # 如果是相对时间格式（如 "-5m,now"、"now/d,now"），直接使用
                if (start_str.startswith("-") or start_str.startswith("now")) and (end_str == "now" or end_str.startswith("now")):
                    params["time_range"] = f"{start_str},{end_str}"
                else:
                    # 尝试解析为时间戳
                    try:
                        start_time = self._parse_time(start_str)
                        end_time = self._parse_time(end_str)
                        params["time_range"] = f"{start_time},{end_time}"
                    except Exception as e:
                        logger.warning(f"[LogyiService] 时间解析失败: {e}，使用默认时间范围")
                        params["time_range"] = "-10m,now"
            else:
                params["time_range"] = "-10m,now"
            
            logger.info(f"[LogyiService] 提交搜索任务: query={params.get('query', '')}, time_range={params.get('time_range')}")
            
            # 发送请求（使用 requests 同步库）
            response = requests.get(
                url,
                params=params,
                headers=self._get_auth_headers(False),
                timeout=30
            )
            
            logger.info(f"[LogyiService] 响应状态: {response.status_code}")
            
            # 先获取原始响应文本
            response_text = response.text
            logger.info(f"[LogyiService] 响应内容前500字符: {response_text[:500]}")
            
            # 尝试解析 JSON
            try:
                data = response.json()
            except Exception as json_err:
                logger.error(f"[LogyiService] JSON解析失败: {json_err}, 响应内容: {response_text[:1000]}")
                raise ValueError(f"日志易API返回非JSON响应: {response_text[:500]}")
                logger.info(f"[LogyiService] 响应数据: {str(data)[:500]}")
                
            # 检查错误
            if response.status_code != 200 or data.get("result") is False or data.get("error"):
                error_msg = data.get("error", {}).get("message") or data.get("message") or "未知错误"
                error_code = data.get("error", {}).get("code") or ""
                
                if any(keyword in str(error_msg) for keyword in ["password", "account", "apikey"]) or error_code == "1100":
                    raise ValueError(f"日志易认证失败: {error_msg}。请检查 LOGYI_APIKEY 和 LOGYI_USERNAME 配置是否正确。")
                
                raise ValueError(f"日志易提交搜索任务失败: [{error_code}] {error_msg}")
            
            # 获取 sid
            sid = data.get("sid") or (data.get("object") or {}).get("sid")
            if not sid:
                raise ValueError(f"搜索任务响应中未找到 sid。响应数据: {str(data)[:500]}")
            
            logger.info(f"[LogyiService] 搜索任务提交成功，获取到 sid: {sid}")
            return sid
                
        except Exception as e:
            logger.error(f"[LogyiService] 提交搜索任务失败: {e}")
            raise
    
    def _normalize_time(self, time_str: str) -> str:
        """
        规范化时间字符串，将常见格式转换为日志易支持的格式
        
        Args:
            time_str: 时间字符串
        
        Returns:
            规范化后的时间字符串
        """
        time_str = time_str.strip().lower()
        
        # 处理常见相对时间格式
        if time_str == "today":
            return "now/d"  # 今天开始
        elif time_str == "yesterday":
            return "now/d-1d"  # 昨天开始
        elif time_str == "now":
            return "now"
        elif time_str.startswith("today-"):
            # 处理 "today-1" 格式，转换为 "now/d-1d"
            try:
                days = int(time_str.split("-")[-1])
                if days == 0:
                    return "now/d"
                else:
                    return f"now/d-{days}d"
            except (ValueError, IndexError):
                return "now/d"
        elif time_str.startswith("yesterday-"):
            # 处理 "yesterday-1" 格式
            try:
                days = int(time_str.split("-")[-1])
                return f"now/d-{days+1}d"
            except (ValueError, IndexError):
                return "now/d-1d"
        
        # 如果不是特殊格式，返回原字符串
        return time_str
    
    def _parse_time(self, time_str: str) -> int:
        """
        解析时间字符串为时间戳（毫秒）
        
        Args:
            time_str: 时间字符串，支持格式：
                - "2024-01-01 00:00:00"
                - "2024-01-01"
                - 时间戳字符串
        
        Returns:
            时间戳（毫秒）
        """
        # 如果已经是数字，直接返回
        if time_str.isdigit():
            ts = int(time_str)
            # 如果是秒级时间戳，转换为毫秒
            if ts < 10000000000:
                return ts * 1000
            return ts
        
        # 尝试解析各种日期格式
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d"
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(time_str, fmt)
                return int(dt.timestamp() * 1000)
            except ValueError:
                continue
        
        raise ValueError(f"无法解析时间格式: {time_str}")
    
    def fetch_search_results(
        self,
        sid: str,
        category: str = "sheets",
        page: int = 0,
        size: int = 20
    ) -> Dict[str, Any]:
        """
        获取异步搜索结果
        
        Args:
            sid: 搜索ID
            category: 类别（默认: "sheets"）
            page: 页码（默认: 0）
            size: 每页大小（默认: 20）
        
        Returns:
            搜索结果字典，包含 status 和 data
        """
        try:
            url = f"{self.base_url}/api/v3/search/fetch/"
            params = {
                "sid": sid,
                "category": category,
                "page": str(page),
                "size": str(size),
                "username": self.username
            }
            
            logger.info(f"[LogyiService] 获取搜索结果: sid={sid}")
            
            response = requests.get(
                url,
                params=params,
                headers=self._get_auth_headers(False),
                timeout=30
            )
            
            data = response.json()
            logger.info(f"[LogyiService] fetch 响应状态: {response.status_code}")
            logger.info(f"[LogyiService] fetch 响应数据: {str(data)[:1000]}")
            
            # 检查 API 错误响应
            if response.status_code != 200:
                error_msg = data.get("error", {}).get("message") or data.get("message") or "未知错误"
                error_code = data.get("error", {}).get("code") or ""
                
                if any(keyword in str(error_msg) for keyword in ["password", "account", "apikey"]) or error_code == "1100":
                    raise ValueError(f"日志易认证失败: {error_msg}")
                
                raise ValueError(f"日志易获取结果失败: [{error_code}] {error_msg}")
            
            # 检查任务状态
            job_status = data.get("job_status") or data.get("status") or ""
            job_status_lower = job_status.lower() if job_status else ""
            
            if job_status_lower in ["running", "pending"]:
                progress = data.get("progress", 0)
                logger.info(f"[LogyiService] 搜索任务进行中 (状态: {job_status})，进度: {progress}%")
                return {"status": "running", "data": data, "sid": sid}
            
            if job_status_lower in ["failed", "error"]:
                error_msg = data.get("error", {}).get("message") or data.get("message") or "搜索任务失败"
                raise ValueError(f"日志易搜索任务失败: {error_msg}")
            
            # 任务完成
            logger.info(f"[LogyiService] 搜索任务完成 (状态: {job_status or '未知'})")
            return {"status": "completed", "data": data, "sid": sid}
                
        except Exception as e:
            logger.error(f"[LogyiService] 获取搜索结果失败: {e}")
            raise
    
    def wait_for_search_results(
        self,
        sid: str,
        max_wait_time: int = 60000,
        poll_interval: int = 1000,
        size: int = 20
    ) -> Dict[str, Any]:
        """
        等待搜索完成并获取结果
        
        Args:
            sid: 搜索ID
            max_wait_time: 最大等待时间（毫秒，默认: 60000）
            poll_interval: 轮询间隔（毫秒，默认: 1000）
            size: 每页大小
        
        Returns:
            搜索结果
        """
        start_time = time.time() * 1000
        poll_count = 0
        
        logger.info(f"[LogyiService] 开始轮询搜索结果 (sid: {sid}, 最大等待时间: {max_wait_time}ms)")
        
        while (time.time() * 1000 - start_time) < max_wait_time:
            poll_count += 1
            elapsed = int(time.time() * 1000 - start_time)
            logger.info(f"[LogyiService] 第 {poll_count} 次轮询 (已等待: {elapsed}ms)")
            
            result = self.fetch_search_results(sid, size=size)
            
            if result["status"] == "completed":
                logger.info(f"[LogyiService] 搜索完成，共轮询 {poll_count} 次，耗时 {elapsed}ms")
                return result
            
            if result["status"] == "running":
                logger.info(f"[LogyiService] 任务进行中，等待 {poll_interval}ms 后继续轮询...")
                self._sleep(poll_interval / 1000)
                continue
            
            logger.warning(f"[LogyiService] 未知的状态: {result['status']}，继续等待...")
            self._sleep(poll_interval / 1000)
        
        total_elapsed = int(time.time() * 1000 - start_time)
        raise TimeoutError(f"等待搜索结果超时 (已等待 {total_elapsed}ms，轮询 {poll_count} 次)")
    
    def _sleep(self, seconds: float):
        """同步休眠"""
        time.sleep(seconds)
    
    def fetch_logs(
        self,
        query: str = "*",
        time_range: Optional[Dict[str, str]] = None,
        max_lines: int = 100
    ) -> List[Dict[str, Any]]:
        """
        从日志易获取日志
        
        Args:
            query: SPL 搜索查询语句
            time_range: 时间范围 {"start": "-5m", "end": "now"}
            max_lines: 最大返回条数
        
        Returns:
            日志数据列表
        """
        try:
            # 1. 提交搜索任务获取 sid
            sid = self.submit_search(query=query, time_range=time_range, max_lines=max_lines)
            
            # 2. 等待搜索完成并获取结果
            result = self.wait_for_search_results(sid, size=min(max_lines, 10000))
            
            # 3. 解析返回数据
            response_data = result.get("data", {})
            
            logger.info(f"[LogyiService] 响应数据的顶级键: {list(response_data.keys())}")
            
            if not response_data:
                logger.warning("[LogyiService] 响应数据为空")
                return []
            
            # 尝试多种可能的数据结构
            results = None
            logs = []
            
            # 情况1: 数据在 responseData.results 中
            if response_data.get("results"):
                results = response_data["results"]
            # 情况2: 数据直接在 responseData 中
            elif response_data.get("sheets") or response_data.get("fields") or response_data.get("data"):
                results = response_data
            # 情况3: 数据在 responseData.object 中
            elif response_data.get("object"):
                results = response_data["object"]
            
            if not results:
                logger.warning(f"[LogyiService] 无法找到结果数据")
                return []
            
            # 从 sheets 中提取数据
            if results.get("sheets") and isinstance(results["sheets"], dict):
                for sheet_key, sheet in results["sheets"].items():
                    logger.info(f"[LogyiService] 处理 sheet: {sheet_key}")
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
                                "count": item.get("count")
                            })
            
            if not logs:
                logger.warning("[LogyiService] 无法从响应中提取日志数据")
                return []
            
            # 格式化日志数据
            formatted_logs = []
            for log in logs:
                formatted = {**log}
                
                # 确保时间戳字段存在
                if not formatted.get("timestamp"):
                    formatted["timestamp"] = (
                        log.get("timestamp") or 
                        log.get("time") or 
                        log.get("@timestamp") or 
                        log.get("date")
                    )
                
                # 确保日志级别字段存在
                if not formatted.get("level"):
                    formatted["level"] = (
                        log.get("level") or 
                        log.get("severity") or 
                        log.get("log_level") or 
                        "INFO"
                    )
                
                # 确保内容字段存在
                if not formatted.get("content") and not formatted.get("raw_message"):
                    formatted["content"] = log.get("message") or log.get("msg") or ""
                
                formatted_logs.append(formatted)
            
            total_hits = results.get("total_hits", 0)
            logger.info(f"[LogyiService] 成功获取 {len(formatted_logs)} 条日志（总命中数: {total_hits}）")
            return formatted_logs
            
        except Exception as e:
            logger.error(f"[LogyiService] 获取日志失败: {e}")
            raise


# 全局日志易服务实例
logyi_service = LogyiService()

