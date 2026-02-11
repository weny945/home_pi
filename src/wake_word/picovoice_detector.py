"""
Picovoice Porcupine 唤醒词检测实现
Picovoice Porcupine Wake Word Detector Implementation

使用 Porcupine 引擎进行高性能唤醒词检测
"""
import logging
from pathlib import Path
from typing import Optional
import numpy as np

try:
    import pvporcupine
    PVPORCUPINE_AVAILABLE = True
except ImportError:
    PVPORCUPINE_AVAILABLE = False
    pvporcupine = None

from .detector import WakeWordDetector

logger = logging.getLogger(__name__)


class PicovoiceDetector(WakeWordDetector):
    """
    Picovoice Porcupine 唤醒词检测器

    特点：
    - 高性能，低延迟
    - 支持自定义唤醒词模型
    - 适合嵌入式设备（树莓派）
    """

    def __init__(
        self,
        model_path: str = None,
        keyword_path: str = None,
        sensitivity: float = 0.5,
        access_key: Optional[str] = None
    ):
        """
        初始化 Picovoice Porcupine 检测器

        Args:
            model_path: Porcupine 模型文件路径 (.pv)
            keyword_path: 唤醒词模型文件路径 (.ppn)
            sensitivity: 检测灵敏度 (0.0-1.0)
            access_key: Picovoice API 密钥（用于访问预训练模型）
        """
        if not PVPORCUPINE_AVAILABLE:
            raise ImportError(
                "请先安装 pvporcupine: pip install pvporcupine\n"
                "树莓派 ARM64: pip install pvporcupine-arm64"
            )

        self._model_path = model_path
        self._keyword_path = keyword_path
        self._sensitivity = sensitivity
        self._access_key = access_key

        self._porcupine = None
        self._ready = False
        self._warning_shown = False

        # 加载模型
        if keyword_path and Path(keyword_path).exists():
            logger.info(f"加载自定义唤醒词模型: {keyword_path}")
            self._load_custom_model(keyword_path, model_path)
        else:
            logger.warning("未找到唤醒词模型文件")
            if keyword_path:
                logger.error(f"模型路径: {keyword_path}")
            logger.error("请提供正确的 .ppn 文件路径")
            raise FileNotFoundError(f"唤醒词模型不存在: {keyword_path}")

    def _load_custom_model(self, keyword_path: str, model_path: Optional[str] = None) -> None:
        """
        加载自定义唤醒词模型

        Args:
            keyword_path: 唤醒词 .ppn 文件路径
            model_path: Porcupine 模型 .pv 文件路径（可选）
        """
        try:
            # 初始化 Porcupine
            kwargs = {
                "keyword_paths": [keyword_path],
                "sensitivities": [self._sensitivity],
            }

            # 如果提供了模型文件路径，优先使用
            if model_path and Path(model_path).exists():
                kwargs["model_path"] = model_path
                logger.info(f"使用自定义模型: {model_path}")
            else:
                # 使用默认的树莓派模型（英文，可能与中文唤醒词不匹配）
                logger.warning("⚠️  未指定模型文件，使用默认模型")
                logger.warning("⚠️  中文唤醒词需要中文模型文件")

            # 使用官网训练的唤醒词需要 Access Key
            if self._access_key:
                kwargs["access_key"] = self._access_key
                logger.info("使用 Picovoice Access Key 验证")
            else:
                logger.warning("⚠️  未提供 Access Key")
                logger.warning("官网训练的唤醒词需要 Access Key")
                logger.warning("获取方式: https://console.picovoice.ai/")

            # 创建 Porcupine 实例
            self._porcupine = pvporcupine.create(**kwargs)

            self._ready = True
            self._warning_shown = False

            logger.info("✅ Picovoice Porcupine 唤醒词模型加载成功")
            logger.info(f"  采样率: {self._porcupine.sample_rate} Hz")
            logger.info(f"  帧大小: {self._porcupine.frame_length} 采样点")
            logger.info(f"  灵敏度: {self._sensitivity}")

        except Exception as e:
            logger.error(f"加载 Picovoice 模型失败: {e}")
            self._ready = False
            raise

    def load_model(self, model_path: str) -> None:
        """
        加载唤醒词模型（兼容接口）

        Args:
            model_path: 唤醒词模型文件路径 (.ppn)
        """
        logger.info(f"加载唤醒词模型: {model_path}")
        self._load_custom_model(model_path, self._model_path)

    def process_frame(self, audio_frame: np.ndarray) -> bool:
        """
        处理音频帧，检测唤醒词

        Args:
            audio_frame: 音频数据 (16kHz, 16bit, 单声道)
                       必须匹配 frame_length 大小

        Returns:
            bool: 是否检测到唤醒词
        """
        if not self._ready or self._porcupine is None:
            if not self._warning_shown:
                logger.warning("检测器未就绪，将无法检测唤醒词")
                self._warning_shown = True
            return False

        try:
            # 确保音频数据格式正确
            if audio_frame.dtype != np.int16:
                audio_frame = audio_frame.astype(np.int16)

            # 检查音频帧大小
            expected_length = self._porcupine.frame_length
            if len(audio_frame) != expected_length:
                # 音频帧大小不匹配，需要处理
                # 方案1: 截断
                if len(audio_frame) > expected_length:
                    audio_frame = audio_frame[:expected_length]
                # 方案2: 填充（用零填充）
                else:
                    padded = np.zeros(expected_length, dtype=np.int16)
                    padded[:len(audio_frame)] = audio_frame
                    audio_frame = padded

            # 检测唤醒词
            keyword_index = self._porcupine.process(audio_frame)

            # keyword_index >= 0 表示检测到唤醒词
            if keyword_index >= 0:
                logger.info("✅ 检测到唤醒词")
                return True

            return False

        except Exception as e:
            logger.error(f"检测唤醒词失败: {e}")
            return False

    @property
    def is_ready(self) -> bool:
        """检测器是否就绪"""
        return self._ready and self._porcupine is not None

    @property
    def frame_length(self) -> int:
        """获取所需的音频帧大小"""
        if self._porcupine:
            return self._porcupine.frame_length
        return 512  # 默认值

    @property
    def sample_rate(self) -> int:
        """获取采样率"""
        if self._porcupine:
            return self._porcupine.sample_rate
        return 16000  # 默认值

    def __del__(self):
        """析构函数，释放资源"""
        if self._porcupine is not None:
            self._porcupine.delete()
