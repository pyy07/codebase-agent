"""代码工具实现"""
import os
import re
import threading
from typing import Optional, List, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field

from codebase_driven_agent.tools.base import BaseCodebaseTool, ToolResult
from codebase_driven_agent.config import settings
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.tools.code")

# 全局取消标志，用于在任务取消时中断代码查询
_cancellation_event = threading.Event()

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

# AST 支持（可选）
try:
    import tree_sitter
    from tree_sitter import Language, Parser
    AST_AVAILABLE = True
except ImportError:
    AST_AVAILABLE = False
    logger.debug("tree-sitter not available, AST features will be disabled")


class CodeToolInput(BaseModel):
    """代码工具输入参数"""
    query: str = Field(..., description="要搜索的代码元素（函数名、类名、变量名、字符串字面量等）或文件路径")
    search_type: Optional[str] = Field(
        "auto", 
        description="搜索类型：'function'（函数名）、'class'（类名）、'variable'（变量名）、'string'（字符串字面量）、'file'（文件路径）、'auto'（自动检测）"
    )
    file_path: Optional[str] = Field(None, description="限制搜索范围到特定文件路径（可选）")
    line_start: Optional[int] = Field(None, description="查看文件时，起始行号（从1开始，包含该行）")
    line_end: Optional[int] = Field(None, description="查看文件时，结束行号（包含该行）。如果未指定，则读取到文件末尾或 max_lines 限制")
    max_results: int = Field(10, description="返回的最大结果数量")
    include_context: bool = Field(True, description="是否包含代码上下文")


class CodeTool(BaseCodebaseTool):
    """代码检索和分析工具"""
    
    name: str = "code_search"
    description: str = """
    用于在代码仓库中搜索代码元素（函数、类、变量、字符串等）和查看代码结构。
    
    主要功能：
    1. **代码元素搜索**：
       - 函数名搜索：查找函数定义和调用位置
       - 类名搜索：查找类定义和使用位置
       - 变量名搜索：查找变量声明和使用位置
       - 字符串字面量搜索：查找代码中的字符串常量
    
    2. **代码结构查看**：
       - 查看特定文件的代码内容
       - 查看目录结构
       - 基于堆栈跟踪定位代码位置
    
    搜索类型（search_type）：
    - "function": 搜索函数名（定义和调用）
    - "class": 搜索类名（定义和使用）
    - "variable": 搜索变量名
    - "string": 搜索字符串字面量
    - "file": 文件路径查询
    - "auto": 自动检测（根据 query 内容推断）
    
    使用示例：
    - query: "someFunctionName", search_type: "function" - 搜索名为 someFunctionName 的函数
    - query: "someClassName", search_type: "class" - 搜索 someClassName 类
    - query: "someVariableName", search_type: "variable" - 搜索 someVariableName 变量
    - query: "string to find", search_type: "string" - 搜索包含该字符串字面量的代码
    - query: "src/utils.py", search_type: "file" - 查看文件内容
    - query: "src/utils.py", search_type: "file", line_start: 10, line_end: 50 - 查看文件第10-50行（减少上下文）
    - query: "src/utils.py", search_type: "file", line_start: 100 - 查看文件从第100行开始的内容
    - query: "processPayment", search_type: "auto" - 自动检测类型并搜索
    
    注意：
    - 此工具专注于代码元素搜索，如需全文搜索文件内容，请使用其他工具
    - 查看文件时，可以使用 line_start 和 line_end 参数指定行范围，减少返回的上下文，提高效率
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
        # 检查是否已取消
        if _cancellation_event.is_set():
            logger.warning("Code search cancelled before starting")
            raise KeyboardInterrupt("Code search cancelled")
        
        matches = []
        query_lower = query.lower()
        
        # 如果查询看起来像文件路径，直接查找
        if "/" in query or query.endswith(".py") or query.endswith(".js"):
            potential_path = self.repo_path / query
            if potential_path.exists():
                return [potential_path]
        
        # 递归搜索文件
        for root, dirs, files in os.walk(self.repo_path):
            # 检查是否已取消
            if _cancellation_event.is_set():
                logger.warning("Code search cancelled during file walk")
                raise KeyboardInterrupt("Code search cancelled")
            
            # 跳过隐藏目录和常见忽略目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', '.git']]
            
            for file in files:
                if query_lower in file.lower():
                    matches.append(Path(root) / file)
                    if len(matches) >= 20:  # 限制结果数量
                        return matches
        
        return matches
    
    def _read_file_content(
        self, 
        file_path: Path, 
        max_lines: int = 100, 
        include_context: bool = True,
        line_start: Optional[int] = None,
        line_end: Optional[int] = None
    ) -> str:
        """读取文件内容（支持指定行范围）"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            
            # 如果指定了行范围，只读取指定范围
            if line_start is not None:
                # 行号从1开始，转换为索引（从0开始）
                start_idx = max(0, line_start - 1)
                if line_end is not None:
                    end_idx = min(total_lines, line_end)
                else:
                    # 如果只指定了起始行，读取到文件末尾或 max_lines 限制
                    end_idx = min(total_lines, start_idx + max_lines)
                
                selected_lines = lines[start_idx:end_idx]
                result = ''.join(selected_lines)
                
                # 添加行范围信息
                actual_end = line_end if line_end else min(total_lines, start_idx + max_lines)
                range_info = f"\n\n[显示第 {line_start} 行到第 {actual_end} 行"
                if actual_end < total_lines or start_idx > 0:
                    range_info += f"，文件共 {total_lines} 行"
                range_info += "]"
                return result.rstrip() + range_info
            
            # 如果没有指定行范围，使用原来的逻辑
            if total_lines <= max_lines:
                return ''.join(lines)
            
            # 返回前 N 行
            return ''.join(lines[:max_lines]) + f"\n... (文件共 {total_lines} 行，已截断)"
        
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return f"Error reading file: {str(e)}"
    
    def _search_with_ripgrep(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """使用 ripgrep 进行快速代码搜索（多策略尝试）"""
        # 检查是否已取消
        if _cancellation_event.is_set():
            logger.warning("Ripgrep search cancelled before starting")
            raise KeyboardInterrupt("Ripgrep search cancelled")
        
        if not RIPGREP_AVAILABLE:
            return []
        
        # 定义多种搜索策略（按优先级排序）
        search_strategies = [
            {
                "name": "literal_fixed_case",
                "query": query,
                "fixed_strings": True,  # -F: 字面量搜索
                "case_sensitive": True,
            },
            {
                "name": "literal_case_insensitive",
                "query": query,
                "fixed_strings": True,
                "case_sensitive": False,  # -i: 大小写不敏感
            },
            {
                "name": "regex_case_insensitive",
                "query": query,
                "fixed_strings": False,  # 正则表达式
                "case_sensitive": False,
            },
            {
                "name": "regex_fixed_case",
                "query": query,
                "fixed_strings": False,
                "case_sensitive": True,
            },
            {
                "name": "word_boundary",
                "query": f"\\b{re.escape(query)}\\b",  # 单词边界
                "fixed_strings": False,
                "case_sensitive": False,
            },
        ]
        
        # 如果查询包含特殊字符，优先尝试字面量搜索
        has_special_chars = bool(re.search(r'[()[\]{}.*+?^$|\\]', query))
        if has_special_chars:
            # 将字面量搜索提前
            search_strategies.insert(0, {
                "name": "literal_escaped",
                "query": re.escape(query),  # 转义特殊字符
                "fixed_strings": True,
                "case_sensitive": False,
            })
        
        # 尝试每种策略，直到找到结果
        for strategy in search_strategies:
            try:
                logger.debug(f"Trying ripgrep strategy: {strategy['name']} with query: {strategy['query'][:100]}")
                
                # 构建 ripgrep 命令
                rg = Ripgrepy(strategy['query'], str(self.repo_path))
                rg = rg.context(2)  # 包含上下文行
                rg = rg.max_count(max_results * 5)  # 获取更多结果以便过滤
                
                # 设置搜索选项
                if strategy['fixed_strings']:
                    rg = rg.fixed_strings()  # -F: 字面量搜索
                if not strategy['case_sensitive']:
                    rg = rg.case_insensitive()  # -i: 大小写不敏感
                
                results = []
                seen_files = set()
                
                for match in rg.run().as_dict:
                    # 检查是否已取消
                    if _cancellation_event.is_set():
                        logger.warning("Ripgrep search cancelled during iteration")
                        raise KeyboardInterrupt("Ripgrep search cancelled")
                    
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
                
                # 如果找到结果，返回
                if results:
                    logger.info(f"Ripgrep search succeeded with strategy: {strategy['name']}, found {len(results)} results")
                    return results
                    
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.debug(f"Ripgrep strategy '{strategy['name']}' failed: {str(e)}, trying next strategy")
                continue
        
        # 所有策略都失败
        logger.warning(f"All ripgrep search strategies failed for query: {query[:100]}")
        return []
    
    def _detect_search_type(self, query: str) -> str:
        """自动检测搜索类型"""
        query_lower = query.lower()
        
        # 检查是否是文件路径
        if '/' in query or '\\' in query or query.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.h', '.go', '.rs')):
            return "file"
        
        # 检查是否是字符串字面量（包含空格或特殊字符）
        if ' ' in query or any(c in query for c in ['"', "'", ':', '(', ')', '[', ']']):
            return "string"
        
        # 检查是否是类名（通常以大写字母开头）
        if query and query[0].isupper() and query.replace('_', '').replace('-', '').isalnum():
            return "class"
        
        # 检查是否是函数名（通常包含括号或常见函数命名模式）
        if '(' in query or query.endswith('()') or (query.replace('_', '').isalnum() and '_' in query):
            return "function"
        
        # 默认作为变量名搜索
        return "variable"
    
    def _search_code_element(self, query: str, search_type: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """搜索代码元素（函数、类、变量、字符串）"""
        results = []
        
        # 根据搜索类型选择策略
        if search_type == "function":
            # 函数名搜索：查找函数定义和调用
            # 使用 ripgrep 搜索函数定义模式：def function_name, function function_name, void function_name 等
            patterns = [
                f"def\\s+{re.escape(query)}",  # Python
                f"function\\s+{re.escape(query)}",  # JavaScript
                f"fn\\s+{re.escape(query)}",  # Rust
                f"func\\s+{re.escape(query)}",  # Go
                f"{re.escape(query)}\\s*\\(",  # 函数调用
            ]
            for pattern in patterns:
                ripgrep_results = self._search_with_ripgrep(pattern, max_results)
                if ripgrep_results:
                    results.extend(ripgrep_results)
                    break
        
        elif search_type == "class":
            # 类名搜索：查找类定义
            patterns = [
                f"class\\s+{re.escape(query)}",  # Python, JavaScript
                f"struct\\s+{re.escape(query)}",  # C/C++, Rust
                f"interface\\s+{re.escape(query)}",  # TypeScript, Java
            ]
            for pattern in patterns:
                ripgrep_results = self._search_with_ripgrep(pattern, max_results)
                if ripgrep_results:
                    results.extend(ripgrep_results)
                    break
        
        elif search_type == "variable":
            # 变量名搜索：查找变量声明和使用
            # 使用单词边界确保精确匹配
            pattern = f"\\b{re.escape(query)}\\b"
            results = self._search_with_ripgrep(pattern, max_results)
        
        elif search_type == "string":
            # 字符串字面量搜索：使用字面量搜索
            results = self._search_with_ripgrep(query, max_results)
        
        else:
            # 默认使用 ripgrep
            results = self._search_with_ripgrep(query, max_results)
        
        return results[:max_results]
    
    def _search_with_ast(self, query: str, search_type: str = "auto", max_results: int = 10) -> List[Dict[str, Any]]:
        """使用 AST 进行代码搜索（支持函数定义、调用关系等）
        
        注意：需要先安装并编译 tree-sitter 语言库
        示例：pip install tree-sitter tree-sitter-python tree-sitter-cpp
        
        这是未来扩展的方向，当前返回空列表，回退到 ripgrep 搜索
        """
        if not AST_AVAILABLE:
            logger.debug("AST search not available (tree-sitter not installed)")
            return []
        
        # TODO: 实现 AST 搜索
        # 1. 检测文件语言类型
        # 2. 加载对应的 tree-sitter 语言解析器
        # 3. 解析代码为 AST
        # 4. 在 AST 中搜索：
        #    - 函数定义（function_def, method_def）
        #    - 函数调用（call_expression）
        #    - 字符串字面量（string_literal）
        #    - 变量名（identifier）
        
        logger.debug("AST search not yet implemented, falling back to ripgrep")
        return []
    
    def _search_in_files(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """在文件中搜索关键词（回退方法）"""
        results = []
        query_lower = query.lower()
        
        # 支持更多文件类型，包括 C/C++
        code_extensions = (
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs',
            '.cpp', '.cxx', '.cc', '.c', '.h', '.hpp', '.hxx',  # C/C++
            '.cs', '.php', '.rb', '.swift', '.kt', '.scala',  # 其他语言
        )
        
        for root, dirs, files in os.walk(self.repo_path):
            # 跳过隐藏目录和常见忽略目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', '.venv', 'build', 'dist']]
            
            for file in files:
                if file.endswith(code_extensions):
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
        # 检查是否已取消
        if _cancellation_event.is_set():
            logger.warning("Directory structure query cancelled before starting")
            raise KeyboardInterrupt("Directory structure query cancelled")
        
        if not dir_path.exists() or not dir_path.is_dir():
            return f"Directory not found: {dir_path}"
        
        structure = []
        
        def _walk_dir(path: Path, prefix: str = "", depth: int = 0):
            # 检查是否已取消
            if _cancellation_event.is_set():
                logger.warning("Directory walk cancelled during traversal")
                raise KeyboardInterrupt("Directory walk cancelled")
            
            if depth > max_depth:
                return
            
            try:
                items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
                for i, item in enumerate(items):
                    # 检查是否已取消（在每次迭代时检查）
                    if _cancellation_event.is_set():
                        logger.warning("Directory walk cancelled during iteration")
                        raise KeyboardInterrupt("Directory walk cancelled")
                    
                    is_last = i == len(items) - 1
                    current_prefix = "└── " if is_last else "├── "
                    structure.append(f"{prefix}{current_prefix}{item.name}")
                    
                    if item.is_dir() and depth < max_depth:
                        next_prefix = prefix + ("    " if is_last else "│   ")
                        _walk_dir(item, next_prefix, depth + 1)
            except PermissionError:
                structure.append(f"{prefix}└── [Permission Denied]")
        
        try:
            _walk_dir(dir_path)
            return "\n".join(structure)
        except KeyboardInterrupt:
            raise
    
    def _execute(
        self, 
        query: str, 
        search_type: Optional[str] = "auto",
        file_path: Optional[str] = None,
        line_start: Optional[int] = None,
        line_end: Optional[int] = None,
        max_results: int = 10,
        include_context: bool = True
    ) -> ToolResult:
        """执行代码元素搜索"""
        # 在执行开始时检查是否已取消
        if _cancellation_event.is_set():
            logger.warning("CodeTool execution cancelled before starting")
            return ToolResult(
                success=False,
                error="Code search was cancelled"
            )
        
        try:
            # 自动检测搜索类型（如果未指定）
            if search_type == "auto":
                search_type = self._detect_search_type(query)
            
            # 打印输入参数
            logger.info("=" * 80)
            logger.info("CodeTool Query Request:")
            logger.info(f"  Query: {query}")
            logger.info(f"  Search Type: {search_type}")
            logger.info(f"  File Path: {file_path or 'None'}")
            logger.info(f"  Line Range: {f'{line_start}-{line_end}' if line_start or line_end else 'None'}")
            logger.info(f"  Max Results: {max_results}")
            logger.info(f"  Include Context: {include_context}")
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
                
                # 如果没有指定行范围，自动设置一个范围（该行前后各10行）
                if line_start is None and line_end is None:
                    line_start = max(1, line_number - 10)
                    line_end = line_number + 10
            
            # 如果指定了文件路径，直接读取文件
            if file_path:
                # 检查是否已取消
                if _cancellation_event.is_set():
                    logger.warning("CodeTool execution cancelled before reading file")
                    raise KeyboardInterrupt("Code search cancelled")
                
                full_path = self.repo_path / file_path
                if full_path.exists():
                    if full_path.is_dir():
                        result_text = f"Directory structure:\n{self._get_directory_structure(full_path)}"
                    else:
                        content = self._read_file_content(
                            full_path, 
                            max_results * 10, 
                            include_context,
                            line_start=line_start,
                            line_end=line_end
                        )
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
                            # 检查是否已取消
                            if _cancellation_event.is_set():
                                logger.warning("CodeTool execution cancelled before reading single file")
                                raise KeyboardInterrupt("Code search cancelled")
                            
                            content = self._read_file_content(
                                files[0], 
                                max_results * 10, 
                                include_context,
                                line_start=line_start,
                                line_end=line_end
                            )
                            result_text = f"File: {files[0].relative_to(self.repo_path)}\n\n{content}"
                            
                            # 添加 Git 信息
                            git_info = self._get_git_info(str(files[0].relative_to(self.repo_path)))
                            if git_info:
                                result_text += git_info
                        else:
                            # 多个文件，返回列表和部分内容
                            result_text = f"Found {len(files)} files matching '{query}':\n\n"
                            for file_path in files[:5]:  # 只显示前5个
                                # 检查是否已取消（在处理每个文件时检查）
                                if _cancellation_event.is_set():
                                    logger.warning("CodeTool execution cancelled during file processing")
                                    raise KeyboardInterrupt("Code search cancelled")
                                
                                rel_path = file_path.relative_to(self.repo_path)
                                preview = self._read_file_content(file_path, 10, False)
                                result_text += f"{rel_path}:\n{preview}\n---\n"
                    else:
                        # 代码元素搜索（根据 search_type 选择策略）
                        search_results = []
                        search_method = None
                        
                        # 如果是文件路径查询，直接处理
                        if search_type == "file":
                            files = self._search_files(query)
                            if files:
                                if len(files) == 1:
                                    content = self._read_file_content(
                                        files[0], 
                                        max_results * 10, 
                                        include_context,
                                        line_start=line_start,
                                        line_end=line_end
                                    )
                                    result_text = f"File: {files[0].relative_to(self.repo_path)}\n\n{content}"
                                    git_info = self._get_git_info(str(files[0].relative_to(self.repo_path)))
                                    if git_info:
                                        result_text += git_info
                                else:
                                    result_text = f"Found {len(files)} files matching '{query}':\n\n"
                                    for file_path in files[:max_results]:
                                        rel_path = file_path.relative_to(self.repo_path)
                                        preview = self._read_file_content(file_path, 10, False)
                                        result_text += f"{rel_path}:\n{preview}\n---\n"
                            else:
                                return ToolResult(
                                    success=False,
                                    error=f"File not found: {query}"
                                )
                        else:
                            # 代码元素搜索
                            logger.info(f"Searching for code element: {query} (type: {search_type})")
                            
                            # 策略1: 尝试 AST 搜索（如果可用且适合）
                            if AST_AVAILABLE and search_type in ["function", "class", "variable"]:
                                logger.info("Trying AST search for code element...")
                                search_results = self._search_with_ast(query, search_type, max_results)
                                if search_results:
                                    search_method = "AST"
                            
                            # 策略2: 使用代码元素搜索（基于 ripgrep 的模式匹配）
                            if not search_results:
                                logger.info(f"Using code element search (type: {search_type})...")
                                search_results = self._search_code_element(query, search_type, max_results)
                                if search_results:
                                    search_method = f"code_element_{search_type}"
                            
                            # 策略3: 回退到通用 ripgrep 搜索
                            if not search_results:
                                logger.info("Falling back to general ripgrep search...")
                                search_results = self._search_with_ripgrep(query, max_results)
                                if search_results:
                                    search_method = "ripgrep"
                            
                            # 策略4: 最后回退到文件内容搜索
                            if not search_results:
                                logger.info("Falling back to file content search...")
                                search_results = self._search_in_files(query, max_results)
                                if search_results:
                                    search_method = "file_content"
                            
                            if search_results:
                                method_info = f" (via {search_method})" if search_method else ""
                                result_text = f"Found {len(search_results)} matches for '{query}' ({search_type}){method_info}:\n\n"
                                for item in search_results:
                                    # 检查是否已取消（在处理每个结果时检查）
                                    if _cancellation_event.is_set():
                                        logger.warning("CodeTool execution cancelled during result processing")
                                        raise KeyboardInterrupt("Code search cancelled")
                                    
                                    result_text += f"{item['file']}:\n"
                                    for match in item['matches']:
                                        result_text += f"  Line {match['line']}: {match['content']}\n"
                                    result_text += "\n"
                            else:
                                return ToolResult(
                                    success=False,
                                    error=f"No {search_type} found matching '{query}' (tried AST, code element search, ripgrep, and file content search)"
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
        
        except KeyboardInterrupt:
            # 任务被取消，重新抛出
            logger.warning("CodeTool execution interrupted by cancellation")
            raise
        except Exception as e:
            logger.error(f"Code search error: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Error searching code: {str(e)}"
            )

