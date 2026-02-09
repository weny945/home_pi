"""
FunASR VAD 检测器实现
FunASR Voice Activity Detection Detector Implementation

使用 FunASR 的内置 VAD 功能进行语音活动检测
"""
import logging
from pathlib import Path
from typing import List, Tuple
import numpy as np

try:
    from funasr import AutoModel
    FUNASR_AVAILABLE = True
    FUNASR_ERROR = None
except ImportError as e:
    FUNASR_AVAILABLE = False
    FUNASR_ERROR = str(e)

from .detector import VADDetector

logger = logging.getLogger(__name__)


class FunASRVADDetector(VADDetector):
    """FunASR VAD 检测器实现"""

    def __init__(
        self,
        vad_model: str = "fsmn-vad",
        device: str = "cpu",
        load_model: bool = True,  # 改为默认加载模型
        **kwargs
    ):
        """
        初始化 FunASR VAD 检测器

        Args:
            vad_model: VAD 模型名称
            device: 运行设备 ("cpu" 或 "cuda:0")
            load_model: 是否立即加载模型（默认 True）
            **kwargs: 其他参数
        """
        if not FUNASR_AVAILABLE:
            error_msg = f"FunASR 依赖未满足: {FUNASR_ERROR}"
            if "torchaudio" in FUNASR_ERROR:
                error_msg += "\n请安装: pip install torchaudio"
            else:
                error_msg += "\n请安装: pip install funasr"
            raise ImportError(error_msg)

        self._vad_model = vad_model
        self._device = device
        self._model_kwargs = kwargs

        self._model = None
        self._ready = False

        if load_model:
            self.load_model()

        logger.info(f"FunASR VAD 检测器已创建 (模型: {vad_model})")

    def load_model(self) -> None:
        """加载 VAD 模型"""
        if self._ready:
            logger.warning("VAD 模型已加载")
            return

        try:
            logger.info(f"正在加载 VAD 模型: {self._vad_model}...")

            self._model = AutoModel(
                model=self._vad_model,
                device=self._device,
                **self._model_kwargs
            )

            self._ready = True
            logger.info("✅ VAD 模型加载成功")

        except Exception as e:
            logger.error(f"VAD 模型加载失败: {e}")
            self._ready = False
            raise

    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        """
        检测音频块是否包含语音

        Args:
            audio_chunk: 音频数据 (16kHz, 16bit, 单声道)

        Returns:
            bool: True 表示包含语音
        """
        if not self._ready:
            logger.warning("VAD 模型未加载，返回 False")
            return False

        try:
            # 使用 FunASR VAD 模型检测
            result = self._model.generate(
                input=audio_chunk,
                cache={},
            )

            # FunASR VAD 返回检测结果
            if result and len(result) > 0:
                # 检查是否检测到语音
                # 具体返回格式可能需要根据实际 FunASR VAD 模型调整
                is_speech = result[0].get("is_speech", False)
                return is_speech

            return False

        except Exception as e:
            logger.error(f"VAD 检测失败: {e}")
            return False

    def process_stream(self, audio_chunks: List[np.ndarray]) -> List[bool]:
        """
        处理音频流，返回每个块的语音检测结果

        Args:
            audio_chunks: 音频块列表

        Returns:
            List[bool]: 每个块是否包含语音
        """
        results = []
        for chunk in audio_chunks:
            results.append(self.is_speech(chunk))
        return results

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
            List[tuple[int, int]]: 语音段列表 (start_ms, end_ms)
        """
        if not self._ready:
            logger.warning("VAD 模型未加载")
            return []

        try:
            # 将音频分割成小块处理
            chunk_size = sample_rate // 10  # 100ms 块
            chunks = []
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i + chunk_size]
                if len(chunk) < chunk_size:
                    # 最后一块，补零
                    chunk = np.pad(chunk, (0, chunk_size - len(chunk)))
                chunks.append(chunk)

            # 检测每个块
            speech_flags = self.process_stream(chunks)

            # 将连续的语音块合并成语音段
            segments = []
            in_speech = False
            start_idx = 0

            for i, is_speech in enumerate(speech_flags):
                if is_speech and not in_speech:
                    # 语音开始
                    in_speech = True
                    start_idx = i
                elif not is_speech and in_speech:
                    # 语音结束
                    in_speech = False
                    end_idx = i
                    # 转换为毫秒
                    start_ms = start_idx * 100
                    end_ms = end_idx * 100
                    segments.append((start_ms, end_ms))

            # 处理结尾的语音段
            if in_speech:
                end_ms = len(chunks) * 100
                start_ms = start_idx * 100
                segments.append((start_ms, end_ms))

            return segments

        except Exception as e:
            logger.error(f"语音段检测失败: {e}")
            return []

    def is_ready(self) -> bool:
        """检测器是否已就绪"""
        return self._ready and self._model is not None
