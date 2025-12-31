"""配置管理模块"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # API 配置
    api_key: Optional[str] = None
    api_key_header: str = "X-API-Key"
    
    # LLM 配置
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None  # 自定义 OpenAI API Base URL（支持其他供应商）
    anthropic_api_key: Optional[str] = None
    llm_provider: str = "openai"  # "openai" 或 "anthropic" 或 "custom"
    llm_base_url: Optional[str] = None  # 自定义 LLM API Base URL（用于其他供应商）
    llm_api_key: Optional[str] = None  # 通用 LLM API Key（用于其他供应商）
    llm_model: str = "gpt-4"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4000
    
    # 日志易配置
    logyi_base_url: Optional[str] = None
    logyi_username: Optional[str] = None
    logyi_apikey: Optional[str] = None
    logyi_appname: Optional[str] = None
    
    # 文件日志配置
    log_file_base_path: Optional[str] = None
    log_query_type: str = "logyi"  # "logyi" 或 "file"
    
    # 数据库配置
    database_url: Optional[str] = None
    
    # Agent 配置
    agent_max_iterations: int = 15
    agent_max_execution_time: int = 300  # 秒
    
    # 任务管理配置
    task_storage_type: str = "memory"  # "memory" 或 "redis"
    redis_url: Optional[str] = None
    task_ttl: int = 3600  # 任务过期时间（秒）
    max_tasks: int = 1000  # 最大任务数
    
    # 代码仓库配置
    code_repo_path: Optional[str] = None
    
    # 缓存配置
    cache_ttl: int = 3600  # 缓存过期时间（秒），默认 1 小时
    cache_max_size: int = 1000  # 最大缓存条目数
    cache_enabled: bool = True  # 是否启用缓存
    
    # 日志配置
    log_level: str = "INFO"  # 日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL


settings = Settings()

