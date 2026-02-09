"""
唤醒词检测抽象层
Wake Word Detector Abstract Layer
"""
from abc import ABC, abstractmethod
import numpy as np


class WakeWordDetector(ABC):
    """唤醒词检测器抽象基类"""

    @abstractmethod
    def process_frame(self, audio_frame: np.ndarray) -> bool:
        """
        处理音频帧，检测是否包含唤醒词

        Args:
            audio_frame: 音频数据 (16kHz, 16bit, 单声道)

        Returns:
            bool: 是否检测到唤醒词
        """
        pass

    @abstractmethod
    def load_model(self, model_path: str) -> None:
        """
        加载唤醒词模型

        Args:
            model_path: 模型文件路径
        """
        pass

    @property
    @abstractmethod
    def is_ready(self) -> bool:
        """检测器是否就绪"""
        pass
