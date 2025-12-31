"""LangChain Callbacks 实现"""
import asyncio
import threading
from typing import Any, Dict, List, Optional
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.agents import AgentAction, AgentFinish
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.agent.callbacks")
from langchain_core.outputs import LLMResult


class SSECallbackHandler(BaseCallbackHandler):
    """SSE 流式输出 Callback Handler"""
    
    def __init__(self, message_queue: asyncio.Queue, plan_steps: Optional[List[Dict[str, Any]]] = None, event_loop: Optional[asyncio.AbstractEventLoop] = None):
        """
        初始化 SSE Callback Handler
        
        Args:
            message_queue: 用于发送 SSE 消息的异步队列
            plan_steps: 分析计划步骤列表（可选）
            event_loop: 事件循环（可选，如果提供则直接使用，否则尝试获取）
        """
        super().__init__()
        self.message_queue = message_queue
        self.step_count = 0
        self.total_steps = 0
        self._loop = event_loop  # 如果提供了事件循环，直接使用
        self._loop_lock = threading.Lock()
        self._cancelled = False  # 标记任务是否已被取消
        self._cancelled_lock = threading.Lock()  # 保护 _cancelled 标志的锁
        self.plan_steps = plan_steps or []  # 分析计划步骤
        self.current_step_index = 0  # 当前执行的步骤索引
    
    def _get_event_loop(self):
        """获取事件循环（线程安全）"""
        with self._loop_lock:
            # 如果已经设置了事件循环，检查是否仍然有效
            if self._loop is not None:
                # 检查循环是否已关闭
                if self._loop.is_closed():
                    self._loop = None
                else:
                    return self._loop
            
            # 尝试获取当前运行的事件循环
            try:
                self._loop = asyncio.get_running_loop()
                return self._loop
            except RuntimeError:
                # 如果没有运行中的循环，尝试获取主循环
                try:
                    self._loop = asyncio.get_event_loop()
                    # 检查循环是否已关闭
                    if self._loop.is_closed():
                        self._loop = None
                        return None
                    return self._loop
                except RuntimeError:
                    # 如果都没有，返回 None（消息将无法发送）
                    # 这通常不应该发生，因为应该在创建 handler 时传递事件循环
                    self._loop = None
                    return None
    
    def set_cancelled(self):
        """标记任务为已取消"""
        with self._cancelled_lock:
            self._cancelled = True
    
    def is_cancelled(self) -> bool:
        """检查任务是否已被取消"""
        with self._cancelled_lock:
            return self._cancelled
    
    def _send_message(self, event: str, data: Dict[str, Any]):
        """发送 SSE 消息（同步方法，内部使用 asyncio）"""
        # 如果任务已被取消，不发送消息
        if self.is_cancelled():
            logger.debug(f"Message not sent (cancelled): {event}")
            return
        
        try:
            loop = self._get_event_loop()
            if loop is None:
                # 无法获取事件循环，记录警告
                logger.warning(f"Failed to get event loop, message not sent: {event}")
                return
            
            message_data = {
                "event": event,
                "data": data,
            }
            
            # 使用 run_coroutine_threadsafe 在同步上下文中调用异步方法
            if loop.is_running():
                # 如果循环正在运行，使用 run_coroutine_threadsafe
                future = asyncio.run_coroutine_threadsafe(
                    self.message_queue.put(message_data),
                    loop
                )
                # 记录消息发送
                logger.debug(f"Message queued via run_coroutine_threadsafe: {event}, data keys: {list(data.keys())}")
            else:
                # 如果循环未运行，直接运行（这种情况应该很少见）
                loop.run_until_complete(
                    self.message_queue.put(message_data)
                )
                logger.debug(f"Message queued via run_until_complete: {event}, data keys: {list(data.keys())}")
        except Exception as e:
            # 记录错误，而不是忽略
            logger.error(f"Failed to send message ({event}): {str(e)}", exc_info=True)
    
    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """LLM 开始调用"""
        # 如果任务已被取消，直接退出，不执行任何操作
        if self.is_cancelled():
            return
        
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
        # 如果任务已被取消，直接退出，不执行任何操作
        if self.is_cancelled():
            return
        
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
        # 如果任务已被取消，直接退出，不执行任何操作
        if self.is_cancelled():
            return
        
        tool_name = serialized.get("name", "unknown")
        self.step_count += 1
        logger.info(f"Tool started: {tool_name}, input: {input_str[:100]}")
        
        # 更新计划步骤状态
        if self.plan_steps and self.current_step_index < len(self.plan_steps):
            self.plan_steps[self.current_step_index]["status"] = "running"
            # 发送步骤更新消息
            self._send_message("plan", {
                "steps": self.plan_steps,
            })
        
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
        
        # 如果有计划步骤，在消息中包含步骤信息
        step_info = None
        if self.plan_steps and self.current_step_index < len(self.plan_steps):
            step_info = self.plan_steps[self.current_step_index]
            message = f"步骤 {step_info['step']}: {message}"
        
        self._send_message("progress", {
            "message": message,
            "progress": progress,
            "step": step,
            "tool": tool_name,
            "input": input_str[:100] if len(input_str) > 100 else input_str,  # 截断输入
            "step_info": step_info,
        })
    
    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """工具调用结束"""
        # 更新计划步骤状态为完成
        if self.plan_steps and self.current_step_index < len(self.plan_steps):
            self.plan_steps[self.current_step_index]["status"] = "completed"
            # 发送步骤更新消息
            self._send_message("plan", {
                "steps": self.plan_steps,
            })
            # 移动到下一步
            self.current_step_index += 1
    
    def on_tool_error(self, error: Exception, **kwargs: Any) -> None:
        """工具调用错误"""
        # 更新计划步骤状态为失败
        if self.plan_steps and self.current_step_index < len(self.plan_steps):
            self.plan_steps[self.current_step_index]["status"] = "failed"
            # 发送步骤更新消息
            self._send_message("plan", {
                "steps": self.plan_steps,
            })
            # 移动到下一步
            self.current_step_index += 1
        
        self._send_message("progress", {
            "message": f"工具执行出错: {str(error)}",
            "progress": 0.8,
            "step": "tool_error",
        })
    
    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> None:
        """Agent 执行动作"""
        # 如果任务已被取消，直接退出，不执行任何操作
        if self.is_cancelled():
            return
        
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
        
        # 如果有计划步骤，在消息中包含步骤信息
        step_info = None
        if self.plan_steps and self.current_step_index < len(self.plan_steps):
            step_info = self.plan_steps[self.current_step_index]
            message = f"步骤 {step_info['step']}: {message}"
        
        self._send_message("progress", {
            "message": message,
            "progress": 0.5,
            "step": "agent_action",
            "tool": tool_name,
            "thought": action.log[:200] if hasattr(action, 'log') and action.log else None,  # Agent 的思考过程
            "step_info": step_info,
        })
    
    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        """Agent 完成执行"""
        logger.info("Agent finished execution")
        self._send_message("progress", {
            "message": "Agent 分析完成，正在生成结果...",
            "progress": 0.9,
            "step": "agent_finish",
        })

