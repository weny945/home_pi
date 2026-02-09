"""
Piper TTS 引擎实现
Piper TTS Engine Implementation
"""
import logging
from pathlib import Path
from typing import Optional
import numpy as np

# ========================================
# 修复 piper-tts 1.4.0 缺少 espeakbridge.so 的问题
# 使用 piper_phonemize 替代 EspeakPhonemizer
# ========================================
try:
    import piper_phonemize
    PIPER_PHONEMIZE_AVAILABLE = True
except ImportError:
    PIPER_PHONEMIZE_AVAILABLE = False
    logging.warning("piper_phonemize 未安装，将尝试使用原生 espeakbridge")

if PIPER_PHONEMIZE_AVAILABLE:
    # 创建一个替代的 EspeakPhonemizer，使用 piper_phonemize
    class _FallbackEspeakPhonemizer:
        """替代的 EspeakPhonemizer，使用 piper_phonemize"""

        def __init__(self, espeak_data_dir: Optional[str] = None):
            """初始化

            Args:
                espeak_data_dir: espeak 数据目录（如果不存在则使用 None，让 piper_phonemize 使用内置数据）
            """
            # 检查目录是否存在，不存在则置 None
            # piper_phonemize 内置了 espeak-ng-data，data_path=None 时会自动使用
            if espeak_data_dir:
                path = Path(espeak_data_dir)
                if not path.exists():
                    logging.warning(f"espeak 数据目录不存在: {espeak_data_dir}，将使用 piper_phonemize 内置数据")
                    espeak_data_dir = None

            self._espeak_data_dir = espeak_data_dir

        def phonemize(self, voice: str, text: str) -> list[list[str]]:
            """将文本转换为音素

            Args:
                voice: espeak 语音（如 "zh"）
                text: 输入文本

            Returns:
                list[list[str]]: 音素列表，每个元素是一个句子的音素
            """
            # piper_phonemize.phonemize_espeak(text, voice, data_path)
            # 注意参数顺序是 (text, voice, data_path)，与 EspeakPhonemizer.phonemize(voice, text) 不同
            # data_path=None 时，piper_phonemize 会使用内置的 espeak-ng-data
            return piper_phonemize.phonemize_espeak(text, voice, self._espeak_data_dir)

    # Monkey patch：必须在导入 piper.voice 之前执行
    # 需要同时 patch 两个地方：
    # 1. piper.phonemize_espeak.EspeakPhonemizer（用于新导入）
    # 2. piper.voice.EspeakPhonemizer（如果已经导入）
    import piper.phonemize_espeak as phonemize_espeak_module
    phonemize_espeak_module.EspeakPhonemizer = _FallbackEspeakPhonemizer

    # 如果 piper.voice 已经导入，也需要 patch
    import sys
    if 'piper.voice' in sys.modules:
        import piper.voice as voice_module
        voice_module.EspeakPhonemizer = _FallbackEspeakPhonemizer
        logging.info("✅ 已 patch piper.voice.EspeakPhonemizer")

    logging.info("✅ 已使用 piper_phonemize 替代 espeakbridge")

# 现在导入 PiperVoice（会使用我们 patch 后的版本）
from piper.voice import PiperVoice
from piper.config import SynthesisConfig

from .engine import TTSEngine

logger = logging.getLogger(__name__)


class PiperTTSEngine(TTSEngine):
    """Piper TTS 引擎实现"""

    def __init__(
        self,
        model_path: str,
        config_path: Optional[str] = None,
        use_cuda: bool = False,
        length_scale: float = 1.0,
        noise_scale: float = 0.667,
        noise_w_scale: float = 0.8,
        sentence_silence: float = 0.0,
        text_enhancement: Optional[dict] = None,
        load_model: bool = True
    ):
        """
        初始化 Piper TTS 引擎

        Args:
            model_path: ONNX 模型路径 (.onnx)
            config_path: 配置文件路径 (.json)，默认为 model_path + ".json"
            use_cuda: 是否使用 CUDA (GPU)
            length_scale: 语速缩放 (1.0 = 正常, <1.0 = 更快, >1.0 = 更慢)
            noise_scale: 音色随机性/情感波动 (0.5-1.0)
            noise_w_scale: 韵律噪声/语气变化 (0.6-1.0)
            sentence_silence: 句间停顿时长（秒）
            text_enhancement: 文本增强配置（支持自定义停顿标记）
            load_model: 是否立即加载模型
        """
        self._model_path = Path(model_path)

        # 智能检测配置文件路径
        if config_path:
            self._config_path = Path(config_path)
        else:
            # 尝试 .onnx.json 后缀
            onnx_json_path = self._model_path.with_suffix('.onnx.json')
            if onnx_json_path.exists():
                self._config_path = onnx_json_path
            else:
                # 回退到 .json 后缀
                self._config_path = self._model_path.with_suffix('.json')

        # 合成参数
        self._synthesis_config = SynthesisConfig(
            length_scale=length_scale,
            noise_scale=noise_scale,
            noise_w_scale=noise_w_scale
        )
        self._length_scale = length_scale
        self._noise_scale = noise_scale
        self._noise_w_scale = noise_w_scale

        # 句间停顿配置（秒）
        self._sentence_silence = sentence_silence

        # 文本增强配置
        self._text_enhancement = text_enhancement or {}

        self._use_cuda = use_cuda
        self._voice: Optional[PiperVoice] = None
        self._sample_rate = 22050  # Piper 默认采样率

        logger.info(f"Piper TTS 配置: length_scale={length_scale}, "
                   f"noise_scale={noise_scale}, noise_w_scale={noise_w_scale}, "
                   f"sentence_silence={sentence_silence}s")

        if not self._model_path.exists():
            raise FileNotFoundError(f"模型文件不存在: {self._model_path}")

        if not self._config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self._config_path}")

        if load_model:
            self.load_model()

    def load_model(self) -> None:
        """加载 Piper 模型"""
        if self._voice is not None:
            logger.info("模型已加载")
            return

        try:
            logger.info(f"正在加载 Piper 模型: {self._model_path.name}")

            # 加载 Piper Voice
            self._voice = PiperVoice.load(
                model_path=self._model_path,
                config_path=self._config_path,
                use_cuda=self._use_cuda
            )

            logger.info("✅ Piper 模型加载成功")

        except Exception as e:
            logger.error(f"加载 Piper 模型失败: {e}")
            raise

    def synthesize(
        self,
        text: str,
        speaker_id: Optional[int] = None
    ) -> np.ndarray:
        """
        合成语音

        Args:
            text: 要合成的文本
            speaker_id: 说话人ID (可选，暂不支持)

        Returns:
            np.ndarray: 音频数据 (22050Hz, 16bit, 单声道)
        """
        if self._voice is None:
            raise RuntimeError("模型未加载，请先调用 load_model()")

        try:
            # **文本预处理：修复常见发音问题 + 支持自定义停顿**
            processed_text = self._preprocess_text(text)

            logger.debug(f"原始文本: {text}")
            logger.debug(f"处理后文本: {processed_text}")

            # 使用 PiperVoice.synthesize 方法
            # 返回的是 AudioChunk 的生成器
            audio_chunks = []
            for chunk in self._voice.synthesize(
                text=processed_text,
                syn_config=self._synthesis_config
            ):
                audio_chunks.append(chunk.audio_int16_array)

            # 合并所有音频块
            if audio_chunks:
                audio_data = np.concatenate(audio_chunks)
            else:
                # 如果没有音频块，返回空数组
                audio_data = np.array([], dtype=np.int16)

            # **添加句间停顿（sentence_silence）**
            if self._sentence_silence > 0:
                audio_data = self._add_sentence_silence(audio_data)

            return audio_data

        except Exception as e:
            logger.error(f"语音合成失败: {e}")
            raise

    def _preprocess_text(self, text: str) -> str:
        """
        文本预处理：修复常见发音问题 + 支持自定义停顿标记

        Args:
            text: 原始文本

        Returns:
            str: 处理后的文本
        """
        if not text:
            return text

        processed = text
        import re

        # === 方案2: 自定义停顿标记支持 ===
        # 检查是否启用文本增强
        enhancement_config = self._text_enhancement
        if enhancement_config.get("enabled", True):
            pause_config = enhancement_config.get("pause_to_punctuation", {})

            if pause_config.get("enabled", True) and enhancement_config.get("pause_marks_enabled", True):
                # 解析 [PAUSE:X.X] 标记
                pause_pattern = r'\[PAUSE:(\d+(?:\.\d+)?)\]'

                def replace_pause_with_punctuation(match):
                    """将停顿标记转换为标点符号"""
                    try:
                        duration = float(match.group(1))

                        # 根据配置获取标点符号
                        commas_per_second = pause_config.get("commas_per_second", 2)
                        num_commas = max(1, int(duration * commas_per_second))

                        # 使用逗号模拟停顿
                        return "，" * num_commas
                    except:
                        return match.group(0)  # 解析失败，保留原标记

                # 替换所有停顿标记
                processed = re.sub(pause_pattern, replace_pause_with_punctuation, processed)

                # 统计替换了多少个停顿标记
                pause_count = len(re.findall(pause_pattern, text))
                if pause_count > 0:
                    logger.debug(f"解析了 {pause_count} 个自定义停顿标记")

        # === 原有的文本修复逻辑 ===

        # **修复1: 句尾的"的"字发音问题**
        if enhancement_config.get("fix_final_particles", True):
            # 检查是否以"的"结尾
            if processed.endswith("的"):
                # 在"的"后面添加逗号，创造自然的停顿
                processed = processed + "，"
                logger.debug(f"句尾'的'字后添加逗号")

        # **修复2: 句尾波浪线处理**
        if enhancement_config.get("remove_wavy_tilde", True):
            # 移除所有波浪线（全角～和半角~）
            processed = re.sub(r'[~～]+', '', processed)
            if '~' in text or '～' in text:
                logger.debug(f"移除波浪线，避免发音异常")

        # **修复3: 其他常见的句尾助词**
        if enhancement_config.get("fix_final_particles", True):
            # "了"、"着"、"过"等句尾助词也可能有类似问题
            sentence_final_particles = ["了", "着", "过"]
            for particle in sentence_final_particles:
                if processed.endswith(particle) and not processed.endswith(f"{particle}，"):
                    processed = processed + "，"
                    logger.debug(f"句尾'{particle}'字后添加逗号")
                    break

        # **修复4: 连续的标点符号简化**
        # "！！！" → "！"
        processed = re.sub(r'[。]+', '。', processed)  # 多个句号
        processed = re.sub(r'[！]+', '！', processed)  # 多个感叹号
        processed = re.sub(r'[？]+', '？', processed)  # 多个问号

        # **修复5: 确保句子有适当的结尾标点**
        # 如果没有任何结尾标点，添加句号
        if len(processed) > 0 and processed[-1] not in ["。", "！", "？", "，", "、", "；", "："]:
            processed = processed + "。"
            logger.debug(f"添加句尾标点")

        return processed

    def _add_sentence_silence(self, audio_data: np.ndarray) -> np.ndarray:
        """
        在音频末尾添加静音（句间停顿）

        Args:
            audio_data: 原始音频数据

        Returns:
            np.ndarray: 添加静音后的音频数据
        """
        if self._sentence_silence <= 0:
            return audio_data

        # 计算需要添加的静音采样点数
        silence_samples = int(self._sentence_silence * self._sample_rate)

        # 创建静音数组（全零）
        silence = np.zeros(silence_samples, dtype=np.int16)

        # 将静音附加到音频末尾
        audio_with_silence = np.concatenate([audio_data, silence])

        logger.debug(f"添加了 {self._sentence_silence}s 的句间停顿 ({silence_samples} 采样点)")

        return audio_with_silence

    def _resample(
        self,
        audio: np.ndarray,
        orig_sr: int,
        target_sr: int
    ) -> np.ndarray:
        """
        重采样音频

        Args:
            audio: 原始音频
            orig_sr: 原始采样率
            target_sr: 目标采样率

        Returns:
            np.ndarray: 重采样后的音频
        """
        from scipy import signal

        number_of_samples = round(len(audio) * float(target_sr) / orig_sr)
        resampled = signal.resample(audio, number_of_samples)
        return resampled.astype(np.int16)

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
        audio_data = self.synthesize(text, speaker_id)

        # 保存为 WAV 文件
        from scipy.io import wavfile

        wavfile.write(output_path, self._sample_rate, audio_data)
        logger.info(f"音频已保存: {output_path}")

    def get_sample_rate(self) -> int:
        """
        获取采样率

        Returns:
            int: 采样率 (22050 Hz)
        """
        return self._sample_rate

    def is_ready(self) -> bool:
        """
        是否已就绪（模型已加载）

        Returns:
            bool: 是否就绪
        """
        return self._voice is not None

    def get_model_info(self) -> dict:
        """
        获取模型信息

        Returns:
            dict: 模型信息
        """
        return {
            "model_path": str(self._model_path),
            "config_path": str(self._config_path),
            "use_cuda": self._use_cuda,
            "sample_rate": self._sample_rate,
            "synthesis_config": {
                "length_scale": self._synthesis_config.length_scale,
                "noise_scale": self._synthesis_config.noise_scale,
                "noise_w_scale": self._synthesis_config.noise_w_scale,
            },
            "is_loaded": self.is_ready(),
        }

    def set_synthesis_config(
        self,
        length_scale: Optional[float] = None,
        noise_scale: Optional[float] = None,
        noise_w_scale: Optional[float] = None
    ) -> None:
        """
        更新合成配置

        Args:
            length_scale: 语速缩放
            noise_scale: 音频噪声控制
            noise_w_scale: 韵律噪声控制
        """
        # 更新内部参数
        if length_scale is not None:
            self._length_scale = length_scale
        if noise_scale is not None:
            self._noise_scale = noise_scale
        if noise_w_scale is not None:
            self._noise_w_scale = noise_w_scale

        # 更新 synthesis_config
        if length_scale is not None:
            self._synthesis_config.length_scale = length_scale
        if noise_scale is not None:
            self._synthesis_config.noise_scale = noise_scale
        if noise_w_scale is not None:
            self._synthesis_config.noise_w_scale = noise_w_scale

        logger.debug(f"合成配置已更新: {self._synthesis_config}")

    def __del__(self):
        """析构函数"""
        # 清理模型资源
        self._voice = None
