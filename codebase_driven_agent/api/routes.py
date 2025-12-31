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
    """执行分析（集成 Agent）"""
    from codebase_driven_agent.agent.executor import AgentExecutorWrapper
    from codebase_driven_agent.agent.output_parser import OutputParser
    
    try:
        # 创建 Agent 执行器
        executor = AgentExecutorWrapper()
        
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
        
        # 解析 Agent 输出
        output_parser = OutputParser()
        parsed_result = output_parser.parse(result.get("output", ""))
        
        # parsed_result 已经是 AnalysisResult 对象，直接使用
        analysis_result = parsed_result
        
        # 从 intermediate_steps 提取相关信息
        from codebase_driven_agent.utils.extractors import extract_from_intermediate_steps
        intermediate_steps = result.get("intermediate_steps", [])
        analysis_result = extract_from_intermediate_steps(intermediate_steps, analysis_result)
        
        return analysis_result
    
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

