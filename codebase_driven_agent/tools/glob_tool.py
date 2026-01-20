"""文件匹配工具实现"""
import glob
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field

from codebase_driven_agent.tools.base import BaseCodebaseTool, ToolResult
from codebase_driven_agent.config import settings
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.tools.glob")


class GlobToolInput(BaseModel):
    """文件匹配工具输入参数"""
    pattern: str = Field(..., description="glob 模式（如 '*.py', '**/*.ts', 'src/**/*.js'）")
    path: Optional[str] = Field(None, description="搜索的基础路径（相对于代码仓库根目录）。如果不指定，从代码仓库根目录搜索")


class GlobTool(BaseCodebaseTool):
    """文件匹配工具
    
    使用 glob 模式匹配文件，支持递归搜索。
    """
    
    name: str = "glob"
    description: str = (
        "使用 glob 模式匹配文件。可以查找符合特定模式的文件，如所有 Python 文件、特定目录下的文件等。"
        "支持递归搜索（使用 **）。"
        "使用场景：需要查找特定类型的文件、特定目录下的文件、配置文件等。"
        "参数：pattern（glob 模式，如 '*.py'、'**/*.ts'）、path（搜索基础路径，可选）。"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, "code_repo_path", settings.code_repo_path)
    
    def _execute(self, pattern: str, path: Optional[str] = None) -> ToolResult:
        """
        执行文件匹配
        
        Args:
            pattern: glob 模式
            path: 搜索基础路径
        
        Returns:
            ToolResult
        """
        try:
            # 验证代码仓库路径
            if not self.code_repo_path:
                return ToolResult(
                    success=False,
                    error="代码仓库路径未配置（CODE_REPO_PATH）。请先配置代码仓库路径。"
                )
            
            # 构建基础路径
            repo_path = Path(self.code_repo_path)
            if not repo_path.exists():
                return ToolResult(
                    success=False,
                    error=f"代码仓库路径不存在: {self.code_repo_path}"
                )
            
            # 确定搜索路径
            if path:
                search_path = repo_path / path
                if not search_path.exists():
                    return ToolResult(
                        success=False,
                        error=f"搜索路径不存在: {path}"
                    )
            else:
                search_path = repo_path
            
            # 构建完整的 glob 模式
            if path:
                full_pattern = str(search_path / pattern)
            else:
                full_pattern = str(repo_path / pattern)
            
            # 执行 glob 匹配
            matched_files = glob.glob(full_pattern, recursive=True)
            
            # 转换为相对路径
            matched_relative = []
            for file_path in matched_files:
                try:
                    rel_path = Path(file_path).relative_to(repo_path)
                    if Path(file_path).is_file():  # 只包含文件，不包含目录
                        matched_relative.append(str(rel_path))
                except ValueError:
                    # 文件不在仓库内，跳过
                    continue
            
            # 按修改时间排序（最新的在前）
            matched_relative.sort(key=lambda p: Path(repo_path / p).stat().st_mtime, reverse=True)
            
            # 限制结果数量（避免返回过多文件）
            max_results = 100
            if len(matched_relative) > max_results:
                matched_relative = matched_relative[:max_results]
                truncated = True
                summary = f"找到 {len(glob.glob(full_pattern, recursive=True))} 个文件，显示前 {max_results} 个（按修改时间排序）"
            else:
                truncated = False
                summary = None
            
            # 构建输出
            result_lines = []
            result_lines.append(f"模式: {pattern}")
            if path:
                result_lines.append(f"搜索路径: {path}")
            result_lines.append(f"匹配文件数: {len(matched_relative)}")
            if truncated:
                result_lines.append(f"（显示前 {max_results} 个）")
            result_lines.append("")
            result_lines.append("文件列表:")
            result_lines.append("")
            
            for i, file_path in enumerate(matched_relative, 1):
                result_lines.append(f"{i:3d}. {file_path}")
            
            result_text = "\n".join(result_lines)
            
            return ToolResult(
                success=True,
                data=result_text,
                truncated=truncated,
                summary=summary
            )
        
        except Exception as e:
            logger.error(f"GlobTool error: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"文件匹配时发生错误: {str(e)}"
            )
