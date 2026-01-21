"""Agent 会话状态管理模块

用于管理暂停的 Agent 执行会话，支持用户交互后的恢复。
"""
import uuid
import time
import threading
from typing import Dict, Optional, Any, TYPE_CHECKING
from datetime import datetime, timedelta

from codebase_driven_agent.utils.logger import setup_logger

if TYPE_CHECKING:
    from codebase_driven_agent.agent.graph_executor import AgentState

logger = setup_logger("codebase_driven_agent.agent.session_manager")


class SessionInfo:
    """会话信息"""
    def __init__(self, request_id: str, state: "AgentState", executor: Any, message_queue: Any):
        self.request_id = request_id
        self.state = state
        self.executor = executor  # GraphExecutor 实例
        self.message_queue = message_queue  # 消息队列
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """检查会话是否过期"""
        elapsed = datetime.now() - self.created_at
        return elapsed > timedelta(minutes=timeout_minutes)


class SessionManager:
    """会话管理器（线程安全）"""
    
    def __init__(self, timeout_minutes: int = 30):
        self._sessions: Dict[str, SessionInfo] = {}
        self._lock = threading.Lock()
        self._timeout_minutes = timeout_minutes
    
    def create_session(
        self, 
        state: "AgentState", 
        executor: Any, 
        message_queue: Any,
        request_id: Optional[str] = None
    ) -> str:
        """创建新会话
        
        Args:
            state: Agent 状态快照
            executor: GraphExecutor 实例
            message_queue: 消息队列
            request_id: 可选的请求 ID（如果不提供则自动生成）
        
        Returns:
            会话的 request_id
        """
        if request_id is None:
            request_id = str(uuid.uuid4())
        
        session = SessionInfo(request_id, state, executor, message_queue)
        
        with self._lock:
            self._sessions[request_id] = session
            logger.info(f"Created session: {request_id}")
        
        return request_id
    
    def get_session(self, request_id: str) -> Optional[SessionInfo]:
        """获取会话信息"""
        with self._lock:
            session = self._sessions.get(request_id)
            if session and session.is_expired(self._timeout_minutes):
                logger.warning(f"Session {request_id} expired, removing")
                del self._sessions[request_id]
                return None
            if session:
                session.last_updated = datetime.now()
            return session
    
    def remove_session(self, request_id: str) -> bool:
        """删除会话"""
        with self._lock:
            if request_id in self._sessions:
                del self._sessions[request_id]
                logger.info(f"Removed session: {request_id}")
                return True
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """清理过期会话，返回清理的数量"""
        with self._lock:
            expired_ids = [
                req_id for req_id, session in self._sessions.items()
                if session.is_expired(self._timeout_minutes)
            ]
            for req_id in expired_ids:
                del self._sessions[req_id]
                logger.info(f"Cleaned up expired session: {req_id}")
            return len(expired_ids)
    
    def get_all_sessions(self) -> Dict[str, SessionInfo]:
        """获取所有会话（用于调试）"""
        with self._lock:
            return dict(self._sessions)


# 全局会话管理器实例
_session_manager = SessionManager()


def get_session_manager() -> SessionManager:
    """获取全局会话管理器实例"""
    return _session_manager
