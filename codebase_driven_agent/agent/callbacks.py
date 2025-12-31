"""LangChain Callbacks 实现"""
import asyncio
import threading
from typing import Any, Dict, List
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.agents import AgentAction, AgentFinish
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.agent.callbacks")
from langchain_core.outputs import LLMResult


class SSECallbackHandler(BaseCallbackHandler):
    """SSE 流式输出 Callback Handler"""
    
    def __init__(self, message_queue: asyncio.Queue):
        """
        初始化 SSE Callback Handler
        
        Args:
            message_queue: 用于发送 SSE 消息的异步队列
        """
        super().__init__()
        self.message_queue = message_queue
        self.step_count = 0
        self.total_steps = 0
        self._loop = None
        self._loop_lock = threading.Lock()
    
    def _get_event_loop(self):
        """获取事件循环（线程安全）"""
        with self._loop_lock:
            if self._loop is None:
                try:
                    # 尝试获取当前运行的事件循环
                    self._loop = asyncio.get_running_loop()
                except RuntimeError:
                    # 如果没有运行中的循环，尝试获取主循环
                    try:
                        self._loop = asyncio.get_event_loop()
                    except RuntimeError:
                        # 如果都没有，返回 None（消息将无法发送）
                        pass
            return self._loop
    
    def _send_message(self, event: str, data: Dict[str, Any]):
        """发送 SSE 消息（同步方法，内部使用 asyncio）"""
        try:
            loop = self._get_event_loop()
            if loop is None:
                # 无法获取事件循环，跳过消息
                return
            
            # 使用 run_coroutine_threadsafe 在同步上下文中调用异步方法
            if loop.is_running():
                # 如果循环正在运行，使用 create_task
                asyncio.run_coroutine_threadsafe(
                    self.message_queue.put({
                        "event": event,
                        "data": data,
                    }),
                    loop
                )
            else:
                # 如果循环未运行，直接运行（这种情况应该很少见）
                loop.run_until_complete(
                    self.message_queue.put({
                        "event": event,
                        "data": data,
                    })
                )
        except Exception:
            # 如果队列已关闭或其他错误，忽略
            pass
    
    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """LLM 开始调用"""
        logger.info("LLM call started")
        # 打印请求详情（debug 级别）
        logger.debug("=" * 80)
        logger.debug("LLM Call Details:")
        logger.debug(f"  Model: {serialized.get('model_name', serialized.get('name', 'unknown'))}")
        logger.debug(f"  Prompts count: {len(prompts)}")
        if prompts:
            logger.debug(f"  First prompt length: {len(prompts[0])} characters")
            logger.debug(f"  First prompt preview (first 500 chars): {prompts[0][:500]}...")
            # 打印完整的 prompt（debug 级别）
            logger.debug("=" * 80)
            logger.debug("Full LLM Prompt:")
            for i, prompt in enumerate(prompts, 1):
                logger.debug(f"  Prompt {i}:")
                logger.debug(prompt)
            logger.debug("=" * 80)
        logger.debug(f"  Additional kwargs: {list(kwargs.keys())}")
        # 尝试获取实际的 API URL 和请求参数（如果可用）
        if 'invocation_params' in kwargs:
            inv_params = kwargs['invocation_params']
            logger.debug("  Invocation Parameters:")
            if 'base_url' in inv_params:
                base_url = inv_params['base_url']
                logger.debug(f"    Base URL: {base_url}")
                # LangChain 会在 base_url 后面添加 /chat/completions
                full_url = f"{base_url.rstrip('/')}/chat/completions"
                logger.debug(f"    Full API URL: {full_url}")
            if 'model_name' in inv_params:
                logger.debug(f"    Model Name: {inv_params['model_name']}")
            if 'api_key' in inv_params:
                api_key = inv_params['api_key']
                logger.debug(f"    API Key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else '***'}")
            if 'temperature' in inv_params:
                logger.debug(f"    Temperature: {inv_params['temperature']}")
            if 'max_tokens' in inv_params:
                logger.debug(f"    Max Tokens: {inv_params['max_tokens']}")
            # 打印完整的 invocation_params（用于调试）
            logger.debug(f"    Full invocation_params keys: {list(inv_params.keys())}")
        logger.debug("=" * 80)
        
        self._send_message("progress", {
            "message": "Agent 正在思考和分析问题...",
            "progress": 0.3,
            "step": "agent_thinking",
        })
    
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """LLM 调用结束"""
        logger.info("LLM call completed")
        # 打印响应详情（debug 级别）
        if response:
            logger.debug("=" * 80)
            logger.debug("LLM Response Details:")
            if hasattr(response, 'llm_output'):
                logger.debug(f"  LLM Output: {response.llm_output}")
            if hasattr(response, 'generations') and response.generations:
                logger.debug(f"  Generations count: {len(response.generations)}")
                if response.generations[0]:
                    first_gen = response.generations[0][0]
                    if hasattr(first_gen, 'text'):
                        logger.debug(f"  First generation length: {len(first_gen.text)} characters")
                        logger.debug(f"  First generation preview (first 500 chars):")
                        logger.debug(f"  {first_gen.text[:500]}...")
                        # 打印完整响应（debug 级别）
                        logger.debug("=" * 80)
                        logger.debug("Full LLM Response:")
                        logger.debug(first_gen.text)
                        logger.debug("=" * 80)
            logger.debug("=" * 80)
    
    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """LLM 调用错误"""
        logger.error("=" * 80)
        logger.error("LLM Call Error:")
        logger.error(f"  Error type: {type(error).__name__}")
        logger.error(f"  Error message: {str(error)}")
        logger.error(f"  Additional kwargs: {kwargs}")
        logger.error("=" * 80)
        
        self._send_message("error", {
            "error": f"LLM 调用错误: {str(error)}",
        })
    
    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> None:
        """Chain 开始执行"""
        pass
    
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Chain 执行结束"""
        pass
    
    def on_chain_error(self, error: Exception, **kwargs: Any) -> None:
        """Chain 执行错误"""
        self._send_message("error", {
            "error": f"Chain 执行错误: {str(error)}",
        })
    
    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """工具开始调用"""
        tool_name = serialized.get("name", "unknown")
        self.step_count += 1
        logger.info(f"Tool started: {tool_name}, input: {input_str[:100]}")
        
        # 根据工具类型发送不同的进度消息
        step_messages = {
            "code_search": ("正在检索相关代码...", "searching_code", 0.4),
            "log_search": ("正在查询日志...", "querying_logs", 0.6),
            "database_query": ("正在查询数据库...", "querying_database", 0.7),
        }
        
        message, step, progress = step_messages.get(
            tool_name,
            (f"正在调用工具: {tool_name}...", "tool_execution", 0.5)
        )
        
        self._send_message("progress", {
            "message": message,
            "progress": progress,
            "step": step,
            "tool": tool_name,
            "input": input_str[:100] if len(input_str) > 100 else input_str,  # 截断输入
        })
    
    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """工具调用结束"""
        # 可以在这里发送工具执行结果（可选，避免信息过多）
        pass
    
    def on_tool_error(self, error: Exception, **kwargs: Any) -> None:
        """工具调用错误"""
        self._send_message("progress", {
            "message": f"工具执行出错: {str(error)}",
            "progress": 0.8,
            "step": "tool_error",
        })
    
    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> None:
        """Agent 执行动作"""
        # Agent 决定调用某个工具
        tool_name = action.tool
        logger.info(f"Agent action: calling tool {tool_name}")
        
        # 根据工具类型显示更友好的消息
        tool_messages = {
            "code_search": "正在搜索相关代码...",
            "log_search": "正在查询日志...",
            "database_query": "正在查询数据库...",
        }
        
        message = tool_messages.get(tool_name, f"正在调用工具: {tool_name}...")
        
        self._send_message("progress", {
            "message": message,
            "progress": 0.5,
            "step": "agent_action",
            "tool": tool_name,
            "thought": action.log[:200] if hasattr(action, 'log') and action.log else None,  # Agent 的思考过程
        })
    
    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        """Agent 完成执行"""
        logger.info("Agent finished execution")
        self._send_message("progress", {
            "message": "Agent 分析完成，正在生成结果...",
            "progress": 0.9,
            "step": "agent_finish",
        })

