"""日志配置模块"""
import logging
import sys
from typing import Optional


def get_log_level(level_name: str) -> int:
    """
    将日志级别名称转换为 logging 级别常量
    
    Args:
        level_name: 日志级别名称（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    
    Returns:
        logging 级别常量
    """
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return level_map.get(level_name.upper(), logging.INFO)


def setup_logger(
    name: str = "codebase_driven_agent",
    level: Optional[int] = None,
    level_name: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    配置日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别（整数），如果提供则优先使用
        level_name: 日志级别名称（字符串），如果 level 未提供则使用此参数
        format_string: 日志格式字符串
    
    Returns:
        配置好的日志记录器
    """
    # 确定日志级别
    if level is None:
        if level_name:
            level = get_log_level(level_name)
        else:
            # 尝试从配置中读取
            try:
                from codebase_driven_agent.config import settings
                level = get_log_level(settings.log_level)
            except:
                level = logging.INFO
    
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 禁用日志传播，避免重复打印（父 logger 不应该处理子 logger 的消息）
    logger.propagate = False
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    formatter = logging.Formatter(format_string)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


# 默认日志记录器（从配置读取级别）
def get_default_logger() -> logging.Logger:
    """获取默认日志记录器，从配置读取日志级别"""
    try:
        from codebase_driven_agent.config import settings
        return setup_logger(level_name=settings.log_level)
    except:
        return setup_logger()


logger = get_default_logger()

