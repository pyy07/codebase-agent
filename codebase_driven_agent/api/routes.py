"""API 路由实现"""
import uuid
import time
import threading
from typing import Dict, Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks

from codebase_driven_agent.api.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    AsyncTaskResponse,
    AnalysisResult,
    ContextFile,
    UserReplyRequest,
    UserReplyResponse,
    SkipUserInputRequest,
    SkipUserInputResponse,
)
from codebase_driven_agent.config import settings
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.api")

router = APIRouter(prefix="/api/v1", tags=["analysis"])

# 任务存储（内存存储，线程安全）
# TODO: 后续可以替换为 Redis
_tasks: Dict[str, Dict] = {}
_task_lock = threading.Lock()  # 线程锁，保证线程安全


def _generate_task_id() -> str:
    """生成任务ID"""
    return str(uuid.uuid4())


def _create_task(task_id: str, status: str = "pending") -> Dict:
    """创建任务（线程安全）"""
    with _task_lock:
        task = {
            "task_id": task_id,
            "status": status,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "result": None,
            "error": None,
            "execution_time": None,
        }
        _tasks[task_id] = task
        return task


def _update_task(task_id: str, **kwargs) -> Optional[Dict]:
    """更新任务状态（线程安全）"""
    with _task_lock:
        if task_id not in _tasks:
            return None
        
        task = _tasks[task_id]
        task.update(kwargs)
        task["updated_at"] = datetime.now()
        return task


def _get_task(task_id: str) -> Optional[Dict]:
    """获取任务（线程安全）"""
    with _task_lock:
        return _tasks.get(task_id)


def _cleanup_expired_tasks():
    """清理过期任务（线程安全）"""
    with _task_lock:
        now = datetime.now()
        expired_task_ids = []
        
        for task_id, task in _tasks.items():
            # 检查任务是否过期
            if task.get("updated_at"):
                age = now - task["updated_at"]
                if age.total_seconds() > settings.task_ttl:
                    expired_task_ids.append(task_id)
        
        # 删除过期任务
        for task_id in expired_task_ids:
            del _tasks[task_id]
            logger.info(f"Cleaned up expired task: {task_id}")
        
        # 限制最大任务数量
        if len(_tasks) > settings.max_tasks:
            # 按更新时间排序，删除最旧的任务
            sorted_tasks = sorted(
                _tasks.items(),
                key=lambda x: x[1].get("updated_at", datetime.min)
            )
            excess_count = len(_tasks) - settings.max_tasks
            for i in range(excess_count):
                task_id = sorted_tasks[i][0]
                del _tasks[task_id]
                logger.info(f"Removed excess task: {task_id}")


def _parse_context_files(context_files: Optional[List[ContextFile]]) -> Dict:
    """解析 context_files，返回结构化数据"""
    if not context_files:
        return {
            "code_snippets": [],
            "log_snippets": [],
        }
    
    code_snippets = []
    log_snippets = []
    
    for ctx_file in context_files:
        if ctx_file.type == "code":
            code_snippets.append({
                "path": ctx_file.path,
                "content": ctx_file.content,
                "line_start": ctx_file.line_start,
                "line_end": ctx_file.line_end,
            })
        elif ctx_file.type == "log":
            log_snippets.append({
                "path": ctx_file.path,
                "content": ctx_file.content,
                "timestamp_start": getattr(ctx_file, "timestamp_start", None),
                "timestamp_end": getattr(ctx_file, "timestamp_end", None),
            })
    
    return {
        "code_snippets": code_snippets,
        "log_snippets": log_snippets,
    }


async def _execute_analysis(request: AnalyzeRequest) -> AnalysisResult:
    """执行分析（集成 Agent）- 使用 GraphExecutorWrapper"""
    from codebase_driven_agent.agent.graph_executor import GraphExecutorWrapper
    from codebase_driven_agent.agent.output_parser import OutputParser
    
    try:
        # 创建 GraphExecutor 执行器
        executor = GraphExecutorWrapper()
        
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
        
        # 执行 Agent
        result = await executor.run(
            input_text=request.input,
            context_files=context_files,
        )
        
        if not result.get("success"):
            raise Exception(result.get("error", "Agent execution failed"))
        
        # GraphExecutorWrapper 返回的 final_result 已经是 AnalysisResult 格式
        if result.get("final_result"):
            return result["final_result"]
        
        # 如果没有 final_result，尝试解析 output
        output_parser = OutputParser()
        parsed_result = output_parser.parse(result.get("output", ""))
        
        return parsed_result
    
    except Exception as e:
        logger.error(f"Analysis execution failed: {str(e)}", exc_info=True)
        # 返回错误结果
        return AnalysisResult(
            root_cause=f"分析失败: {str(e)}",
            suggestions=["请检查输入是否正确", "请检查工具配置是否完整"],
            confidence=0.0,
            related_code=None,
            related_logs=None,
            related_data=None,
        )


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_sync(request: AnalyzeRequest):
    """
    同步分析接口
    
    接收用户输入和可选的 context_files，同步执行分析并返回结果。
    
    支持请求缓存和去重：
    - 相同输入（包括 context_files）的请求会返回缓存结果
    - 缓存默认保留 1 小时
    - 可以通过配置 CACHE_TTL 和 CACHE_MAX_SIZE 调整缓存参数
    """
    start_time = time.time()
    
    try:
        # 检查缓存（如果启用）
        from codebase_driven_agent.utils.cache import get_request_cache
        cache = get_request_cache()
        
        if cache:
            # 构建请求数据用于缓存键生成
            request_data = {
                "input": request.input,
                "context_files": [
                    {
                        "type": ctx.type,
                        "path": ctx.path,
                        "content": ctx.content,
                        "line_start": ctx.line_start,
                        "line_end": ctx.line_end,
                    }
                    for ctx in (request.context_files or [])
                ],
            }
            
            # 尝试从缓存获取结果
            cached_result = cache.get(request_data)
            if cached_result:
                logger.info("Returning cached result")
                execution_time = time.time() - start_time
                return AnalyzeResponse(
                    task_id=None,
                    status="completed",
                    result=cached_result,
                    error=None,
                    execution_time=execution_time,
                )
        
        # 解析 context_files
        _parse_context_files(request.context_files)
        logger.info(f"Received analysis request with {len(request.context_files or [])} context files")
        
        # 执行分析
        result = await _execute_analysis(request)
        
        # 缓存结果（仅缓存成功的结果）
        if cache and result and result.confidence > 0:
            request_data = {
                "input": request.input,
                "context_files": [
                    {
                        "type": ctx.type,
                        "path": ctx.path,
                        "content": ctx.content,
                        "line_start": ctx.line_start,
                        "line_end": ctx.line_end,
                    }
                    for ctx in (request.context_files or [])
                ],
            }
            cache.set(request_data, result)
        
        execution_time = time.time() - start_time
        
        return AnalyzeResponse(
            task_id=None,
            status="completed",
            result=result,
            error=None,
            execution_time=execution_time,
        )
    
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}", exc_info=True)
        execution_time = time.time() - start_time
        
        return AnalyzeResponse(
            task_id=None,
            status="failed",
            result=None,
            error=str(e),
            execution_time=execution_time,
        )


async def _execute_analysis_async(task_id: str, request: AnalyzeRequest):
    """异步执行分析"""
    try:
        _update_task(task_id, status="running")
        
        # 解析 context_files
        context_data = _parse_context_files(request.context_files)
        logger.info(f"Task {task_id}: Starting analysis with {len(request.context_files or [])} context files")
        
        # 执行分析
        start_time = time.time()
        result = await _execute_analysis(request)
        execution_time = time.time() - start_time
        
        # 更新任务状态
        _update_task(
            task_id,
            status="completed",
            result=result,
            execution_time=execution_time,
        )
        logger.info(f"Task {task_id}: Analysis completed in {execution_time:.2f}s")
    
    except Exception as e:
        logger.error(f"Task {task_id}: Analysis failed: {str(e)}", exc_info=True)
        execution_time = time.time() - start_time if 'start_time' in locals() else None
        
        _update_task(
            task_id,
            status="failed",
            error=str(e),
            execution_time=execution_time,
        )


@router.post("/analyze/async", response_model=AsyncTaskResponse)
async def analyze_async(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    异步分析接口
    
    接收用户输入和可选的 context_files，创建异步任务并立即返回任务ID。
    """
    # 清理过期任务
    _cleanup_expired_tasks()
    
    # 创建任务
    task_id = _generate_task_id()
    _create_task(task_id, status="pending")
    
    # 提交后台任务
    background_tasks.add_task(_execute_analysis_async, task_id, request)
    
    logger.info(f"Created async task: {task_id}")
    
    return AsyncTaskResponse(
        task_id=task_id,
        status="pending",
        message="Task created successfully",
    )


@router.get("/analyze/{task_id}", response_model=AnalyzeResponse)
async def get_task_status(task_id: str):
    """
    查询任务状态
    
    根据任务ID查询异步任务的执行状态和结果。
    """
    task = _get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return AnalyzeResponse(
        task_id=task["task_id"],
        status=task["status"],
        result=task.get("result"),
        error=task.get("error"),
        execution_time=task.get("execution_time"),
    )


@router.post("/analyze/reply", response_model=UserReplyResponse)
async def reply_to_agent(reply_request: UserReplyRequest):
    """
    用户回复 Agent 的询问
    
    当 Agent 请求用户输入时，用户可以通过此端点提交回复。
    系统会恢复 Agent 执行流程，继续分析。
    """
    from codebase_driven_agent.agent.session_manager import get_session_manager
    from langchain_core.messages import HumanMessage
    import asyncio
    
    session_manager = get_session_manager()
    session = session_manager.get_session(reply_request.request_id)
    
    if not session:
        logger.warning(f"Session not found or expired: {reply_request.request_id}")
        raise HTTPException(
            status_code=404,
            detail="会话不存在或已过期，请重新开始分析"
        )
    
    try:
        # 将用户回复添加到消息历史
        state = session.state
        messages = list(state.get("messages", []))
        messages.append(HumanMessage(content=f"用户回复：{reply_request.reply}"))
        
        # 更新状态
        updated_state = dict(state)
        updated_state["messages"] = messages
        updated_state["should_continue"] = True  # 恢复执行
        updated_state["decision"] = None  # 清除之前的决策
        
        # 恢复 Agent 执行
        executor = session.executor
        message_queue = session.message_queue
        
        # 标记"请求用户输入"步骤为已完成，并更新 current_step
        plan_steps = updated_state.get("plan_steps", [])
        current_step = updated_state.get("current_step", 0)
        
        # 找到用户交互步骤（通常是当前步骤）
        user_input_step_idx = None
        for step_idx, step in enumerate(plan_steps):
            if step.get("tool_name") == "user_input" or step.get("action", "").lower().find("请求用户输入") >= 0:
                user_input_step_idx = step_idx
                break
        
        # 发送步骤执行结果，标记用户输入步骤为已完成
        if message_queue and user_input_step_idx is not None:
            try:
                step_execution_msg = {
                    "event": "step_execution",
                    "data": {
                        "step": user_input_step_idx + 1,
                        "action": plan_steps[user_input_step_idx].get("action"),
                        "target": plan_steps[user_input_step_idx].get("target"),
                        "status": "completed",
                        "result": f"用户已回复：{reply_request.reply[:200]}",
                    }
                }
                message_queue.put_nowait(step_execution_msg)
                logger.info(f"User reply: Marked user input step {user_input_step_idx + 1} as completed")
            except Exception as e:
                logger.error(f"Failed to mark user input step as completed: {e}", exc_info=True)
        
        # 更新 current_step：用户交互步骤已完成，移动到下一个步骤
        if user_input_step_idx is not None:
            updated_state["current_step"] = user_input_step_idx + 1
            logger.info(f"User reply: Updated current_step from {current_step} to {user_input_step_idx + 1}")
        
        # 确保 executor 的 message_queue 正确设置（用户回复后的执行需要使用同一个队列）
        # GraphExecutorWrapper 内部使用 self.executor (GraphExecutor)，需要设置 executor.executor.message_queue
        graph_executor = None
        if executor:
            if hasattr(executor, 'executor') and hasattr(executor.executor, 'message_queue'):
                graph_executor = executor.executor
                graph_executor.message_queue = message_queue
                logger.info(f"Updated executor.executor.message_queue for session {reply_request.request_id}")
            elif hasattr(executor, 'message_queue'):
                graph_executor = executor
                graph_executor.message_queue = message_queue
                logger.info(f"Updated executor.message_queue for session {reply_request.request_id}")
        
        if not graph_executor:
            logger.error(f"Failed to get graph_executor for session {reply_request.request_id}")
            raise HTTPException(
                status_code=500,
                detail="无法获取执行器实例"
            )
        
        # 在后台继续执行 Agent
        async def continue_execution():
            try:
                # 使用更新后的状态继续执行
                # 注意：这里需要从 request_user_input 节点之后继续，即 execute_step
                # 但由于 LangGraph 的限制，我们需要重新运行图，从当前状态开始
                # 实际上，由于图结构是 request_user_input -> execute_step，用户回复后应该继续执行
                # 我们需要手动触发下一步执行
                
                # 更新会话状态
                session.state = updated_state
                
                # 发送用户回复消息到前端
                if message_queue:
                    logger.info(f"Putting user_reply message into queue for session {reply_request.request_id}")
                    message_queue.put_nowait({
                        "event": "user_reply",
                        "data": {
                            "request_id": reply_request.request_id,
                            "reply": reply_request.reply,
                        }
                    })
                    logger.info(f"User_reply message queued successfully, queue size: {message_queue.qsize()}")
                
                # 由于 LangGraph 不支持从中间节点开始执行，我们需要手动执行后续节点
                # 图结构是：request_user_input -> execute_step -> decide -> ...
                # 用户回复后，应该让 Agent 基于新信息重新决策下一步
                
                # 继续执行决策和执行循环
                max_iterations = 50  # 防止无限循环
                iteration = 0
                
                while iteration < max_iterations:
                    iteration += 1
                    
                    # 检查是否还有未执行的步骤
                    plan_steps = updated_state.get("plan_steps", [])
                    current_step = updated_state.get("current_step", 0)
                    
                    # 如果还有未执行的步骤，先执行下一个步骤
                    if current_step < len(plan_steps):
                        logger.info(f"User reply: Executing next step {current_step + 1}/{len(plan_steps)}")
                        # 执行下一个步骤
                        import asyncio
                        step_result = await asyncio.to_thread(
                            graph_executor._execute_step_node,
                            updated_state
                        )
                        updated_state.update(step_result)
                        session.state = updated_state
                        
                        # 执行步骤后，继续循环进行决策
                        continue
                    
                    # 如果没有更多步骤，执行决策节点（基于用户回复和已有结果重新决策）
                    logger.info("User reply: No more steps, executing decision node")
                    decision_result = graph_executor._decision_node(updated_state)
                    updated_state.update(decision_result)
                    session.state = updated_state
                    
                    # 检查下一步动作
                    next_action = graph_executor._should_continue(updated_state)
                    logger.info(f"User reply: Next action after decision: {next_action}")
                    
                    if next_action == "synthesize":
                        # 生成最终结果
                        logger.info("User reply: Executing synthesize node")
                        # 在线程池中执行同步的 _synthesize_node，避免阻塞事件循环
                        import asyncio
                        synthesize_result = await asyncio.to_thread(
                            graph_executor._synthesize_node,
                            updated_state
                        )
                        updated_state.update(synthesize_result)
                        session.state = updated_state
                        # _synthesize_node 会自动发送 result 和 done 事件到消息队列
                        logger.info("User reply: Synthesize completed, result and done events should be queued")
                        break
                    elif next_action == "request_input":
                        # 再次请求用户输入，保存会话
                        logger.info("User reply: Action is 'request_input', executing request_user_input node")
                        # 确保 graph_executor 的 message_queue 正确设置
                        if not graph_executor.message_queue:
                            graph_executor.message_queue = message_queue
                            logger.info(f"User reply: Set graph_executor.message_queue for request_input")
                        request_result = graph_executor._request_user_input_node(updated_state)
                        updated_state.update(request_result)
                        session.state = updated_state
                        # 更新会话的 request_id
                        new_request_id = request_result.get("request_id")
                        if new_request_id and new_request_id != reply_request.request_id:
                            session_manager.remove_session(reply_request.request_id)
                            session_manager.create_session(
                                state=updated_state,
                                executor=executor,
                                message_queue=message_queue,
                                request_id=new_request_id
                            )
                        # _request_user_input_node 会自动发送 user_input_request 事件到消息队列
                        logger.info(f"User reply: Request user input node completed, request_id={new_request_id}, message_queue size={message_queue.qsize() if message_queue else 'N/A'}")
                        # 确保消息队列中有事件（如果 _request_user_input_node 没有发送，这里手动发送）
                        if message_queue and message_queue.qsize() == 0:
                            logger.warning(f"User reply: message_queue is empty after request_user_input_node, manually sending event")
                            try:
                                message_queue.put_nowait({
                                    "event": "user_input_request",
                                    "data": {
                                        "request_id": new_request_id,
                                        "question": updated_state.get("user_input_question", ""),
                                        "context": updated_state.get("user_input_context", ""),
                                    }
                                })
                                logger.info(f"User reply: Manually sent user_input_request event")
                            except Exception as e:
                                logger.error(f"Failed to manually queue user_input_request message: {e}", exc_info=True)
                        break
                    elif next_action == "continue":
                        # "continue" 表示应该执行 execute_step 节点
                        logger.info("User reply: Action is 'continue', executing step node")
                        # 在线程池中执行同步的 _execute_step_node，避免阻塞事件循环
                        import asyncio
                        step_result = await asyncio.to_thread(
                            graph_executor._execute_step_node,
                            updated_state
                        )
                        updated_state.update(step_result)
                        session.state = updated_state
                        # 执行步骤后，继续循环进行决策
                    elif next_action == "execute_step":
                        # 继续执行步骤（这个分支实际上不应该被 _should_continue 返回，但保留以防万一）
                        logger.info("User reply: Action is 'execute_step', executing step node")
                        # 在线程池中执行同步的 _execute_step_node，避免阻塞事件循环
                        import asyncio
                        step_result = await asyncio.to_thread(
                            graph_executor._execute_step_node,
                            updated_state
                        )
                        updated_state.update(step_result)
                        session.state = updated_state
                    elif next_action == "plan" or next_action == "adjust_plan":
                        # 调整计划
                        logger.info(f"User reply: Action is '{next_action}', executing plan node")
                        # 在线程池中执行同步的 _plan_node，避免阻塞事件循环
                        import asyncio
                        plan_result = await asyncio.to_thread(
                            graph_executor._plan_node,
                            updated_state
                        )
                        updated_state.update(plan_result)
                        session.state = updated_state
                    elif next_action == "end":
                        logger.info("User reply: Action is 'end', stopping execution")
                        break
                    else:
                        logger.warning(f"Unknown next action: {next_action}, stopping execution")
                        break
                
                # 清理会话
                session_manager.remove_session(reply_request.request_id)
                
            except Exception as e:
                logger.error(f"Error continuing execution after user reply: {e}", exc_info=True)
                if message_queue:
                    message_queue.put_nowait({
                        "event": "error",
                        "data": {"error": f"继续执行时出错: {str(e)}"}
                    })
                session_manager.remove_session(reply_request.request_id)
        
        # 在后台任务中继续执行（不等待完成，立即返回）
        task = asyncio.create_task(continue_execution())
        logger.info(f"Created background task for continue_execution, task id: {id(task)}")
        
        logger.info(f"User reply received for session {reply_request.request_id}, continuing execution in background")
        
        # 立即返回，不等待后台任务完成
        return UserReplyResponse(
            success=True,
            message="回复已收到，Agent 将继续分析"
        )
        
    except Exception as e:
        logger.error(f"Error processing user reply: {e}", exc_info=True)
        session_manager.remove_session(reply_request.request_id)
        raise HTTPException(
            status_code=500,
            detail=f"处理用户回复时出错: {str(e)}"
        )


@router.post("/analyze/skip", response_model=SkipUserInputResponse)
async def skip_user_input(skip_request: SkipUserInputRequest):
    """
    跳过用户输入，让 Agent 基于已有信息直接得出结论
    
    当用户无法提供进一步信息时，可以通过此端点跳过用户输入请求。
    系统会通知 Agent 用户无法提供信息，让 Agent 基于已有信息得出结论。
    """
    from codebase_driven_agent.agent.session_manager import get_session_manager
    from langchain_core.messages import HumanMessage
    import asyncio
    
    session_manager = get_session_manager()
    session = session_manager.get_session(skip_request.request_id)
    
    if not session:
        logger.warning(f"Session not found or expired: {skip_request.request_id}")
        raise HTTPException(
            status_code=404,
            detail="会话不存在或已过期，请重新开始分析"
        )
    
    try:
        # 将跳过信息添加到消息历史
        state = session.state
        messages = list(state.get("messages", []))
        messages.append(HumanMessage(content="用户无法提供进一步信息，请基于已有信息得出结论。"))
        
        # 更新状态
        updated_state = dict(state)
        updated_state["messages"] = messages
        updated_state["should_continue"] = True  # 恢复执行
        updated_state["decision"] = None  # 清除之前的决策
        
        # 恢复 Agent 执行
        executor = session.executor
        message_queue = session.message_queue
        
        # 确保 executor 的 message_queue 正确设置
        graph_executor = None
        if executor:
            if hasattr(executor, 'executor') and hasattr(executor.executor, 'message_queue'):
                graph_executor = executor.executor
                graph_executor.message_queue = message_queue
                logger.info(f"Updated executor.executor.message_queue for session {skip_request.request_id}")
            elif hasattr(executor, 'message_queue'):
                graph_executor = executor
                graph_executor.message_queue = message_queue
                logger.info(f"Updated executor.message_queue for session {skip_request.request_id}")
        
        if not graph_executor:
            logger.error(f"Failed to get graph_executor for session {skip_request.request_id}")
            raise HTTPException(
                status_code=500,
                detail="无法获取执行器实例"
            )
        
        # 在后台继续执行 Agent，直接进入 synthesize
        async def continue_execution():
            try:
                session.state = updated_state
                
                # 发送跳过消息到前端
                if message_queue:
                    message_queue.put_nowait({
                        "event": "user_reply",
                        "data": {
                            "request_id": skip_request.request_id,
                            "reply": "[已跳过，Agent 将基于已有信息得出结论]",
                        }
                    })
                
                # graph_executor 已经在上面设置好了
                if not graph_executor:
                    raise ValueError("graph_executor is not available")
                
                # 直接执行 synthesize 节点，基于已有信息得出结论
                logger.info("Skip user input: Executing synthesize node directly")
                # 在线程池中执行同步的 _synthesize_node，避免阻塞事件循环
                import asyncio
                synthesize_result = await asyncio.to_thread(
                    graph_executor._synthesize_node,
                    updated_state
                )
                updated_state.update(synthesize_result)
                session.state = updated_state
                # _synthesize_node 会自动发送 result 和 done 事件到消息队列
                logger.info("Skip user input: Synthesize completed, result and done events should be queued")
                
                # 清理会话
                session_manager.remove_session(skip_request.request_id)
                
            except Exception as e:
                logger.error(f"Error continuing execution after skip: {e}", exc_info=True)
                if message_queue:
                    message_queue.put_nowait({
                        "event": "error",
                        "data": {"error": f"继续执行时出错: {str(e)}"}
                    })
                session_manager.remove_session(skip_request.request_id)
        
        # 在后台任务中继续执行
        asyncio.create_task(continue_execution())
        
        logger.info(f"User input skipped for session {skip_request.request_id}, continuing execution")
        
        return SkipUserInputResponse(
            success=True,
            message="已跳过，Agent 将基于已有信息得出结论"
        )
        
    except Exception as e:
        logger.error(f"Error processing skip request: {e}", exc_info=True)
        session_manager.remove_session(skip_request.request_id)
        raise HTTPException(
            status_code=500,
            detail=f"处理跳过请求时出错: {str(e)}"
        )

