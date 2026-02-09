"""
LLM 对话生成模块
LLM Dialogue Generation Module

Phase 1.3: 使用千问 API 实现对话生成
"""
from .engine import LLMEngine
from .qwen_engine import QwenLLMEngine

__all__ = [
    "LLMEngine",
    "QwenLLMEngine",
]
