"""
OpenWakeWord 唤醒词检测实现
OpenWakeWord Detector Implementation
"""
import logging
from pathlib import Path
from typing import Optional
import numpy as np

try:
    import openwakeword
    from openwakeword.model import Model
except ImportError:
    openwakeword = None
    Model = None

from .detector import WakeWordDetector

logger = logging.getLogger(__name__)


class OpenWakeWordDetector(WakeWordDetector):
    """OpenWakeWord 唤醒词检测器实现"""

    def __init__(
        self,
        model_path: str = None,
        threshold: float = 0.5,
        inference_framework: str = "tflite"
    ):
        """
        初始化 OpenWakeWord 检测器

        Args:
            model_path: 模型文件路径 (可选，如果不指定则加载所有预训练模型)
            threshold: 检测阈值 (0-1)
            inference_framework: 推理框架 ("tflite" 或 "onnx")
        """
        if openwakeword is None:
            raise ImportError("请先安装 openwakeword: pip install openwakeword")

        self._model_path = model_path
        self._threshold = threshold
        self._inference_framework = inference_framework

        self._model: Optional[Model] = None
        self._ready = False
        self._warning_shown = False  # 防止重复警告

        # 加载模型
        if model_path is None:
            # 没有指定模型，加载默认 alexa 模型
            logger.info("未指定模型路径，加载默认 alexa 模型...")
            self.load_all_models()
        elif Path(model_path).exists():
            # 指定的模型文件存在，加载自定义模型
            logger.info(f"加载自定义模型: {model_path}")
            self.load_model(model_path)
        else:
            # 指定的模型文件不存在，回退到加载默认 alexa 模型
            logger.warning(f"模型文件不存在: {model_path}")
            logger.info("回退到加载默认 alexa 模型...")
            self.load_all_models()

    def load_all_models(self) -> None:
        """
        加载默认的 alexa 唤醒词模型
        """
        try:
            logger.info("加载默认 alexa 唤醒词模型...")

            # 只加载 alexa 模型
            self._model = Model(
                wakeword_models=["alexa"],
                inference_framework=self._inference_framework
            )

            model_names = list(self._model.models.keys())
            logger.info(f"✅ 成功加载 {len(model_names)} 个唤醒词模型:")
            for name in model_names:
                logger.info(f"  - {name}")

            self._ready = True
            self._warning_shown = False  # 重置警告标志
            logger.info("✅ 唤醒词模型加载成功")
            logger.info("💡 提示: 可以使用唤醒词 'alexa'")

        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            self._ready = False
            raise

    def load_model(self, model_path: str) -> None:
        """
        加载唤醒词模型

        Args:
            model_path: 模型文件路径
        """
        try:
            logger.info(f"加载唤醒词模型: {model_path}")

            self._model = Model(
                wakeword_models=[model_path],
                inference_framework=self._inference_framework
            )

            self._model_path = model_path
            self._ready = True
            self._warning_shown = False  # 重置警告标志

            logger.info("✅ 唤醒词模型加载成功")

        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            self._ready = False
            raise

    def process_frame(self, audio_frame: np.ndarray) -> bool:
        """
        处理音频帧，检测唤醒词

        Args:
            audio_frame: 音频数据 (16kHz, 16bit, 单声道)

        Returns:
            bool: 是否检测到唤醒词
        """
        if not self._ready or self._model is None:
            # 只输出一次警告，避免日志刷屏
            if not self._warning_shown:
                logger.warning("检测器未就绪，将无法检测唤醒词")
                self._warning_shown = True
            return False

        try:
            # 确保音频数据格式正确
            if audio_frame.dtype != np.int16:
                audio_frame = audio_frame.astype(np.int16)

            # 预测
            predictions = self._model.predict(audio_frame)

            # 检查是否有唤醒词被检测到
            for keyword, score in predictions.items():
                if score >= self._threshold:
                    logger.info(f"检测到唤醒词: {keyword} (置信度: {score:.3f})")
                    return True

            return False

        except Exception as e:
            logger.error(f"检测唤醒词失败: {e}")
            return False

    @property
    def is_ready(self) -> bool:
        """检测器是否就绪"""
        return self._ready and self._model is not None
