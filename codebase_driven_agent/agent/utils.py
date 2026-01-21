"""Agent 工具函数"""
from typing import List
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from codebase_driven_agent.tools import CodeTool, LogTool, DatabaseTool
from codebase_driven_agent.config import settings
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.agent.utils")

# 启用 OpenAI 客户端的详细日志
import logging
openai_logger = logging.getLogger("openai")
openai_logger.setLevel(logging.DEBUG)


def create_llm():
    """创建 LLM 实例"""
    logger.info("Creating LLM instance...")
    logger.info("=" * 80)
    logger.info("Checking LLM Configuration:")
    logger.info(f"  LLM_BASE_URL: {settings.llm_base_url}")
    logger.info(f"  LLM_API_KEY: {'***' if settings.llm_api_key else 'None'}")
    logger.info(f"  OPENAI_BASE_URL: {settings.openai_base_url}")
    logger.info(f"  OPENAI_API_KEY: {'***' if settings.openai_api_key else 'None'}")
    logger.info(f"  LLM_MODEL: {settings.llm_model}")
    logger.info("=" * 80)
    
    # 优先使用自定义 Base URL（支持其他供应商）
    if settings.llm_base_url and settings.llm_api_key:
        # 使用自定义 Base URL（OpenAI 兼容接口）
        logger.info("=" * 80)
        logger.info("LLM Configuration:")
        logger.info(f"  Provider: Custom (using LLM_BASE_URL)")
        logger.info(f"  Base URL: {settings.llm_base_url}")
        logger.info(f"  Model: {settings.llm_model}")
        logger.info(f"  API Key: {settings.llm_api_key[:10]}...{settings.llm_api_key[-4:] if len(settings.llm_api_key) > 14 else '***'}")
        logger.info(f"  Temperature: {settings.llm_temperature}")
        logger.info(f"  Max Tokens: {settings.llm_max_tokens}")
        logger.info("=" * 80)
        llm = ChatOpenAI(
            model_name=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )
        # 打印实际使用的配置和完整的 API URL
        logger.info(f"  Actual Base URL (from client): {llm.openai_api_base if hasattr(llm, 'openai_api_base') else settings.llm_base_url}")
        logger.info(f"  Actual Model Name: {llm.model_name}")
        # 构建完整的 API URL（LangChain 会自动添加 /chat/completions）
        full_api_url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
        logger.info(f"  Full API URL: {full_api_url}")
        logger.info(f"  Request will be sent to: POST {full_api_url}")
        logger.info(f"  Request headers will include: Authorization: Bearer {settings.llm_api_key[:10]}...{settings.llm_api_key[-4:] if len(settings.llm_api_key) > 14 else '***'}")
        return llm
    elif settings.openai_api_key:
        # 使用 OpenAI（支持自定义 Base URL）
        base_url = settings.openai_base_url or "https://api.openai.com/v1"
        logger.info("=" * 80)
        logger.info("LLM Configuration:")
        logger.info(f"  Provider: OpenAI")
        logger.info(f"  Base URL: {base_url}")
        logger.info(f"  Model: {settings.llm_model}")
        logger.info(f"  API Key: {settings.openai_api_key[:10]}...{settings.openai_api_key[-4:] if len(settings.openai_api_key) > 14 else '***'}")
        logger.info(f"  Temperature: {settings.llm_temperature}")
        logger.info(f"  Max Tokens: {settings.llm_max_tokens}")
        logger.info("=" * 80)
        llm = ChatOpenAI(
            model_name=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            api_key=settings.openai_api_key,
            base_url=base_url,  # 如果设置了自定义 Base URL，使用它
        )
        # 打印实际使用的配置
        logger.info(f"  Actual Base URL (from client): {llm.openai_api_base if hasattr(llm, 'openai_api_base') else base_url}")
        logger.info(f"  Actual Model Name: {llm.model_name}")
        # 构建完整的 API URL（LangChain 会自动添加 /chat/completions）
        full_api_url = f"{base_url.rstrip('/')}/chat/completions"
        logger.info(f"  Full API URL: {full_api_url}")
        return llm
    elif settings.anthropic_api_key:
        logger.info("=" * 80)
        logger.info("LLM Configuration:")
        logger.info(f"  Provider: Anthropic")
        logger.info(f"  Model: {settings.llm_model}")
        logger.info(f"  API Key: {settings.anthropic_api_key[:10]}...{settings.anthropic_api_key[-4:] if len(settings.anthropic_api_key) > 14 else '***'}")
        logger.info(f"  Temperature: {settings.llm_temperature}")
        logger.info(f"  Max Tokens: {settings.llm_max_tokens}")
        logger.info("=" * 80)
        return ChatAnthropic(
            model=settings.llm_model if settings.llm_model.startswith("claude") else "claude-3-opus-20240229",
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            api_key=settings.anthropic_api_key,
        )
    else:
        raise ValueError(
            "No LLM API key configured. Please set one of: "
            "OPENAI_API_KEY, ANTHROPIC_API_KEY, or LLM_API_KEY with LLM_BASE_URL"
        )


def get_tools() -> List:
    """获取所有工具列表（支持动态注册）"""
    logger.info("get_tools() called")
    # 优先使用注册表（如果可用）
    try:
        logger.info("Trying to load tools from registry...")
        from codebase_driven_agent.tools.registry import get_tool_registry
        logger.info("Importing get_tool_registry...")
        registry = get_tool_registry()
        logger.info("Got tool registry, calling get_all_tools()...")
        tools = registry.get_all_tools()
        logger.info(f"Registry returned {len(tools)} tools")
        if tools:
            logger.info(f"Loaded {len(tools)} tools from registry: {[tool.name for tool in tools]}")
            return tools
        else:
            logger.warning("Registry returned empty tools list, falling back to manual registration")
    except Exception as e:
        logger.warning(f"Failed to load tools from registry: {str(e)}, falling back to manual registration", exc_info=True)
    
    # 回退到手动注册（向后兼容）
    logger.info("Using manual tool registration fallback")
    tools = []
    
    # 代码工具
    try:
        logger.debug("Initializing CodeTool...")
        code_tool = CodeTool()
        tools.append(code_tool)
        logger.debug("CodeTool initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize CodeTool: {str(e)}")
    
    # 日志工具
    try:
        logger.debug("Initializing LogTool...")
        log_tool = LogTool()
        tools.append(log_tool)
        logger.debug("LogTool initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize LogTool: {str(e)}")
    
    # 数据库工具（只有在配置了数据库 URL 时才初始化）
    try:
        from codebase_driven_agent.config import settings
        if settings.database_url:
            logger.debug("Initializing DatabaseTool...")
            database_tool = DatabaseTool()
            tools.append(database_tool)
            logger.debug("DatabaseTool initialized")
        else:
            logger.debug("Database URL not configured, skipping DatabaseTool")
    except Exception as e:
        logger.warning(f"Failed to initialize DatabaseTool: {str(e)}")
    
    logger.info(f"Manual registration completed, total tools: {len(tools)}")
    if not tools:
        logger.error("No tools available! Agent will not be able to perform any actions.")
    
    return tools
