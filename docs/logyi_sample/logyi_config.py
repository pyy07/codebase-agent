"""
日志易配置模块
"""
import os
import logging
from typing import Optional
from pathlib import Path

# 尝试加载 python-dotenv 以支持 .env 文件
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

logger = logging.getLogger(__name__)

# 自动加载 .env 文件（如果存在）
if DOTENV_AVAILABLE:
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"[LogyiConfig] 已加载 .env 文件: {env_path}")
    else:
        logger.debug(f"[LogyiConfig] .env 文件不存在: {env_path}")
else:
    logger.warning("[LogyiConfig] python-dotenv 未安装，无法加载 .env 文件。建议安装: pip install python-dotenv")


class LogyiConfig:
    """
    日志易配置类
    管理日志易 API 的配置信息
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        apikey: Optional[str] = None,
        appname: Optional[str] = None
    ):
        """
        初始化配置
        
        Args:
            base_url: 日志易 API 基础 URL
            username: 用户名
            apikey: API Key
            appname: 应用名称（如果设置，查询时会自动添加 appname:xxx 过滤）
        """
        self.base_url = base_url or os.getenv("LOGYI_BASE_URL", "")
        self.username = username or os.getenv("LOGYI_USERNAME", "")
        self.apikey = apikey or os.getenv("LOGYI_APIKEY", "")
        self.appname = appname or os.getenv("LOGYI_APPNAME", "")
    
    def is_configured(self) -> bool:
        """
        检查配置是否完整
        
        Returns:
            如果配置完整返回 True，否则返回 False
        """
        return bool(self.apikey and self.username)
    
    def get_auth_headers(self, include_content_type: bool = False) -> dict:
        """
        获取认证头
        
        Args:
            include_content_type: 是否包含 Content-Type 头 (GET请求通常不需要)
        
        Returns:
            认证头字典
        """
        # 检查配置是否完整
        if not self.is_configured():
            raise ValueError("日志易认证信息未配置,请配置 LOGYI_APIKEY 和 LOGYI_USERNAME")
        
        # 按照原来的实现方式：使用 Authorization 头
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Authorization": f"apikey {self.apikey}"
        }
        
        if include_content_type:
            headers["Content-Type"] = "application/json"
        
        return headers


# 全局配置实例
logyi_config = LogyiConfig()

