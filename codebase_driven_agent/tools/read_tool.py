"""文件读取工具实现"""
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from codebase_driven_agent.tools.base import BaseCodebaseTool, ToolResult
from codebase_driven_agent.config import settings
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.tools.read")


class ReadToolInput(BaseModel):
    """文件读取工具输入参数"""
    file_path: str = Field(..., description="要读取的文件路径（相对于代码仓库根目录）")
    offset: Optional[int] = Field(None, description="起始行号（从1开始，包含该行）。如果不指定，从文件开头读取")
    limit: Optional[int] = Field(None, description="读取的行数。如果不指定，读取到文件末尾")


class ReadTool(BaseCodebaseTool):
    """文件读取工具
    
    用于读取代码仓库中的文件内容，支持指定行号范围。
    """
    
    name: str = "read"
    description: str = (
        "读取文件内容。读取代码仓库中的任何文件，支持指定行号范围。"
        ""
        "功能："
        "- 读取完整文件内容"
        "- 读取指定行号范围的内容"
        "- 支持多种文件格式（代码文件、配置文件、文档等）"
        ""
        "使用场景："
        "- 查看特定文件的代码内容"
        "- 查看文件的特定行范围"
        "- 查看配置文件、文档等"
        ""
        "参数："
        "- file_path（必需）：文件路径，相对于代码仓库根目录，例如 'src/utils.py'"
        "- offset（可选）：起始行号，从1开始，包含该行。例如 offset=100 表示从第100行开始"
        "- limit（可选）：读取的行数。例如 limit=51 表示读取51行（100-150行）"
        ""
        "使用示例："
        "- 读取完整文件：read(file_path='src/main.py')"
        "- 读取第 100-150 行：read(file_path='src/utils.py', offset=100, limit=51)"
        "- 读取从第 50 行开始的内容：read(file_path='config.json', offset=50)"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, "code_repo_path", settings.code_repo_path)
    
    def _execute(self, file_path: str, offset: Optional[int] = None, limit: Optional[int] = None) -> ToolResult:
        """
        执行文件读取
        
        Args:
            file_path: 文件路径
            offset: 起始行号（从1开始）
            limit: 读取的行数
        
        Returns:
            ToolResult
        """
        logger.info("=" * 80)
        logger.info("ReadTool execution started")
        logger.info(f"  file_path: {file_path}")
        logger.info(f"  offset: {offset}")
        logger.info(f"  limit: {limit}")
        logger.info(f"  code_repo_path: {self.code_repo_path}")
        logger.info("=" * 80)
        
        try:
            # 验证代码仓库路径
            if not self.code_repo_path:
                return ToolResult(
                    success=False,
                    error="代码仓库路径未配置（CODE_REPO_PATH）。请先配置代码仓库路径。"
                )
            
            # 构建完整路径
            repo_path = Path(self.code_repo_path).resolve()
            if not repo_path.exists():
                return ToolResult(
                    success=False,
                    error=f"代码仓库路径不存在: {self.code_repo_path}"
                )
            
            # 将 file_path 标准化为相对路径（移除前导斜杠和反斜杠）
            # 确保 file_path 被当作相对于 repo_path 的相对路径
            normalized_file_path = file_path.strip().lstrip('/\\')
            
            # 构建完整路径（file_path 必须是相对路径）
            full_path = (repo_path / normalized_file_path).resolve()
            
            logger.info(f"  normalized_file_path: {normalized_file_path}")
            logger.info(f"  repo_path: {repo_path}")
            logger.info(f"  full_path: {full_path}")
            logger.info(f"  full_path.exists(): {full_path.exists()}")
            
            # 确保文件在代码仓库内（防止路径遍历攻击）
            try:
                relative_path = full_path.relative_to(repo_path)
                logger.info(f"  relative_path: {relative_path}")
            except ValueError:
                logger.error(f"Path traversal detected: {file_path} -> {full_path}")
                return ToolResult(
                    success=False,
                    error=f"文件路径超出代码仓库范围: {file_path} (解析后: {full_path})"
                )
            
            # 检查文件是否存在
            if not full_path.exists():
                logger.warning(f"File not found: {full_path}")
                # 尝试查找相似的文件
                possible_files = []
                if repo_path.exists():
                    for p in repo_path.rglob(normalized_file_path.split('/')[-1] if '/' in normalized_file_path else normalized_file_path):
                        if p.is_file():
                            possible_files.append(str(p.relative_to(repo_path)))
                            if len(possible_files) >= 5:
                                break
                
                error_msg = f"文件不存在: {file_path}"
                if possible_files:
                    error_msg += f"\n\n可能的文件路径：\n" + "\n".join(f"  - {f}" for f in possible_files[:5])
                return ToolResult(
                    success=False,
                    error=error_msg
                )
            
            # 检查是否为文件
            if not full_path.is_file():
                return ToolResult(
                    success=False,
                    error=f"路径不是文件: {file_path}"
                )
            
            # 检测二进制文件
            try:
                with open(full_path, 'rb') as f:
                    chunk = f.read(8192)
                    if b'\x00' in chunk:
                        return ToolResult(
                            success=False,
                            error=f"文件是二进制文件，无法读取: {file_path}"
                        )
            except Exception as e:
                return ToolResult(
                    success=False,
                    error=f"无法读取文件: {str(e)}"
                )
            
            # 读取文件内容
            try:
                with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                # 尝试其他编码
                try:
                    with open(full_path, 'r', encoding='gbk', errors='replace') as f:
                        lines = f.readlines()
                except Exception as e:
                    return ToolResult(
                        success=False,
                        error=f"无法解码文件内容: {str(e)}"
                    )
            except Exception as e:
                return ToolResult(
                    success=False,
                    error=f"读取文件失败: {str(e)}"
                )
            
            # 处理行号范围
            total_lines = len(lines)
            start_idx = 0
            end_idx = total_lines
            
            if offset is not None:
                if offset < 1:
                    return ToolResult(
                        success=False,
                        error=f"起始行号必须 >= 1，当前值: {offset}"
                    )
                start_idx = offset - 1  # 转换为0-based索引
            
            if limit is not None:
                if limit < 1:
                    return ToolResult(
                        success=False,
                        error=f"读取行数必须 >= 1，当前值: {limit}"
                    )
                end_idx = min(start_idx + limit, total_lines)
            
            # 提取指定范围的行
            selected_lines = lines[start_idx:end_idx]
            
            logger.info(f"  total_lines: {total_lines}")
            logger.info(f"  start_idx: {start_idx}, end_idx: {end_idx}")
            logger.info(f"  selected_lines count: {len(selected_lines)}")
            
            # 构建输出
            result_lines = []
            result_lines.append(f"文件: {file_path}")
            result_lines.append(f"总行数: {total_lines}")
            if offset is not None or limit is not None:
                result_lines.append(f"显示范围: 第 {start_idx + 1} 行 - 第 {end_idx} 行（共 {len(selected_lines)} 行）")
            result_lines.append("")
            result_lines.append("内容:")
            result_lines.append("")
            
            # 添加行号
            for i, line in enumerate(selected_lines, start=start_idx + 1):
                result_lines.append(f"{i:4d} | {line.rstrip()}")
            
            result_text = "\n".join(result_lines)
            
            logger.info(f"  result_text length: {len(result_text)} characters")
            logger.info(f"  result_text preview (first 200 chars): {result_text[:200]}")
            
            # 检查是否需要截断
            truncated = False
            summary = None
            if len(result_text) > self.max_output_length:
                truncated_result, truncated = self._truncate_data(result_text, self.max_output_length)
                summary = f"文件共 {total_lines} 行，显示 {len(selected_lines)} 行"
                result_text = truncated_result
            
            return ToolResult(
                success=True,
                data=result_text,
                truncated=truncated,
                summary=summary
            )
        
        except Exception as e:
            logger.error(f"ReadTool error: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"读取文件时发生错误: {str(e)}"
            )
