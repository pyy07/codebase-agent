"""AST 代码分析器"""
from typing import List, Optional, Dict, Tuple
from pathlib import Path
from codebase_driven_agent.tools.ast_parser import get_ast_config, AST_AVAILABLE
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.tools.ast_analyzer")


class ASTCodeAnalyzer:
    """AST 代码分析器类
    
    提供基于 AST 的代码查询和分析功能，包括：
    - 函数定义查找
    - 函数调用查找
    - 调用链追踪
    - 变量使用追踪
    """
    
    def __init__(self):
        """初始化 AST 代码分析器"""
        self.config = get_ast_config()
        if not AST_AVAILABLE:
            logger.warning("tree-sitter not available, AST features will be disabled")
    
    def _get_node_text(self, node, source_code: str) -> str:
        """获取节点的源代码文本
        
        Args:
            node: AST 节点
            source_code: 源代码内容
            
        Returns:
            str: 节点对应的源代码文本
        """
        start_byte = node.start_byte
        end_byte = node.end_byte
        return source_code[start_byte:end_byte]
    
    def _find_nodes_by_type(self, node, node_type: str, source_code: str) -> List[Tuple]:
        """递归查找指定类型的节点
        
        Args:
            node: AST 根节点
            node_type: 节点类型（如 'function_definition', 'call'）
            source_code: 源代码内容
            
        Returns:
            List[Tuple]: (节点, 行号, 列号) 列表
        """
        results = []
        
        def traverse(n):
            if n.type == node_type:
                # 获取行号和列号
                start_point = n.start_point
                results.append((n, start_point[0] + 1, start_point[1] + 1))
            
            for child in n.children:
                traverse(child)
        
        traverse(node)
        return results
    
    def find_function_definition(self, file_path: str, source_code: str, function_name: str) -> List[Dict]:
        """查找函数定义
        
        Args:
            file_path: 文件路径
            source_code: 源代码内容
            function_name: 函数名
            
        Returns:
            List[Dict]: 函数定义信息列表，每个字典包含：
                - file_path: 文件路径
                - name: 函数名
                - line: 行号
                - column: 列号
                - code: 函数代码
        """
        if not AST_AVAILABLE:
            return []
        
        language = self.config.get_language_from_file(file_path)
        if not language or not self.config.is_language_supported(language):
            return []
        
        tree = self.config.parse_file(file_path, source_code)
        if not tree:
            return []
        
        results = []
        
        # Python: function_definition
        # JavaScript/TypeScript: function_declaration, method_definition
        # C++: function_definition
        # Java: method_declaration, constructor_declaration
        if language == 'python':
            function_nodes = self._find_nodes_by_type(tree.root_node, 'function_definition', source_code)
            for node, line, column in function_nodes:
                # 查找函数名节点
                for child in node.children:
                    if child.type == 'identifier':
                        name = self._get_node_text(child, source_code)
                        if name == function_name:
                            code = self._get_node_text(node, source_code)
                            results.append({
                                'file_path': file_path,
                                'name': name,
                                'line': line,
                                'column': column,
                                'code': code
                            })
                            break
        
        elif language in ['javascript', 'typescript']:
            # 查找 function_declaration
            function_nodes = self._find_nodes_by_type(tree.root_node, 'function_declaration', source_code)
            for node, line, column in function_nodes:
                for child in node.children:
                    if child.type == 'identifier':
                        name = self._get_node_text(child, source_code)
                        if name == function_name:
                            code = self._get_node_text(node, source_code)
                            results.append({
                                'file_path': file_path,
                                'name': name,
                                'line': line,
                                'column': column,
                                'code': code
                            })
                            break
            
            # 查找 method_definition (类方法)
            method_nodes = self._find_nodes_by_type(tree.root_node, 'method_definition', source_code)
            for node, line, column in method_nodes:
                for child in node.children:
                    if child.type == 'property_name':
                        name_node = child.children[0] if child.children else None
                        if name_node and name_node.type == 'identifier':
                            name = self._get_node_text(name_node, source_code)
                            if name == function_name:
                                code = self._get_node_text(node, source_code)
                                results.append({
                                    'file_path': file_path,
                                    'name': name,
                                    'line': line,
                                    'column': column,
                                    'code': code
                                })
                                break
        
        elif language == 'cpp':
            # C++: function_definition
            function_nodes = self._find_nodes_by_type(tree.root_node, 'function_definition', source_code)
            for node, line, column in function_nodes:
                # 查找函数名（declarator -> function_declarator -> identifier）
                def find_function_name(n):
                    if n.type == 'identifier':
                        return self._get_node_text(n, source_code)
                    for child in n.children:
                        result = find_function_name(child)
                        if result:
                            return result
                    return None
                
                name = find_function_name(node)
                if name == function_name:
                    code = self._get_node_text(node, source_code)
                    results.append({
                        'file_path': file_path,
                        'name': name,
                        'line': line,
                        'column': column,
                        'code': code
                    })
        
        elif language == 'java':
            # Java: method_declaration
            method_nodes = self._find_nodes_by_type(tree.root_node, 'method_declaration', source_code)
            for node, line, column in method_nodes:
                # 查找方法名（identifier 在 declarator 中）
                for child in node.children:
                    if child.type == 'identifier':
                        name = self._get_node_text(child, source_code)
                        if name == function_name:
                            code = self._get_node_text(node, source_code)
                            results.append({
                                'file_path': file_path,
                                'name': name,
                                'line': line,
                                'column': column,
                                'code': code
                            })
                            break
                    elif child.type == 'method_declarator':
                        # 方法声明器中查找标识符
                        for subchild in child.children:
                            if subchild.type == 'identifier':
                                name = self._get_node_text(subchild, source_code)
                                if name == function_name:
                                    code = self._get_node_text(node, source_code)
                                    results.append({
                                        'file_path': file_path,
                                        'name': name,
                                        'line': line,
                                        'column': column,
                                        'code': code
                                    })
                                    break
            
            # Java: constructor_declaration
            constructor_nodes = self._find_nodes_by_type(tree.root_node, 'constructor_declaration', source_code)
            for node, line, column in constructor_nodes:
                # 构造函数名就是类名
                for child in node.children:
                    if child.type == 'identifier':
                        name = self._get_node_text(child, source_code)
                        if name == function_name:
                            code = self._get_node_text(node, source_code)
                            results.append({
                                'file_path': file_path,
                                'name': name,
                                'line': line,
                                'column': column,
                                'code': code
                            })
                            break
        
        return results
    
    def find_function_calls(self, file_path: str, source_code: str, function_name: str) -> List[Dict]:
        """查找函数调用
        
        Args:
            file_path: 文件路径
            source_code: 源代码内容
            function_name: 函数名
            
        Returns:
            List[Dict]: 函数调用信息列表，每个字典包含：
                - file_path: 文件路径
                - name: 函数名
                - line: 行号
                - column: 列号
                - code: 调用代码
        """
        if not AST_AVAILABLE:
            return []
        
        language = self.config.get_language_from_file(file_path)
        if not language or not self.config.is_language_supported(language):
            return []
        
        tree = self.config.parse_file(file_path, source_code)
        if not tree:
            return []
        
        results = []
        
        # 查找 call 节点
        # Python/JavaScript: call
        # C++: call_expression
        # Java: method_invocation
        if language in ['python', 'javascript', 'typescript']:
            call_nodes = self._find_nodes_by_type(tree.root_node, 'call', source_code)
        elif language == 'cpp':
            call_nodes = self._find_nodes_by_type(tree.root_node, 'call_expression', source_code)
        elif language == 'java':
            call_nodes = self._find_nodes_by_type(tree.root_node, 'method_invocation', source_code)
        else:
            call_nodes = []
        
        for node, line, column in call_nodes:
            # 查找被调用的函数名
            function_node = node.children[0] if node.children else None
            if function_node:
                # Python: identifier 或 attribute (如 obj.method)
                # JavaScript: identifier 或 member_expression (如 obj.method)
                # C++: identifier 或 field_expression (如 obj.method)
                # Java: identifier 或 member_select (如 obj.method)
                if function_node.type == 'identifier':
                    name = self._get_node_text(function_node, source_code)
                    if name == function_name:
                        code = self._get_node_text(node, source_code)
                        results.append({
                            'file_path': file_path,
                            'name': name,
                            'line': line,
                            'column': column,
                            'code': code
                        })
                elif function_node.type in ['attribute', 'member_expression', 'field_expression', 'member_select']:
                    # 处理 obj.method() 的情况
                    # 查找最后一个 identifier
                    def find_last_identifier(n):
                        if n.type == 'identifier':
                            return n
                        for child in reversed(n.children):
                            result = find_last_identifier(child)
                            if result:
                                return result
                        return None
                    
                    identifier_node = find_last_identifier(function_node)
                    if identifier_node:
                        name = self._get_node_text(identifier_node, source_code)
                        if name == function_name:
                            code = self._get_node_text(node, source_code)
                            results.append({
                                'file_path': file_path,
                                'name': name,
                                'line': line,
                                'column': column,
                                'code': code
                            })
        
        return results
    
    def trace_call_chain(self, file_path: str, source_code: str, function_name: str, max_depth: int = 10) -> List[Dict]:
        """追踪函数调用链
        
        从指定函数开始，向上追踪调用链
        
        Args:
            file_path: 文件路径
            source_code: 源代码内容
            function_name: 起始函数名
            max_depth: 最大追踪深度
            
        Returns:
            List[Dict]: 调用链信息列表，每个字典包含：
                - file_path: 文件路径
                - function: 函数名
                - line: 行号
                - depth: 调用深度
        """
        if not AST_AVAILABLE:
            return []
        
        # 首先找到函数定义
        definitions = self.find_function_definition(file_path, source_code, function_name)
        if not definitions:
            return []
        
        results = []
        visited = set()
        
        def trace_from_function(func_name: str, depth: int):
            if depth > max_depth or func_name in visited:
                return
            
            visited.add(func_name)
            
            # 查找调用该函数的地方
            calls = self.find_function_calls(file_path, source_code, func_name)
            for call in calls:
                results.append({
                    'file_path': file_path,
                    'function': func_name,
                    'line': call['line'],
                    'depth': depth
                })
                
                # 递归查找调用者的调用者
                # 这里简化处理，实际应该找到包含调用的函数
                # TODO: 实现更完整的调用链追踪
        
        trace_from_function(function_name, 0)
        return results
    
    def find_variable_usage(self, file_path: str, source_code: str, variable_name: str) -> List[Dict]:
        """查找变量使用
        
        Args:
            file_path: 文件路径
            source_code: 源代码内容
            variable_name: 变量名
            
        Returns:
            List[Dict]: 变量使用信息列表，每个字典包含：
                - file_path: 文件路径
                - name: 变量名
                - line: 行号
                - column: 列号
                - code: 使用代码片段
        """
        if not AST_AVAILABLE:
            return []
        
        language = self.config.get_language_from_file(file_path)
        if not language or not self.config.is_language_supported(language):
            return []
        
        tree = self.config.parse_file(file_path, source_code)
        if not tree:
            return []
        
        results = []
        
        # 查找所有 identifier 节点
        identifier_nodes = self._find_nodes_by_type(tree.root_node, 'identifier', source_code)
        
        for node, line, column in identifier_nodes:
            name = self._get_node_text(node, source_code)
            if name == variable_name:
                # 获取包含该标识符的父节点代码（如赋值、调用等）
                parent = node.parent
                if parent:
                    code = self._get_node_text(parent, source_code)
                    results.append({
                        'file_path': file_path,
                        'name': name,
                        'line': line,
                        'column': column,
                        'code': code[:200]  # 限制代码长度
                    })
        
        return results
