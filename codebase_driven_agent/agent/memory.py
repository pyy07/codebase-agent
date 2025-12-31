"""Agent Memory 机制"""
from typing import List, Dict
from langchain_core.chat_history import InMemoryChatMessageHistory


class AgentMemory:
    """Agent 内存管理
    
    注意：使用 InMemoryChatMessageHistory 替代已弃用的 ConversationBufferMemory
    以兼容 LangChain 1.0+ 的新 API
    """
    
    def __init__(self, memory_type: str = "buffer"):
        """
        初始化 Agent Memory
        
        Args:
            memory_type: 内存类型，"buffer" 或 "summary"
        """
        self.memory_type = memory_type
        # 使用新的 InMemoryChatMessageHistory API (LangChain 1.0+)
        self.memory = InMemoryChatMessageHistory()
        self.conversation_history: List[Dict] = []
    
    def add_user_message(self, message: str):
        """添加用户消息"""
        self.memory.add_user_message(message)
        self.conversation_history.append({
            "type": "user",
            "content": message
        })
    
    def add_ai_message(self, message: str):
        """添加 AI 消息"""
        self.memory.add_ai_message(message)
        self.conversation_history.append({
            "type": "ai",
            "content": message
        })
    
    def get_memory_variables(self) -> Dict:
        """获取内存变量"""
        # ChatMessageHistory 返回消息列表，而不是字典
        messages = self.memory.messages
        return {
            "chat_history": messages,
            "history": messages
        }
    
    def clear(self):
        """清空内存"""
        self.memory.clear()
        self.conversation_history = []
    
    def get_history(self) -> List[Dict]:
        """获取对话历史"""
        return self.conversation_history.copy()
    
    def get_memory_instance(self) -> InMemoryChatMessageHistory:
        """获取 LangChain Memory 实例"""
        return self.memory

