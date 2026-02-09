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

# AST 分析器导入（可选）
try:
    from codebase_driven_agent.tools.ast_analyzer import ASTCodeAnalyzer
    AST_ANALYZER_AVAILABLE = True
except ImportError:
    AST_ANALYZER_AVAILABLE = False
    ASTCodeAnalyzer = None

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
    query: str = Field(..., description="要搜索的代码元素（函数名、类名、变量名、字符串字面量等）或文件路径（用于关系分析）")
    search_type: Optional[str] = Field(
        "auto", 
        description="搜索类型：'function'（函数名）、'class'（类名）、'variable'（变量名）、'string'（字符串字面量）、'method'（类方法）、'call'（函数调用位置）、'import'（导入语句）、'constant'（常量）、'enum'（枚举）、'interface'（接口）、'namespace'（命名空间）、'macro'（宏定义）、'decorator'（装饰器）、'type'（类型别名）、'call_graph'（函数调用关系图）、'inheritance'（类继承关系）、'dependencies'（模块依赖关系）、'auto'（自动检测）"
    )
    file_path: Optional[str] = Field(None, description="限制搜索范围到特定文件路径（可选）")
    max_results: int = Field(10, description="返回的最大结果数量")
    include_context: bool = Field(True, description="是否包含代码上下文")


class CodeTool(BaseCodebaseTool):
    """代码检索和分析工具"""
    
    name: str = "code_search"
    description: str = """
    用于在代码仓库中搜索代码元素（函数、类、变量、字符串等）。
    
    功能：
    - 函数名搜索：精确查找函数定义和调用位置（支持 Python、JavaScript/TypeScript、C++、Java）
    - 类名搜索：查找类定义和使用位置
    - 变量名搜索：精确查找变量使用位置（支持 Python、JavaScript/TypeScript、C++、Java）
    - 字符串字面量搜索：查找代码中的字符串常量
    - 方法搜索：查找类方法（类的成员函数）
    - 函数调用位置搜索：只搜索函数调用位置，不搜索定义
    - 导入语句搜索：查找 import/from/include 等导入语句
    - 常量搜索：查找常量定义（const、final 等）
    - 枚举搜索：查找枚举类型定义
    - 接口搜索：查找接口定义（TypeScript/Java）
    - 命名空间搜索：查找命名空间定义（C++）
    - 宏定义搜索：查找宏定义（C/C++）
    - 装饰器搜索：查找装饰器使用（Python）
    - 类型别名搜索：查找类型别名定义（TypeScript）
    - 函数调用关系图：构建文件的函数调用关系图，用于追踪错误传播路径、理解代码执行流程、识别影响范围
    - 类继承关系分析：分析类的继承层次结构，用于理解类的设计、识别需要重构的类、分析多态行为
    - 模块依赖关系分析：分析模块的导入和依赖关系，用于理解代码组织结构、识别循环依赖、分析模块间耦合度
    
    使用场景：
    - 查找函数定义和调用位置
    - 查找类定义和使用位置
    - 查找变量使用位置
    - 搜索代码中的字符串常量
    - 查找类方法
    - 只查找函数调用位置（不包含定义）
    - 查找导入语句
    - 查找常量、枚举、接口等定义
    - 追踪函数调用关系
    - 构建函数调用关系图（用于错误追踪、影响范围分析）
    - 分析类继承关系（用于架构分析、重构规划）
    - 分析模块依赖关系（用于识别循环依赖、评估耦合度）
    
    参数：
    - query（必需）：要搜索的代码元素名称
    - search_type（可选）：搜索类型，支持以下类型：
      * "function"：函数定义和调用
      * "class"：类定义
      * "variable"：变量使用
      * "string"：字符串字面量
      * "method"：类方法（类的成员函数）
      * "call"：函数调用位置（只搜索调用，不搜索定义）
      * "import"：导入语句
      * "constant"：常量（如 Python 的常量、C++ 的 const 变量）
      * "enum"：枚举类型
      * "interface"：接口（TypeScript/Java）
      * "namespace"：命名空间（C++）
      * "macro"：宏定义（C/C++）
      * "decorator"：装饰器（Python）
      * "type"：类型别名（TypeScript）
      * "call_graph"：函数调用关系图（需要提供文件路径，分析文件内所有函数的调用关系）
      * "inheritance"：类继承关系（需要提供文件路径，分析文件内所有类的继承关系）
      * "dependencies"：模块依赖关系（需要提供文件路径，分析文件的导入和依赖关系）
      * "auto"：自动检测类型（默认）
    - file_path（可选）：限制搜索范围到特定文件路径
    - max_results（可选）：返回的最大结果数量，默认 10
    - include_context（可选）：是否包含代码上下文，默认 True
    
    使用示例：
    - query: "someFunctionName", search_type: "function" - 搜索名为 someFunctionName 的函数
    - query: "someClassName", search_type: "class" - 搜索 someClassName 类
    - query: "someVariableName", search_type: "variable" - 搜索 someVariableName 变量
    - query: "someMethod", search_type: "method" - 搜索类方法
    - query: "someFunction", search_type: "call" - 只搜索函数调用位置
    - query: "import os", search_type: "import" - 搜索导入语句
    - query: "MAX_SIZE", search_type: "constant" - 搜索常量
    - query: "string to find", search_type: "string" - 搜索包含该字符串字面量的代码
    - query: "processPayment", search_type: "auto" - 自动检测类型并搜索
    - query: "PaymentService.py", search_type: "call_graph" - 构建 PaymentService.py 文件的函数调用关系图
    - query: "UserService.java", search_type: "inheritance" - 分析 UserService.java 文件的类继承关系
    - query: "utils.py", search_type: "dependencies" - 分析 utils.py 文件的模块依赖关系
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
        
        # 初始化 AST 分析器（如果可用）
        ast_analyzer = None
        if AST_AVAILABLE and AST_ANALYZER_AVAILABLE:
            try:
                ast_analyzer = ASTCodeAnalyzer()
                logger.debug("AST analyzer initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize AST analyzer: {str(e)}")
        object.__setattr__(self, "ast_analyzer", ast_analyzer)
    
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
        
        # 注意：不再检测文件路径，文件读取应使用 read 工具
        
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
        """搜索代码元素（函数、类、变量、字符串等）"""
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
        
        elif search_type == "method":
            # 方法搜索：查找类方法（类的成员函数）
            patterns = [
                f"def\\s+{re.escape(query)}",  # Python 方法
                f"{re.escape(query)}\\s*\\(",  # 方法调用（如 obj.method()）
                f"\\b{re.escape(query)}\\s*\\(",  # 方法调用（带单词边界）
            ]
            for pattern in patterns:
                ripgrep_results = self._search_with_ripgrep(pattern, max_results)
                if ripgrep_results:
                    results.extend(ripgrep_results)
                    break
        
        elif search_type == "call":
            # 函数调用位置搜索：只搜索调用，不搜索定义
            patterns = [
                f"{re.escape(query)}\\s*\\(",  # 函数调用
                f"\\b{re.escape(query)}\\s*\\(",  # 函数调用（带单词边界）
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
        
        elif search_type == "interface":
            # 接口搜索：查找接口定义（TypeScript/Java）
            patterns = [
                f"interface\\s+{re.escape(query)}",  # TypeScript, Java
            ]
            for pattern in patterns:
                ripgrep_results = self._search_with_ripgrep(pattern, max_results)
                if ripgrep_results:
                    results.extend(ripgrep_results)
                    break
        
        elif search_type == "enum":
            # 枚举搜索：查找枚举定义
            patterns = [
                f"enum\\s+{re.escape(query)}",  # C/C++, Rust, TypeScript, Java
            ]
            for pattern in patterns:
                ripgrep_results = self._search_with_ripgrep(pattern, max_results)
                if ripgrep_results:
                    results.extend(ripgrep_results)
                    break
        
        elif search_type == "namespace":
            # 命名空间搜索：查找命名空间定义（C++）
            patterns = [
                f"namespace\\s+{re.escape(query)}",  # C++
            ]
            for pattern in patterns:
                ripgrep_results = self._search_with_ripgrep(pattern, max_results)
                if ripgrep_results:
                    results.extend(ripgrep_results)
                    break
        
        elif search_type == "macro":
            # 宏定义搜索：查找宏定义（C/C++）
            patterns = [
                f"#define\\s+{re.escape(query)}",  # C/C++
            ]
            for pattern in patterns:
                ripgrep_results = self._search_with_ripgrep(pattern, max_results)
                if ripgrep_results:
                    results.extend(ripgrep_results)
                    break
        
        elif search_type == "decorator":
            # 装饰器搜索：查找装饰器使用（Python）
            patterns = [
                f"@{re.escape(query)}",  # Python 装饰器
            ]
            for pattern in patterns:
                ripgrep_results = self._search_with_ripgrep(pattern, max_results)
                if ripgrep_results:
                    results.extend(ripgrep_results)
                    break
        
        elif search_type == "import":
            # 导入语句搜索：查找导入语句
            patterns = [
                f"import\\s+.*{re.escape(query)}",  # Python, JavaScript
                f"from\\s+.*{re.escape(query)}",  # Python
                f"#include\\s+.*{re.escape(query)}",  # C/C++
                f"using\\s+.*{re.escape(query)}",  # C++
            ]
            for pattern in patterns:
                ripgrep_results = self._search_with_ripgrep(pattern, max_results)
                if ripgrep_results:
                    results.extend(ripgrep_results)
                    break
        
        elif search_type == "constant":
            # 常量搜索：查找常量定义
            patterns = [
                f"const\\s+{re.escape(query)}",  # JavaScript, C++
                f"final\\s+.*{re.escape(query)}",  # Java
                f"\\b{re.escape(query)}\\s*=",  # 常量赋值（如 MAX_SIZE = 100）
            ]
            for pattern in patterns:
                ripgrep_results = self._search_with_ripgrep(pattern, max_results)
                if ripgrep_results:
                    results.extend(ripgrep_results)
                    break
        
        elif search_type == "type":
            # 类型别名搜索：查找类型别名定义（TypeScript）
            patterns = [
                f"type\\s+{re.escape(query)}",  # TypeScript
                f"typedef\\s+.*{re.escape(query)}",  # C/C++
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
        示例：pip install tree-sitter tree-sitter-python tree-sitter-javascript tree-sitter-typescript
        """
        if not AST_AVAILABLE or not self.ast_analyzer:
            logger.debug("AST search not available (tree-sitter not installed or analyzer not initialized)")
            return []
        
        results = []
        
        try:
            # 支持的代码文件扩展名
            code_extensions = ('.py', '.js', '.ts', '.tsx', '.jsx', '.cpp', '.cc', '.cxx', '.java')
            
            # 遍历代码文件
            for root, dirs, files in os.walk(self.repo_path):
                # 跳过隐藏目录和常见忽略目录
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', '.venv', 'build', 'dist']]
                
                for file in files:
                    if not file.endswith(code_extensions):
                        continue
                    
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(self.repo_path)
                    
                    try:
                        # 读取文件内容
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            source_code = f.read()
                        
                        # 根据搜索类型调用不同的 AST 查询方法
                        matches = []
                        
                        if search_type == "function":
                            # 查找函数定义
                            definitions = self.ast_analyzer.find_function_definition(str(rel_path), source_code, query)
                            for defn in definitions:
                                matches.append({
                                    'line': defn['line'],
                                    'content': defn['code'].split('\n')[0] if defn['code'] else f"def {query}()"
                                })
                            
                            # 查找函数调用
                            calls = self.ast_analyzer.find_function_calls(str(rel_path), source_code, query)
                            for call in calls:
                                matches.append({
                                    'line': call['line'],
                                    'content': call['code'].split('\n')[0] if call['code'] else f"{query}()"
                                })
                        
                        elif search_type == "method":
                            # 方法搜索：查找类方法（AST 分析器中的 find_function_definition 已经包含 method_definition）
                            definitions = self.ast_analyzer.find_function_definition(str(rel_path), source_code, query)
                            for defn in definitions:
                                matches.append({
                                    'line': defn['line'],
                                    'content': defn['code'].split('\n')[0] if defn['code'] else f"def {query}()"
                                })
                        
                        elif search_type == "call":
                            # 函数调用位置搜索：只搜索调用，不搜索定义
                            calls = self.ast_analyzer.find_function_calls(str(rel_path), source_code, query)
                            for call in calls:
                                matches.append({
                                    'line': call['line'],
                                    'content': call['code'].split('\n')[0] if call['code'] else f"{query}()"
                                })
                        
                        elif search_type == "variable":
                            # 查找变量使用
                            usages = self.ast_analyzer.find_variable_usage(str(rel_path), source_code, query)
                            for usage in usages:
                                matches.append({
                                    'line': usage['line'],
                                    'content': usage['code'].split('\n')[0] if usage['code'] else query
                                })
                        
                        elif search_type == "class":
                            # 类搜索暂时使用 ripgrep（AST 类分析需要更复杂的实现）
                            logger.debug(f"Class search via AST not yet implemented for {query}, falling back to ripgrep")
                            return []
                        
                        elif search_type in ["import", "constant", "enum", "interface", "namespace", "macro", "decorator", "type"]:
                            # 这些类型目前主要通过 ripgrep 搜索，AST 支持可以后续扩展
                            logger.debug(f"{search_type} search via AST not yet implemented for {query}, falling back to ripgrep")
                            return []
                        
                        # 如果有匹配结果，添加到结果列表
                        if matches:
                            results.append({
                                'file': str(rel_path),
                                'matches': matches[:max_results]  # 限制每个文件的匹配数
                            })
                            
                            if len(results) >= max_results:
                                break
                    
                    except Exception as e:
                        logger.debug(f"Error processing file {rel_path} with AST: {str(e)}")
                        continue
                
                if len(results) >= max_results:
                    break
            
            logger.info(f"AST search found {len(results)} files with matches for '{query}'")
            return results[:max_results]
        
        except Exception as e:
            logger.error(f"AST search error: {str(e)}", exc_info=True)
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
    
    def _format_call_graph(self, graph: Dict[str, Any]) -> str:
        """格式化函数调用关系图输出"""
        if not graph or not graph.get('nodes'):
            return "未找到函数调用关系（文件中可能没有函数定义）"
        
        result = []
        result.append("=" * 80)
        result.append("函数调用关系图")
        result.append("=" * 80)
        result.append(f"节点数量（函数定义）: {len(graph['nodes'])}")
        result.append(f"边数量（调用关系）: {len(graph['edges'])}")
        result.append("")
        
        result.append("函数列表（节点）:")
        for node in graph['nodes']:
            result.append(f"  - {node['name']} ({node['file_path']}:{node['line']}:{node['column']})")
        result.append("")
        
        if graph['edges']:
            result.append("调用关系（边）:")
            for edge in graph['edges']:
                result.append(f"  {edge['from_function']} -> {edge['to_function']} ({edge['file_path']}:{edge['line']}:{edge['column']})")
        else:
            result.append("调用关系: 未找到函数调用（函数可能没有调用其他函数）")
        
        result.append("=" * 80)
        return "\n".join(result)
    
    def _format_inheritance(self, inheritance_list: List[Dict[str, Any]]) -> str:
        """格式化类继承关系输出"""
        if not inheritance_list:
            return "未找到类继承关系（文件中可能没有类定义）"
        
        result = []
        result.append("=" * 80)
        result.append("类继承关系分析")
        result.append("=" * 80)
        result.append(f"找到 {len(inheritance_list)} 个类:")
        result.append("")
        
        for cls in inheritance_list:
            result.append(f"类名: {cls['class_name']}")
            if cls['parent_classes']:
                result.append(f"  父类: {', '.join(cls['parent_classes'])}")
            else:
                result.append(f"  父类: 无（基类）")
            result.append(f"  位置: {cls['file_path']}:{cls['line']}:{cls['column']}")
            result.append("")
        
        result.append("=" * 80)
        return "\n".join(result)
    
    def _format_dependencies(self, dependencies_list: List[Dict[str, Any]]) -> str:
        """格式化模块依赖关系输出"""
        if not dependencies_list:
            return "未找到模块依赖关系（文件中可能没有导入语句）"
        
        result = []
        result.append("=" * 80)
        result.append("模块依赖关系分析")
        result.append("=" * 80)
        result.append(f"找到 {len(dependencies_list)} 个依赖:")
        result.append("")
        
        for dep in dependencies_list:
            result.append(f"模块名: {dep['module_name']}")
            result.append(f"  导入类型: {dep['import_type']}")
            if dep['imported_items']:
                result.append(f"  导入项: {', '.join(dep['imported_items'])}")
            else:
                result.append(f"  导入项: 全部（import {dep['module_name']}）")
            result.append(f"  位置: {dep['file_path']}:{dep['line']}:{dep['column']}")
            result.append("")
        
        result.append("=" * 80)
        return "\n".join(result)
    
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
            logger.info(f"  Max Results: {max_results}")
            logger.info(f"  Include Context: {include_context}")
            logger.info(f"  Repo Path: {self.repo_path}")
            logger.info("=" * 80)
            
            result_text = ""
            
            # 处理代码关系分析类型（call_graph, inheritance, dependencies）
            if search_type in ["call_graph", "inheritance", "dependencies"]:
                # 确定要分析的文件路径
                target_file = None
                if file_path:
                    target_file = self.repo_path / file_path
                elif query and (query.endswith('.py') or query.endswith('.js') or query.endswith('.ts') or 
                               query.endswith('.java') or query.endswith('.cpp') or query.endswith('.c')):
                    # query 看起来像文件路径
                    target_file = self.repo_path / query
                
                if not target_file or not target_file.exists() or not target_file.is_file():
                    return ToolResult(
                        success=False,
                        error=f"代码关系分析需要提供有效的文件路径。请使用 file_path 参数指定文件，或将文件路径作为 query 参数。\n示例：code_search(query='PaymentService.py', search_type='call_graph')"
                    )
                
                # 检查 AST 分析器是否可用
                if not AST_AVAILABLE or not self.ast_analyzer:
                    return ToolResult(
                        success=False,
                        error="代码关系分析功能需要 tree-sitter。请安装：pip install tree-sitter tree-sitter-python tree-sitter-javascript tree-sitter-typescript tree-sitter-cpp tree-sitter-java"
                    )
                
                try:
                    # 读取文件内容
                    with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
                        source_code = f.read()
                    
                    rel_path = target_file.relative_to(self.repo_path)
                    
                    # 根据类型调用相应的分析方法
                    if search_type == "call_graph":
                        logger.info(f"Building call graph for file: {rel_path}")
                        graph = self.ast_analyzer.build_call_graph(str(rel_path), source_code)
                        result_text = self._format_call_graph(graph)
                    
                    elif search_type == "inheritance":
                        logger.info(f"Analyzing class inheritance for file: {rel_path}")
                        inheritance = self.ast_analyzer.analyze_class_inheritance(str(rel_path), source_code)
                        result_text = self._format_inheritance(inheritance)
                    
                    elif search_type == "dependencies":
                        logger.info(f"Analyzing module dependencies for file: {rel_path}")
                        dependencies = self.ast_analyzer.analyze_module_dependencies(str(rel_path), source_code)
                        result_text = self._format_dependencies(dependencies)
                    
                    # 截断和摘要
                    truncated_data, is_truncated = self._truncate_data(result_text)
                    summary = self._create_summary(result_text) if is_truncated else None
                    
                    return ToolResult(
                        success=True,
                        data=truncated_data,
                        truncated=is_truncated,
                        summary=summary
                    )
                
                except Exception as e:
                    logger.error(f"Error analyzing code relationships: {str(e)}", exc_info=True)
                    return ToolResult(
                        success=False,
                        error=f"分析代码关系时出错: {str(e)}"
                    )
            
            # 如果指定了文件路径，检查是否是目录
            if file_path:
                full_path = self.repo_path / file_path
                if full_path.exists() and full_path.is_dir():
                    # 目录结构查看
                    result_text = f"Directory structure:\n{self._get_directory_structure(full_path)}"
                else:
                    # 在指定文件范围内搜索代码元素
                    search_results = []
                    search_method = None
                    logger.info(f"Searching for code element: {query} (type: {search_type}) in file: {file_path}")
                    
                    # 策略1: 尝试 AST 搜索（如果可用且适合）
                    if AST_AVAILABLE and search_type in ["function", "method", "call", "class", "variable"]:
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
            else:
                # 检查是否是目录查询
                potential_dir = self.repo_path / query
                if potential_dir.exists() and potential_dir.is_dir():
                    result_text = f"Directory structure:\n{self._get_directory_structure(potential_dir)}"
                else:
                    # 检查是否是文件路径查询（search_type == "file"）
                    if search_type == "file":
                        files = self._search_files(query)
                        if files:
                            # 返回文件列表
                            result_text = f"找到 {len(files)} 个匹配的文件：\n\n"
                            for fp in files[:max_results]:
                                rel_path = fp.relative_to(self.repo_path)
                                result_text += f"  - {rel_path}\n"
                        else:
                            result_text = f"未找到文件: {query}"
                    else:
                        # 代码元素搜索（根据 search_type 选择策略）
                        search_results = []
                        search_method = None
                        
                        # 代码元素搜索
                        logger.info(f"Searching for code element: {query} (type: {search_type})")
                        
                        # 策略1: 尝试 AST 搜索（如果可用且适合）
                        if AST_AVAILABLE and search_type in ["function", "method", "call", "class", "variable"]:
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

