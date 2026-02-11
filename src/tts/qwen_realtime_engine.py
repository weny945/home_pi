"""
阿里云千问流式 TTS 引擎（WebSocket）
Qwen Realtime Streaming TTS Engine (WebSocket)
"""
import logging
import asyncio
import json
import numpy as np
import os
from typing import Optional

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from .engine import TTSEngine

logger = logging.getLogger(__name__)


class QwenRealtimeEngine(TTSEngine):
    """
    阿里云千问流式 TTS 引擎

    使用 WebSocket 连接实现流式音频生成
    首字延迟 (TTFC) 约 97ms
    """

    def __init__(self, config: dict):
        """
        初始化千问流式 TTS 引擎

        Args:
            config: 配置字典，格式如下：
                {
                    "dashscope": {
                        "api_key": "sk-xxx",
                        "url": "wss://dashscope.aliyuncs.com/api-ws/v1/realtime",
                        "model": "qwen3-tts-flash-realtime",
                        "voice": "zhixiaobai",
                        "format": "pcm",
                        "sample_rate": 24000,
                        "mode": "server_commit",
                        "timeout": 30
                    }
                }
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError(
                "需要安装 websockets 库: pip install websockets"
            )

        dashscope_config = config.get("dashscope", {})
        self._api_key = dashscope_config.get("api_key", "")

        # 支持环境变量替换
        if self._api_key and self._api_key.startswith("${"):
            env_var = self._api_key[2:-1]
            self._api_key = os.environ.get(env_var, "")

        self._url = dashscope_config.get(
            "url",
            "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
        )
        self._model = dashscope_config.get("model", "qwen3-tts-flash-realtime")
        self._voice = dashscope_config.get("voice", "zhixiaobai")
        self._format = dashscope_config.get("format", "pcm")
        self._sample_rate = dashscope_config.get("sample_rate", 24000)
        self._mode = dashscope_config.get("mode", "server_commit")
        self._timeout = dashscope_config.get("timeout", 30)

        logger.info("=" * 60)
        logger.info("千问流式 TTS 引擎初始化")
        logger.info("=" * 60)
        logger.info(f"  模型: {self._model}")
        logger.info(f"  发音人: {self._voice}")
        logger.info(f"  采样率: {self._sample_rate} Hz")
        logger.info(f"  格式: {self._format}")
        logger.info(f"  模式: {self._mode}")
        logger.info("=" * 60)

    def synthesize(
        self,
        text: str,
        speaker_id: Optional[int] = None
    ) -> np.ndarray:
        """
        合成语音（流式）

        Args:
            text: 输入文本
            speaker_id: 说话人ID（不支持，忽略）

        Returns:
            np.ndarray: 音频数据 (int16, 单声道, 24000Hz)
        """
        if not self._api_key:
            raise Exception("千问 TTS API key 未配置，请设置 DASHSCOPE_API_KEY 环境变量")

        # 运行异步流式合成
        return asyncio.run(self._synthesize_async(text))

    async def _synthesize_async(self, text: str) -> np.ndarray:
        """异步流式合成"""
        # 构建控制指令
        control_instruction = {
            "text": text,
            "voice": self._voice,
            "sample_rate": self._sample_rate,
            "format": self._format,
            "mode": self._mode
        }

        logger.debug(f"千问流式 TTS 请求: {text[:30]}...")

        audio_chunks = []

        try:
            # 建立 WebSocket 连接
            async with websockets.connect(
                self._url,
                close_timeout=self._timeout
            ) as websocket:
                # 发送控制指令
                await websocket.send(json.dumps({
                    "header": {
                        "action": "run-task",
                        "task_id": "tts_task",
                        "model": self._model
                    },
                    "payload": {
                        "instruction": control_instruction
                    }
                }))

                # 接收音频数据
                while True:
                    try:
                        message = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=self._timeout
                        )
                    except asyncio.TimeoutError:
                        logger.warning("千问流式 TTS 接收超时")
                        break

                    data = json.loads(message)

                    # 检查消息类型
                    header = data.get("header", {})
                    action = header.get("action", "")
                    status = header.get("status", "")

                    if action == "task-start":
                        logger.debug("流式 TTS 任务开始")

                    elif action == "task-finish":
                        logger.debug("流式 TTS 任务完成")
                        break

                    elif action == "audio-data":
                        # 解析音频数据
                        payload = data.get("payload", {})
                        audio_b64 = payload.get("audio", "")

                        if audio_b64:
                            import base64
                            audio_bytes = base64.b64decode(audio_b64)

                            # PCM 格式直接转换
                            if self._format == "pcm":
                                # PCM 16-bit signed little-endian
                                chunk = np.frombuffer(audio_bytes, dtype=np.int16)
                                audio_chunks.append(chunk)
                            else:
                                logger.warning(f"不支持的流式格式: {self._format}")

                    elif action == "error":
                        error_msg = data.get("payload", {}).get("message", "未知错误")
                        raise Exception(f"千问流式 TTS 错误: {error_msg}")

        except websockets.exceptions.ConnectionClosed as e:
            raise Exception(f"WebSocket 连接关闭: {e}")
        except Exception as e:
            logger.error(f"千问流式 TTS 合成失败: {e}")
            raise

        # 合并所有音频块
        if audio_chunks:
            return np.concatenate(audio_chunks)
        else:
            raise Exception("未收到任何音频数据")

    def get_sample_rate(self) -> int:
        """获取采样率"""
        return self._sample_rate

    def is_ready(self) -> bool:
        """
        检查引擎是否已就绪

        Returns:
            bool: 是否就绪
        """
        if not WEBSOCKETS_AVAILABLE:
            return False

        if not self._api_key:
            logger.warning("千问 TTS API key 未配置")
            return False

        return True

    def get_model_info(self) -> dict:
        """
        获取模型信息

        Returns:
            dict: 模型信息
        """
        return {
            "engine_type": "QwenRealtimeTTS",
            "model": self._model,
            "voice": self._voice,
            "sample_rate": self._sample_rate,
            "format": self._format,
            "mode": self._mode,
            "websocket_url": self._url,
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
