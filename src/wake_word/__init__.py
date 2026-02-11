"""唤醒词检测模块"""
from .detector import WakeWordDetector
from .openwakeword_detector import OpenWakeWordDetector
from .picovoice_detector import PicovoiceDetector

__all__ = ["WakeWordDetector", "OpenWakeWordDetector", "PicovoiceDetector"]
