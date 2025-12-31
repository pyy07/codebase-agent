"""FastAPI 应用入口"""
import asyncio
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from codebase_driven_agent.utils.logger import setup_logger
from codebase_driven_agent.api.routes import router as analysis_router
from codebase_driven_agent.api.sse import router as sse_router
from codebase_driven_agent.api.middleware import (
    APIKeyMiddleware,
    RateLimitMiddleware,
    InputValidationMiddleware,
    MetricsMiddleware,
)
from codebase_driven_agent.utils.metrics import get_metrics_collector
from codebase_driven_agent.config import settings

# 配置日志（从配置读取日志级别）
logger = setup_logger("codebase_driven_agent", level_name=settings.log_level)


def print_configuration():
    """打印读取到的配置"""
    logger.info("=" * 80)
    logger.info("Application Configuration:")
    logger.info("=" * 80)
    
    # API 配置
    logger.info("API Configuration:")
    logger.info(f"  API_KEY: {'***' if settings.api_key else 'None'}")
    logger.info(f"  API_KEY_HEADER: {settings.api_key_header}")
    
    # LLM 配置
    logger.info("LLM Configuration:")
    logger.info(f"  OPENAI_API_KEY: {settings.openai_api_key[:10] + '...' + settings.openai_api_key[-4:] if settings.openai_api_key and len(settings.openai_api_key) > 14 else ('***' if settings.openai_api_key else 'None')}")
    logger.info(f"  OPENAI_BASE_URL: {settings.openai_base_url}")
    logger.info(f"  ANTHROPIC_API_KEY: {'***' if settings.anthropic_api_key else 'None'}")
    logger.info(f"  LLM_PROVIDER: {settings.llm_provider}")
    logger.info(f"  LLM_BASE_URL: {settings.llm_base_url}")
    logger.info(f"  LLM_API_KEY: {settings.llm_api_key[:10] + '...' + settings.llm_api_key[-4:] if settings.llm_api_key and len(settings.llm_api_key) > 14 else ('***' if settings.llm_api_key else 'None')}")
    logger.info(f"  LLM_MODEL: {settings.llm_model}")
    logger.info(f"  LLM_TEMPERATURE: {settings.llm_temperature}")
    logger.info(f"  LLM_MAX_TOKENS: {settings.llm_max_tokens}")
    
    # 日志查询配置
    logger.info("Log Query Configuration:")
    logger.info(f"  LOG_QUERY_TYPE: {settings.log_query_type}")
    logger.info(f"  LOGYI_BASE_URL: {settings.logyi_base_url}")
    logger.info(f"  LOGYI_USERNAME: {settings.logyi_username}")
    logger.info(f"  LOGYI_APIKEY: {'***' if settings.logyi_apikey else 'None'}")
    logger.info(f"  LOGYI_APPNAME: {settings.logyi_appname}")
    logger.info(f"  LOG_FILE_BASE_PATH: {settings.log_file_base_path}")
    
    # 数据库配置
    logger.info("Database Configuration:")
    logger.info(f"  DATABASE_URL: {'***' if settings.database_url else 'None'}")
    
    # Agent 配置
    logger.info("Agent Configuration:")
    logger.info(f"  AGENT_MAX_ITERATIONS: {settings.agent_max_iterations}")
    logger.info(f"  AGENT_MAX_EXECUTION_TIME: {settings.agent_max_execution_time}")
    
    # 代码仓库配置
    logger.info("Code Repository Configuration:")
    logger.info(f"  CODE_REPO_PATH: {settings.code_repo_path}")
    
    # 缓存配置
    logger.info("Cache Configuration:")
    logger.info(f"  CACHE_ENABLED: {settings.cache_enabled}")
    logger.info(f"  CACHE_TTL: {settings.cache_ttl}")
    logger.info(f"  CACHE_MAX_SIZE: {settings.cache_max_size}")
    
    # 日志配置
    logger.info("Logging Configuration:")
    logger.info(f"  LOG_LEVEL: {settings.log_level}")
    
    logger.info("=" * 80)

app = FastAPI(
    title="Codebase Driven Agent",
    description="基于代码库驱动的通用 AI Agent 平台。当前阶段专注于问题分析和错误排查，未来将扩展到更多代码库驱动场景。",
    version="0.1.0",
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 认证中间件
app.add_middleware(APIKeyMiddleware)

# 请求限流中间件
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

# 输入验证中间件
app.add_middleware(InputValidationMiddleware)

# 指标收集中间件
app.add_middleware(MetricsMiddleware)

# 打印配置信息
print_configuration()

# 注册路由
app.include_router(analysis_router)
app.include_router(sse_router)


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy"}


@app.get("/api/v1/info")
async def get_info():
    """服务信息接口"""
    return {
        "name": "Codebase Driven Agent",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/api/v1/metrics")
async def metrics():
    """获取指标信息（Prometheus 格式）"""
    collector = get_metrics_collector()
    metrics_data = collector.get_metrics()
    return metrics_data


@app.get("/api/v1/cache/stats")
async def cache_stats():
    """获取缓存统计信息"""
    from codebase_driven_agent.utils.cache import get_request_cache
    cache = get_request_cache()
    if cache:
        return cache.get_stats()
    return {"enabled": False}


@app.post("/api/v1/cache/clear")
async def clear_cache():
    """清空缓存"""
    from codebase_driven_agent.utils.cache import clear_request_cache
    clear_request_cache()
    return {"status": "cleared"}


@app.get("/api/v1/tools")
async def list_tools():
    """列出所有注册的工具"""
    from codebase_driven_agent.tools.registry import get_tool_registry
    registry = get_tool_registry()
    return registry.list_tools()


@app.post("/api/v1/tools/{tool_name}/enable")
async def enable_tool(tool_name: str):
    """启用工具"""
    from codebase_driven_agent.tools.registry import get_tool_registry
    registry = get_tool_registry()
    success = registry.enable_tool(tool_name)
    if success:
        return {"status": "enabled", "tool": tool_name}
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")


@app.post("/api/v1/tools/{tool_name}/disable")
async def disable_tool(tool_name: str):
    """禁用工具"""
    from codebase_driven_agent.tools.registry import get_tool_registry
    registry = get_tool_registry()
    success = registry.disable_tool(tool_name)
    if success:
        return {"status": "disabled", "tool": tool_name}
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")


def _start_cache_cleanup_task():
    """启动缓存清理后台任务"""
    def cleanup_loop():
        import time
        from codebase_driven_agent.utils.cache import get_request_cache
        
        while True:
            try:
                time.sleep(300)  # 每 5 分钟清理一次
                cache = get_request_cache()
                if cache:
                    cache.cleanup_expired()
            except KeyboardInterrupt:
                logger.info("Cache cleanup task interrupted")
                break
            except Exception as e:
                logger.error(f"Cache cleanup error: {str(e)}", exc_info=True)
    
    cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
    cleanup_thread.start()
    logger.info("Cache cleanup task started")


# 启动后台任务
_start_cache_cleanup_task()


if __name__ == "__main__":
    import uvicorn
    import signal
    import sys
    
    def signal_handler(sig, frame):
        """处理 Ctrl+C 信号"""
        logger.info("\n收到中断信号 (Ctrl+C)，正在关闭服务...")
        sys.exit(0)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        logger.info("服务被用户中断")
        sys.exit(0)

