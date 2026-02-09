"""唤醒词检测模块"""
from .detector import WakeWordDetector
from .openwakeword_detector import OpenWakeWordDetector

__all__ = ["WakeWordDetector", "OpenWakeWordDetector"]
