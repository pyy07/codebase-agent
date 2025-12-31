"""SSE 流式接口实现"""
import json
import asyncio
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from codebase_driven_agent.api.models import AnalyzeRequest, AnalysisResult
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.api.sse")

router = APIRouter(prefix="/api/v1", tags=["streaming"])


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
        return SSEMessage.format("progress", {
            "message": message,
            "progress": progress,
            "step": step,
        })
    
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


async def _execute_analysis_stream(
    request: AnalyzeRequest,
    message_queue: Optional[asyncio.Queue] = None,
    request_obj: Optional[Request] = None,
) -> AsyncGenerator[str, None]:
    """
    流式执行分析
    
    这是一个生成器函数，逐步产生分析进度和结果。
    
    Args:
        request: 分析请求
        message_queue: SSE 消息队列（用于 Callback Handler）
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
                step="parsing_context"
            )
            await asyncio.sleep(0.1)
        
        # 创建消息队列（如果未提供）
        if message_queue is None:
            message_queue = asyncio.Queue()
        
        # 创建 SSE Callback Handler
        from codebase_driven_agent.agent.callbacks import SSECallbackHandler
        callback_handler = SSECallbackHandler(message_queue)
        
        # 执行 Agent 分析
        from codebase_driven_agent.agent.executor import AgentExecutorWrapper
        from codebase_driven_agent.agent.output_parser import OutputParser
        from codebase_driven_agent.utils.extractors import extract_from_intermediate_steps
        
        # 创建 Agent 执行器（带 Callback）
        executor = AgentExecutorWrapper(callbacks=[callback_handler])
        
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
        
        # 启动 Agent 执行（在后台任务中，使用 shield 保护，避免被生成器取消影响）
        logger.info(f"Starting agent execution for input: {request.input[:100]}...")
        # 创建一个不会被生成器取消影响的任务
        async def run_agent_safely():
            """安全运行 Agent，即使生成器被取消也继续执行"""
            try:
                return await executor.run(
                    input_text=request.input,
                    context_files=context_files,
                )
            except asyncio.CancelledError:
                # 如果被取消，记录日志但不重新抛出，让任务继续运行
                logger.warning("Agent execution was cancelled, but continuing in background")
                # 重新创建任务，让它在后台继续运行
                background_task = asyncio.create_task(
                    executor.run(
                        input_text=request.input,
                        context_files=context_files,
                    )
                )
                # 添加完成回调
                def log_background_completion(task):
                    try:
                        if task.done():
                            result = task.result()
                            logger.info(f"Background agent task completed: success={result.get('success')}")
                    except Exception as e:
                        logger.error(f"Background agent task failed: {str(e)}", exc_info=True)
                background_task.add_done_callback(log_background_completion)
                # 等待后台任务完成（但不阻塞生成器）
                return await background_task
        
        agent_task = asyncio.create_task(run_agent_safely())
        # 添加回调，即使生成器被取消，也记录任务完成情况
        def log_agent_completion(task):
            try:
                if task.done():
                    result = task.result()
                    logger.info(f"Agent task completed (background): success={result.get('success')}")
            except asyncio.CancelledError:
                logger.warning("Agent task was cancelled")
            except Exception as e:
                logger.error(f"Agent task failed: {str(e)}", exc_info=True)
        agent_task.add_done_callback(log_agent_completion)
        logger.info("Agent task created (protected from generator cancellation)")
        
        # 同时处理 SSE 消息队列和 Agent 执行
        agent_completed = False
        agent_result = None
        
        # 发送 Agent 启动消息
        try:
            yield SSEMessage.progress("Agent 已启动，正在分析问题...", progress=0.1, step="agent_started")
        except (GeneratorExit, asyncio.CancelledError):
            logger.info("Client disconnected after agent started, but agent continues")
            # 不 return，让 Agent 继续运行
            raise
        
        # 处理消息队列和 Agent 执行
        loop = asyncio.get_event_loop()
        last_progress_time = loop.time()
        heartbeat_interval = 2.0  # 每 2 秒发送一次心跳
        pending_tasks = []
        loop_count = 0
        
        logger.info("Entering main event loop...")
        try:
            while True:
                loop_count += 1
                if loop_count % 20 == 0:  # 每 20 次循环（约 10 秒）记录一次
                    logger.debug(f"Event loop iteration {loop_count}, agent_completed={agent_completed}, queue_size={message_queue.qsize()}")
                current_time = loop.time()
                
                # 检查是否需要发送心跳（如果长时间没有消息）
                if current_time - last_progress_time > heartbeat_interval:
                    try:
                        yield SSEMessage.progress("分析进行中，请稍候...", progress=0.5, step="processing")
                        last_progress_time = current_time
                    except (GeneratorExit, asyncio.CancelledError):
                        logger.info("Client disconnected during heartbeat, but agent continues")
                        # 不 break，让 Agent 继续运行，只是不再发送消息
                        break
                
                # 创建任务列表
                tasks = [agent_task]
                
                # 如果队列不为空，添加消息接收任务
                if not message_queue.empty():
                    tasks.append(asyncio.create_task(message_queue.get()))
                
                # 如果只有 Agent 任务，使用超时等待，定期检查队列
                if len(tasks) == 1:
                    try:
                        # 等待 Agent 完成或超时（使用 shield 保护，避免被生成器取消影响）
                        logger.debug("Waiting for agent task completion (timeout=0.5s)...")
                        # 使用 shield 保护 agent_task，避免被生成器取消影响
                        shielded_task = asyncio.shield(agent_task)
                        agent_result = await asyncio.wait_for(shielded_task, timeout=0.5)
                        agent_completed = True
                        logger.info("Agent task completed!")
                        break
                    except asyncio.TimeoutError:
                        # 超时，检查队列中是否有消息
                        if not message_queue.empty():
                            logger.debug(f"Agent still running, checking message queue (size={message_queue.qsize()})...")
                            try:
                                msg = await asyncio.wait_for(message_queue.get(), timeout=0.1)
                                if msg:
                                    event = msg.get("event", "progress")
                                    data = msg.get("data", {})
                                    
                                    if event == "progress":
                                        try:
                                            yield SSEMessage.progress(
                                                data.get("message", ""),
                                                progress=data.get("progress", 0.0),
                                                step=data.get("step"),
                                            )
                                            last_progress_time = loop.time()
                                        except (GeneratorExit, asyncio.CancelledError):
                                            logger.info("Client disconnected during progress message, but agent continues")
                                            break
                                    elif event == "error":
                                        try:
                                            yield SSEMessage.error(data.get("error", "Unknown error"))
                                        except (GeneratorExit, asyncio.CancelledError):
                                            logger.info("Client disconnected during error message")
                                            break
                            except asyncio.TimeoutError:
                                pass
                        continue
                
                # 等待任一任务完成（使用 shield 保护 agent_task）
                # 将 agent_task 用 shield 包装，避免被生成器取消影响
                shielded_tasks = [asyncio.shield(agent_task) if task == agent_task else task for task in tasks]
                done, pending = await asyncio.wait(
                    shielded_tasks,
                    timeout=0.5,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                
                # 保存 pending 任务以便后续取消
                pending_tasks.extend(pending)
                
                # 处理完成的任务
                logger.debug(f"Processing {len(done)} completed tasks")
                for task in done:
                    # 检查是否是 agent_task（可能是 shielded 版本）
                    # 通过比较任务的协程对象来判断
                    is_agent_task = False
                    if task == agent_task:
                        is_agent_task = True
                    elif hasattr(task, '_coro') and hasattr(agent_task, '_coro'):
                        # 检查是否是 shielded 版本的 agent_task
                        try:
                            # shielded task 的内部结构可能不同，直接尝试获取结果
                            if not task.cancelled():
                                is_agent_task = True
                        except:
                            pass
                    
                    if is_agent_task:
                        # Agent 执行完成
                        logger.info("Agent task completed in asyncio.wait")
                        agent_completed = True
                        # 获取原始 agent_task 的结果（而不是 shielded 版本）
                        agent_result = await agent_task
                    else:
                        # 收到 SSE 消息
                        try:
                            msg = await task
                            if msg:
                                event = msg.get("event", "progress")
                                data = msg.get("data", {})
                                logger.debug(f"Received SSE message: event={event}, step={data.get('step')}")
                                
                                if event == "progress":
                                    try:
                                        yield SSEMessage.progress(
                                            data.get("message", ""),
                                            progress=data.get("progress", 0.0),
                                            step=data.get("step"),
                                        )
                                        last_progress_time = asyncio.get_event_loop().time()
                                    except (GeneratorExit, asyncio.CancelledError):
                                        logger.info("Client disconnected during progress message, but agent continues")
                                        break
                                elif event == "error":
                                    try:
                                        yield SSEMessage.error(data.get("error", "Unknown error"))
                                    except (GeneratorExit, asyncio.CancelledError):
                                        logger.info("Client disconnected during error message")
                                        break
                        except Exception as e:
                            logger.warning(f"Failed to process SSE message: {str(e)}")
                
                # Agent 完成，处理剩余消息后退出
                if agent_completed:
                    # 处理队列中剩余的消息
                    while not message_queue.empty():
                        try:
                            msg = await asyncio.wait_for(message_queue.get(), timeout=0.1)
                            if msg:
                                event = msg.get("event", "progress")
                                data = msg.get("data", {})
                                
                                if event == "progress":
                                    try:
                                        yield SSEMessage.progress(
                                            data.get("message", ""),
                                            progress=data.get("progress", 0.0),
                                            step=data.get("step"),
                                        )
                                        last_progress_time = asyncio.get_event_loop().time()
                                    except (GeneratorExit, asyncio.CancelledError):
                                        logger.info("Client disconnected during progress message, but agent continues")
                                        break
                                elif event == "error":
                                    try:
                                        yield SSEMessage.error(data.get("error", "Unknown error"))
                                    except (GeneratorExit, asyncio.CancelledError):
                                        logger.info("Client disconnected during error message")
                                        break
                        except asyncio.TimeoutError:
                            break
                    break
                
                # 如果 asyncio.wait 超时（没有任务完成），继续循环
                if not done:
                    continue
        except GeneratorExit:
            # 生成器被关闭（客户端断开连接），不取消 Agent 任务，让它继续运行
            logger.info("Generator closed (client disconnected), agent task continues in background")
            # 不取消 Agent 任务，让它继续运行
            # 只取消消息队列相关的任务
            for task in pending_tasks:
                if not task.done() and task != agent_task:
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, KeyboardInterrupt):
                        pass
            # GeneratorExit 需要重新抛出，让生成器正常关闭
            # 但 Agent 任务会继续运行
            raise
        except (asyncio.CancelledError, KeyboardInterrupt) as e:
            # 只有在服务器端主动取消时才取消 Agent 任务
            logger.warning(f"Analysis stream cancelled: {type(e).__name__}, cleaning up tasks...")
            logger.warning(f"Agent completed: {agent_completed}, Agent task done: {agent_task.done()}")
            
            # 取消 Agent 任务（只有在服务器端主动取消时）
            if not agent_completed and not agent_task.done():
                logger.warning("Cancelling agent task...")
                agent_task.cancel()
                try:
                    await agent_task
                except (asyncio.CancelledError, KeyboardInterrupt):
                    logger.debug("Agent task cancellation confirmed")
                    pass
            
            # 取消所有 pending 任务
            for task in pending_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, KeyboardInterrupt):
                        pass
            
            logger.info("All tasks cancelled")
            raise
        
        # 确保 Agent 任务完成
        if not agent_completed:
            logger.info("Waiting for agent task to complete...")
            try:
                agent_result = await agent_task
                logger.info("Agent task completed successfully")
            except asyncio.CancelledError:
                logger.info("Agent task cancelled")
                yield SSEMessage.error("分析被取消")
                return
        
        logger.info(f"Agent result success: {agent_result.get('success')}")
        if not agent_result.get("success"):
            error_msg = agent_result.get("error", "Agent execution failed")
            logger.error(f"Agent execution failed: {error_msg}")
            yield SSEMessage.error(error_msg)
            return
        
        # 解析 Agent 输出
        logger.info("Parsing agent output...")
        output_parser = OutputParser()
        parsed_result = output_parser.parse(agent_result.get("output", ""))
        # parsed_result 是 AnalysisResult 对象（Pydantic 模型），不是字典
        logger.info(f"Parsed result type: {type(parsed_result).__name__}")
        logger.info(f"Parsed result - root_cause: {parsed_result.root_cause[:100] if parsed_result.root_cause else 'None'}...")
        logger.info(f"Parsed result - suggestions count: {len(parsed_result.suggestions) if parsed_result.suggestions else 0}")
        
        # parsed_result 已经是 AnalysisResult 对象，直接使用
        result = parsed_result
        
        # 从 intermediate_steps 提取相关信息
        intermediate_steps = agent_result.get("intermediate_steps", [])
        result = extract_from_intermediate_steps(intermediate_steps, result)
        
        # 发送结果
        yield SSEMessage.result(result)
        
        # 发送完成消息
        yield SSEMessage.done()
    
    except Exception as e:
        logger.error(f"Stream analysis failed: {str(e)}", exc_info=True)
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
    
    async def event_generator() -> AsyncGenerator[str, None]:
        """事件生成器"""
        try:
            # 检查客户端是否断开连接
            async for message in _execute_analysis_stream(request, request_obj=request_obj):
                # 检查客户端是否断开连接
                try:
                    if await request_obj.is_disconnected():
                        logger.info("Client disconnected, stopping stream (but agent continues)")
                        # 客户端断开，停止发送消息，但让 Agent 继续运行
                        break
                except Exception as e:
                    logger.debug(f"Error checking client connection: {str(e)}")
                
                try:
                    yield message
                except (GeneratorExit, asyncio.CancelledError):
                    # 客户端断开连接，生成器被关闭
                    logger.info("Generator closed by client disconnect, but agent continues")
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
                # 如果客户端已断开，忽略发送错误
                pass
    
    return EventSourceResponse(event_generator())

