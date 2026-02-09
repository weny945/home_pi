"""
ReSpeaker 4-Mic 音频输入实现
ReSpeaker 4-Mic Audio Input Implementation
"""
import logging
from typing import Optional
import numpy as np
import pyaudio

from .microphone import MicrophoneInput

logger = logging.getLogger(__name__)


class ReSpeakerInput(MicrophoneInput):
    """ReSpeaker 4-Mic 音频输入实现"""

    def __init__(
        self,
        device_name: str = "seeed-4mic-voicecard",
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 512,
        format: int = pyaudio.paInt16,
        device_index: Optional[int] = None,
        input_gain: float = 1.0
    ):
        """
        初始化 ReSpeaker 音频输入

        Args:
            device_name: 输入设备名称（用于查找设备索引，当 device_index 为 None 时使用）
            sample_rate: 采样率 (Hz)
            channels: 通道数（1=单声道, 2=立体声）
            chunk_size: 音频块大小（帧数）
            format: 音频格式（默认 16-bit PCM）
            device_index: 直接指定设备索引（优先级高于 device_name）
            input_gain: 软件增益 (1.0=无增益, >1.0=放大)
        """
        self._device_name = device_name
        self._sample_rate = sample_rate
        self._channels = channels
        self._chunk_size = chunk_size
        self._format = format
        self._input_gain = input_gain

        self._audio: Optional[pyaudio.PyAudio] = None
        self._stream = None
        self._device_index: Optional[int] = device_index

        # 如果没有直接指定设备索引，则通过名称查找
        if self._device_index is None:
            self._find_device()

    def _find_device(self) -> None:
        """查找 ReSpeaker 设备索引"""
        audio = pyaudio.PyAudio()

        for i in range(audio.get_device_count()):
            info = audio.get_device_info_by_index(i)
            if self._device_name in info.get('name', ''):
                self._device_index = i
                logger.info(f"找到音频设备: {info['name']} (索引: {i})")
                break

        audio.terminate()

        if self._device_index is None:
            logger.warning(f"未找到设备 '{self._device_name}'，使用默认设备")
            self._device_index = None  # 使用系统默认

    def start_stream(self) -> None:
        """启动音频流"""
        if self._stream is not None:
            logger.warning("音频流已启动")
            return

        self._audio = pyaudio.PyAudio()

        try:
            self._stream = self._audio.open(
                format=self._format,
                channels=self._channels,
                rate=self._sample_rate,
                input=True,
                input_device_index=self._device_index,
                frames_per_buffer=self._chunk_size,
                stream_callback=None
            )

            logger.info(f"音频流已启动 (设备: {self._device_name or '默认'})")

        except Exception as e:
            logger.error(f"启动音频流失败: {e}")
            self._audio.terminate()
            self._audio = None
            raise

    def read_chunk(self) -> np.ndarray:
        """
        读取一个音频块

        Returns:
            np.ndarray: 音频数据 (int16)

        Raises:
            RuntimeError: 音频流未启动
        """
        if self._stream is None:
            raise RuntimeError("音频流未启动，请先调用 start_stream()")

        try:
            # 读取音频数据
            data = self._stream.read(self._chunk_size, exception_on_overflow=False)

            # 转换为 numpy array
            audio_data = np.frombuffer(data, dtype=np.int16)

            # 应用软件增益
            if self._input_gain != 1.0:
                audio_data = audio_data * self._input_gain
                # 防止溢出，限制在 int16 范围内
                audio_data = np.clip(audio_data, -32768, 32767).astype(np.int16)

            return audio_data

        except Exception as e:
            logger.error(f"读取音频数据失败: {e}")
            raise

    def stop_stream(self) -> None:
        """停止音频流"""
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
                logger.info("音频流已停止")
            except Exception as e:
                logger.error(f"停止音频流失败: {e}")
            finally:
                self._stream = None

        if self._audio is not None:
            try:
                self._audio.terminate()
            except Exception as e:
                logger.error(f"终止 PyAudio 失败: {e}")
            finally:
                self._audio = None

    @property
    def is_active(self) -> bool:
        """音频流是否激活"""
        return self._stream is not None and self._stream.is_active()

    @property
    def sample_rate(self) -> int:
        """采样率"""
        return self._sample_rate

    @property
    def channels(self) -> int:
        """通道数"""
        return self._channels

    @property
    def chunk_size(self) -> int:
        """音频块大小"""
        return self._chunk_size

    def __del__(self):
        """析构函数，确保资源释放"""
        self.stop_stream()
