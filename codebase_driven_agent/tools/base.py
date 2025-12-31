"""LangChain Tools 基础接口规范"""
from abc import ABC, abstractmethod
from typing import Any, Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """工具执行结果"""
    success: bool = Field(..., description="是否成功")
    data: Any = Field(None, description="返回数据")
    error: Optional[str] = Field(None, description="错误信息")
    truncated: bool = Field(False, description="数据是否被截断")
    summary: Optional[str] = Field(None, description="数据摘要（如果被截断）")


class BaseCodebaseTool(BaseTool, ABC):
    """代码库驱动工具基类
    
    所有工具都应该继承此类，确保统一的接口和行为。
    """
    
    # Pydantic V2 兼容：将实例变量定义为类变量，使用 Field 设置默认值
    max_output_length: int = Field(default=5000, exclude=True)
    enable_truncation: bool = Field(default=True, exclude=True)
    
    def __init__(self, **kwargs):
        # 提取自定义参数
        max_output_length = kwargs.pop("max_output_length", 5000)
        enable_truncation = kwargs.pop("enable_truncation", True)
        
        super().__init__(**kwargs)
        
        # 使用 object.__setattr__ 绕过 Pydantic 的字段验证
        object.__setattr__(self, "max_output_length", max_output_length)
        object.__setattr__(self, "enable_truncation", enable_truncation)
    
    def _run(self, *args, **kwargs) -> str:
        """
        同步执行工具
        
        子类应该实现 _execute 方法，而不是直接重写此方法
        """
        try:
            result = self._execute(*args, **kwargs)
            return self._format_result(result)
        except KeyboardInterrupt:
            # 任务被取消，重新抛出以便上层处理
            raise
        except Exception as e:
            return self._format_error(str(e))
    
    async def _arun(self, *args, **kwargs) -> str:
        """
        异步执行工具
        
        子类应该实现 _execute_async 方法，而不是直接重写此方法
        """
        try:
            result = await self._execute_async(*args, **kwargs)
            return self._format_result(result)
        except Exception as e:
            return self._format_error(str(e))
    
    @abstractmethod
    def _execute(self, *args, **kwargs) -> ToolResult:
        """
        执行工具逻辑（同步）
        
        子类必须实现此方法
        """
        pass
    
    async def _execute_async(self, *args, **kwargs) -> ToolResult:
        """
        执行工具逻辑（异步）
        
        默认实现调用同步方法，子类可以重写以实现真正的异步逻辑
        """
        return self._execute(*args, **kwargs)
    
    def _format_result(self, result: ToolResult) -> str:
        """格式化工具结果为字符串"""
        if not result.success:
            return f"错误: {result.error}"
        
        output = ""
        
        if result.summary:
            output += f"摘要: {result.summary}\n\n"
        
        if result.truncated:
            output += f"[注意: 结果已截断，仅显示前 {self.max_output_length} 个字符]\n\n"
        
        # 格式化数据
        if isinstance(result.data, str):
            output += result.data
        elif isinstance(result.data, (list, dict)):
            import json
            output += json.dumps(result.data, ensure_ascii=False, indent=2)
        else:
            output += str(result.data)
        
        return output[:self.max_output_length] if self.enable_truncation else output
    
    def _format_error(self, error: str) -> str:
        """格式化错误信息"""
        return f"工具执行失败: {error}\n\n请检查参数是否正确，或尝试其他方法。"
    
    def _truncate_data(self, data: str, max_length: Optional[int] = None) -> tuple:
        """
        截断数据
        
        Returns:
            (truncated_data, is_truncated)
        """
        max_length = max_length or self.max_output_length
        if len(data) <= max_length:
            return data, False
        
        truncated = data[:max_length] + "\n\n[数据已截断...]"
        return truncated, True
    
    def _create_summary(self, data: Any) -> str:
        """
        创建数据摘要
        
        子类可以重写此方法以实现自定义摘要逻辑
        """
        if isinstance(data, str):
            if len(data) > 200:
                return data[:200] + "..."
            return data
        elif isinstance(data, list):
            return f"共 {len(data)} 条记录"
        elif isinstance(data, dict):
            return f"包含 {len(data)} 个字段"
        else:
            return str(data)[:200]

