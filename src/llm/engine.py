"""
LLM 引擎抽象接口
LLM Engine Abstract Interface

Phase 1.3: 对话生成模块
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class LLMEngine(ABC):
    """
    LLM 引擎抽象基类

    定义了对话生成引擎的通用接口
    """

    @abstractmethod
    def generate(
        self,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> str:
        """
        生成回复

        Args:
            prompt: 用户输入的提示词
            conversation_history: 对话历史，格式为 [{"role": "user", "content": "..."}, ...]
            **kwargs: 其他参数（如 temperature, max_tokens 等）

        Returns:
            str: 生成的回复文本
        """
        pass

    @abstractmethod
    def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        对话接口（带完整返回信息）

        Args:
            message: 用户消息
            conversation_history: 对话历史
            **kwargs: 其他参数

        Returns:
            dict: 包含回复和其他信息的字典
            {
                "reply": str,           # 回复文本
                "usage": dict,          # 使用情况（tokens）
                "model": str,           # 使用的模型
                "finish_reason": str,   # 结束原因
            }
        """
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """
        检查引擎是否就绪

        Returns:
            bool: 是否就绪
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息

        Returns:
            dict: 模型信息
            {
                "name": str,        # 模型名称
                "provider": str,    # 提供商
                "version": str,     # 版本
            }
        """
        pass

    @abstractmethod
    def reset_conversation(self) -> None:
        """
        重置对话上下文

        清空对话历史，开始新的对话
        """
        pass

    @abstractmethod
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """
        获取当前对话历史

        Returns:
            list: 对话历史
        """
        pass
