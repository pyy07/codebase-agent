"""AST 代码分析器"""
from typing import List, Optional, Dict, Tuple, Any
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
    - 函数调用关系图构建
    - 类继承关系分析
    - 模块依赖关系分析
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
    
    def _extract_function_name_from_call(self, call_node, source_code: str, language: str) -> Optional[str]:
        """从调用节点中提取函数名
        
        Args:
            call_node: 调用节点
            source_code: 源代码内容
            language: 编程语言
            
        Returns:
            Optional[str]: 函数名，如果无法提取则返回 None
        """
        if not call_node.children:
            return None
        
        function_node = call_node.children[0]
        
        if function_node.type == 'identifier':
            return self._get_node_text(function_node, source_code)
        elif function_node.type in ['attribute', 'member_expression', 'field_expression', 'member_select']:
            # 处理 obj.method() 的情况，提取最后一个 identifier
            def find_last_identifier(n):
                if n.type == 'identifier':
                    return self._get_node_text(n, source_code)
                for child in reversed(n.children):
                    result = find_last_identifier(child)
                    if result:
                        return result
                return None
            
            return find_last_identifier(function_node)
        
        return None
    
    def _extract_all_functions(self, file_path: str, source_code: str) -> List[Dict]:
        """提取文件中的所有函数定义
        
        Args:
            file_path: 文件路径
            source_code: 源代码内容
            
        Returns:
            List[Dict]: 函数定义列表，每个字典包含 name, line, column, file_path
        """
        if not AST_AVAILABLE:
            return []
        
        language = self.config.get_language_from_file(file_path)
        if not language or not self.config.is_language_supported(language):
            return []
        
        tree = self.config.parse_file(file_path, source_code)
        if not tree:
            return []
        
        functions = []
        
        # 根据语言类型查找函数定义节点
        if language == 'python':
            function_nodes = self._find_nodes_by_type(tree.root_node, 'function_definition', source_code)
            for node, line, column in function_nodes:
                for child in node.children:
                    if child.type == 'identifier':
                        name = self._get_node_text(child, source_code)
                        functions.append({
                            'name': name,
                            'line': line,
                            'column': column,
                            'file_path': file_path
                        })
                        break
        
        elif language in ['javascript', 'typescript']:
            # function_declaration
            function_nodes = self._find_nodes_by_type(tree.root_node, 'function_declaration', source_code)
            for node, line, column in function_nodes:
                for child in node.children:
                    if child.type == 'identifier':
                        name = self._get_node_text(child, source_code)
                        functions.append({
                            'name': name,
                            'line': line,
                            'column': column,
                            'file_path': file_path
                        })
                        break
            
            # method_definition
            method_nodes = self._find_nodes_by_type(tree.root_node, 'method_definition', source_code)
            for node, line, column in method_nodes:
                for child in node.children:
                    if child.type == 'property_name':
                        name_node = child.children[0] if child.children else None
                        if name_node and name_node.type == 'identifier':
                            name = self._get_node_text(name_node, source_code)
                            functions.append({
                                'name': name,
                                'line': line,
                                'column': column,
                                'file_path': file_path
                            })
                            break
        
        elif language == 'cpp':
            function_nodes = self._find_nodes_by_type(tree.root_node, 'function_definition', source_code)
            for node, line, column in function_nodes:
                def find_function_name(n):
                    if n.type == 'identifier':
                        return self._get_node_text(n, source_code)
                    for child in n.children:
                        result = find_function_name(child)
                        if result:
                            return result
                    return None
                
                name = find_function_name(node)
                if name:
                    functions.append({
                        'name': name,
                        'line': line,
                        'column': column,
                        'file_path': file_path
                    })
        
        elif language == 'java':
            method_nodes = self._find_nodes_by_type(tree.root_node, 'method_declaration', source_code)
            for node, line, column in method_nodes:
                for child in node.children:
                    if child.type == 'identifier':
                        name = self._get_node_text(child, source_code)
                        functions.append({
                            'name': name,
                            'line': line,
                            'column': column,
                            'file_path': file_path
                        })
                        break
                    elif child.type == 'method_declarator':
                        for subchild in child.children:
                            if subchild.type == 'identifier':
                                name = self._get_node_text(subchild, source_code)
                                functions.append({
                                    'name': name,
                                    'line': line,
                                    'column': column,
                                    'file_path': file_path
                                })
                                break
        
        return functions
    
    def build_call_graph(self, file_path: str, source_code: str) -> Dict[str, Any]:
        """构建函数调用关系图
        
        Args:
            file_path: 文件路径
            source_code: 源代码内容
            
        Returns:
            Dict[str, Any]: 调用关系图，包含：
                - nodes: 节点列表（函数定义）
                - edges: 边列表（函数调用关系）
                每个节点包含：name, line, column, file_path
                每条边包含：from_function, to_function, line, column
        """
        if not AST_AVAILABLE:
            return {'nodes': [], 'edges': []}
        
        language = self.config.get_language_from_file(file_path)
        if not language or not self.config.is_language_supported(language):
            return {'nodes': [], 'edges': []}
        
        tree = self.config.parse_file(file_path, source_code)
        if not tree:
            return {'nodes': [], 'edges': []}
        
        # 提取所有函数定义作为节点
        nodes = self._extract_all_functions(file_path, source_code)
        
        # 构建函数名到函数信息的映射
        function_map = {func['name']: func for func in nodes}
        
        # 查找所有函数调用作为边
        edges = []
        
        # 根据语言类型查找调用节点
        if language in ['python', 'javascript', 'typescript']:
            call_nodes = self._find_nodes_by_type(tree.root_node, 'call', source_code)
        elif language == 'cpp':
            call_nodes = self._find_nodes_by_type(tree.root_node, 'call_expression', source_code)
        elif language == 'java':
            call_nodes = self._find_nodes_by_type(tree.root_node, 'method_invocation', source_code)
        else:
            call_nodes = []
        
        # 需要找到包含调用的函数（调用者）
        def find_containing_function(node):
            """查找包含该节点的函数定义"""
            current = node.parent
            while current:
                if language == 'python' and current.type == 'function_definition':
                    for child in current.children:
                        if child.type == 'identifier':
                            return self._get_node_text(child, source_code)
                elif language in ['javascript', 'typescript']:
                    if current.type == 'function_declaration':
                        for child in current.children:
                            if child.type == 'identifier':
                                return self._get_node_text(child, source_code)
                    elif current.type == 'method_definition':
                        for child in current.children:
                            if child.type == 'property_name':
                                name_node = child.children[0] if child.children else None
                                if name_node and name_node.type == 'identifier':
                                    return self._get_node_text(name_node, source_code)
                elif language == 'cpp' and current.type == 'function_definition':
                    def find_function_name(n):
                        if n.type == 'identifier':
                            return self._get_node_text(n, source_code)
                        for child in n.children:
                            result = find_function_name(child)
                            if result:
                                return result
                        return None
                    return find_function_name(current)
                elif language == 'java':
                    if current.type == 'method_declaration':
                        for child in current.children:
                            if child.type == 'identifier':
                                return self._get_node_text(child, source_code)
                            elif child.type == 'method_declarator':
                                for subchild in child.children:
                                    if subchild.type == 'identifier':
                                        return self._get_node_text(subchild, source_code)
                
                current = current.parent
            return None
        
        for call_node, line, column in call_nodes:
            called_function = self._extract_function_name_from_call(call_node, source_code, language)
            if called_function and called_function in function_map:
                caller_function = find_containing_function(call_node)
                if caller_function and caller_function in function_map:
                    edges.append({
                        'from_function': caller_function,
                        'to_function': called_function,
                        'line': line,
                        'column': column
                    })
        
        return {
            'nodes': nodes,
            'edges': edges
        }
    
    def analyze_class_inheritance(self, file_path: str, source_code: str) -> List[Dict]:
        """分析类继承关系
        
        Args:
            file_path: 文件路径
            source_code: 源代码内容
            
        Returns:
            List[Dict]: 类继承关系列表，每个字典包含：
                - class_name: 类名
                - parent_classes: 父类列表
                - line: 行号
                - column: 列号
                - file_path: 文件路径
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
        
        if language == 'python':
            class_nodes = self._find_nodes_by_type(tree.root_node, 'class_definition', source_code)
            for node, line, column in class_nodes:
                class_name = None
                parent_classes = []
                
                # 查找类名
                for child in node.children:
                    if child.type == 'identifier':
                        class_name = self._get_node_text(child, source_code)
                    elif child.type == 'argument_list':
                        # Python 的继承列表在 argument_list 中
                        for arg in child.children:
                            if arg.type == 'identifier':
                                parent_classes.append(self._get_node_text(arg, source_code))
                            elif arg.type == 'attribute':
                                # 处理 module.Class 的情况
                                parent_name = self._get_node_text(arg, source_code)
                                parent_classes.append(parent_name)
                
                if class_name:
                    results.append({
                        'class_name': class_name,
                        'parent_classes': parent_classes,
                        'line': line,
                        'column': column,
                        'file_path': file_path
                    })
        
        elif language in ['javascript', 'typescript']:
            class_nodes = self._find_nodes_by_type(tree.root_node, 'class_declaration', source_code)
            for node, line, column in class_nodes:
                class_name = None
                parent_classes = []
                
                for child in node.children:
                    if child.type == 'class_heritage':
                        # TypeScript/JavaScript 的继承在 class_heritage 中
                        for heritage_child in child.children:
                            if heritage_child.type == 'identifier':
                                parent_classes.append(self._get_node_text(heritage_child, source_code))
                            elif heritage_child.type == 'member_expression':
                                parent_name = self._get_node_text(heritage_child, source_code)
                                parent_classes.append(parent_name)
                    elif child.type == 'type_identifier' or child.type == 'identifier':
                        class_name = self._get_node_text(child, source_code)
                
                if class_name:
                    results.append({
                        'class_name': class_name,
                        'parent_classes': parent_classes,
                        'line': line,
                        'column': column,
                        'file_path': file_path
                    })
        
        elif language == 'cpp':
            class_nodes = self._find_nodes_by_type(tree.root_node, 'class_specifier', source_code)
            for node, line, column in class_nodes:
                class_name = None
                parent_classes = []
                
                for child in node.children:
                    if child.type == 'type_identifier':
                        class_name = self._get_node_text(child, source_code)
                    elif child.type == 'base_clause':
                        # C++ 的基类列表在 base_clause 中
                        for base in child.children:
                            if base.type == 'base_class_specifier':
                                for base_child in base.children:
                                    if base_child.type == 'type_identifier':
                                        parent_classes.append(self._get_node_text(base_child, source_code))
                
                if class_name:
                    results.append({
                        'class_name': class_name,
                        'parent_classes': parent_classes,
                        'line': line,
                        'column': column,
                        'file_path': file_path
                    })
        
        elif language == 'java':
            class_nodes = self._find_nodes_by_type(tree.root_node, 'class_declaration', source_code)
            for node, line, column in class_nodes:
                class_name = None
                parent_classes = []
                
                for child in node.children:
                    if child.type == 'type_identifier':
                        class_name = self._get_node_text(child, source_code)
                    elif child.type == 'superclass':
                        # Java 的父类在 superclass 中
                        for super_child in child.children:
                            if super_child.type == 'type_identifier':
                                parent_classes.append(self._get_node_text(super_child, source_code))
                    elif child.type == 'super_interfaces':
                        # Java 的接口在 super_interfaces 中
                        for interface_child in child.children:
                            if interface_child.type == 'type_identifier':
                                parent_classes.append(self._get_node_text(interface_child, source_code))
                
                if class_name:
                    results.append({
                        'class_name': class_name,
                        'parent_classes': parent_classes,
                        'line': line,
                        'column': column,
                        'file_path': file_path
                    })
        
        return results
    
    def analyze_module_dependencies(self, file_path: str, source_code: str) -> List[Dict]:
        """分析模块依赖关系
        
        Args:
            file_path: 文件路径
            source_code: 源代码内容
            
        Returns:
            List[Dict]: 模块依赖列表，每个字典包含：
                - module_name: 导入的模块名
                - import_type: 导入类型（import/from/require/include）
                - imported_items: 导入的具体项（可选）
                - line: 行号
                - column: 列号
                - file_path: 文件路径
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
        
        if language == 'python':
            # import_statement 和 import_from_statement
            import_nodes = self._find_nodes_by_type(tree.root_node, 'import_statement', source_code)
            for node, line, column in import_nodes:
                module_name = None
                imported_items = []
                
                for child in node.children:
                    if child.type == 'dotted_name':
                        module_name = self._get_node_text(child, source_code)
                    elif child.type == 'import_list':
                        for item in child.children:
                            if item.type == 'dotted_as_name':
                                imported_items.append(self._get_node_text(item, source_code))
                            elif item.type == 'aliased_import':
                                for alias_child in item.children:
                                    if alias_child.type == 'dotted_name':
                                        imported_items.append(self._get_node_text(alias_child, source_code))
                
                if module_name:
                    results.append({
                        'module_name': module_name,
                        'import_type': 'import',
                        'imported_items': imported_items,
                        'line': line,
                        'column': column,
                        'file_path': file_path
                    })
            
            # from ... import ...
            from_nodes = self._find_nodes_by_type(tree.root_node, 'import_from_statement', source_code)
            for node, line, column in from_nodes:
                module_name = None
                imported_items = []
                
                for child in node.children:
                    if child.type == 'module_name' or child.type == 'dotted_name':
                        module_name = self._get_node_text(child, source_code)
                    elif child.type == 'import_list':
                        for item in child.children:
                            if item.type == 'dotted_as_name':
                                imported_items.append(self._get_node_text(item, source_code))
                            elif item.type == 'aliased_import':
                                for alias_child in item.children:
                                    if alias_child.type == 'dotted_name':
                                        imported_items.append(self._get_node_text(alias_child, source_code))
                            elif item.type == 'identifier':
                                imported_items.append(self._get_node_text(item, source_code))
                
                if module_name:
                    results.append({
                        'module_name': module_name,
                        'import_type': 'from',
                        'imported_items': imported_items,
                        'line': line,
                        'column': column,
                        'file_path': file_path
                    })
        
        elif language in ['javascript', 'typescript']:
            # import_statement
            import_nodes = self._find_nodes_by_type(tree.root_node, 'import_statement', source_code)
            for node, line, column in import_nodes:
                module_name = None
                imported_items = []
                
                for child in node.children:
                    if child.type == 'string':
                        # import "module" 或 import 'module'
                        module_name = self._get_node_text(child, source_code).strip('"\'')
                    elif child.type == 'import_clause':
                        for import_child in child.children:
                            if import_child.type == 'namespace_import':
                                namespace = import_child.children[0] if import_child.children else None
                                if namespace:
                                    imported_items.append(self._get_node_text(namespace, source_code))
                            elif import_child.type == 'named_imports':
                                for named in import_child.children:
                                    if named.type == 'import_specifier':
                                        for spec_child in named.children:
                                            if spec_child.type == 'identifier':
                                                imported_items.append(self._get_node_text(spec_child, source_code))
                
                if module_name:
                    results.append({
                        'module_name': module_name,
                        'import_type': 'import',
                        'imported_items': imported_items,
                        'line': line,
                        'column': column,
                        'file_path': file_path
                    })
            
            # require() 调用
            call_nodes = self._find_nodes_by_type(tree.root_node, 'call_expression', source_code)
            for node, line, column in call_nodes:
                if node.children:
                    func_node = node.children[0]
                    if func_node.type == 'identifier':
                        func_name = self._get_node_text(func_node, source_code)
                        if func_name == 'require':
                            # 查找参数中的模块名
                            if len(node.children) > 1:
                                arg_node = node.children[1]
                                if arg_node.type == 'arguments':
                                    for arg in arg_node.children:
                                        if arg.type == 'string':
                                            module_name = self._get_node_text(arg, source_code).strip('"\'')
                                            if module_name:
                                                results.append({
                                                    'module_name': module_name,
                                                    'import_type': 'require',
                                                    'imported_items': [],
                                                    'line': line,
                                                    'column': column,
                                                    'file_path': file_path
                                                })
        
        elif language == 'cpp':
            # #include 预处理指令
            preproc_nodes = self._find_nodes_by_type(tree.root_node, 'preproc_include', source_code)
            for node, line, column in preproc_nodes:
                module_name = None
                
                for child in node.children:
                    if child.type == 'string_literal':
                        module_name = self._get_node_text(child, source_code).strip('"<>')
                    elif child.type == 'system_lib_string':
                        module_name = self._get_node_text(child, source_code).strip('<>')
                
                if module_name:
                    results.append({
                        'module_name': module_name,
                        'import_type': 'include',
                        'imported_items': [],
                        'line': line,
                        'column': column,
                        'file_path': file_path
                    })
        
        elif language == 'java':
            # import_declaration
            import_nodes = self._find_nodes_by_type(tree.root_node, 'import_declaration', source_code)
            for node, line, column in import_nodes:
                module_name = None
                
                for child in node.children:
                    if child.type == 'scoped_identifier':
                        module_name = self._get_node_text(child, source_code)
                    elif child.type == 'asterisk':
                        # import package.*
                        # 需要找到 package 名
                        parent = node.parent
                        if parent:
                            for parent_child in parent.children:
                                if parent_child.type == 'scoped_identifier':
                                    module_name = self._get_node_text(parent_child, source_code) + '.*'
                
                if module_name:
                    results.append({
                        'module_name': module_name,
                        'import_type': 'import',
                        'imported_items': [],
                        'line': line,
                        'column': column,
                        'file_path': file_path
                    })
        
        return results
