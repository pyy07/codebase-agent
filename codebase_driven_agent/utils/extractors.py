"""从 Agent intermediate_steps 提取相关信息"""
from typing import List, Dict, Any, Optional
from codebase_driven_agent.api.models import AnalysisResult


def extract_related_code(intermediate_steps: List) -> Optional[List[Dict[str, Any]]]:
    """
    从 intermediate_steps 提取相关代码信息
    
    Args:
        intermediate_steps: Agent 的中间步骤列表（可能是消息列表或元组列表）
        
    Returns:
        相关代码列表，格式为 [{"file": str, "lines": [int, int], "description": str}]
    """
    import re
    related_code = []
    seen_files = set()  # 避免重复
    
    # 如果 intermediate_steps 是消息列表（LangChain 1.0+），需要转换格式
    if intermediate_steps and not isinstance(intermediate_steps[0], (tuple, list)):
        # 这是消息列表，需要从消息中提取工具调用信息
        # 暂时跳过，因为需要更复杂的解析逻辑
        return None
    
    for step in intermediate_steps:
        # 检查 step 是否是元组或列表
        if not isinstance(step, (tuple, list)) or len(step) < 2:
            continue
        
        action, observation = step[0], step[1]
        
        # 检查是否是 CodeTool 的调用
        if hasattr(action, 'tool') and action.tool == 'code_search':
            if isinstance(observation, str):
                # CodeTool 返回格式示例：
                # "File: path/to/file.py\n\n[代码内容]"
                # 或包含匹配行的格式
                lines = observation.split('\n')
                current_file = None
                line_numbers = []
                
                # 方法1: 查找 "File: " 开头的行
                for i, line in enumerate(lines):
                    if line.startswith('File: '):
                        current_file = line.replace('File: ', '').strip()
                    # 方法2: 查找包含文件扩展名的路径模式
                    elif not current_file:
                        # 匹配类似 "path/to/file.py:123" 或 "file.py" 的模式
                        file_pattern = r'([^\s]+\.(py|js|ts|java|go|rs))(?::(\d+))?'
                        match = re.search(file_pattern, line)
                        if match:
                            current_file = match.group(1)
                            if match.group(3):
                                line_numbers.append(int(match.group(3)))
                    # 方法3: 查找匹配的行号信息（格式：line: X）
                    elif 'line:' in line.lower() or 'line ' in line.lower():
                        line_match = re.search(r'line[:\s]+(\d+)', line, re.IGNORECASE)
                        if line_match:
                            line_numbers.append(int(line_match.group(1)))
                
                # 如果找到了文件，添加到结果中
                if current_file and current_file not in seen_files:
                    seen_files.add(current_file)
                    
                    # 确定行号范围
                    if line_numbers:
                        min_line = min(line_numbers)
                        max_line = max(line_numbers)
                        # 扩展范围，包含上下文
                        lines_range = [max(1, min_line - 5), max_line + 10]
                    else:
                        # 如果没有找到具体行号，使用默认范围
                        lines_range = [1, 100]
                    
                    related_code.append({
                        "file": current_file,
                        "lines": lines_range,
                        "description": "从代码搜索工具调用中提取",
                    })
    
    return related_code if related_code else None


def extract_related_logs(intermediate_steps: List) -> Optional[List[Dict[str, Any]]]:
    """
    从 intermediate_steps 提取相关日志信息
    
    Args:
        intermediate_steps: Agent 的中间步骤列表（可能是消息列表或元组列表）
        
    Returns:
        相关日志列表，格式为 [{"timestamp": str, "content": str, "description": str}]
    """
    import re
    related_logs = []
    
    # 如果 intermediate_steps 是消息列表（LangChain 1.0+），需要转换格式
    if intermediate_steps and not isinstance(intermediate_steps[0], (tuple, list)):
        # 这是消息列表，需要从消息中提取工具调用信息
        # 暂时跳过，因为需要更复杂的解析逻辑
        return None
    
    for step in intermediate_steps:
        # 检查 step 是否是元组或列表
        if not isinstance(step, (tuple, list)) or len(step) < 2:
            continue
        
        action, observation = step[0], step[1]
        
        # 检查是否是 LogTool 的调用
        if hasattr(action, 'tool') and action.tool == 'log_search':
            if isinstance(observation, str):
                # LogTool 返回格式示例：
                # "[1] 2024-01-01 10:00:00 [ERROR] Error message\n"
                lines = observation.split('\n')
                
                # 解析日志条目
                for line in lines:
                    # 匹配日志格式：[序号] 时间戳 [级别] 消息
                    log_pattern = r'\[(\d+)\]\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[(\w+)\]\s+(.+)'
                    match = re.match(log_pattern, line)
                    
                    if match:
                        timestamp = match.group(2)
                        level = match.group(3)
                        message = match.group(4)
                        
                        related_logs.append({
                            "timestamp": timestamp,
                            "content": f"[{level}] {message}",
                            "description": "从日志查询工具调用中提取",
                        })
                        
                        # 限制提取的日志数量
                        if len(related_logs) >= 5:
                            break
                    elif line.strip() and not line.startswith('=') and not line.startswith('Found'):
                        # 如果不是标准格式，但包含内容，也提取
                        # 跳过分隔线和统计信息
                        if len(related_logs) < 5:
                            related_logs.append({
                                "timestamp": "N/A",
                                "content": line[:500],
                                "description": "从日志查询工具调用中提取",
                            })
    
    return related_logs if related_logs else None


def extract_related_data(intermediate_steps: List) -> Optional[List[Dict[str, Any]]]:
    """
    从 intermediate_steps 提取相关数据库查询结果
    
    Args:
        intermediate_steps: Agent 的中间步骤列表（可能是消息列表或元组列表）
        
    Returns:
        相关数据列表，格式为 [{"query": str, "result": str, "description": str}]
    """
    related_data = []
    
    # 如果 intermediate_steps 是消息列表（LangChain 1.0+），需要转换格式
    if intermediate_steps and not isinstance(intermediate_steps[0], (tuple, list)):
        # 这是消息列表，需要从消息中提取工具调用信息
        # 暂时跳过，因为需要更复杂的解析逻辑
        return None
    
    for step in intermediate_steps:
        # 检查 step 是否是元组或列表
        if not isinstance(step, (tuple, list)) or len(step) < 2:
            continue
        
        action, observation = step[0], step[1]
        
        # 检查是否是 DatabaseTool 的调用
        if hasattr(action, 'tool') and action.tool == 'database_query':
            if isinstance(observation, str):
                # 提取查询结果
                # DatabaseTool 返回格式示例：
                # "Query returned 5 rows:\n\nColumns: id, name, ...\n\nRow 1:\n  id: 1\n  name: ..."
                
                # 尝试提取 SQL 查询（从 action.tool_input）
                query = "N/A"
                if hasattr(action, 'tool_input'):
                    if isinstance(action.tool_input, dict):
                        # DatabaseTool 的输入格式：{"action": "query", "sql": "SELECT ..."}
                        query = action.tool_input.get('sql', action.tool_input.get('query_string', 'N/A'))
                    elif isinstance(action.tool_input, str):
                        query = action.tool_input
                
                # 提取结果预览（前300字符，包含关键信息）
                result_preview = observation[:500] if len(observation) > 500 else observation
                
                # 如果结果包含行数信息，提取它
                if "Query returned" in observation:
                    lines = observation.split('\n')
                    preview_lines = []
                    for line in lines[:10]:  # 取前10行
                        if line.strip() and not line.startswith('='):
                            preview_lines.append(line)
                    result_preview = '\n'.join(preview_lines)
                
                related_data.append({
                    "query": query,
                    "result": result_preview,
                    "description": "数据库查询结果",
                })
                
                # 限制提取的查询数量
                if len(related_data) >= 3:
                    break
    
    return related_data if related_data else None


def extract_from_intermediate_steps(
    intermediate_steps: List,
    result: AnalysisResult,
) -> AnalysisResult:
    """
    从 intermediate_steps 提取相关信息并更新结果
    
    Args:
        intermediate_steps: Agent 的中间步骤列表
        result: 分析结果对象
        
    Returns:
        更新后的分析结果对象
    """
    # 提取相关信息
    related_code = extract_related_code(intermediate_steps)
    related_logs = extract_related_logs(intermediate_steps)
    related_data = extract_related_data(intermediate_steps)
    
    # 更新结果（如果原来为 None）
    if result.related_code is None and related_code:
        result.related_code = related_code
    
    if result.related_logs is None and related_logs:
        result.related_logs = related_logs
    
    if result.related_data is None and related_data:
        result.related_data = related_data
    
    return result

