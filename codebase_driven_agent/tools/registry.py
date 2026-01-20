"""Tool 动态注册机制"""
import importlib
import threading
from typing import List, Dict, Optional, Type
from codebase_driven_agent.tools.base import BaseCodebaseTool
from codebase_driven_agent.utils.logger import setup_logger

logger = setup_logger("codebase_driven_agent.tools.registry")


class ToolRegistry:
    """Tool 注册表（支持动态注册）"""
    
    def __init__(self):
        self._tools: Dict[str, Type[BaseCodebaseTool]] = {}
        self._tool_instances: Dict[str, BaseCodebaseTool] = {}
        self._lock = threading.Lock()
        self._enabled_tools: set = set()  # 启用的工具名称集合
    
    def register(
        self,
        tool_class: Type[BaseCodebaseTool],
        enabled: bool = True,
        auto_init: bool = True,
    ) -> bool:
        """
        注册工具类
        
        Args:
            tool_class: 工具类（继承 BaseCodebaseTool）
            enabled: 是否默认启用
            auto_init: 是否自动初始化实例
        
        Returns:
            是否注册成功
        """
        if not issubclass(tool_class, BaseCodebaseTool):
            logger.error(f"Tool {tool_class.__name__} must inherit from BaseCodebaseTool")
            return False
        
        tool_name = tool_class.name if hasattr(tool_class, 'name') else tool_class.__name__
        
        with self._lock:
            self._tools[tool_name] = tool_class
            
            if enabled:
                self._enabled_tools.add(tool_name)
            
            # 自动初始化实例
            if auto_init and enabled:
                try:
                    instance = tool_class()
                    self._tool_instances[tool_name] = instance
                    logger.info(f"Registered and initialized tool: {tool_name}")
                except Exception as e:
                    logger.warning(f"Failed to initialize tool {tool_name}: {str(e)}")
                    if tool_name in self._enabled_tools:
                        self._enabled_tools.remove(tool_name)
            else:
                logger.info(f"Registered tool class: {tool_name} (not initialized)")
        
        return True
    
    def unregister(self, tool_name: str) -> bool:
        """
        注销工具
        
        Args:
            tool_name: 工具名称
        
        Returns:
            是否注销成功
        """
        with self._lock:
            if tool_name in self._tools:
                del self._tools[tool_name]
                if tool_name in self._tool_instances:
                    del self._tool_instances[tool_name]
                if tool_name in self._enabled_tools:
                    self._enabled_tools.remove(tool_name)
                logger.info(f"Unregistered tool: {tool_name}")
                return True
            return False
    
    def enable_tool(self, tool_name: str) -> bool:
        """
        启用工具
        
        Args:
            tool_name: 工具名称
        
        Returns:
            是否启用成功
        """
        with self._lock:
            if tool_name not in self._tools:
                logger.warning(f"Tool {tool_name} not found")
                return False
            
            if tool_name not in self._enabled_tools:
                self._enabled_tools.add(tool_name)
                
                # 如果还没有实例，创建实例
                if tool_name not in self._tool_instances:
                    try:
                        tool_class = self._tools[tool_name]
                        instance = tool_class()
                        self._tool_instances[tool_name] = instance
                        logger.info(f"Enabled and initialized tool: {tool_name}")
                    except Exception as e:
                        logger.warning(f"Failed to initialize tool {tool_name}: {str(e)}")
                        self._enabled_tools.remove(tool_name)
                        return False
                else:
                    logger.info(f"Enabled tool: {tool_name}")
            
            return True
    
    def disable_tool(self, tool_name: str) -> bool:
        """
        禁用工具
        
        Args:
            tool_name: 工具名称
        
        Returns:
            是否禁用成功
        """
        with self._lock:
            if tool_name in self._enabled_tools:
                self._enabled_tools.remove(tool_name)
                logger.info(f"Disabled tool: {tool_name}")
                return True
            return False
    
    def get_tool(self, tool_name: str, lock_held: bool = False) -> Optional[BaseCodebaseTool]:
        """
        获取工具实例
        
        Args:
            tool_name: 工具名称
        
        Returns:
            工具实例，如果不存在或未启用则返回 None
        """
        logger.info(f"get_tool() called for: {tool_name}, lock_held={lock_held}")
        
        # 如果锁已经持有，直接执行逻辑
        if lock_held:
            if tool_name not in self._enabled_tools:
                logger.debug(f"Tool {tool_name} not in enabled_tools")
                return None
            
            if tool_name in self._tool_instances:
                logger.debug(f"Returning existing instance for {tool_name}")
                return self._tool_instances[tool_name]
            
            # 如果工具已启用但没有实例，尝试创建
            if tool_name in self._tools:
                logger.debug(f"Creating new instance for {tool_name}")
                try:
                    tool_class = self._tools[tool_name]
                    instance = tool_class()
                    self._tool_instances[tool_name] = instance
                    logger.debug(f"Successfully created instance for {tool_name}")
                    return instance
                except Exception as e:
                    logger.error(f"Failed to create tool instance {tool_name}: {str(e)}", exc_info=True)
                    return None
            
            logger.warning(f"Tool {tool_name} not found in _tools")
            return None
        
        # 如果没有持有锁，尝试获取锁
        logger.debug(f"Attempting to acquire lock for get_tool({tool_name})...")
        try:
            import threading
            lock_acquired = self._lock.acquire(timeout=5.0)
            if not lock_acquired:
                logger.error(f"Failed to acquire lock in get_tool({tool_name}) within 5 seconds!")
                return None
            
            try:
                if tool_name not in self._enabled_tools:
                    logger.debug(f"Tool {tool_name} not in enabled_tools")
                    return None
                
                if tool_name in self._tool_instances:
                    logger.debug(f"Returning existing instance for {tool_name}")
                    return self._tool_instances[tool_name]
                
                # 如果工具已启用但没有实例，尝试创建
                if tool_name in self._tools:
                    logger.debug(f"Creating new instance for {tool_name}")
                    try:
                        tool_class = self._tools[tool_name]
                        instance = tool_class()
                        self._tool_instances[tool_name] = instance
                        logger.debug(f"Successfully created instance for {tool_name}")
                        return instance
                    except Exception as e:
                        logger.error(f"Failed to create tool instance {tool_name}: {str(e)}", exc_info=True)
                        return None
                
                logger.warning(f"Tool {tool_name} not found in _tools")
                return None
            finally:
                self._lock.release()
                logger.debug(f"Lock released in get_tool({tool_name})")
        except Exception as e:
            logger.error(f"Error in get_tool({tool_name}): {str(e)}", exc_info=True)
            if self._lock.locked():
                self._lock.release()
            return None
    
    def get_all_tools(self) -> List[BaseCodebaseTool]:
        """
        获取所有启用的工具实例
        
        Returns:
            工具实例列表
        """
        logger.info(f"get_all_tools() called, enabled_tools: {self._enabled_tools}")
        logger.info(f"Attempting to acquire lock for get_all_tools()...")
        try:
            # 使用超时避免死锁
            import threading
            lock_acquired = self._lock.acquire(timeout=5.0)
            if not lock_acquired:
                logger.error("Failed to acquire lock in get_all_tools() within 5 seconds!")
                return []
            
            try:
                tools = []
                logger.info(f"Lock acquired, getting tools for {len(self._enabled_tools)} enabled tools")
                for tool_name in self._enabled_tools:
                    logger.info(f"Getting tool: {tool_name}")
                    tool = self.get_tool(tool_name, lock_held=True)  # 传递 lock_held=True 避免死锁
                    if tool:
                        tools.append(tool)
                        logger.info(f"Added tool: {tool_name}")
                    else:
                        logger.warning(f"Failed to get tool: {tool_name}")
                logger.info(f"get_all_tools() returning {len(tools)} tools")
                return tools
            finally:
                self._lock.release()
                logger.debug("Lock released in get_all_tools()")
        except Exception as e:
            logger.error(f"Error in get_all_tools(): {str(e)}", exc_info=True)
            if self._lock.locked():
                self._lock.release()
            return []
    
    def list_tools(self) -> Dict[str, Dict]:
        """
        列出所有注册的工具
        
        Returns:
            工具信息字典
        """
        with self._lock:
            tools_info = {}
            for tool_name, tool_class in self._tools.items():
                tools_info[tool_name] = {
                    "name": tool_name,
                    "class": tool_class.__name__,
                    "enabled": tool_name in self._enabled_tools,
                    "initialized": tool_name in self._tool_instances,
                    "description": getattr(tool_class, 'description', ''),
                }
            return tools_info
    
    def load_from_module(self, module_path: str, tool_class_name: str) -> bool:
        """
        从模块动态加载工具
        
        Args:
            module_path: 模块路径（如 "codebase_driven_agent.tools.your_tool"）
            tool_class_name: 工具类名称（如 "YourTool"）
        
        Returns:
            是否加载成功
        """
        try:
            module = importlib.import_module(module_path)
            tool_class = getattr(module, tool_class_name)
            
            if not issubclass(tool_class, BaseCodebaseTool):
                logger.error(f"{tool_class_name} is not a subclass of BaseCodebaseTool")
                return False
            
            return self.register(tool_class)
        
        except ImportError as e:
            logger.error(f"Failed to import module {module_path}: {str(e)}")
            return False
        except AttributeError as e:
            logger.error(f"Tool class {tool_class_name} not found in {module_path}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Failed to load tool from {module_path}.{tool_class_name}: {str(e)}")
            return False


# 全局注册表实例
_registry: Optional[ToolRegistry] = None
_registry_lock = threading.Lock()


def get_tool_registry() -> ToolRegistry:
    """获取工具注册表实例（单例模式）"""
    global _registry
    
    logger.debug("get_tool_registry() called")
    if _registry is None:
        logger.debug("Registry is None, creating new instance...")
        with _registry_lock:
            logger.debug("Acquired registry lock")
            if _registry is None:
                logger.info("Creating new ToolRegistry instance...")
                _registry = ToolRegistry()
                logger.info("ToolRegistry created, registering default tools...")
                # 注册默认工具
                _register_default_tools(_registry)
                logger.info("Default tools registered")
            else:
                logger.debug("Registry was created by another thread")
        logger.debug("Released registry lock")
    else:
        logger.debug("Using existing registry instance")
    
    logger.debug("Returning registry instance")
    return _registry


def _register_default_tools(registry: ToolRegistry):
    """注册默认工具"""
    # 核心工具
    try:
        from codebase_driven_agent.tools.code_tool import CodeTool
        registry.register(CodeTool, enabled=True)
    except Exception as e:
        logger.warning(f"Failed to register CodeTool: {str(e)}")
    
    try:
        from codebase_driven_agent.tools.log_tool import LogTool
        registry.register(LogTool, enabled=True)
    except Exception as e:
        logger.warning(f"Failed to register LogTool: {str(e)}")
    
    try:
        from codebase_driven_agent.tools.database_tool import DatabaseTool
        from codebase_driven_agent.config import settings
        # 只有在配置了数据库 URL 时才注册 DatabaseTool
        if settings.database_url:
            registry.register(DatabaseTool, enabled=True)
        else:
            logger.debug("Database URL not configured, skipping DatabaseTool registration")
    except Exception as e:
        logger.warning(f"Failed to register DatabaseTool: {str(e)}")
    
    # 内置工具集
    try:
        from codebase_driven_agent.tools.read_tool import ReadTool
        registry.register(ReadTool, enabled=True)
    except Exception as e:
        logger.warning(f"Failed to register ReadTool: {str(e)}")
    
    try:
        from codebase_driven_agent.tools.glob_tool import GlobTool
        registry.register(GlobTool, enabled=True)
    except Exception as e:
        logger.warning(f"Failed to register GlobTool: {str(e)}")
    
    try:
        from codebase_driven_agent.tools.grep_tool import GrepTool
        registry.register(GrepTool, enabled=True)
    except Exception as e:
        logger.warning(f"Failed to register GrepTool: {str(e)}")
    
    try:
        from codebase_driven_agent.tools.bash_tool import BashTool
        registry.register(BashTool, enabled=True)
    except Exception as e:
        logger.warning(f"Failed to register BashTool: {str(e)}")
    
    try:
        from codebase_driven_agent.tools.webfetch_tool import WebFetchTool
        registry.register(WebFetchTool, enabled=True)
    except Exception as e:
        logger.warning(f"Failed to register WebFetchTool: {str(e)}")
    
    try:
        from codebase_driven_agent.tools.websearch_tool import WebSearchTool
        from codebase_driven_agent.config import settings
        # 只有在配置了搜索 API Key 时才注册 WebSearchTool
        exa_key = getattr(settings, 'exa_api_key', None)
        serper_key = getattr(settings, 'serper_api_key', None)
        if exa_key or serper_key:
            registry.register(WebSearchTool, enabled=True)
        else:
            logger.debug("Search API Key not configured, skipping WebSearchTool registration")
    except Exception as e:
        logger.warning(f"Failed to register WebSearchTool: {str(e)}")

