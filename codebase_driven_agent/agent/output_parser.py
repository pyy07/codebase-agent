"""输出解析器 - 将 Agent 输出解析为结构化结果"""
import json
import re
from typing import Dict, List, Optional
from codebase_driven_agent.api.models import AnalysisResult


class OutputParser:
    """Agent 输出解析器"""
    
    def parse(self, agent_output: str) -> AnalysisResult:
        """
        解析 Agent 输出为结构化结果
        
        Args:
            agent_output: Agent 的原始输出文本
        
        Returns:
            AnalysisResult: 结构化的分析结果
        """
        # 尝试解析 JSON 格式的输出
        json_result = self._try_parse_json(agent_output)
        if json_result:
            return self._build_from_dict(json_result)
        
        # 解析文本格式的输出
        return self._parse_text_format(agent_output)
    
    def _try_parse_json(self, text: str) -> Optional[Dict]:
        """尝试解析 JSON 格式的输出"""
        # 查找 JSON 代码块
        json_pattern = r'```json\s*(\{.*?\})\s*```'
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 尝试直接解析整个文本为 JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        return None
    
    def _parse_text_format(self, text: str) -> AnalysisResult:
        """解析文本格式的输出"""
        root_cause = self._extract_section(text, ["根因分析", "Root Cause", "原因", "问题原因"])
        suggestions = self._extract_list(text, ["应急建议", "处理建议", "Suggestions", "建议", "解决方案"])
        confidence = self._extract_confidence(text)
        
        return AnalysisResult(
            root_cause=root_cause or "无法确定根因",
            suggestions=suggestions or ["请查看详细日志和代码"],
            confidence=confidence,
            related_code=None,
            related_logs=None,
            related_data=None,
        )
    
    def _extract_section(self, text: str, keywords: List[str]) -> Optional[str]:
        """提取特定章节的内容"""
        for keyword in keywords:
            pattern = rf'{keyword}[：:]\s*(.+?)(?=\n\n|\n[A-Z\u4e00-\u9fa5]|$)'
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                # 清理内容
                content = re.sub(r'\n+', ' ', content)
                return content[:500]  # 限制长度
        
        return None
    
    def _extract_list(self, text: str, keywords: List[str]) -> List[str]:
        """提取列表项"""
        items = []
        
        for keyword in keywords:
            # 查找列表部分
            pattern = rf'{keyword}[：:]\s*\n((?:[-*•]\s*.+\n?)+)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                list_text = match.group(1)
                # 提取列表项
                item_pattern = r'[-*•]\s*(.+?)(?=\n[-*•]|\n\n|$)'
                matches = re.findall(item_pattern, list_text)
                items.extend([m.strip() for m in matches if m.strip()])
        
        # 如果没有找到列表，尝试提取编号列表
        if not items:
            numbered_pattern = r'\d+[\.\)]\s*(.+?)(?=\n\d+[\.\)]|\n\n|$)'
            matches = re.findall(numbered_pattern, text)
            items = [m.strip() for m in matches if m.strip()]
        
        return items[:10]  # 限制数量
    
    def _extract_confidence(self, text: str) -> float:
        """提取置信度评分"""
        # 查找置信度相关的文本
        patterns = [
            r'置信度[：:]\s*(\d+(?:\.\d+)?)',
            r'confidence[：:]\s*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)%\s*(?:置信|confidence)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1))
                    # 如果是百分比，转换为 0-1
                    if value > 1:
                        value = value / 100.0
                    return max(0.0, min(1.0, value))
                except ValueError:
                    continue
        
        # 默认置信度
        return 0.7
    
    def _build_from_dict(self, data: Dict) -> AnalysisResult:
        """从字典构建 AnalysisResult"""
        return AnalysisResult(
            root_cause=data.get("root_cause", "无法确定根因"),
            suggestions=data.get("suggestions", []),
            confidence=data.get("confidence", 0.7),
            related_code=data.get("related_code"),
            related_logs=data.get("related_logs"),
            related_data=data.get("related_data"),
        )

