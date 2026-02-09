"""
麦克风抽象层
Microphone Abstract Layer
"""
from abc import ABC, abstractmethod
import numpy as np


class MicrophoneInput(ABC):
    """麦克风输入抽象基类"""

    @abstractmethod
    def start_stream(self) -> None:
        """启动音频流"""
        pass

    @abstractmethod
    def read_chunk(self) -> np.ndarray:
        """
        读取一个音频块

        Returns:
            np.ndarray: 音频数据 (16kHz, 16bit, 单声道)
        """
        pass

    @abstractmethod
    def stop_stream(self) -> None:
        """停止音频流"""
        pass

    @property
    @abstractmethod
    def is_active(self) -> bool:
        """音频流是否激活"""
        pass

    @property
    @abstractmethod
    def sample_rate(self) -> int:
        """采样率"""
        pass

    @property
    @abstractmethod
    def channels(self) -> int:
        """通道数"""
        pass

    @property
    @abstractmethod
    def chunk_size(self) -> int:
        """音频块大小（帧数）"""
        pass
