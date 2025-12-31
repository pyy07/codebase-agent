"""代码工具实现"""
import os
import re
from typing import Optional, List, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field

from codebase_driven_agent.tools.base import BaseCodebaseTool, ToolResult
from codebase_driven_agent.config import settings
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.tools.code")

try:
    import git
    GITPYTHON_AVAILABLE = True
except ImportError:
    GITPYTHON_AVAILABLE = False
    logger.warning("gitpython not available, Git operations will be disabled")

try:
    from ripgrepy import Ripgrepy
    RIPGREP_AVAILABLE = True
except ImportError:
    RIPGREP_AVAILABLE = False
    logger.warning("ripgrep-py not available, will use fallback search")


class CodeToolInput(BaseModel):
    """代码工具输入参数"""
    query: str = Field(..., description="搜索查询（关键词、文件路径、函数名、堆栈跟踪等）")
    file_path: Optional[str] = Field(None, description="特定文件路径（可选）")
    max_lines: int = Field(100, description="返回的最大行数")
    include_context: bool = Field(True, description="是否包含上下文")
    use_ripgrep: bool = Field(True, description="是否使用 ripgrep 进行快速搜索")


class CodeTool(BaseCodebaseTool):
    """代码检索和分析工具"""
    
    name: str = "code_search"
    description: str = """
    用于在代码仓库中搜索和分析代码。
    
    功能：
    - 根据关键词搜索代码文件（使用 ripgrep 快速搜索）
    - 查看特定文件的代码内容
    - 查看目录结构
    - 提取代码上下文
    - 基于错误堆栈跟踪定位代码位置
    - 查看 Git 提交历史和文件变更
    
    使用示例：
    - query: "error handling" - 搜索包含错误处理的代码
    - query: "main.py" - 查看 main.py 文件
    - query: "src/utils" - 查看 src/utils 目录结构
    - query: "File \"app.py\", line 42" - 基于堆栈跟踪定位代码
    """
    args_schema: type[CodeToolInput] = CodeToolInput
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 使用 object.__setattr__ 绕过 Pydantic V2 的字段验证
        repo_path = Path(settings.code_repo_path or ".")
        object.__setattr__(self, "repo_path", repo_path)
        if not repo_path.exists():
            logger.warning(f"Code repository path does not exist: {repo_path}")
        
        # 初始化 Git 仓库（如果可用）
        git_repo = None
        if GITPYTHON_AVAILABLE:
            try:
                git_repo = git.Repo(repo_path, search_parent_directories=True)
            except Exception as e:
                logger.debug(f"Git repository not found or not initialized: {str(e)}")
        object.__setattr__(self, "git_repo", git_repo)
    
    def _search_files(self, query: str) -> List[Path]:
        """搜索匹配的文件"""
        matches = []
        query_lower = query.lower()
        
        # 如果查询看起来像文件路径，直接查找
        if "/" in query or query.endswith(".py") or query.endswith(".js"):
            potential_path = self.repo_path / query
            if potential_path.exists():
                return [potential_path]
        
        # 递归搜索文件
        for root, dirs, files in os.walk(self.repo_path):
            # 跳过隐藏目录和常见忽略目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', '.git']]
            
            for file in files:
                if query_lower in file.lower():
                    matches.append(Path(root) / file)
                    if len(matches) >= 20:  # 限制结果数量
                        return matches
        
        return matches
    
    def _read_file_content(self, file_path: Path, max_lines: int = 100, include_context: bool = True) -> str:
        """读取文件内容（带截断）"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            if len(lines) <= max_lines:
                return ''.join(lines)
            
            # 返回前 N 行
            return ''.join(lines[:max_lines]) + f"\n... (文件共 {len(lines)} 行，已截断)"
        
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return f"Error reading file: {str(e)}"
    
    def _search_with_ripgrep(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """使用 ripgrep 进行快速代码搜索"""
        if not RIPGREP_AVAILABLE:
            return []
        
        try:
            # 构建 ripgrep 命令
            rg = Ripgrepy(query, str(self.repo_path))
            rg = rg.context(2)  # 包含上下文行
            rg = rg.max_count(max_results * 5)  # 获取更多结果以便过滤
            
            results = []
            seen_files = set()
            
            for match in rg.run().as_dict:
                file_path = match.get('data', {}).get('path', {}).get('text', '')
                line_number = match.get('data', {}).get('line_number', 0)
                line_text = match.get('data', {}).get('lines', {}).get('text', '').strip()
                
                if not file_path or file_path in seen_files:
                    continue
                
                # 跳过二进制文件和常见忽略目录
                if any(skip in file_path for skip in ['.git', '__pycache__', 'node_modules', '.venv']):
                    continue
                
                rel_path = str(Path(file_path).relative_to(self.repo_path))
                
                # 提取匹配行及其上下文
                matches = [{
                    "line": line_number,
                    "content": line_text
                }]
                
                results.append({
                    "file": rel_path,
                    "matches": matches
                })
                
                seen_files.add(file_path)
                if len(results) >= max_results:
                    break
            
            return results
        except Exception as e:
            logger.warning(f"Ripgrep search failed: {str(e)}, falling back to file search")
            return []
    
    def _search_in_files(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """在文件中搜索关键词（回退方法）"""
        results = []
        query_lower = query.lower()
        
        for root, dirs, files in os.walk(self.repo_path):
            # 跳过隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if file.endswith(('.py', '.js', '.ts', '.java', '.go', '.rs')):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if query_lower in content.lower():
                                # 提取匹配的行
                                lines = content.split('\n')
                                matching_lines = []
                                for i, line in enumerate(lines, 1):
                                    if query_lower in line.lower():
                                        matching_lines.append({
                                            "line": i,
                                            "content": line.strip()
                                        })
                                        if len(matching_lines) >= 5:
                                            break
                                
                                results.append({
                                    "file": str(file_path.relative_to(self.repo_path)),
                                    "matches": matching_lines[:5]
                                })
                                
                                if len(results) >= max_results:
                                    return results
                    except Exception:
                        continue
        
        return results
    
    def _parse_stack_trace(self, query: str) -> Optional[Dict[str, Any]]:
        """解析堆栈跟踪信息，提取文件路径和行号"""
        # 匹配常见的堆栈跟踪格式：
        # File "path/to/file.py", line 42
        #   at path/to/file.js:42:10
        # path/to/file.py:42
        
        patterns = [
            r'File\s+["\']([^"\']+)["\'],\s*line\s+(\d+)',
            r'at\s+([^\s:]+):(\d+):',
            r'([^\s:]+):(\d+):',
            r'([^\s:]+):(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                file_path = match.group(1)
                line_number = int(match.group(2))
                return {
                    "file_path": file_path,
                    "line_number": line_number
                }
        
        return None
    
    def _get_git_info(self, file_path: Optional[str] = None) -> Optional[str]:
        """获取 Git 信息（提交历史、文件变更等）"""
        if not GITPYTHON_AVAILABLE or not self.git_repo:
            return None
        
        try:
            info_parts = []
            
            if file_path:
                # 获取特定文件的提交历史
                full_path = self.repo_path / file_path
                if full_path.exists():
                    try:
                        commits = list(self.git_repo.iter_commits(paths=str(file_path), max_count=5))
                        if commits:
                            info_parts.append("\n最近 5 次提交:")
                            for commit in commits:
                                info_parts.append(f"  - {commit.hexsha[:8]}: {commit.message.split(chr(10))[0]}")
                    except Exception as e:
                        logger.debug(f"Failed to get git history for {file_path}: {str(e)}")
            else:
                # 获取仓库基本信息
                try:
                    info_parts.append(f"当前分支: {self.git_repo.active_branch.name}")
                    info_parts.append(f"最新提交: {self.git_repo.head.commit.hexsha[:8]}")
                    info_parts.append(f"提交信息: {self.git_repo.head.commit.message.split(chr(10))[0]}")
                except Exception as e:
                    logger.debug(f"Failed to get git info: {str(e)}")
            
            return "\n".join(info_parts) if info_parts else None
        except Exception as e:
            logger.debug(f"Git operation failed: {str(e)}")
            return None
    
    def _get_directory_structure(self, dir_path: Path, max_depth: int = 2) -> str:
        """获取目录结构"""
        if not dir_path.exists() or not dir_path.is_dir():
            return f"Directory not found: {dir_path}"
        
        structure = []
        
        def _walk_dir(path: Path, prefix: str = "", depth: int = 0):
            if depth > max_depth:
                return
            
            try:
                items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
                for i, item in enumerate(items):
                    is_last = i == len(items) - 1
                    current_prefix = "└── " if is_last else "├── "
                    structure.append(f"{prefix}{current_prefix}{item.name}")
                    
                    if item.is_dir() and depth < max_depth:
                        next_prefix = prefix + ("    " if is_last else "│   ")
                        _walk_dir(item, next_prefix, depth + 1)
            except PermissionError:
                structure.append(f"{prefix}└── [Permission Denied]")
        
        _walk_dir(dir_path)
        return "\n".join(structure)
    
    def _execute(self, query: str, file_path: Optional[str] = None, max_lines: int = 100, include_context: bool = True, use_ripgrep: bool = True) -> ToolResult:
        """执行代码搜索"""
        try:
            # 打印输入参数
            logger.info("=" * 80)
            logger.info("CodeTool Query Request:")
            logger.info(f"  Query: {query}")
            logger.info(f"  File Path: {file_path or 'None'}")
            logger.info(f"  Max Lines: {max_lines}")
            logger.info(f"  Include Context: {include_context}")
            logger.info(f"  Use Ripgrep: {use_ripgrep}")
            logger.info(f"  Repo Path: {self.repo_path}")
            logger.info("=" * 80)
            
            result_text = ""
            
            # 尝试解析堆栈跟踪
            stack_info = self._parse_stack_trace(query)
            if stack_info:
                # 如果解析到堆栈跟踪，直接定位到该文件
                file_path = stack_info["file_path"]
                line_number = stack_info["line_number"]
                logger.info(f"Detected stack trace: {file_path}:{line_number}")
            
            # 如果指定了文件路径，直接读取文件
            if file_path:
                full_path = self.repo_path / file_path
                if full_path.exists():
                    if full_path.is_dir():
                        result_text = f"Directory structure:\n{self._get_directory_structure(full_path)}"
                    else:
                        content = self._read_file_content(full_path, max_lines, include_context)
                        result_text = f"File: {file_path}\n\n{content}"
                        
                        # 如果是从堆栈跟踪定位的，高亮显示行号
                        if stack_info:
                            result_text += f"\n\n[定位自堆栈跟踪: 第 {line_number} 行]"
                        
                        # 添加 Git 信息
                        git_info = self._get_git_info(file_path)
                        if git_info:
                            result_text += git_info
                else:
                    return ToolResult(
                        success=False,
                        error=f"File not found: {file_path}"
                    )
            else:
                # 检查是否是目录查询
                potential_dir = self.repo_path / query
                if potential_dir.exists() and potential_dir.is_dir():
                    result_text = f"Directory structure:\n{self._get_directory_structure(potential_dir)}"
                else:
                    # 搜索文件
                    files = self._search_files(query)
                    if files:
                        if len(files) == 1:
                            # 单个文件，返回内容
                            content = self._read_file_content(files[0], max_lines, include_context)
                            result_text = f"File: {files[0].relative_to(self.repo_path)}\n\n{content}"
                            
                            # 添加 Git 信息
                            git_info = self._get_git_info(str(files[0].relative_to(self.repo_path)))
                            if git_info:
                                result_text += git_info
                        else:
                            # 多个文件，返回列表和部分内容
                            result_text = f"Found {len(files)} files matching '{query}':\n\n"
                            for file_path in files[:5]:  # 只显示前5个
                                rel_path = file_path.relative_to(self.repo_path)
                                preview = self._read_file_content(file_path, 10, False)
                                result_text += f"{rel_path}:\n{preview}\n---\n"
                    else:
                        # 在文件内容中搜索（优先使用 ripgrep）
                        if use_ripgrep and RIPGREP_AVAILABLE:
                            search_results = self._search_with_ripgrep(query, max_results=5)
                        else:
                            search_results = self._search_in_files(query, max_results=5)
                        
                        if search_results:
                            result_text = f"Found matches in {len(search_results)} files:\n\n"
                            for item in search_results:
                                result_text += f"{item['file']}:\n"
                                for match in item['matches']:
                                    result_text += f"  Line {match['line']}: {match['content']}\n"
                                result_text += "\n"
                        else:
                            return ToolResult(
                                success=False,
                                error=f"No code found matching '{query}'"
                            )
            
            # 截断和摘要
            truncated_data, is_truncated = self._truncate_data(result_text)
            summary = self._create_summary(result_text) if is_truncated else None
            
            # 打印输出结果摘要
            logger.info("=" * 80)
            logger.info("CodeTool Query Result:")
            logger.info(f"  Success: True")
            logger.info(f"  Result Length: {len(result_text)} characters")
            logger.info(f"  Truncated: {is_truncated}")
            if summary:
                logger.info(f"  Summary: {summary}")
            # 打印结果预览（前500字符）
            if result_text:
                preview = result_text[:500].replace('\n', '\\n')
                logger.info(f"  Result Preview: {preview}...")
            logger.info("=" * 80)
            
            return ToolResult(
                success=True,
                data=truncated_data,
                truncated=is_truncated,
                summary=summary
            )
        
        except Exception as e:
            logger.error(f"Code search error: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Error searching code: {str(e)}"
            )

