"""
阿里云千问 TTS 引擎（远程，非流式 HTTP API）
Qwen TTS Engine (Remote, Non-streaming HTTP API)
"""
import logging
import requests
import numpy as np
import base64
import io
import tempfile
import os
from typing import Optional

from .engine import TTSEngine

logger = logging.getLogger(__name__)


class QwenTTSEngine(TTSEngine):
    """
    阿里云千问 TTS 引擎

    支持的提供商：
    - Dashscope: 阿里云千问 TTS（推荐）
    - OpenAI: OpenAI TTS API（备选）
    """

    def __init__(self, config: dict):
        """
        初始化千问 TTS 引擎

        Args:
            config: 配置字典，格式如下：
                {
                    "provider": "dashscope",  # 或 "openai"
                    "dashscope": {
                        "api_key": "sk-xxx",
                        "endpoint": "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/generation",
                        "model": "qwen3-tts-flash",
                        "format": "mp3",
                        "sample_rate": 24000,
                        "volume": 50,
                        "voice": "zhixiaobai",
                        "rate": 1.0,
                        "pitch": 1.0,
                        "timeout": 30,
                        "retry": 2
                    },
                    "openai": {
                        "api_key": "sk-xxx",
                        "endpoint": "https://api.openai.com/v1/audio/speech",
                        "model": "tts-1",
                        "voice": "alloy",
                        "timeout": 30
                    }
                }
        """
        self._config = config
        self._provider = config.get("provider", "dashscope")

        # Dashscope 配置
        if self._provider == "dashscope":
            dashscope_config = config.get("dashscope", {})
            self._api_key = dashscope_config.get("api_key")

            # 支持环境变量替换
            if self._api_key and self._api_key.startswith("${"):
                env_var = self._api_key[2:-1]  # 移除 ${}
                self._api_key = os.environ.get(env_var, "")

            self._endpoint = dashscope_config.get(
                "endpoint",
                "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/generation"
            )
            self._model = dashscope_config.get("model", "qwen3-tts-flash")
            self._format = dashscope_config.get("format", "mp3")
            self._sample_rate = dashscope_config.get("sample_rate", 24000)
            self._volume = dashscope_config.get("volume", 50)
            self._voice = dashscope_config.get("voice", "zhixiaobai")
            self._rate = dashscope_config.get("rate", 1.0)
            self._pitch = dashscope_config.get("pitch", 1.0)
            self._timeout = dashscope_config.get("timeout", 30)
            self._retry = dashscope_config.get("retry", 2)

        # OpenAI 配置（备选）
        elif self._provider == "openai":
            openai_config = config.get("openai", {})
            self._api_key = openai_config.get("api_key")

            # 支持环境变量替换
            if self._api_key and self._api_key.startswith("${"):
                env_var = self._api_key[2:-1]
                self._api_key = os.environ.get(env_var, "")

            self._endpoint = openai_config.get(
                "endpoint",
                "https://api.openai.com/v1/audio/speech"
            )
            self._model = openai_config.get("model", "tts-1")
            self._voice = openai_config.get("voice", "alloy")
            self._timeout = openai_config.get("timeout", 30)
            self._format = "mp3"
            self._sample_rate = 24000

        else:
            raise ValueError(f"不支持的 TTS 提供商: {self._provider}")

        logger.info("=" * 60)
        logger.info("千问 TTS 引擎初始化")
        logger.info("=" * 60)
        logger.info(f"  提供商: {self._provider}")
        logger.info(f"  模型: {self._model}")
        logger.info(f"  发音人: {self._voice}")
        logger.info(f"  采样率: {self._sample_rate} Hz")
        logger.info(f"  格式: {self._format}")
        logger.info("=" * 60)

    def synthesize(
        self,
        text: str,
        speaker_id: Optional[int] = None
    ) -> np.ndarray:
        """
        合成语音

        Args:
            text: 输入文本
            speaker_id: 说话人ID（千问 TTS 不支持，忽略）

        Returns:
            np.ndarray: 音频数据 (int16, 单声道, 24000Hz)
        """
        if self._provider == "dashscope":
            return self._synthesize_dashscope(text)
        elif self._provider == "openai":
            return self._synthesize_openai(text)
        else:
            raise ValueError(f"不支持的 TTS 提供商: {self._provider}")

    def _synthesize_dashscope(self, text: str) -> np.ndarray:
        """使用 Dashscope API 合成语音"""
        if not self._api_key:
            raise Exception("千问 TTS API key 未配置，请设置 DASHSCOPE_API_KEY 环境变量")

        # 构建请求
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self._model,
            "input": {
                "text": text
            },
            "parameters": {
                "text_type": "PlainText",
                "sample_rate": self._sample_rate,
                "format": self._format,
                "volume": self._volume,
                "rate": self._rate,
                "pitch": self._pitch,
                "voice": self._voice
            }
        }

        # 发送请求（带重试）
        for attempt in range(self._retry + 1):
            try:
                logger.debug(f"千问 TTS 请求 (尝试 {attempt + 1}/{self._retry + 1}): {text[:30]}...")

                response = requests.post(
                    self._endpoint,
                    headers=headers,
                    json=payload,
                    timeout=self._timeout
                )

                response.raise_for_status()
                result = response.json()

                # 检查响应状态
                if result.get("output", {}).get("task_status") == "SUCCESS":
                    # 获取音频数据
                    audio_b64 = result["output"]["audio"]
                    audio_bytes = base64.b64decode(audio_b64)

                    # 转换为 numpy array
                    return self._decode_audio(audio_bytes, self._format)
                else:
                    error_msg = result.get("output", {}).get("message", "未知错误")
                    error_code = result.get("code", "")
                    raise Exception(f"千问 TTS 失败: {error_msg} (code: {error_code})")

            except requests.exceptions.Timeout:
                logger.warning(f"千问 TTS 请求超时 (尝试 {attempt + 1})")
                if attempt < self._retry:
                    continue
                else:
                    raise Exception(f"千问 TTS 请求超时（{self._timeout}秒）")

            except requests.exceptions.ConnectionError as e:
                logger.warning(f"千问 TTS 网络错误: {e}")
                if attempt < self._retry:
                    continue
                else:
                    raise Exception(f"千问 TTS 网络连接失败: {e}")

            except Exception as e:
                logger.error(f"千问 TTS 请求失败: {e}")
                raise

    def _synthesize_openai(self, text: str) -> np.ndarray:
        """使用 OpenAI API 合成语音"""
        if not self._api_key:
            raise Exception("OpenAI API key 未配置，请设置 OPENAI_API_KEY 环境变量")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self._model,
            "input": text,
            "voice": self._voice,
            "response_format": "mp3"
        }

        response = requests.post(
            self._endpoint,
            headers=headers,
            json=payload,
            timeout=self._timeout
        )

        response.raise_for_status()
        audio_bytes = response.content

        # 转换为 numpy array
        return self._decode_audio(audio_bytes, "mp3")

    def _decode_audio(self, audio_bytes: bytes, format: str) -> np.ndarray:
        """
        解码音频数据

        Args:
            audio_bytes: 音频字节流
            format: 音频格式 (mp3, wav)

        Returns:
            np.ndarray: 音频数据 (int16, 单声道)
        """
        try:
            from pydub import AudioSegment
        except ImportError:
            raise ImportError(
                "需要安装 pydub 库来解码音频: pip install pydub"
            )

        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as f:
            temp_path = f.name
            f.write(audio_bytes)

        try:
            # 使用 pydub 加载音频
            audio = AudioSegment.from_file(temp_path, format=format)

            # 转换为目标格式
            audio = audio.set_frame_rate(self._sample_rate)
            audio = audio.set_channels(1)
            audio = audio.set_sample_width(2)  # 16-bit

            # 转换为 numpy array
            samples = np.array(audio.get_array_of_samples(), dtype=np.int16)

            return samples

        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def get_sample_rate(self) -> int:
        """获取采样率"""
        return self._sample_rate

    def is_ready(self) -> bool:
        """
        检查引擎是否已就绪

        Returns:
            bool: 是否就绪
        """
        if not self._api_key:
            logger.warning("千问 TTS API key 未配置")
            return False

        # 简单检测网络连通性
        try:
            if self._provider == "dashscope":
                response = requests.get(
                    "https://dashscope.aliyuncs.com",
                    timeout=5
                )
            elif self._provider == "openai":
                response = requests.get(
                    "https://api.openai.com",
                    timeout=5
                )
            return True
        except:
            logger.warning("千问 TTS 网络不可达")
            return False

    def get_model_info(self) -> dict:
        """
        获取模型信息

        Returns:
            dict: 模型信息
        """
        return {
            "engine_type": "QwenTTS",
            "provider": self._provider,
            "model": self._model,
            "voice": self._voice,
            "sample_rate": self._sample_rate,
            "format": self._format,
            "api_endpoint": self._endpoint,
            "ready": self.is_ready()
        }

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
            speaker_id: 说话人ID（可选）
        """
        audio_data = self.synthesize(text, speaker_id)

        # 保存为 WAV 文件
        import wave
        with wave.open(output_path, 'wb') as wav_file:
            wav_file.setnchannels(1)  # 单声道
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self._sample_rate)
            wav_file.writeframes(audio_data.tobytes())

        logger.info(f"音频已保存到: {output_path}")

    def check_health(self) -> bool:
        """
        检查引擎健康状态

        Returns:
            bool: 是否健康
        """
        return self.is_ready()
