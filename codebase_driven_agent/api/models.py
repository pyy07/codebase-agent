"""API 请求/响应模型"""
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ContextFile(BaseModel):
    """辅助上下文文件"""
    type: str = Field(..., description="文件类型：'code' 或 'log'")
    path: Optional[str] = Field(None, description="文件路径（代码文件时必需）")
    content: str = Field(..., description="文件内容")
    line_start: Optional[int] = Field(None, description="起始行号（代码文件时可选）")
    line_end: Optional[int] = Field(None, description="结束行号（代码文件时可选）")


class AnalyzeRequest(BaseModel):
    """分析请求模型"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "input": "错误日志或问题描述",
                "context_files": [
                    {
                        "type": "code",
                        "path": "src/main.py",
                        "content": "代码片段内容",
                        "line_start": 10,
                        "line_end": 50
                    }
                ]
            }
        }
    )
    
    input: str = Field(..., description="用户输入（错误日志、问题描述、疑问等）")
    context_files: Optional[List[ContextFile]] = Field(
        default=None,
        description="辅助上下文文件列表（可选）"
    )


class AnalysisResult(BaseModel):
    """分析结果模型"""
    root_cause: str = Field(..., description="根因分析")
    suggestions: List[str] = Field(..., description="应急处理建议列表")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度评分（0-1）")
    related_code: Optional[List[dict]] = Field(None, description="相关代码引用")
    related_logs: Optional[List[dict]] = Field(None, description="相关日志引用")
    related_data: Optional[List[dict]] = Field(None, description="相关数据库查询结果")


class AnalyzeResponse(BaseModel):
    """分析响应模型"""
    task_id: Optional[str] = Field(None, description="任务ID（异步请求时返回）")
    status: str = Field(..., description="任务状态：'pending', 'running', 'completed', 'failed'")
    result: Optional[AnalysisResult] = Field(None, description="分析结果（完成时返回）")
    error: Optional[str] = Field(None, description="错误信息（失败时返回）")
    execution_time: Optional[float] = Field(None, description="执行时间（秒）")


class AsyncTaskResponse(BaseModel):
    """异步任务响应模型"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态：'pending', 'running', 'completed', 'failed'")
    message: str = Field(..., description="响应消息")

