"""
语音识别模块
Speech-to-Text Module (STT)
"""
from .engine import STTEngine
from .funasr_engine import FunASRSTTEngine

__all__ = ["STTEngine", "FunASRSTTEngine"]
