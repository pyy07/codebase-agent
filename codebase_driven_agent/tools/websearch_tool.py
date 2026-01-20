"""网络搜索工具实现（可选）"""
from typing import Optional
from pydantic import BaseModel, Field

from codebase_driven_agent.tools.base import BaseCodebaseTool, ToolResult
from codebase_driven_agent.config import settings
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.tools.websearch")

# 尝试导入搜索 API 库
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    try:
        import requests
        HTTPX_AVAILABLE = False
        REQUESTS_AVAILABLE = True
    except ImportError:
        HTTPX_AVAILABLE = False
        REQUESTS_AVAILABLE = False


class WebSearchToolInput(BaseModel):
    """网络搜索工具输入参数"""
    query: str = Field(..., description="搜索查询")
    max_results: Optional[int] = Field(5, description="最大结果数量（默认5）")


class WebSearchTool(BaseCodebaseTool):
    """网络搜索工具（可选）
    
    使用搜索 API 进行网络搜索。需要配置 API Key。
    支持 Exa API 或 Serper API。
    """
    
    name: str = "websearch"
    description: str = (
        "在网络上搜索信息。可以搜索文档、错误解决方案、API 使用示例等。"
        "注意：需要配置搜索 API Key（EXA_API_KEY 或 SERPER_API_KEY）。"
        "使用场景：查找错误解决方案、API 文档、最佳实践等。"
        "参数：query（搜索查询）、max_results（最大结果数量，可选，默认5）。"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, "exa_api_key", getattr(settings, 'exa_api_key', None))
        object.__setattr__(self, "serper_api_key", getattr(settings, 'serper_api_key', None))
        object.__setattr__(self, "timeout", 10)
    
    def _search_with_exa(self, query: str, max_results: int) -> ToolResult:
        """使用 Exa API 搜索"""
        if not self.exa_api_key:
            return ToolResult(
                success=False,
                error="Exa API Key 未配置（EXA_API_KEY）。请先配置 API Key。"
            )
        
        try:
            if HTTPX_AVAILABLE:
                import httpx
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        "https://api.exa.ai/search",
                        headers={
                            "x-api-key": self.exa_api_key,
                            "Content-Type": "application/json"
                        },
                        json={
                            "query": query,
                            "num_results": max_results,
                            "type": "keyword"
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
            elif REQUESTS_AVAILABLE:
                import requests
                response = requests.post(
                    "https://api.exa.ai/search",
                    headers={
                        "x-api-key": self.exa_api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "query": query,
                        "num_results": max_results,
                        "type": "keyword"
                    },
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
            else:
                return ToolResult(
                    success=False,
                    error="需要安装 httpx 或 requests 库才能使用此工具"
                )
            
            # 格式化结果
            results = data.get('results', [])
            result_lines = []
            result_lines.append(f"搜索查询: {query}")
            result_lines.append(f"结果数: {len(results)}")
            result_lines.append("")
            
            for i, result in enumerate(results, 1):
                result_lines.append(f"{i}. {result.get('title', '无标题')}")
                result_lines.append(f"   URL: {result.get('url', '')}")
                if result.get('text'):
                    text = result['text'][:200] + "..." if len(result['text']) > 200 else result['text']
                    result_lines.append(f"   摘要: {text}")
                result_lines.append("")
            
            result_text = "\n".join(result_lines)
            
            return ToolResult(
                success=True,
                data=result_text
            )
        
        except Exception as e:
            logger.error(f"Exa search error: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"搜索失败: {str(e)}"
            )
    
    def _search_with_serper(self, query: str, max_results: int) -> ToolResult:
        """使用 Serper API 搜索"""
        if not self.serper_api_key:
            return ToolResult(
                success=False,
                error="Serper API Key 未配置（SERPER_API_KEY）。请先配置 API Key。"
            )
        
        try:
            if HTTPX_AVAILABLE:
                import httpx
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        "https://google.serper.dev/search",
                        headers={
                            "X-API-KEY": self.serper_api_key,
                            "Content-Type": "application/json"
                        },
                        json={
                            "q": query,
                            "num": max_results
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
            elif REQUESTS_AVAILABLE:
                import requests
                response = requests.post(
                    "https://google.serper.dev/search",
                    headers={
                        "X-API-KEY": self.serper_api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "q": query,
                        "num": max_results
                    },
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
            else:
                return ToolResult(
                    success=False,
                    error="需要安装 httpx 或 requests 库才能使用此工具"
                )
            
            # 格式化结果
            results = data.get('organic', [])
            result_lines = []
            result_lines.append(f"搜索查询: {query}")
            result_lines.append(f"结果数: {len(results)}")
            result_lines.append("")
            
            for i, result in enumerate(results, 1):
                result_lines.append(f"{i}. {result.get('title', '无标题')}")
                result_lines.append(f"   URL: {result.get('link', '')}")
                if result.get('snippet'):
                    result_lines.append(f"   摘要: {result['snippet']}")
                result_lines.append("")
            
            result_text = "\n".join(result_lines)
            
            return ToolResult(
                success=True,
                data=result_text
            )
        
        except Exception as e:
            logger.error(f"Serper search error: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"搜索失败: {str(e)}"
            )
    
    def _execute(self, query: str, max_results: Optional[int] = 5) -> ToolResult:
        """
        执行网络搜索
        
        Args:
            query: 搜索查询
            max_results: 最大结果数量
        
        Returns:
            ToolResult
        """
        try:
            max_results = max(1, min(max_results or 5, 10))  # 限制在 1-10 之间
            
            # 检查是否有可用的 API Key
            if not self.exa_api_key and not self.serper_api_key:
                return ToolResult(
                    success=False,
                    error="未配置搜索 API Key。请配置 EXA_API_KEY 或 SERPER_API_KEY 环境变量。"
                )
            
            # 优先使用 Exa，如果没有则使用 Serper
            if self.exa_api_key:
                return self._search_with_exa(query, max_results)
            elif self.serper_api_key:
                return self._search_with_serper(query, max_results)
            else:
                return ToolResult(
                    success=False,
                    error="未配置搜索 API Key"
                )
        
        except Exception as e:
            logger.error(f"WebSearchTool error: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"搜索时发生错误: {str(e)}"
            )
