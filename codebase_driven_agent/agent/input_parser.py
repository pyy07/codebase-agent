"""用户输入解析器"""
import re
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class ParsedInput:
    """解析后的用户输入"""
    original_input: str
    input_type: str  # "error_log", "question", "problem_description"
    keywords: List[str]
    error_type: Optional[str] = None
    file_paths: List[str] = None
    line_numbers: List[int] = None
    stack_trace: Optional[str] = None
    timestamp: Optional[str] = None
    request_id: Optional[str] = None
    
    def __post_init__(self):
        if self.file_paths is None:
            self.file_paths = []
        if self.line_numbers is None:
            self.line_numbers = []


class InputParser:
    """用户输入解析器"""
    
    # 错误日志常见模式
    ERROR_PATTERNS = [
        r'(?i)(error|exception|failed|failure)',
        r'(?i)(traceback|stack trace)',
        r'(?i)(at\s+\S+\.py:\d+)',  # Python 文件路径和行号
        r'(?i)(File\s+["\']\S+["\'],\s+line\s+\d+)',
    ]
    
    # 文件路径模式
    FILE_PATH_PATTERNS = [
        r'["\']([^"\']+\.py)["\']',  # Python 文件
        r'([a-zA-Z0-9_/\\]+\.(py|js|java|go|rs|ts))',  # 常见代码文件
        r'(/[\w/.-]+\.\w+)',  # Unix 路径
        r'([A-Z]:\\[\w\\.-]+\.\w+)',  # Windows 路径
    ]
    
    # 行号模式
    LINE_NUMBER_PATTERNS = [
        r'line\s+(\d+)',
        r':(\d+):',
        r'\((\d+)\)',
    ]
    
    # 时间戳模式
    TIMESTAMP_PATTERNS = [
        r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})',
        r'(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})',
        r'(\d{2}-\d{2}-\d{4}\s+\d{2}:\d{2}:\d{2})',
    ]
    
    # 请求ID模式
    REQUEST_ID_PATTERNS = [
        r'(request[_-]?id[:\s=]+([a-zA-Z0-9-]+))',
        r'(trace[_-]?id[:\s=]+([a-zA-Z0-9-]+))',
        r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',  # UUID
    ]
    
    def parse(self, user_input: str) -> ParsedInput:
        """
        解析用户输入
        
        Args:
            user_input: 用户输入的原始文本
        
        Returns:
            ParsedInput: 解析后的结构化数据
        """
        input_type = self._detect_input_type(user_input)
        keywords = self._extract_keywords(user_input)
        
        parsed = ParsedInput(
            original_input=user_input,
            input_type=input_type,
            keywords=keywords,
        )
        
        if input_type == "error_log":
            parsed.error_type = self._extract_error_type(user_input)
            parsed.stack_trace = self._extract_stack_trace(user_input)
        
        parsed.file_paths = self._extract_file_paths(user_input)
        parsed.line_numbers = self._extract_line_numbers(user_input)
        parsed.timestamp = self._extract_timestamp(user_input)
        parsed.request_id = self._extract_request_id(user_input)
        
        return parsed
    
    def _detect_input_type(self, text: str) -> str:
        """检测输入类型"""
        text_lower = text.lower()
        
        # 检查是否是错误日志
        error_indicators = ['error', 'exception', 'traceback', 'stack trace', 'failed']
        if any(indicator in text_lower for indicator in error_indicators):
            return "error_log"
        
        # 检查是否是问题描述
        question_indicators = ['?', '为什么', '如何', '怎么', 'what', 'why', 'how']
        if any(indicator in text for indicator in question_indicators):
            return "question"
        
        # 默认为问题描述
        return "problem_description"
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取：提取重要单词
        # 过滤掉常见停用词
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
            '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
        }
        
        # 提取单词（支持中英文）
        words = re.findall(r'\b[a-zA-Z]{3,}\b|\b[\u4e00-\u9fa5]+\b', text.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 1]
        
        # 去重并限制数量
        return list(dict.fromkeys(keywords))[:20]
    
    def _extract_error_type(self, text: str) -> Optional[str]:
        """提取错误类型"""
        error_patterns = [
            r'(?i)(\w+Error)',
            r'(?i)(\w+Exception)',
            r'(?i)(error:\s*([^\n]+))',
            r'(?i)(exception:\s*([^\n]+))',
        ]
        
        for pattern in error_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1) if match.lastindex >= 1 else match.group(0)
        
        return None
    
    def _extract_stack_trace(self, text: str) -> Optional[str]:
        """提取堆栈跟踪"""
        # 查找 Traceback 或 Stack trace 部分
        patterns = [
            r'(?i)(traceback[^\n]*\n(?:.*\n)*?.*)',
            r'(?i)(stack trace[^\n]*\n(?:.*\n)*?.*)',
            r'(at\s+\S+\.py:\d+.*\n(?:.*\n)*?.*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_file_paths(self, text: str) -> List[str]:
        """提取文件路径"""
        file_paths = []
        
        for pattern in self.FILE_PATH_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    file_paths.extend([m for m in match if m])
                else:
                    file_paths.append(match)
        
        # 去重
        return list(dict.fromkeys(file_paths))
    
    def _extract_line_numbers(self, text: str) -> List[int]:
        """提取行号"""
        line_numbers = []
        
        for pattern in self.LINE_NUMBER_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    line_num = int(match)
                    if 1 <= line_num <= 100000:  # 合理的行号范围
                        line_numbers.append(line_num)
                except ValueError:
                    continue
        
        # 去重并排序
        return sorted(list(set(line_numbers)))
    
    def _extract_timestamp(self, text: str) -> Optional[str]:
        """提取时间戳"""
        for pattern in self.TIMESTAMP_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_request_id(self, text: str) -> Optional[str]:
        """提取请求ID"""
        for pattern in self.REQUEST_ID_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # 返回捕获组中的ID
                return match.group(match.lastindex) if match.lastindex else match.group(0)
        
        return None

