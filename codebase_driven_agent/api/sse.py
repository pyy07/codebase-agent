"""SSE 流式接口实现"""

import json
import asyncio
import queue
from typing import AsyncGenerator, Optional, Set, List, Dict, Any
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from codebase_driven_agent.api.models import AnalyzeRequest, AnalysisResult
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.api.sse")

router = APIRouter(prefix="/api/v1", tags=["streaming"])

# 全局 agent 任务注册表，用于在服务器关闭时取消所有任务
_active_agent_tasks: Set[asyncio.Task] = set()
_tasks_lock = asyncio.Lock()


async def register_agent_task(task: asyncio.Task):
    """注册 agent 任务"""
    async with _tasks_lock:
        _active_agent_tasks.add(task)
        logger.debug(f"Registered agent task, total active tasks: {len(_active_agent_tasks)}")


async def unregister_agent_task(task: asyncio.Task):
    """注销 agent 任务"""
    async with _tasks_lock:
        _active_agent_tasks.discard(task)
        logger.debug(f"Unregistered agent task, total active tasks: {len(_active_agent_tasks)}")


async def cancel_all_agent_tasks():
    """取消所有正在运行的 agent 任务（服务器关闭时调用）"""
    async with _tasks_lock:
        if not _active_agent_tasks:
            logger.info("No active agent tasks to cancel")
            return

        logger.info(f"Cancelling {len(_active_agent_tasks)} active agent tasks...")
        tasks_to_cancel = list(_active_agent_tasks)
        for task in tasks_to_cancel:
            if not task.done():
                task.cancel()
                logger.debug(f"Cancelled agent task: {task}")

        # 等待所有任务完成取消，设置很短的超时避免无限等待
        if tasks_to_cancel:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks_to_cancel, return_exceptions=True),
                    timeout=1.0,  # 最多等待 1 秒，因为线程中的操作无法被取消
                )
                logger.info(f"All {len(tasks_to_cancel)} agent tasks cancelled")
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for {len(tasks_to_cancel)} agent tasks to cancel")
                logger.warning("Note: Some agent tasks may still be running in background threads")
                # 超时后不再等待，直接继续关闭流程
                # 线程中的操作（如 requests.get）无法被取消，会继续运行直到完成

        _active_agent_tasks.clear()


class SSEMessage:
    """SSE 消息格式"""

    @staticmethod
    def format(event: str, data: dict) -> str:
        """
        格式化 SSE 消息

        Args:
            event: 事件类型（progress, result, error, done）
            data: 消息数据

        Returns:
            格式化的 SSE 消息字符串
        """
        lines = [f"event: {event}"]

        # 将数据转换为 JSON
        if isinstance(data, dict):
            data_str = json.dumps(data, ensure_ascii=False)
        else:
            data_str = json.dumps({"message": str(data)}, ensure_ascii=False)

        # 多行数据需要每行前加 "data: "
        for line in data_str.split("\n"):
            lines.append(f"data: {line}")

        lines.append("")  # 空行表示消息结束
        return "\n".join(lines)

    @staticmethod
    def progress(message: str, progress: float = 0.0, step: Optional[str] = None) -> str:
        """进度消息"""
        return SSEMessage.format(
            "progress",
            {
                "message": message,
                "progress": progress,
                "step": step,
            },
        )

    @staticmethod
    def result(result: AnalysisResult) -> str:
        """结果消息"""
        return SSEMessage.format("result", result.model_dump())

    @staticmethod
    def error(error: str) -> str:
        """错误消息"""
        return SSEMessage.format("error", {"error": error})

    @staticmethod
    def done() -> str:
        """完成消息"""
        return SSEMessage.format("done", {"message": "Analysis completed"})

    @staticmethod
    def plan(steps: List[Dict[str, Any]]) -> str:
        """任务计划消息"""
        return SSEMessage.format("plan", {"steps": steps})


async def _run_graph_executor_stream(
    executor: Any,
    input_text: str,
    context_files: Optional[List],
    message_queue: queue.Queue,
):
    """
    运行 GraphExecutor 并将事件发送到消息队列

    Args:
        executor: GraphExecutorWrapper 实例
        input_text: 用户输入
        context_files: 上下文文件列表
        message_queue: SSE 消息队列（线程安全的 queue.Queue）
    """
    try:
        # GraphExecutor.run() 是异步生成器
        async for event in executor.executor.run(input_text, context_files):
            if event and isinstance(event, dict):
                # 使用线程安全的 put_nowait
                message_queue.put_nowait(event)
    except Exception as e:
        logger.error(f"Error in _run_graph_executor_stream: {e}", exc_info=True)
        message_queue.put_nowait({"event": "error", "data": {"error": str(e)}})


async def _execute_analysis_stream(
    request: AnalyzeRequest,
    message_queue: Optional[queue.Queue] = None,
    request_obj: Optional[Request] = None,
) -> AsyncGenerator[str, None]:
    """
    流式执行分析（使用 GraphExecutor）

    这是一个生成器函数，逐步产生分析进度和结果。

    Args:
        request: 分析请求
        message_queue: SSE 消息队列（使用线程安全的 queue.Queue）
    """
    try:
        # 发送开始消息（立即发送，确保用户看到反馈）
        yield SSEMessage.progress("开始分析...", progress=0.0, step="initializing")

        # 发送心跳消息，确保连接正常
        yield SSEMessage.progress("正在初始化 Agent...", progress=0.05, step="initializing")
        await asyncio.sleep(0.05)

        # 解析 context_files
        if request.context_files:
            yield SSEMessage.progress(
                f"解析 {len(request.context_files)} 个上下文文件...",
                progress=0.1,
                step="parsing_context",
            )
            await asyncio.sleep(0.1)

        # 创建消息队列（使用线程安全的 queue.Queue）
        if message_queue is None:
            message_queue = queue.Queue()

        # 解析 context_files
        context_files = None
        if request.context_files:
            context_files = [
                {
                    "type": ctx.type,
                    "path": ctx.path,
                    "content": ctx.content,
                    "line_start": ctx.line_start,
                    "line_end": ctx.line_end,
                }
                for ctx in request.context_files
            ]

        # 执行 Agent 分析（使用 GraphExecutor）
        from codebase_driven_agent.agent.graph_executor import GraphExecutorWrapper
        from codebase_driven_agent.agent.output_parser import OutputParser
        from codebase_driven_agent.utils.extractors import extract_from_intermediate_steps

        # 清空日志查询缓存（确保缓存仅在当次请求生效）
        from codebase_driven_agent.utils.log_query import get_log_query_instance

        log_query_instance = get_log_query_instance()
        if hasattr(log_query_instance, "clear_cache"):
            log_query_instance.clear_cache()
            logger.debug("Log query cache cleared for new analysis request")

        # 重置全局取消标志（确保每次新请求开始时都是未取消状态）
        try:
            from codebase_driven_agent.tools.code_tool import _cancellation_event

            _cancellation_event.clear()
            logger.debug("Global cancellation event cleared for new analysis request")
        except Exception as e:
            logger.debug(f"Failed to clear global cancellation event: {e}")

        # 创建 GraphExecutor（新的图式执行器）
        event_loop = asyncio.get_event_loop()
        executor = GraphExecutorWrapper(callbacks=None, message_queue=message_queue, event_loop=event_loop)

        # 发送 Agent 启动消息
        try:
            yield SSEMessage.progress(
                "Agent 已启动，正在分析问题...", progress=0.1, step="agent_started"
            )
        except GeneratorExit:
            logger.info(
                "Client disconnected after agent started, agent task continues in background"
            )
            # 客户端断开，让 Agent 继续运行
            raise
        except asyncio.CancelledError:
            logger.info("Task cancelled after agent started")
            # 任务被取消，退出
            raise

        # 使用 GraphExecutor 执行分析
        logger.info("Starting GraphExecutor...")
        agent_completed = False
        agent_result = None
        agent_task = None

        try:
            # GraphExecutor.run() 是异步生成器，直接使用即可
            agent_task = asyncio.create_task(
                _run_graph_executor_stream(executor, request.input, context_files, message_queue)
            )
            # 注册 agent 任务，用于服务器关闭时取消
            await register_agent_task(agent_task)

            # 处理消息队列
            loop = asyncio.get_event_loop()
            last_progress_time = loop.time()
            heartbeat_interval = 2.0  # 每 2 秒发送一次心跳

            logger.info("Entering message processing loop...")
            while not agent_task.done():
                try:
                    # 从线程安全的 queue.Queue 中非阻塞地获取消息
                    try:
                        msg = message_queue.get_nowait()
                    except queue.Empty:
                        # 队列为空，等待一小段时间后继续
                        await asyncio.sleep(0.1)
                        
                        # 检查是否需要发送心跳
                        current_time = loop.time()
                        if current_time - last_progress_time > heartbeat_interval:
                            try:
                                yield SSEMessage.progress(
                                    "分析进行中，请稍候...", progress=0.5, step="processing"
                                )
                                last_progress_time = current_time
                                logger.debug("Heartbeat sent")
                            except GeneratorExit:
                                logger.info("Client disconnected during heartbeat")
                                raise
                            except asyncio.CancelledError:
                                logger.info("Task cancelled during heartbeat")
                                break
                        continue
                    
                    if msg:
                        event = msg.get("event", "progress")
                        data = msg.get("data", {})

                        logger.info(
                            f"Processing queued message: {event}, data keys: {list(data.keys())}"
                        )

                        if event == "progress":
                            try:
                                yield SSEMessage.progress(
                                    data.get("message", ""),
                                    progress=data.get("progress", 0.0),
                                    step=data.get("step"),
                                )
                                last_progress_time = loop.time()
                            except GeneratorExit:
                                logger.info("Client disconnected during progress message")
                                raise
                            except asyncio.CancelledError:
                                logger.info("Task cancelled during progress message")
                                break
                        elif event == "plan":
                            try:
                                logger.info(f"Sending plan with {len(data.get('steps', []))} steps to client")
                                yield SSEMessage.plan(data.get("steps", []))
                                logger.debug(
                                    f"Plan message sent with {len(data.get('steps', []))} steps"
                                )
                            except GeneratorExit:
                                logger.info("Client disconnected during plan message")
                                raise
                            except asyncio.CancelledError:
                                logger.info("Task cancelled during plan message")
                                break
                        elif event == "error":
                            try:
                                yield SSEMessage.error(data.get("error", "Unknown error"))
                            except GeneratorExit:
                                logger.info("Client disconnected during error message")
                                raise
                            except asyncio.CancelledError:
                                logger.info("Task cancelled during error message")
                                break
                        elif event == "result":
                            # 保存结果
                            agent_result = data
                            try:
                                # data 已经是字典格式，直接使用 format 而不是 result()
                                yield SSEMessage.format("result", data)
                            except GeneratorExit:
                                logger.info("Client disconnected during result message")
                                raise
                            except asyncio.CancelledError:
                                logger.info("Task cancelled during result message")
                                break
                        elif event == "done":
                            try:
                                # data 已经是字典格式，直接使用 format
                                yield SSEMessage.format("done", data)
                            except GeneratorExit:
                                logger.info("Client disconnected during done message")
                                raise
                            except asyncio.CancelledError:
                                logger.info("Task cancelled during done message")
                                break
                except GeneratorExit:
                    raise
                except Exception as e:
                    logger.error(f"Error processing queued message: {e}", exc_info=True)

            # 等待 agent 任务完成
            await agent_task
            
            # **重要**：agent 任务完成后，继续处理队列中剩余的消息
            logger.info("Agent task completed, processing remaining queued messages...")
            remaining_messages = 0
            while True:
                try:
                    msg = message_queue.get_nowait()
                    if msg:
                        remaining_messages += 1
                        event = msg.get("event", "progress")
                        data = msg.get("data", {})
                        
                        logger.info(f"Processing remaining message #{remaining_messages}: {event}")
                        
                        if event == "result":
                            agent_result = data
                            yield SSEMessage.format("result", data)
                        elif event == "done":
                            yield SSEMessage.format("done", data)
                        elif event == "plan":
                            yield SSEMessage.plan(data.get("steps", []))
                        elif event == "progress":
                            yield SSEMessage.progress(
                                data.get("message", ""),
                                progress=data.get("progress", 0.0),
                                step=data.get("step"),
                            )
                        elif event == "error":
                            yield SSEMessage.error(data.get("error", "Unknown error"))
                except queue.Empty:
                    # 队列已空，退出
                    logger.info(f"All remaining messages processed (total: {remaining_messages})")
                    break
                except Exception as e:
                    logger.error(f"Error processing remaining message: {e}", exc_info=True)
                    break

        except GeneratorExit:
            # 生成器被关闭（客户端断开连接），agent 任务继续在后台运行
            logger.info(
                "Generator closed (client disconnected), agent task continues in background"
            )
            # Agent 任务继续运行
            raise
        except asyncio.CancelledError as e:
            # 检查是否是 GeneratorExit 导致的 CancelledError
            logger.warning(f"Analysis stream cancelled: {type(e).__name__}")

            # Agent 任务继续运行（除非是服务器关闭）
            if not agent_task.done():
                logger.info(
                    "Agent task still running, not cancelling (may be due to client disconnect)"
                )

            raise
        except KeyboardInterrupt as e:
            # 服务器关闭（Ctrl+C），必须取消所有 Agent 任务
            logger.warning(f"Analysis stream cancelled by server shutdown: {type(e).__name__}")

            # 取消 Agent 任务（服务器关闭时必须取消）
            if not agent_completed and not agent_task.done():
                logger.warning("Cancelling agent task due to server shutdown...")
                agent_task.cancel()
                try:
                    await agent_task
                except (asyncio.CancelledError, KeyboardInterrupt):
                    logger.debug("Agent task cancellation confirmed")
                    pass

            raise

        logger.info(f"Agent result success: {agent_result is not None}")
        if agent_result and not agent_result.get("success", True):
            error_msg = agent_result.get("error", "Agent execution failed")
            logger.error(f"Agent execution failed: {error_msg}")
            yield SSEMessage.error(error_msg)
            return

        # GraphExecutor 已经返回了结构化的结果，直接发送
        if agent_result:
            # 结果已经在 _run_graph_executor_stream 中发送过了
            pass

        logger.info("Stream analysis completed successfully")

    except GeneratorExit:
        # 生成器被关闭（客户端断开连接）
        logger.info("Generator closed (client disconnected)")
        raise
    except asyncio.CancelledError as e:
        # 任务被取消
        logger.warning(f"Analysis stream cancelled: {type(e).__name__}")
        raise
    except Exception as e:
        # 其他错误
        logger.error(f"Error in _execute_analysis_stream: {e}", exc_info=True)
        yield SSEMessage.error(str(e))


@router.post("/analyze/stream")
async def analyze_stream(request: AnalyzeRequest, request_obj: Request):
    """
    SSE 流式分析接口

    接收用户输入和可选的 context_files，通过 Server-Sent Events (SSE) 流式返回分析进度和结果。

    响应格式：
    - event: progress - 分析进度更新
    - event: result - 分析结果
    - event: error - 错误信息
    - event: done - 分析完成
    """

    async def event_generator():
        """事件生成器"""
        try:
            # 检查客户端是否断开连接
            async for message in _execute_analysis_stream(request, request_obj=request_obj):
                # 检查客户端是否断开连接
                try:
                    if await request_obj.is_disconnected():
                        logger.info("Client disconnected, stopping stream")
                        # 客户端断开，停止发送消息，但让 Agent 继续运行
                        break
                except Exception as e:
                    logger.debug(f"Error checking client connection: {str(e)}")

                try:
                    # EventSourceResponse 期望接收字典，会自动格式化为 SSE 格式
                    # 但我们的 message 已经是格式化的字符串，所以直接发送
                    # 注意：sse-starlette 的 EventSourceResponse 如果接收字符串，会在每行前加 "data: "
                    # 所以我们需要确保消息格式正确
                    yield message
                except (GeneratorExit, asyncio.CancelledError):
                    # 客户端断开连接，生成器被关闭
                    logger.info(
                        "Generator closed by client disconnect, agent task continues in background"
                    )
                    # 重新抛出，让生成器正常关闭
                    raise

                # 添加小延迟，避免发送过快
                await asyncio.sleep(0.05)

        except GeneratorExit:
            # 生成器被关闭（客户端断开连接），这是正常的
            logger.info("Generator closed (client disconnected)")
            return
        except (asyncio.CancelledError, KeyboardInterrupt) as e:
            logger.warning(f"Stream cancelled by interrupt: {type(e).__name__}")
            # 不发送错误消息，直接退出
            return
        except Exception as e:
            logger.error(f"Stream error: {str(e)}", exc_info=True)
            try:
                yield SSEMessage.error(str(e))
            except:
                pass

    return EventSourceResponse(event_generator())
