"""
TTS 引擎抽象接口
TTS Engine Abstract Interface
"""
from abc import ABC, abstractmethod
from typing import Optional
import numpy as np


class TTSEngine(ABC):
    """TTS 引擎抽象基类"""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        speaker_id: Optional[int] = None
    ) -> np.ndarray:
        """
        合成语音

        Args:
            text: 要合成的文本
            speaker_id: 说话人ID (可选)

        Returns:
            np.ndarray: 音频数据 (16kHz, 16bit, 单声道)
        """
        pass

    @abstractmethod
    def get_sample_rate(self) -> int:
        """
        获取采样率

        Returns:
            int: 采样率 (16000 Hz)
        """
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """
        是否已就绪（模型已加载）

        Returns:
            bool: 是否就绪
        """
        pass

    @abstractmethod
    def get_model_info(self) -> dict:
        """
        获取模型信息

        Returns:
            dict: 模型信息
        """
        pass

    @abstractmethod
    def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        speaker_id: Optional[int] = None
    ) -> None:
        """
        合成语音并保存到文件

        Args:
            text: 要合成的文本
            output_path: 输出文件路径
            speaker_id: 说话人ID (可选)
        """
        pass
