"""请求缓存和去重工具"""
import hashlib
import json
import threading
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from codebase_driven_agent.config import settings
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.utils.cache")


class RequestCache:
    """请求缓存和去重"""
    
    def __init__(self, ttl: int = 3600, max_size: int = 1000):
        """
        初始化缓存
        
        Args:
            ttl: 缓存过期时间（秒），默认 1 小时
            max_size: 最大缓存条目数，默认 1000
        """
        self.ttl = ttl
        self.max_size = max_size
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._access_times: Dict[str, datetime] = {}  # 记录访问时间，用于 LRU
    
    def _generate_key(self, request_data: Dict[str, Any]) -> str:
        """
        生成缓存键
        
        Args:
            request_data: 请求数据（包含 input 和 context_files）
        
        Returns:
            缓存键（MD5 hash）
        """
        # 规范化请求数据（排序、去除 None 值）
        normalized = {
            "input": request_data.get("input", "").strip(),
            "context_files": self._normalize_context_files(request_data.get("context_files", [])),
        }
        
        # 转换为 JSON 字符串并计算 hash
        json_str = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(json_str.encode('utf-8')).hexdigest()
    
    def _normalize_context_files(self, context_files: list) -> list:
        """规范化上下文文件（用于生成缓存键）"""
        normalized = []
        for ctx_file in context_files:
            if isinstance(ctx_file, dict):
                normalized.append({
                    "type": ctx_file.get("type"),
                    "path": ctx_file.get("path", "").strip(),
                    "content": ctx_file.get("content", "").strip(),
                    "line_start": ctx_file.get("line_start"),
                    "line_end": ctx_file.get("line_end"),
                })
            else:
                # 如果是 Pydantic 模型，转换为字典
                normalized.append({
                    "type": getattr(ctx_file, "type", None),
                    "path": getattr(ctx_file, "path", "").strip() if hasattr(ctx_file, "path") else "",
                    "content": getattr(ctx_file, "content", "").strip() if hasattr(ctx_file, "content") else "",
                    "line_start": getattr(ctx_file, "line_start", None),
                    "line_end": getattr(ctx_file, "line_end", None),
                })
        return normalized
    
    def get(self, request_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        获取缓存结果
        
        Args:
            request_data: 请求数据
        
        Returns:
            缓存的结果，如果不存在或已过期则返回 None
        """
        cache_key = self._generate_key(request_data)
        
        with self._lock:
            if cache_key not in self._cache:
                return None
            
            cached_item = self._cache[cache_key]
            
            # 检查是否过期
            if datetime.now() - cached_item["created_at"] > timedelta(seconds=self.ttl):
                del self._cache[cache_key]
                if cache_key in self._access_times:
                    del self._access_times[cache_key]
                logger.debug(f"Cache expired for key: {cache_key[:8]}...")
                return None
            
            # 更新访问时间
            self._access_times[cache_key] = datetime.now()
            
            logger.debug(f"Cache hit for key: {cache_key[:8]}...")
            return cached_item["result"]
    
    def set(self, request_data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        设置缓存结果
        
        Args:
            request_data: 请求数据
            result: 结果数据
        """
        cache_key = self._generate_key(request_data)
        
        with self._lock:
            # 检查缓存大小，如果超过限制则删除最旧的条目（LRU）
            if len(self._cache) >= self.max_size and cache_key not in self._cache:
                self._evict_lru()
            
            self._cache[cache_key] = {
                "result": result,
                "created_at": datetime.now(),
            }
            self._access_times[cache_key] = datetime.now()
            
            logger.debug(f"Cached result for key: {cache_key[:8]}...")
    
    def _evict_lru(self):
        """删除最近最少使用的条目（LRU）"""
        if not self._access_times:
            # 如果没有访问时间记录，删除最旧的缓存条目
            if self._cache:
                oldest_key = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k]["created_at"]
                )
                del self._cache[oldest_key]
            return
        
        # 找到最近最少使用的条目
        lru_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
        del self._cache[lru_key]
        del self._access_times[lru_key]
        logger.debug(f"Evicted LRU cache entry: {lru_key[:8]}...")
    
    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()
            logger.info("Cache cleared")
    
    def cleanup_expired(self) -> int:
        """
        清理过期条目
        
        Returns:
            清理的条目数
        """
        now = datetime.now()
        expired_keys = []
        
        with self._lock:
            for cache_key, cached_item in self._cache.items():
                if now - cached_item["created_at"] > timedelta(seconds=self.ttl):
                    expired_keys.append(cache_key)
            
            for cache_key in expired_keys:
                del self._cache[cache_key]
                if cache_key in self._access_times:
                    del self._access_times[cache_key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl": self.ttl,
                "usage_percent": len(self._cache) / self.max_size * 100 if self.max_size > 0 else 0,
            }


# 全局缓存实例
_request_cache: Optional[RequestCache] = None
_cache_lock = threading.Lock()


def get_request_cache() -> Optional[RequestCache]:
    """获取请求缓存实例（单例模式）"""
    global _request_cache
    
    # 检查是否启用缓存
    cache_enabled = getattr(settings, 'cache_enabled', True)
    if not cache_enabled:
        return None
    
    if _request_cache is None:
        with _cache_lock:
            if _request_cache is None:
                # 从配置读取缓存参数（如果配置了）
                cache_ttl = getattr(settings, 'cache_ttl', 3600)
                cache_max_size = getattr(settings, 'cache_max_size', 1000)
                _request_cache = RequestCache(ttl=cache_ttl, max_size=cache_max_size)
    
    return _request_cache


def clear_request_cache() -> None:
    """清空请求缓存"""
    cache = get_request_cache()
    cache.clear()

