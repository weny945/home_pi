"""
语音活动检测模块
Voice Activity Detection (VAD) Module
"""
from .detector import VADDetector
from .funasr_vad import FunASRVADDetector

__all__ = ["VADDetector", "FunASRVADDetector"]
