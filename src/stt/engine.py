"""
STT 引擎抽象接口
Speech-to-Text Engine Abstract Interface
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)


class STTEngine(ABC):
    """STT 引擎抽象基类"""

    @abstractmethod
    def transcribe(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000
    ) -> str:
        """
        转录音频为文本

        Args:
            audio_data: 音频数据 (numpy array, 16kHz, 16bit, 单声道)
            sample_rate: 采样率 (默认 16000 Hz)

        Returns:
            str: 识别的文本

        Raises:
            RuntimeError: 引擎未就绪
            ValueError: 音频数据格式错误
        """
        pass

    @abstractmethod
    def transcribe_file(
        self,
        audio_file: str
    ) -> str:
        """
        转录音频文件为文本

        Args:
            audio_file: 音频文件路径 (WAV 格式)

        Returns:
            str: 识别的文本
        """
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """引擎是否已就绪（模型已加载）"""
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息

        Returns:
            dict: 模型信息字典
        """
        pass

    @abstractmethod
    def load_model(self) -> None:
        """加载模型"""
        pass

    def get_supported_sample_rate(self) -> int:
        """
        获取支持的采样率

        Returns:
            int: 采样率 (Hz)
        """
        return 16000
