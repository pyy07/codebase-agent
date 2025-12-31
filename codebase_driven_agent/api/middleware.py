"""API 中间件"""
import time
from typing import Callable
from collections import defaultdict
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from codebase_driven_agent.config import settings
from codebase_driven_agent.utils.logger import setup_logger
from codebase_driven_agent.utils.metrics import record_request_metrics

logger = setup_logger("codebase_driven_agent.api.middleware")


class APIKeyMiddleware(BaseHTTPMiddleware):
    """API Key 认证中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        # 排除健康检查和文档接口
        if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc", "/api/v1/info"]:
            return await call_next(request)
        
        # 检查是否配置了 API Key
        if settings.api_key:
            api_key = request.headers.get(settings.api_key_header)
            
            if not api_key or api_key != settings.api_key:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid or missing API key"}
                )
        
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """请求限流中间件"""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)  # {client_ip: [timestamps]}
    
    async def dispatch(self, request: Request, call_next: Callable):
        # 排除健康检查和文档接口
        if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc", "/api/v1/info"]:
            return await call_next(request)
        
        # 获取客户端IP
        client_ip = request.client.host if request.client else "unknown"
        
        # 清理过期记录
        now = time.time()
        self.requests[client_ip] = [
            ts for ts in self.requests[client_ip]
            if now - ts < 60  # 保留最近60秒的记录
        ]
        
        # 检查限流
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded"}
            )
        
        # 记录请求
        self.requests[client_ip].append(now)
        
        return await call_next(request)


class MetricsMiddleware(BaseHTTPMiddleware):
    """指标收集中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        import time
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # 记录指标
            endpoint = request.url.path
            method = request.method
            status_code = response.status_code
            
            record_request_metrics(endpoint, method, status_code, duration)
            
            return response
        except Exception:
            duration = time.time() - start_time
            endpoint = request.url.path
            method = request.method
            
            # 记录错误指标
            record_request_metrics(endpoint, method, 500, duration)
            raise


class InputValidationMiddleware(BaseHTTPMiddleware):
    """输入验证中间件（防止 Prompt Injection）"""
    
    # 危险关键词列表（可以根据需要扩展）
    DANGEROUS_PATTERNS = [
        "ignore previous instructions",
        "forget all previous",
        "you are now",
        "system:",
        "assistant:",
        "user:",
        "ignore the above",
        "disregard",
    ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        # 只对分析接口进行验证
        if request.url.path.startswith("/api/v1/analyze"):
            # 读取请求体
            body = await request.body()
            
            # 检查请求体大小（防止过大请求）
            if len(body) > 10 * 1024 * 1024:  # 10MB
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={"detail": "Request body too large"}
                )
            
            # 检查危险模式（简单检查，后续可以更复杂）
            body_text = body.decode("utf-8", errors="ignore").lower()
            for pattern in self.DANGEROUS_PATTERNS:
                if pattern.lower() in body_text:
                    logger.warning(f"Potential prompt injection detected: {pattern}")
                    # 可以选择拒绝请求或记录警告
                    # return JSONResponse(
                    #     status_code=status.HTTP_400_BAD_REQUEST,
                    #     content={"detail": "Invalid input detected"}
                    # )
        
        return await call_next(request)

