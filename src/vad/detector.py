"""
VAD 检测器抽象接口
Voice Activity Detection Detector Abstract Interface
"""
import logging
from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np

logger = logging.getLogger(__name__)


class VADDetector(ABC):
    """VAD 检测器抽象基类"""

    @abstractmethod
    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        """
        检测音频块是否包含语音

        Args:
            audio_chunk: 音频数据 (16kHz, 16bit, 单声道)

        Returns:
            bool: True 表示包含语音，False 表示静音
        """
        pass

    @abstractmethod
    def process_stream(
        self,
        audio_chunks: List[np.ndarray]
    ) -> List[bool]:
        """
        处理音频流，返回每个块的语音检测结果

        Args:
            audio_chunks: 音频块列表

        Returns:
            List[bool]: 每个块是否包含语音
        """
        pass

    @abstractmethod
    def detect_speech_segments(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000
    ) -> List[tuple[int, int]]:
        """
        检测音频中的语音段

        Args:
            audio_data: 完整音频数据
            sample_rate: 采样率

        Returns:
            List[tuple[int, int]]: 语音段列表，每个元组为 (start_ms, end_ms)
        """
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """检测器是否已就绪"""
        pass

    def get_speech_duration(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000
    ) -> float:
        """
        计算音频中语音的总时长

        Args:
            audio_data: 音频数据
            sample_rate: 采样率

        Returns:
            float: 语音时长（秒）
        """
        segments = self.detect_speech_segments(audio_data, sample_rate)
        total_duration = sum(end - start for start, end in segments) / 1000.0
        return total_duration
