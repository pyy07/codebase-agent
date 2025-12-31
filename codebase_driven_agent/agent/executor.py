"""Agent 执行器实现"""
import asyncio
import json
from typing import List, Optional, Dict, Any
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from codebase_driven_agent.agent.prompt import generate_system_prompt
from codebase_driven_agent.agent.memory import AgentMemory
from codebase_driven_agent.tools import CodeTool, LogTool, DatabaseTool
from codebase_driven_agent.utils.database import get_schema_info, format_schema_info
from codebase_driven_agent.config import settings
from codebase_driven_agent.utils.logger import setup_logger
from codebase_driven_agent.utils.metrics import record_agent_metrics

logger = setup_logger("codebase_driven_agent.agent.executor")

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


def create_agent_executor(
    memory: Optional[AgentMemory] = None,
    max_iterations: Optional[int] = None,
    max_execution_time: Optional[int] = None,
    callbacks: Optional[List] = None,
):
    """
    创建 Agent（LangChain 1.0+ 使用 create_agent）
    
    Args:
        memory: Agent 记忆（可选）
        max_iterations: 最大迭代次数（可选，默认使用配置）
        max_execution_time: 最大执行时间（秒，可选，默认使用配置）
        callbacks: 回调函数列表（可选）
    
    Returns:
        Agent 实例（可直接调用 invoke 方法）
    """
    logger.info("Creating agent executor...")
    
    # 创建 LLM
    logger.info("Creating LLM instance...")
    llm = create_llm()
    logger.info(f"LLM created: {type(llm).__name__}")
    
    # 获取工具
    logger.info("Getting tools...")
    tools = get_tools()
    logger.info(f"Loaded {len(tools)} tools: {[tool.name for tool in tools]}")
    
    # 获取 Schema 信息（用于注入到 Prompt）
    logger.info("Getting database schema info...")
    try:
        schema_info = get_schema_info()
        logger.info(f"Schema info retrieved: {len(schema_info.get('tables', {}))} tables")
    except Exception as e:
        logger.warning(f"Failed to get schema info: {str(e)}")
        schema_info = {}
    schema_text = format_schema_info(schema_info) if schema_info else "No database schema available."
    logger.info(f"Schema text length: {len(schema_text)}")
    
    # 检查是否使用日志易（需要添加 SPL 查询示例）
    logger.info("Checking log query instance...")
    from codebase_driven_agent.utils.log_query import get_log_query_instance
    include_spl_examples = False
    try:
        log_query_instance = get_log_query_instance()
        # 检查是否是日志易实现
        from codebase_driven_agent.utils.log_query import LogyiLogQuery
        if isinstance(log_query_instance, LogyiLogQuery):
            include_spl_examples = True
            logger.info("Using Logyi log query, will include SPL examples")
    except Exception as e:
        # 如果无法获取日志查询实例，忽略
        logger.debug(f"Could not get log query instance: {str(e)}")
        pass
    
    # 生成系统提示
    logger.debug("Generating system prompt...")
    tools_description = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])
    logger.debug(f"Tools description length: {len(tools_description)}")
    system_prompt = generate_system_prompt(
        tools_description=tools_description,
        schema_info=schema_text,
        include_spl_examples=include_spl_examples,
    )
    logger.debug(f"System prompt generated, length: {len(system_prompt)}")
    # 打印完整的 prompt（debug 级别）
    logger.debug("=" * 80)
    logger.debug("Full System Prompt:")
    logger.debug(system_prompt)
    logger.debug("=" * 80)
    
    # 使用新的 create_agent API (LangChain 1.0+)
    logger.info("Creating agent with LangChain create_agent API...")
    agent_runnable = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )
    logger.info("Agent created successfully")
    
    # 在 LangChain 1.0+ 中，create_agent 返回的 agent 可以直接使用
    # 存储配置信息供后续使用
    agent_runnable._max_iterations = max_iterations or settings.agent_max_iterations
    agent_runnable._max_execution_time = max_execution_time or settings.agent_max_execution_time
    agent_runnable._callbacks = callbacks or []
    
    logger.info(f"Agent configured: max_iterations={agent_runnable._max_iterations}, max_execution_time={agent_runnable._max_execution_time}")
    
    return agent_runnable


class AgentExecutorWrapper:
    """Agent 执行器包装类"""
    
    def __init__(
        self,
        memory: Optional[AgentMemory] = None,
        max_iterations: Optional[int] = None,
        max_execution_time: Optional[int] = None,
        callbacks: Optional[List] = None,
    ):
        self.memory = memory or AgentMemory()
        self.callbacks = callbacks or []
        self.executor = create_agent_executor(
            memory=self.memory,
            max_iterations=max_iterations,
            max_execution_time=max_execution_time,
            callbacks=self.callbacks,
        )
    
    async def run(
        self,
        input_text: str,
        context_files: Optional[List[Dict[str, Any]]] = None,
        plan_steps: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        执行 Agent 分析
        
        Args:
            input_text: 用户输入
            context_files: 上下文文件列表（可选）
            plan_steps: 分析计划步骤列表（可选）
        
        Returns:
            执行结果字典
        """
        import time
        start_time = time.time()
        
        try:
            logger.info(f"Agent execution started, input length: {len(input_text)}")
            
            # 构建输入（包含上下文文件信息和计划）
            full_input = input_text
            
            # 如果有计划步骤，将其包含在输入中
            if plan_steps:
                plan_text = "\n\n## 📋 分析计划（请严格按照此计划执行）\n\n"
                for step in plan_steps:
                    step_num = step.get("step", 0)
                    action = step.get("action", "")
                    target = step.get("target", "")
                    if target:
                        plan_text += f"步骤 {step_num}: {action} - {target}\n"
                    else:
                        plan_text += f"步骤 {step_num}: {action}\n"
                plan_text += "\n**重要提示**：\n"
                plan_text += "1. 请严格按照上述计划执行，按顺序完成每个步骤\n"
                plan_text += "2. 每个步骤完成后，继续执行下一步，不要跳过\n"
                plan_text += "3. 优先使用代码工具（code_search）查找相关代码，因为代码是问题的根源\n"
                plan_text += "4. 如果某个步骤失败，尝试其他方法，但不要跳过计划中的步骤\n"
                plan_text += "5. 完成所有步骤后，给出完整的分析结论\n"
                full_input = f"{input_text}{plan_text}"
                logger.info(f"Plan steps included in input: {len(plan_steps)} steps")
            
            # 添加上下文文件信息
            if context_files:
                logger.info(f"Processing {len(context_files)} context files")
                context_info = self._format_context_files(context_files)
                full_input = f"{full_input}\n\nAdditional Context:\n{context_info}"
            
            logger.info(f"Prepared input, total length: {len(full_input)}")
            
            # 执行 Agent (LangChain 1.0+ 使用 messages 格式)
            # Callbacks 需要在调用时传递
            input_data = {
                "messages": [
                    {"role": "user", "content": full_input}
                ]
            }
            # 如果有 callbacks，添加到 config 中
            # 同时传递 max_iterations 配置（LangChain 1.0+ 支持通过 config 传递）
            config = {}
            if self.callbacks:
                config["callbacks"] = self.callbacks
                logger.info(f"Using {len(self.callbacks)} callback handlers")
            
            # 传递 max_iterations 配置
            if hasattr(self.executor, '_max_iterations'):
                config["max_iterations"] = self.executor._max_iterations
                logger.info(f"Setting max_iterations={config['max_iterations']}")

            # 打印请求信息（用于调试）
            logger.info("=" * 80)
            logger.info("LLM Request Details:")
            logger.info(f"  Model: {settings.llm_model}")
            logger.info(f"  Base URL: {settings.llm_base_url or settings.openai_base_url or 'https://api.openai.com/v1'}")
            logger.info(f"  Temperature: {settings.llm_temperature}")
            logger.info(f"  Max Tokens: {settings.llm_max_tokens}")
            logger.info(f"  Input Length: {len(full_input)} characters")
            logger.info(f"  Input Preview (first 500 chars): {full_input[:500]}...")
            logger.info("=" * 80)
            
            # 在调用之前检查是否已取消
            for callback in self.callbacks:
                if hasattr(callback, 'is_cancelled') and callback.is_cancelled():
                    logger.warning("Task already cancelled before LLM call, exiting immediately")
                    raise asyncio.CancelledError("Task has been cancelled")
            
            logger.info("Invoking agent executor (this may take a while for LLM calls)...")
            
            # 创建一个包装函数，在调用前检查取消状态
            def invoke_with_cancel_check():
                """包装 invoke 调用，在执行前检查取消状态"""
                # 检查是否已取消，如果已取消，直接退出
                for callback in self.callbacks:
                    if hasattr(callback, 'is_cancelled') and callback.is_cancelled():
                        logger.warning("Task cancelled before invoke, exiting immediately")
                        # 直接抛出 CancelledError，让上层处理
                        raise KeyboardInterrupt("Task has been cancelled")
                
                # 执行 invoke
                return self.executor.invoke(input_data, config=config if config else None)
            
            try:
                logger.info("Starting asyncio.to_thread for executor.invoke...")
                # 添加超时保护，避免 LLM 调用无限期阻塞
                max_execution_time = self.executor._max_execution_time if hasattr(self.executor, '_max_execution_time') else 300
                logger.info(f"LLM call timeout set to {max_execution_time} seconds")
                
                # 使用 asyncio.to_thread 在线程池中执行同步的 invoke 调用
                # 使用 wait_for 来确保超时和取消能够生效
                result = await asyncio.wait_for(
                    asyncio.to_thread(invoke_with_cancel_check),
                    timeout=max_execution_time
                )
                logger.info("asyncio.to_thread completed, got result")
            except asyncio.TimeoutError:
                logger.error(f"LLM call timed out after {max_execution_time} seconds")
                raise TimeoutError(f"Agent execution timed out after {max_execution_time} seconds")
            except asyncio.CancelledError:
                logger.warning("Agent executor was cancelled, exiting immediately")
                # 通知所有 callback handler 任务已被取消
                for callback in self.callbacks:
                    if hasattr(callback, 'set_cancelled'):
                        try:
                            callback.set_cancelled()
                        except Exception as e:
                            logger.debug(f"Failed to set cancelled on callback: {e}")
                # 重新抛出 CancelledError，立即退出
                raise
            except KeyboardInterrupt:
                # 如果是在线程中检测到取消，转换为 CancelledError
                logger.warning("KeyboardInterrupt caught in thread, exiting immediately")
                raise asyncio.CancelledError("Task cancelled") from None
            except Exception as e:
                error_msg = str(e)
                # 处理常见的 LLM API 错误，提供更友好的错误信息
                if "502" in error_msg or "Bad Gateway" in error_msg:
                    error_msg = "LLM API 服务暂时不可用（502 Bad Gateway），请稍后重试。这可能是服务端问题或网络问题。"
                elif "401" in error_msg or "Unauthorized" in error_msg:
                    error_msg = "LLM API 认证失败（401 Unauthorized），请检查 API Key 配置。"
                elif "429" in error_msg or "rate limit" in error_msg.lower():
                    error_msg = "LLM API 请求频率过高（429 Rate Limit），请稍后重试。"
                elif "timeout" in error_msg.lower():
                    error_msg = f"LLM API 请求超时，请检查网络连接或稍后重试。原始错误：{error_msg}"
                elif "503" in error_msg or "Service Unavailable" in error_msg:
                    error_msg = "LLM API 服务暂时不可用（503 Service Unavailable），请稍后重试。"
                
                logger.error(f"Error in executor.invoke: {error_msg}", exc_info=True)
                raise Exception(error_msg) from e
            
            logger.info("Agent executor completed successfully")
            
            execution_time = time.time() - start_time
            logger.info(f"Agent execution took {execution_time:.2f} seconds")
            
            # LangChain 1.0+ 返回格式: {"messages": [...]}
            # 提取最后一条消息作为输出
            if isinstance(result, dict) and "messages" in result:
                messages = result["messages"]
                logger.info(f"Processing {len(messages)} messages from agent")
                # 查找最后一条 AI 消息
                output = ""
                tool_calls = 0
                for msg in reversed(messages):
                    if hasattr(msg, "content") and msg.content:
                        output = msg.content
                        break
                    elif isinstance(msg, dict) and msg.get("content"):
                        output = msg["content"]
                        break
                    # 统计工具调用
                    if hasattr(msg, "tool_calls") or (isinstance(msg, dict) and "tool_calls" in msg):
                        tool_calls += 1
            else:
                output = str(result) if result else ""
                tool_calls = 0
                logger.warning(f"Unexpected result format: {type(result)}")
            
            logger.info(f"Extracted output length: {len(output)}, tool calls: {tool_calls}")
            
            # 记录指标
            record_agent_metrics(execution_time, tool_calls, success=True)
            
            return {
                "success": True,
                "output": output,
                "intermediate_steps": result.get("messages", []) if isinstance(result, dict) else [],
            }
        
        except Exception as e:
            execution_time = time.time() - start_time
            tool_calls = 0
            
            # 记录错误指标
            record_agent_metrics(execution_time, tool_calls, success=False)
            
            logger.error(f"Agent execution failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "output": None,
                "intermediate_steps": [],
            }
    
    def _format_context_files(self, context_files: List[Dict[str, Any]]) -> str:
        """格式化上下文文件信息"""
        formatted = []
        for ctx_file in context_files:
            if ctx_file.get("type") == "code":
                formatted.append(
                    f"Code file: {ctx_file.get('path', 'unknown')}\n"
                    f"Lines: {ctx_file.get('line_start', '?')}-{ctx_file.get('line_end', '?')}\n"
                    f"Content:\n{ctx_file.get('content', '')}\n"
                )
            elif ctx_file.get("type") == "log":
                formatted.append(
                    f"Log file: {ctx_file.get('path', 'unknown')}\n"
                    f"Content:\n{ctx_file.get('content', '')}\n"
                )
        
        return "\n---\n".join(formatted)

