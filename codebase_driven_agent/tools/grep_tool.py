"""内容搜索工具实现"""
import re
import os
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field

from codebase_driven_agent.tools.base import BaseCodebaseTool, ToolResult
from codebase_driven_agent.config import settings
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.tools.grep")

# 尝试导入 ripgrepy
try:
    from ripgrepy import Ripgrepy
    RIPGREP_AVAILABLE = True
except ImportError:
    RIPGREP_AVAILABLE = False
    logger.debug("ripgrep-py not available, will use Python regex fallback")


class GrepToolInput(BaseModel):
    """内容搜索工具输入参数"""
    pattern: str = Field(..., description="搜索模式（正则表达式）")
    path: Optional[str] = Field(None, description="搜索路径（文件或目录，相对于代码仓库根目录）。如果不指定，搜索整个代码仓库")
    include: Optional[str] = Field(None, description="文件类型过滤（glob 模式，如 '*.py'、'*.js'）。如果不指定，搜索所有文本文件")


class GrepTool(BaseCodebaseTool):
    """内容搜索工具
    
    使用正则表达式搜索文件内容，支持文件类型过滤。
    """
    
    name: str = "grep"
    description: str = (
        "使用正则表达式搜索文件内容。可以在代码仓库中搜索包含特定模式的文件和行。"
        "支持文件类型过滤。"
        "使用场景：查找函数调用、变量使用、错误信息、特定字符串等。"
        "参数：pattern（正则表达式）、path（搜索路径，可选）、include（文件类型过滤，可选，如 '*.py'）。"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, "code_repo_path", settings.code_repo_path)
    
    def _search_with_ripgrep(self, pattern: str, search_path: Path, include: Optional[str] = None) -> List[dict]:
        """使用 ripgrep 搜索"""
        try:
            rg = Ripgrepy(pattern, str(search_path))
            
            if include:
                rg = rg.type(include.replace('*.', ''))
            
            results = rg.json().run()
            
            matches = []
            for item in results:
                if isinstance(item, dict) and 'data' in item:
                    data = item['data']
                    if 'path' in data and 'lines' in data:
                        file_path = data['path']['text']
                        for line_data in data['lines'].get('text', '').split('\n'):
                            if pattern in line_data or re.search(pattern, line_data):
                                line_num = data.get('line_number', {}).get('text', '0')
                                matches.append({
                                    'file': file_path,
                                    'line': int(line_num) if line_num.isdigit() else 0,
                                    'content': line_data.strip()
                                })
            
            return matches
        except Exception as e:
            logger.warning(f"ripgrep search failed: {str(e)}, falling back to Python regex")
            return []
    
    def _search_with_python(self, pattern: str, search_path: Path, include: Optional[str] = None) -> List[dict]:
        """使用 Python regex 搜索（fallback）"""
        matches = []
        compiled_pattern = re.compile(pattern)
        
        # 确定要搜索的文件
        files_to_search = []
        
        if search_path.is_file():
            files_to_search = [search_path]
        else:
            # 递归搜索目录
            for root, dirs, files in os.walk(search_path):
                # 跳过隐藏目录和常见忽略目录
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', '.git']]
                
                for file in files:
                    file_path = Path(root) / file
                    
                    # 文件类型过滤
                    if include:
                        if not file_path.match(include):
                            continue
                    
                    # 跳过二进制文件
                    try:
                        with open(file_path, 'rb') as f:
                            chunk = f.read(8192)
                            if b'\x00' in chunk:
                                continue
                    except Exception:
                        continue
                    
                    files_to_search.append(file_path)
        
        # 搜索每个文件
        for file_path in files_to_search:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    for line_num, line in enumerate(f, 1):
                        if compiled_pattern.search(line):
                            rel_path = file_path.relative_to(self.code_repo_path)
                            matches.append({
                                'file': str(rel_path),
                                'line': line_num,
                                'content': line.rstrip()
                            })
            except Exception as e:
                logger.debug(f"Failed to search file {file_path}: {str(e)}")
                continue
        
        return matches
    
    def _execute(self, pattern: str, path: Optional[str] = None, include: Optional[str] = None) -> ToolResult:
        """
        执行内容搜索
        
        Args:
            pattern: 正则表达式模式
            path: 搜索路径
            include: 文件类型过滤
        
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
            
            # 构建搜索路径
            repo_path = Path(self.code_repo_path)
            if not repo_path.exists():
                return ToolResult(
                    success=False,
                    error=f"代码仓库路径不存在: {self.code_repo_path}"
                )
            
            if path:
                search_path = repo_path / path
                if not search_path.exists():
                    return ToolResult(
                        success=False,
                        error=f"搜索路径不存在: {path}"
                    )
            else:
                search_path = repo_path
            
            # 验证正则表达式
            try:
                re.compile(pattern)
            except re.error as e:
                return ToolResult(
                    success=False,
                    error=f"无效的正则表达式: {str(e)}"
                )
            
            # 执行搜索
            if RIPGREP_AVAILABLE and search_path.is_dir():
                try:
                    matches = self._search_with_ripgrep(pattern, search_path, include)
                except Exception as e:
                    logger.warning(f"ripgrep search failed: {str(e)}, falling back to Python regex")
                    matches = self._search_with_python(pattern, search_path, include)
            else:
                matches = self._search_with_python(pattern, search_path, include)
            
            # 按文件和行号排序
            matches.sort(key=lambda x: (x['file'], x['line']))
            
            # 限制结果数量
            max_results = 50
            truncated = False
            if len(matches) > max_results:
                matches = matches[:max_results]
                truncated = True
                summary = f"找到 {len(matches)} 个匹配（显示前 {max_results} 个）"
            else:
                summary = None
            
            # 构建输出
            result_lines = []
            result_lines.append(f"搜索模式: {pattern}")
            if path:
                result_lines.append(f"搜索路径: {path}")
            if include:
                result_lines.append(f"文件类型: {include}")
            result_lines.append(f"匹配数: {len(matches)}")
            if truncated:
                result_lines.append(f"（显示前 {max_results} 个）")
            result_lines.append("")
            result_lines.append("匹配结果:")
            result_lines.append("")
            
            current_file = None
            for match in matches:
                if match['file'] != current_file:
                    if current_file is not None:
                        result_lines.append("")
                    result_lines.append(f"文件: {match['file']}")
                    current_file = match['file']
                
                result_lines.append(f"  {match['line']:4d} | {match['content']}")
            
            result_text = "\n".join(result_lines)
            
            # 检查是否需要截断输出
            if len(result_text) > self.max_output_length:
                truncated_result, truncated = self._truncate_data(result_text, self.max_output_length)
                if summary:
                    summary = f"{summary}，输出已截断"
                else:
                    summary = "输出已截断"
                result_text = truncated_result
            
            return ToolResult(
                success=True,
                data=result_text,
                truncated=truncated,
                summary=summary
            )
        
        except Exception as e:
            logger.error(f"GrepTool error: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"内容搜索时发生错误: {str(e)}"
            )
