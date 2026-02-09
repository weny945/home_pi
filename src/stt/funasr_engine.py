"""
FunASR STT 引擎实现
FunASR Speech-to-Text Engine Implementation

使用 FunASR SenseVoiceSmall 模型进行离线语音识别
"""
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any
import numpy as np

try:
    from funasr import AutoModel
    FUNASR_AVAILABLE = True
    FUNASR_ERROR = None
except ImportError as e:
    FUNASR_AVAILABLE = False
    FUNASR_ERROR = str(e)

from .engine import STTEngine

logger = logging.getLogger(__name__)

# 配置 jieba 缓存目录到持久化位置，避免每次重启重新构建字典
# 通过修改 tempfile.tempdir 让 jieba 使用持久化缓存目录
_JIEBA_CACHE_DIR = Path("./models/jieba_cache")
_JIEBA_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 创建一个持久化的 tmp 目录用于 jieba 缓存
_PERSISTENT_TMP = _JIEBA_CACHE_DIR / "tmp"
_PERSISTENT_TMP.mkdir(parents=True, exist_ok=True)

# 在导入 jieba 之前设置 tempdir（会影响后续导入的 jieba）
# 注意：这需要在导入 funasr 之前设置，因为 funasr 内部会导入 jieba
tempfile.tempdir = str(_PERSISTENT_TMP)

logger.info(f"jieba 持久化缓存目录: {_JIEBA_CACHE_DIR}")


class FunASRSTTEngine(STTEngine):
    """FunASR STT 引擎实现"""

    def __init__(
        self,
        model_name: str = "iic/SenseVoiceSmall",
        device: str = "cpu",
        load_model: bool = True,  # 改为默认加载模型
        vad_model: str = "fsmn-vad",
        punc_model: str = "ct-punc",
        **kwargs
    ):
        """
        初始化 FunASR STT 引擎

        Args:
            model_name: 模型名称 (默认: SenseVoiceSmall)
            device: 运行设备 ("cpu" 或 "cuda:0")
            load_model: 是否立即加载模型（默认 True）
            vad_model: VAD 模型名称（用于语音活动检测）
            punc_model: 标点模型名称（用于加标点）
            **kwargs: 其他 FunASR 参数
        """
        if not FUNASR_AVAILABLE:
            error_msg = f"FunASR 依赖未满足: {FUNASR_ERROR}"
            if "torchaudio" in FUNASR_ERROR:
                error_msg += "\n请安装: pip install torchaudio"
            else:
                error_msg += "\n请安装: pip install funasr"
            raise ImportError(error_msg)

        self._model_name = model_name
        self._device = device
        self._vad_model = vad_model
        self._punc_model = punc_model
        self._model_kwargs = kwargs

        self._model = None
        self._ready = False

        if load_model:
            self.load_model()

        logger.info(f"FunASR STT 引擎已创建 (模型: {model_name})")

    def load_model(self) -> None:
        """加载 FunASR 模型"""
        if self._ready:
            logger.warning("模型已加载")
            return

        try:
            logger.info(f"正在加载 FunASR 模型: {self._model_name}...")

            # 使用 FunASR AutoModel 加载模型
            self._model = AutoModel(
                model=self._model_name,
                device=self._device,
                vad_model=self._vad_model,
                punc_model=self._punc_model,
                **self._model_kwargs
            )

            self._ready = True
            logger.info("✅ FunASR 模型加载成功")

        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            self._ready = False
            raise

    def transcribe(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000
    ) -> str:
        """
        转录音频为文本

        P1-3 优化: 支持懒加载，首次调用时自动加载模型

        Args:
            audio_data: 音频数据 (numpy array, 16kHz, 单声道)
                       支持 int16 (会自动转换为 float32) 或 float32
            sample_rate: 采样率 (默认 16000 Hz)

        Returns:
            str: 识别的文本

        Raises:
            RuntimeError: 模型加载失败
        """
        # P1-3 优化: 懒加载 - 首次调用时自动加载模型
        if not self._ready or self._model is None:
            logger.info("⏳ 首次使用 STT，正在加载模型...")
            self.load_model()
            logger.info("✅ 模型加载完成")

        try:
            # 确保音频数据格式正确
            # FunASR 需要浮点类型（float32），范围 [-1.0, 1.0]
            # 注意：即使模型使用 fp16，输入仍需保持 float32
            # torchaudio 的特征提取（fbank）不支持 float16
            if audio_data.dtype == np.int16:
                # 将 int16 转换为 float32 并归一化
                audio_data = audio_data.astype(np.float32) / 32768.0
            elif audio_data.dtype != np.float32:
                # 确保输入是 float32（FunASR 内部会处理 fp16 转换）
                audio_data = audio_data.astype(np.float32)

            # 调用 FunASR 进行识别
            # FunASR 需要音频数据为 numpy array 或文件路径
            result = self._model.generate(
                input=audio_data,
                cache={},
                language="auto",  # 自动检测语言（支持中英文混合）
                use_itn=True,  # 使用逆文本标准化
            )

            # 提取识别文本
            if result and len(result) > 0:
                text = result[0].get("text", "")
                logger.debug(f"识别结果: {text}")
                return text
            else:
                logger.warning("未识别到任何文本")
                return ""

        except Exception as e:
            logger.error(f"语音识别失败: {e}")
            raise

    def transcribe_file(self, audio_file: str) -> str:
        """
        转录音频文件为文本

        P1-3 优化: 支持懒加载

        Args:
            audio_file: 音频文件路径 (WAV 格式)

        Returns:
            str: 识别的文本
        """
        if not Path(audio_file).exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_file}")

        # P1-3 优化: 懒加载
        if not self._ready or self._model is None:
            logger.info("⏳ 首次使用 STT，正在加载模型...")
            self.load_model()
            logger.info("✅ 模型加载完成")

        try:
            # FunASR 支持直接传入文件路径
            result = self._model.generate(
                input=audio_file,
                cache={},
                language="auto",
                use_itn=True,
            )

            if result and len(result) > 0:
                text = result[0].get("text", "")
                logger.debug(f"文件识别结果: {text}")
                return text
            else:
                logger.warning(f"未识别到任何文本 ({audio_file})")
                return ""

        except Exception as e:
            logger.error(f"文件语音识别失败 ({audio_file}): {e}")
            raise

    def is_ready(self) -> bool:
        """引擎是否已就绪"""
        return self._ready and self._model is not None

    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息

        Returns:
            dict: 模型信息字典
        """
        return {
            "model_name": self._model_name,
            "device": self._device,
            "vad_model": self._vad_model,
            "punc_model": self._punc_model,
            "is_ready": self._ready,
            "supported_sample_rate": 16000,
        }

    def get_supported_sample_rate(self) -> int:
        """获取支持的采样率"""
        return 16000

    # P1-3 优化: 添加模型卸载功能
    def unload_model(self) -> None:
        """
        卸载模型以释放内存

        P1-3 优化: 长时间不使用时可调用此方法释放内存
        下次调用 transcribe 时会自动重新加载
        """
        if self._model is not None:
            logger.info("正在卸载 FunASR 模型以释放内存...")
            try:
                # 删除模型引用
                self._model = None
                self._ready = False
                logger.info("✅ 模型已卸载")
            except Exception as e:
                logger.error(f"卸载模型时出错: {e}")
        else:
            logger.warning("模型未加载，无需卸载")

    def reload_model(self) -> None:
        """
        重新加载模型

        P1-3 优化: 用于在卸载后重新加载模型
        """
        logger.info("正在重新加载 FunASR 模型...")
        self._ready = False  # 重置标记，强制重新加载
        self.load_model()
        logger.info("✅ 模型重新加载完成")
