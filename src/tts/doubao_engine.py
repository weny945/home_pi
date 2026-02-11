"""
豆包 TTS 引擎（V3 HTTP 单向流式 API）
Doubao TTS Engine Implementation (火山引擎/ByteDance)

API 版本: V3 HTTP 单向流式
文档: https://www.volcengine.com/docs/6561/1598757

特点：
- 支持流式输出，降低首字延迟
- 多种发音人（豆包语音合成模型 1.0/2.0）
- 支持中英混合
- 高质量音频输出（支持 mp3/wav/pcm）
"""
import logging
import os
import base64
import json
import uuid
from typing import Optional

import numpy as np
import requests

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

from .engine import TTSEngine

logger = logging.getLogger(__name__)


class DoubaoTTSEngine(TTSEngine):
    """
    豆包 TTS 引擎（火山引擎 V3 HTTP 单向流式 API）

    特点：
    - V3 HTTP 单向流式 API
    - 支持多种发音人
    - 支持中英混合
    - 高质量音频输出
    """

    # 推荐的发音人配置（豆包语音合成模型 1.0）
    VOICES_V1 = {
        # 女声
        "zh_female_shuangkuaisisi_moon_bigtts": "双快思思-月（女声，推荐）",
        "zh_female_qingxinmeili": "清新美丽女声",
        "zh_female_wenrou": "温柔女声",
        "zh_female_tianmei": "甜美女声",
        "zh_female_huoli": "活力女声",
        "zh_female_qingxin": "清新女声",
        # 男声
        "zh_male_qingchen": "清朗男声（推荐）",
        "zh_male_chunhou": "醇厚男声",
        "zh_male_wenhe": "温和男声",
        "zh_male_huoli": "活力男声",
    }

    # 豆包语音合成模型 2.0 发音人
    VOICES_V2 = {
        # 女声（基础发音人，更通用）
        "zh_female_qingxinmeili": "清新美丽女声（推荐）",
        "zh_female_wenrou": "温柔女声",
        "zh_female_tianmei": "甜美女声",
        "zh_female_huoli": "活力女声",
        # 男声
        "zh_male_wennuan": "温暖男声（推荐）",
        "zh_male_qingchen": "清朗男声",
        "zh_male_chunhou": "醇厚男声",
    }

    # 合并所有发音人
    VOICES = {**VOICES_V1, **VOICES_V2}

    # 资源 ID 配置
    RESOURCE_IDS = {
        "seed-tts-1.0": "豆包语音合成模型 1.0（字符版）",
        "seed-tts-1.0-concurr": "豆包语音合成模型 1.0（并发版）",
        "seed-tts-2.0": "豆包语音合成模型 2.0（字符版）",
        "seed-icl-1.0": "声音复刻 1.0（字符版）",
        "seed-icl-2.0": "声音复刻 2.0",
    }

    # API 配置
    API_ENDPOINT = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"

    def __init__(
        self,
        config: dict
    ):
        """
        初始化豆包 TTS 引擎（V3 HTTP 单向流式 API）

        Args:
            config: 配置字典，包含:
                - api_key: 火山引擎 Access Token
                - app_id: 火山引擎 APP ID
                - resource_id: 资源 ID（如 seed-tts-1.0）
                - uid: 用户唯一标识
                - voice: 发音人
                - format: 音频格式（mp3/wav/pcm）
                - sample_rate: 采样率
                - model: 模型版本（如 seed-tts-1.1）
                - speed: 语速（-50 到 100）
                - volume: 音量（-50 到 100）
        """
        doubao_config = config.get("doubao", {})

        # API 配置（V3 使用 Access Token，不再需要复杂的签名）
        self._access_key = doubao_config.get("api_key") or os.getenv("DOUBAO_ACCESS_KEY")
        self._app_id = doubao_config.get("app_id") or os.getenv("DOUBAO_APP_ID")
        self._resource_id = doubao_config.get("resource_id", "seed-tts-1.0")
        self._uid = doubao_config.get("uid", "default_user")

        # 验证必需参数
        if not self._access_key:
            raise ValueError(
                "豆包 TTS Access Key 未配置。请在 config.yaml 中设置 tts.doubao.api_key "
                "或设置 DOUBAO_ACCESS_KEY 环境变量"
            )
        if not self._app_id:
            raise ValueError(
                "豆包 TTS App ID 未配置。请在 config.yaml 中设置 tts.doubao.app_id "
                "或设置 DOUBAO_APP_ID 环境变量"
            )

        # 验证 resource_id
        if self._resource_id not in self.RESOURCE_IDS:
            logger.warning(f"未知资源 ID: {self._resource_id}，使用默认 seed-tts-1.0")
            self._resource_id = "seed-tts-1.0"

        # 语音参数
        self._voice = doubao_config.get("voice", "zh_female_qingxinmeili")  # 默认使用模型 2.0 发音人
        self._model = doubao_config.get("model", "seed-tts-2.0-expressive")  # 默认使用模型 2.0 expressive

        # 音频参数
        self._format = doubao_config.get("format", "pcm").lower()  # 默认使用 PCM，无需 pydub
        self._sample_rate = doubao_config.get("sample_rate", 24000)
        self._speed = doubao_config.get("speed", 0)  # 语速，0 表示正常
        self._volume = doubao_config.get("volume", 0)  # 音量，0 表示正常

        # 超时和重试
        self._timeout = doubao_config.get("timeout", 30)
        self._retry = doubao_config.get("retry", 1)

        # 验证发音人
        if self._voice not in self.VOICES:
            logger.warning(f"未知发音人: {self._voice}，使用默认发音人")
            self._voice = "zh_female_shuangkuaisisi_moon_bigtts"

        # 创建 session 以支持连接复用（推荐）
        self._session = requests.Session()

        logger.info(f"豆包 TTS 引擎初始化完成 (V3 HTTP 单向流式)")
        logger.info(f"  发音人: {self._voice} ({self.VOICES.get(self._voice, '')})")
        logger.info(f"  资源 ID: {self._resource_id} ({self.RESOURCE_IDS.get(self._resource_id, '')})")
        logger.info(f"  格式: {self._format}, 采样率: {self._sample_rate}Hz")

        # 打印调试信息（脱敏）
        logger.debug(f"  App ID: {self._app_id}")
        logger.debug(f"  Access Key: {self._access_key[:10]}...")

    def synthesize(self, text: str, speaker_id: Optional[str] = None) -> np.ndarray:
        """
        合成语音（V3 HTTP 单向流式 API）

        Args:
            text: 输入文本
            speaker_id: 说话人ID（可选，未使用）

        Returns:
            np.ndarray: 音频数据（int16 PCM）
        """
        if not text:
            logger.warning("输入文本为空")
            return np.array([], dtype=np.int16)

        # 构造 V3 请求体
        payload = {
            "user": {
                "uid": self._uid,
            },
            "req_params": {
                "text": text,
                "speaker": self._voice,
                "audio_params": {
                    "format": self._format,
                    "sample_rate": self._sample_rate,
                },
            },
        }

        # 可选：添加模型版本（仅非空时）
        if self._model and self._model.strip():
            payload["req_params"]["model"] = self._model

        # 可选：添加语速
        if self._speed != 0:
            payload["req_params"]["audio_params"]["speech_rate"] = self._speed

        # 可选：添加音量
        if self._volume != 0:
            payload["req_params"]["audio_params"]["loudness_rate"] = self._volume

        # 构造 V3 请求头
        headers = {
            "X-Api-App-Id": self._app_id,
            "X-Api-Access-Key": self._access_key,
            "X-Api-Resource-Id": self._resource_id,
            "X-Api-Request-Id": str(uuid.uuid4()),
            "Content-Type": "application/json",
        }

        # 发送请求（带重试）
        for attempt in range(self._retry + 1):
            try:
                logger.debug(f"发送豆包 TTS 请求 (V3 HTTP 单向流式, 尝试 {attempt + 1}/{self._retry + 1})")

                # 使用 session 发送流式请求
                response = self._session.post(
                    self.API_ENDPOINT,
                    headers=headers,
                    json=payload,
                    stream=True,
                    timeout=self._timeout
                )

                # 检查响应状态
                if response.status_code != 200:
                    error_msg = f"API 请求失败: {response.status_code}"
                    try:
                        error_detail = response.json()
                        error_msg += f" - {error_detail.get('message', '未知错误')}"
                        # 添加更多调试信息
                        if 'code' in error_detail:
                            error_msg += f" (code: {error_detail['code']})"
                    except:
                        error_msg += f" - {response.text[:200]}"

                    if attempt < self._retry:
                        logger.warning(f"{error_msg}，重试中...")
                        continue
                    else:
                        # 打印请求信息用于调试
                        logger.error(f"请求 URL: {self.API_ENDPOINT}")
                        logger.error(f"Resource ID: {self._resource_id}")
                        logger.error(f"Voice: {self._voice}")
                        logger.error(f"App ID: {self._app_id[:10]}...")
                        raise RuntimeError(error_msg)

                # 解析流式响应
                audio_chunks = []
                for line in response.iter_lines():
                    if not line:
                        continue

                    try:
                        result = json.loads(line)
                        code = result.get("code")

                        # 音频数据（code=0）
                        if code == 0:
                            audio_data_base64 = result.get("data")
                            if audio_data_base64:
                                audio_bytes = base64.b64decode(audio_data_base64)
                                audio_chunks.append(audio_bytes)

                        # 合成结束（code=20000000）
                        elif code == 20000000:
                            logger.debug("豆包 TTS 合成完成")
                            break

                        # 错误
                        else:
                            error_msg = result.get("message", "未知错误")
                            raise RuntimeError(f"豆包 TTS 错误 (code={code}): {error_msg}")

                    except json.JSONDecodeError:
                        logger.warning(f"无法解析 JSON 行: {line[:100]}")
                        continue

                if not audio_chunks:
                    raise RuntimeError("未收到任何音频数据")

                # 合并所有音频块
                combined_audio = b"".join(audio_chunks)

                logger.debug(f"收到音频数据，共 {len(combined_audio)} 字节")

                # 解码音频
                return self._decode_audio(combined_audio)

            except requests.exceptions.Timeout:
                if attempt < self._retry:
                    logger.warning(f"请求超时，重试中...")
                    continue
                else:
                    raise RuntimeError("豆包 TTS 请求超时")

            except Exception as e:
                if attempt < self._retry:
                    logger.warning(f"合成失败: {e}，重试中...")
                    continue
                else:
                    raise

    def _decode_audio(self, audio_bytes: bytes) -> np.ndarray:
        """
        解码音频字节数据

        Args:
            audio_bytes: 音频字节数据

        Returns:
            np.ndarray: 音频数据（int16 PCM）
        """
        if self._format == "pcm":
            # PCM 格式：直接读取为 int16
            audio_data = np.frombuffer(audio_bytes, dtype=np.int16)

        elif self._format == "wav":
            # WAV 格式：跳过 WAV 头（44 字节）
            if len(audio_bytes) > 44:
                audio_data = np.frombuffer(audio_bytes[44:], dtype=np.int16)
            else:
                audio_data = np.frombuffer(audio_bytes, dtype=np.int16)

        elif self._format == "mp3":
            # MP3 格式：使用 pydub 解码
            if not PYDUB_AVAILABLE:
                raise ImportError(
                    "MP3 格式需要 pydub 库。请运行: pip install pydub"
                )

            # 保存到临时文件
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name

            try:
                # 使用 pydub 加载并转换为 PCM
                audio = AudioSegment.from_mp3(temp_path)

                # 转换为目标采样率
                if audio.frame_rate != self._sample_rate:
                    audio = audio.set_frame_rate(self._sample_rate)

                # 转换为单声道
                if audio.channels != 1:
                    audio = audio.set_channels(1)

                # 转换为 numpy 数组
                audio_data = np.array(audio.get_array_of_samples(), dtype=np.int16)

            finally:
                # 删除临时文件
                try:
                    os.unlink(temp_path)
                except:
                    pass

        else:
            raise ValueError(f"不支持的音频格式: {self._format}")

        return audio_data
        """
        解码音频字节数据

        Args:
            audio_bytes: 音频字节数据

        Returns:
            np.ndarray: 音频数据（int16 PCM）
        """
        if self._format == "wav":
            # WAV 格式：直接读取 PCM 数据
            # 跳过 WAV 头（44 字节）
            if len(audio_bytes) > 44:
                audio_data = np.frombuffer(audio_bytes[44:], dtype=np.int16)
            else:
                audio_data = np.frombuffer(audio_bytes, dtype=np.int16)

        elif self._format == "mp3":
            # MP3 格式：使用 pydub 解码
            if not PYDUB_AVAILABLE:
                raise ImportError(
                    "MP3 格式需要 pydub 库。请运行: pip install pydub"
                )

            # 保存到临时文件
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name

            try:
                # 使用 pydub 加载并转换为 WAV
                audio = AudioSegment.from_mp3(temp_path)

                # 转换为目标采样率
                if audio.frame_rate != self._sample_rate:
                    audio = audio.set_frame_rate(self._sample_rate)

                # 转换为单声道
                if audio.channels != 1:
                    audio = audio.set_channels(1)

                # 转换为 numpy 数组
                audio_data = np.array(audio.get_array_of_samples(), dtype=np.int16)

            finally:
                # 删除临时文件
                try:
                    os.unlink(temp_path)
                except:
                    pass

        else:
            raise ValueError(f"不支持的音频格式: {self._format}")

        return audio_data

    def is_ready(self) -> bool:
        """
        检查引擎是否就绪

        Returns:
            bool: 是否就绪
        """
        return bool(self._access_key and self._app_id)

    def get_sample_rate(self) -> int:
        """
        获取采样率

        Returns:
            int: 采样率（Hz）
        """
        return self._sample_rate

    def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        speaker_id: Optional[str] = None
    ) -> None:
        """
        合成语音并保存到文件

        Args:
            text: 要合成的文本
            output_path: 输出文件路径
            speaker_id: 说话人ID（可选）
        """
        audio_data = self.synthesize(text, speaker_id)

        import wave
        with wave.open(output_path, 'wb') as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(self._sample_rate)
            f.writeframes(audio_data.tobytes())

        logger.info(f"音频已保存到: {output_path}")

    def get_model_info(self) -> dict:
        """
        获取模型信息

        Returns:
            dict: 模型信息
        """
        return {
            "name": f"DoubaoTTS V3 ({self._voice})",
            "provider": "火山引擎 (ByteDance)",
            "api_version": "V3 HTTP 单向流式",
            "engine_type": "doubao",
            "model": self._model,
            "voice": self._voice,
            "voice_description": self.VOICES.get(self._voice, ""),
            "resource_id": self._resource_id,
            "resource_id_description": self.RESOURCE_IDS.get(self._resource_id, ""),
            "format": self._format,
            "sample_rate": self._sample_rate,
            "speed": self._speed,
            "volume": self._volume,
        }

    def __del__(self):
        """析构函数，关闭 session"""
        if hasattr(self, '_session'):
            self._session.close()
