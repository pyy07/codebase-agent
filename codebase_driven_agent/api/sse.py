"""SSE 流式接口实现"""
import json
import asyncio
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
                    timeout=1.0  # 最多等待 1 秒，因为线程中的操作无法被取消
                )
                logger.info(f"All {len(tasks_to_cancel)} agent tasks cancelled")
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for {len(tasks_to_cancel)} agent tasks to cancel")
                logger.warning("Note: Some agent tasks may still be running in background threads")
                # 超时后不再等待，直接继续关闭流程
                # 线程中的操作（如 requests.get）无法被取消，会继续运行直到完成
        
        _active_agent_tasks.clear()


async def _generate_analysis_plan(
    input_text: str,
    context_files: Optional[List],
    executor: Any,
    callback_handler: Optional[Any],
) -> List[Dict[str, Any]]:
    """
    生成分析计划
    
    Args:
        input_text: 用户输入
        context_files: 上下文文件列表
        executor: Agent 执行器
        callback_handler: Callback handler
    
    Returns:
        任务步骤列表
    """
    try:
        from codebase_driven_agent.config import settings
        from codebase_driven_agent.agent.executor import create_llm
        
        # 构建计划生成的 prompt
        plan_prompt = f"""请分析以下问题，并制定详细的分析计划。

用户问题：
{input_text}

请按照以下格式输出分析计划（每个步骤一行）：
步骤1: [具体操作] - [预期目标]
步骤2: [具体操作] - [预期目标]
步骤3: [具体操作] - [预期目标]
...

要求：
1. 计划要具体、可执行
2. 每个步骤对应一个工具调用或分析操作
3. 步骤要按逻辑顺序排列
4. 只输出计划，不要执行任何操作

分析计划："""

        if context_files:
            context_info = "\n".join([
                f"- {ctx.get('path', 'unknown')}: {ctx.get('content', '')[:200]}..."
                for ctx in context_files
            ])
            plan_prompt += f"\n\n上下文文件：\n{context_info}"

        # 创建 LLM 实例
        llm = create_llm()
        
        # 调用 LLM 生成计划
        logger.info("Calling LLM to generate analysis plan...")
        # LLM 的 invoke 方法需要直接传递字符串或 BaseMessage 列表
        from langchain_core.messages import HumanMessage
        plan_input = [HumanMessage(content=plan_prompt)]
        
        # 使用 asyncio.to_thread 在线程中执行同步调用
        def invoke_llm():
            return llm.invoke(plan_input)
        
        plan_response = await asyncio.to_thread(invoke_llm)
        
        # 解析计划
        plan_text = ""
        if hasattr(plan_response, 'content'):
            plan_text = plan_response.content
        elif isinstance(plan_response, dict) and 'content' in plan_response:
            plan_text = plan_response['content']
        elif isinstance(plan_response, str):
            plan_text = plan_response
        else:
            logger.warning(f"Unexpected plan response format: {type(plan_response)}")
            return []
        
        logger.info(f"Plan response received, length: {len(plan_text)}")
        
        # 解析步骤
        steps = []
        lines = plan_text.split('\n')
        step_num = 1
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 匹配 "步骤N: ..." 格式
            import re
            step_pattern = r'步骤\s*(\d+)\s*[:：]\s*(.+?)(?:\s*-\s*(.+))?$'
            match = re.match(step_pattern, line)
            
            if match:
                step_num = int(match.group(1))
                action = match.group(2).strip()
                target = match.group(3).strip() if match.group(3) else ""
                
                steps.append({
                    "step": step_num,
                    "action": action,
                    "target": target,
                    "status": "pending",  # pending, running, completed, failed
                })
            elif line.startswith('步骤') or re.match(r'^\d+[\.:]', line):
                # 尝试其他格式
                parts = re.split(r'[:：-]', line, maxsplit=2)
                if len(parts) >= 2:
                    action = parts[1].strip()
                    target = parts[2].strip() if len(parts) > 2 else ""
                    steps.append({
                        "step": step_num,
                        "action": action,
                        "target": target,
                        "status": "pending",
                    })
                    step_num += 1
        
        logger.info(f"Parsed {len(steps)} steps from plan")
        return steps
        
    except Exception as e:
        logger.error(f"Failed to generate analysis plan: {e}", exc_info=True)
        return []


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
    
    @staticmethod
    def plan(steps: List[Dict[str, Any]]) -> str:
        """任务计划消息"""
        return SSEMessage.format("plan", {"steps": steps})


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
        
        # 执行 Agent 分析
        from codebase_driven_agent.agent.executor import AgentExecutorWrapper
        from codebase_driven_agent.agent.output_parser import OutputParser
        from codebase_driven_agent.utils.extractors import extract_from_intermediate_steps
        
        # 先让 Agent 生成分析计划
        logger.info("Generating analysis plan...")
        plan_steps = []
        try:
            executor_temp = AgentExecutorWrapper(callbacks=[])
            plan_steps = await _generate_analysis_plan(request.input, context_files, executor_temp, None)
            if plan_steps:
                logger.info(f"Generated analysis plan with {len(plan_steps)} steps")
                yield SSEMessage.plan(plan_steps)
                await asyncio.sleep(0.1)  # 短暂延迟，确保前端收到计划
        except Exception as e:
            logger.warning(f"Failed to generate analysis plan: {e}, continuing without plan")
        
        # 创建 SSE Callback Handler（传入计划步骤）
        from codebase_driven_agent.agent.callbacks import SSECallbackHandler
        callback_handler = SSECallbackHandler(message_queue, plan_steps=plan_steps)
        
        # 清空日志查询缓存（确保缓存仅在当次请求生效）
        from codebase_driven_agent.utils.log_query import get_log_query_instance
        log_query_instance = get_log_query_instance()
        if hasattr(log_query_instance, 'clear_cache'):
            log_query_instance.clear_cache()
            logger.debug("Log query cache cleared for new analysis request")
        
        # 创建 Agent 执行器（带 Callback）
        executor = AgentExecutorWrapper(callbacks=[callback_handler])
        
        # 启动 Agent 执行
        logger.info(f"Starting agent execution for input: {request.input[:100]}...")
        agent_task = asyncio.create_task(
            executor.run(
                input_text=request.input,
                context_files=context_files,
            )
        )
        # 注册 agent 任务，用于服务器关闭时取消
        await register_agent_task(agent_task)
        
        # 添加回调，记录任务完成情况并注销任务
        def log_agent_completion(task):
            try:
                if task.done():
                    result = task.result()
                    logger.info(f"Agent task completed: success={result.get('success')}")
            except asyncio.CancelledError:
                logger.info("Agent task was cancelled")
            except Exception as e:
                logger.error(f"Agent task failed: {str(e)}", exc_info=True)
            finally:
                # 注销任务（在事件循环中异步执行）
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(unregister_agent_task(task))
                    else:
                        # 如果没有运行的事件循环，使用线程安全的方式
                        import threading
                        def unregister_in_thread():
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            try:
                                new_loop.run_until_complete(unregister_agent_task(task))
                            finally:
                                new_loop.close()
                        threading.Thread(target=unregister_in_thread, daemon=True).start()
                except RuntimeError:
                    # 如果没有事件循环，创建一个新任务
                    asyncio.create_task(unregister_agent_task(task))
        
        agent_task.add_done_callback(log_agent_completion)
        logger.info("Agent task created and registered")
        
        # 同时处理 SSE 消息队列和 Agent 执行
        agent_completed = False
        agent_result = None
        
        # 发送 Agent 启动消息
        try:
            yield SSEMessage.progress("Agent 已启动，正在分析问题...", progress=0.1, step="agent_started")
        except (GeneratorExit, asyncio.CancelledError):
            logger.info("Client disconnected after agent started, cancelling agent task")
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
                    logger.info(f"Event loop iteration {loop_count}, agent_completed={agent_completed}, queue_size={message_queue.qsize()}, agent_task.done()={agent_task.done()}")
                current_time = loop.time()
                
                # 先检查队列中是否有消息（优先处理消息）
                try:
                    msg = message_queue.get_nowait()
                    if msg:
                        event = msg.get("event", "progress")
                        data = msg.get("data", {})
                        
                        logger.info(f"Processing queued message: {event}, step={data.get('step')}, message={data.get('message', '')[:50]}...")
                        
                        if event == "progress":
                            try:
                                yield SSEMessage.progress(
                                    data.get("message", ""),
                                    progress=data.get("progress", 0.0),
                                    step=data.get("step"),
                                )
                                last_progress_time = current_time
                                logger.debug(f"Progress message sent successfully")
                            except (GeneratorExit, asyncio.CancelledError):
                                logger.info("Client disconnected during progress message")
                                break
                        elif event == "plan":
                            try:
                                yield SSEMessage.plan(data.get("steps", []))
                                logger.debug(f"Plan message sent with {len(data.get('steps', []))} steps")
                            except (GeneratorExit, asyncio.CancelledError):
                                logger.info("Client disconnected during plan message")
                                break
                        elif event == "error":
                            try:
                                yield SSEMessage.error(data.get("error", "Unknown error"))
                            except (GeneratorExit, asyncio.CancelledError):
                                logger.info("Client disconnected during error message")
                                break
                        continue  # 处理完消息后继续循环
                except asyncio.QueueEmpty:
                    # 队列为空，继续检查其他条件
                    pass
                except Exception as e:
                    logger.error(f"Error processing queued message: {e}", exc_info=True)
                
                # 检查是否需要发送心跳（如果长时间没有消息）
                if current_time - last_progress_time > heartbeat_interval:
                    try:
                        yield SSEMessage.progress("分析进行中，请稍候...", progress=0.5, step="processing")
                        last_progress_time = current_time
                        logger.debug("Heartbeat sent")
                    except (GeneratorExit, asyncio.CancelledError):
                        logger.info("Client disconnected during heartbeat")
                        # 不 break，让 Agent 继续运行，只是不再发送消息
                        break
                
                # 创建任务列表
                tasks = [agent_task]
                
                # 如果队列不为空，添加消息接收任务
                if not message_queue.empty():
                    tasks.append(asyncio.create_task(message_queue.get()))
                
                # 如果只有 Agent 任务，使用超时等待，定期检查队列
                if len(tasks) == 1:
                    # 先检查队列中是否有消息（不等待）
                    if not message_queue.empty():
                        try:
                            msg = message_queue.get_nowait()
                            if msg:
                                event = msg.get("event", "progress")
                                data = msg.get("data", {})
                                
                                logger.debug(f"Processing queued message: {event}, data keys: {list(data.keys())}")
                                
                                if event == "progress":
                                    try:
                                        yield SSEMessage.progress(
                                            data.get("message", ""),
                                            progress=data.get("progress", 0.0),
                                            step=data.get("step"),
                                        )
                                        last_progress_time = loop.time()
                                        logger.debug(f"Progress message sent: {data.get('message', '')[:50]}...")
                                    except (GeneratorExit, asyncio.CancelledError):
                                        logger.info("Client disconnected during progress message")
                                        break
                                elif event == "plan":
                                    try:
                                        yield SSEMessage.plan(data.get("steps", []))
                                        logger.debug(f"Plan message sent with {len(data.get('steps', []))} steps")
                                    except (GeneratorExit, asyncio.CancelledError):
                                        logger.info("Client disconnected during plan message")
                                        break
                                elif event == "plan":
                                    try:
                                        yield SSEMessage.plan(data.get("steps", []))
                                        logger.debug(f"Plan message sent with {len(data.get('steps', []))} steps")
                                    except (GeneratorExit, asyncio.CancelledError):
                                        logger.info("Client disconnected during plan message")
                                        break
                                elif event == "error":
                                    try:
                                        yield SSEMessage.error(data.get("error", "Unknown error"))
                                    except (GeneratorExit, asyncio.CancelledError):
                                        logger.info("Client disconnected during error message")
                                        break
                        except asyncio.QueueEmpty:
                            pass
                        except Exception as e:
                            logger.error(f"Error processing queued message: {e}", exc_info=True)
                    
                    # 然后等待 Agent 完成或超时
                    try:
                        # 等待 Agent 完成或超时
                        logger.debug("Waiting for agent task completion (timeout=0.5s)...")
                        agent_result = await asyncio.wait_for(agent_task, timeout=0.5)
                        agent_completed = True
                        logger.info("Agent task completed!")
                        break
                    except asyncio.TimeoutError:
                        # 超时，继续循环检查队列
                        continue
                
                # 等待任一任务完成
                done, pending = await asyncio.wait(
                    tasks,
                    timeout=0.5,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                
                # 保存 pending 任务以便后续取消
                pending_tasks.extend(pending)
                
                # 处理完成的任务
                logger.debug(f"Processing {len(done)} completed tasks")
                for task in done:
                    # 检查是否是 agent_task
                    is_agent_task = (task == agent_task)
                    
                    if is_agent_task:
                        # Agent 执行完成
                        logger.info("Agent task completed in asyncio.wait")
                        agent_completed = True
                        # 获取 agent_task 的结果
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
                                        logger.info("Client disconnected during progress message")
                                        break
                                elif event == "plan":
                                    try:
                                        yield SSEMessage.plan(data.get("steps", []))
                                    except (GeneratorExit, asyncio.CancelledError):
                                        logger.info("Client disconnected during plan message")
                                        break
                                elif event == "plan":
                                    try:
                                        yield SSEMessage.plan(data.get("steps", []))
                                    except (GeneratorExit, asyncio.CancelledError):
                                        logger.info("Client disconnected during plan message")
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
                                        logger.info("Client disconnected during progress message")
                                        break
                                elif event == "plan":
                                    try:
                                        yield SSEMessage.plan(data.get("steps", []))
                                    except (GeneratorExit, asyncio.CancelledError):
                                        logger.info("Client disconnected during plan message")
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
            # 生成器被关闭（客户端断开连接），agent 任务继续在后台运行
            logger.info("Generator closed (client disconnected), agent task continues in background")
            # 不取消 Agent 任务，让它继续在后台运行
            # 只取消消息队列相关的任务
            for task in pending_tasks:
                if not task.done() and task != agent_task:
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, KeyboardInterrupt):
                        pass
            # GeneratorExit 需要重新抛出，让生成器正常关闭
            # Agent 任务会继续运行（已注册，服务器关闭时会取消）
            raise
        except (asyncio.CancelledError, KeyboardInterrupt) as e:
            # 服务器关闭（Ctrl+C），必须取消所有 Agent 任务
            logger.warning(f"Analysis stream cancelled by server shutdown: {type(e).__name__}, cancelling all tasks...")
            logger.warning(f"Agent completed: {agent_completed}, Agent task done: {agent_task.done()}")
            
            # 通知 callback handler 任务已被取消（如果存在）
            try:
                if 'callback_handler' in locals() and callback_handler is not None:
                    if hasattr(callback_handler, 'set_cancelled'):
                        callback_handler.set_cancelled()
                        logger.debug("Callback handler marked as cancelled")
            except Exception as ex:
                logger.debug(f"Failed to set cancelled on callback handler: {ex}")
            
            # 取消 Agent 任务（服务器关闭时必须取消）
            if not agent_completed and not agent_task.done():
                logger.warning("Cancelling agent task due to server shutdown...")
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
            
            logger.info("All tasks cancelled due to server shutdown")
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
                    logger.info("Generator closed by client disconnect, agent task continues in background")
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

