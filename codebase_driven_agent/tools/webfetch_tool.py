"""网页获取工具实现"""
import re
from typing import Optional
from pydantic import BaseModel, Field

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

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False

from codebase_driven_agent.tools.base import BaseCodebaseTool, ToolResult
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.tools.webfetch")


class WebFetchToolInput(BaseModel):
    """网页获取工具输入参数"""
    url: str = Field(..., description="要获取的网页 URL")


class WebFetchTool(BaseCodebaseTool):
    """网页获取工具
    
    获取网页内容并提取文本。
    """
    
    name: str = "webfetch"
    description: str = (
        "获取网页内容并提取文本。可以获取任何公开网页的内容。"
        "使用场景：获取文档、API 文档、错误信息参考等。"
        "参数：url（网页 URL）。"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, "timeout", 10)  # 请求超时时间（秒）
        object.__setattr__(self, "max_content_length", 1_000_000)  # 最大内容长度（1MB）
    
    def _extract_text_from_html(self, html: str) -> str:
        """从 HTML 提取文本"""
        if BEAUTIFULSOUP_AVAILABLE:
            try:
                soup = BeautifulSoup(html, 'html.parser')
                # 移除 script 和 style 标签
                for script in soup(["script", "style"]):
                    script.decompose()
                # 提取文本
                text = soup.get_text()
                # 清理空白字符
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)
                return text
            except Exception as e:
                logger.warning(f"Failed to parse HTML with BeautifulSoup: {str(e)}")
                # Fallback to regex
                pass
        
        # 简单的 HTML 标签移除（fallback）
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _execute(self, url: str) -> ToolResult:
        """
        获取网页内容
        
        Args:
            url: 网页 URL
        
        Returns:
            ToolResult
        """
        try:
            # 验证 URL
            if not url.startswith(('http://', 'https://')):
                return ToolResult(
                    success=False,
                    error=f"无效的 URL，必须以 http:// 或 https:// 开头: {url}"
                )
            
            # 获取网页内容
            try:
                if HTTPX_AVAILABLE:
                    with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                        response = client.get(url)
                        response.raise_for_status()
                        content = response.text
                        content_type = response.headers.get('content-type', '')
                elif REQUESTS_AVAILABLE:
                    response = requests.get(url, timeout=self.timeout, allow_redirects=True)
                    response.raise_for_status()
                    content = response.text
                    content_type = response.headers.get('content-type', '')
                else:
                    return ToolResult(
                        success=False,
                        error="需要安装 httpx 或 requests 库才能使用此工具"
                    )
            except Exception as e:
                return ToolResult(
                    success=False,
                    error=f"获取网页失败: {str(e)}"
                )
            
            # 检查内容长度
            if len(content) > self.max_content_length:
                content = content[:self.max_content_length]
                logger.warning(f"网页内容过长，已截断到 {self.max_content_length} 字符")
            
            # 提取文本
            if 'text/html' in content_type.lower():
                text_content = self._extract_text_from_html(content)
            else:
                text_content = content
            
            # 构建输出
            result_lines = []
            result_lines.append(f"URL: {url}")
            result_lines.append(f"内容类型: {content_type}")
            result_lines.append(f"内容长度: {len(text_content)} 字符")
            result_lines.append("")
            result_lines.append("内容:")
            result_lines.append("")
            result_lines.append(text_content)
            
            result_text = "\n".join(result_lines)
            
            # 检查是否需要截断
            truncated = False
            summary = None
            if len(result_text) > self.max_output_length:
                truncated_result, truncated = self._truncate_data(result_text, self.max_output_length)
                summary = f"网页内容已截断（原始长度: {len(text_content)} 字符）"
                result_text = truncated_result
            
            return ToolResult(
                success=True,
                data=result_text,
                truncated=truncated,
                summary=summary
            )
        
        except Exception as e:
            logger.error(f"WebFetchTool error: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"获取网页时发生错误: {str(e)}"
            )
