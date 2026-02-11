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
        # 检查是否是 ALSA 设备名称格式（如 plughw:0,0, hw:0,0, default）
        alsa_formats = ['plughw:', 'hw:', 'default', 'sysdefault']
        is_alsa_device = any(self._device_name.startswith(fmt) for fmt in alsa_formats)

        if is_alsa_device:
            logger.info(f"使用 ALSA 设备名称: {self._device_name}")
            # 不设置 device_index，稍后会通过其他方式打开
            self._device_index = None
            return

        # 否则通过设备名称查找索引
        audio = pyaudio.PyAudio()

        for i in range(audio.get_device_count()):
            info = audio.get_device_info_by_index(i)
            if self._device_name in info.get('name', ''):
                self._device_index = i
                logger.info(f"找到音频设备: {info['name']} (索引: {i})")
                break

        audio.terminate()

        if self._device_index is None:
            logger.warning(f"未找到设备 '{self._device_name}'，将尝试使用 ALSA 默认设备")
            # 尝试使用 ALSA 默认设备作为后备方案
            self._device_name = "plughw:0,0"

    def start_stream(self) -> None:
        """启动音频流"""
        if self._stream is not None:
            logger.warning("音频流已启动")
            return

        self._audio = pyaudio.PyAudio()

        try:
            # 检查是否是 ALSA 设备名称
            alsa_formats = ['plughw:', 'hw:', 'default', 'sysdefault']
            is_alsa_device = any(self._device_name.startswith(fmt) for fmt in alsa_formats)

            if is_alsa_device and self._device_index is None:
                # 使用 ALSA 设备名称
                # PyAudio 在 Linux 上默认使用 ALSA，可以直接通过名称打开
                logger.info(f"尝试打开 ALSA 设备: {self._device_name}")

                # 尝试查找匹配的设备索引
                found_device = None
                for i in range(self._audio.get_device_count()):
                    info = self._audio.get_device_info_by_index(i)
                    device_name_lower = info.get('name', '').lower()

                    # 尝试多种匹配方式
                    if (self._device_name in device_name_lower or
                        'respeaker' in device_name_lower or
                        'arrayuac10' in device_name_lower):
                        # 检查是否有输入通道（某些设备报告为 0 但实际可用）
                        logger.info(f"找到候选设备: {info['name']} (索引: {i})")
                        found_device = i
                        break

                if found_device is not None:
                    # 使用找到的设备
                    self._stream = self._audio.open(
                        format=self._format,
                        channels=self._channels,
                        rate=self._sample_rate,
                        input=True,
                        input_device_index=found_device,
                        frames_per_buffer=self._chunk_size,
                        stream_callback=None
                    )
                else:
                    # 没找到匹配设备，尝试使用默认设备
                    logger.warning("未找到匹配的 ALSA 设备，尝试使用默认输入设备")
                    self._stream = self._audio.open(
                        format=self._format,
                        channels=self._channels,
                        rate=self._sample_rate,
                        input=True,
                        input_device_index=None,  # 使用默认设备
                        frames_per_buffer=self._chunk_size,
                        stream_callback=None
                    )
            else:
                # 使用设备索引
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
            logger.error("请尝试以下解决方法:")
            logger.error("  1. 检查麦克风连接: lsusb | grep -i mic")
            logger.error("  2. 检查 ALSA 设备: arecord -l")
            logger.error("  3. 尝试录音测试: arecord -D plughw:0,0 -d 3 -f cd test.wav")
            logger.error("  4. 检查 PyAudio 设备: python tests/manual/diagnose_audio_devices.py")
            logger.error("  5. 重启系统: sudo reboot")
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
