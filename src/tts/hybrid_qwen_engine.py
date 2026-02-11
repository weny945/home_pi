"""
混合 TTS 引擎（千问 TTS + Piper + 智能路由 + 缓存）
Hybrid TTS Engine (Qwen + Piper + Smart Routing + Cache)
"""
import logging
import time
from typing import Optional, Literal
import numpy as np

from .engine import TTSEngine
from .piper_engine import PiperTTSEngine

logger = logging.getLogger(__name__)


class HybridQwenTTSEngine(TTSEngine):
    """
    混合 TTS 引擎（千问 + Piper）

    策略：
    1. 所有文本优先使用千问 TTS
    2. 短文本（<100字）：使用非流式 HTTP API
    3. 长文本（≥100字）：使用流式 WebSocket API
    4. 特定场景：根据配置强制使用流式/非流式
    5. 千问失败时自动降级到 Piper
    """

    def __init__(
        self,
        local_engine: PiperTTSEngine,
        qwen_engine: TTSEngine,
        realtime_engine: Optional[TTSEngine] = None,
        config: dict = None
    ):
        """
        初始化混合千问 TTS 引擎

        Args:
            local_engine: 本地 Piper 引擎
            qwen_engine: 千问非流式引擎
            realtime_engine: 千问流式引擎（可选）
            config: 配置字典，格式如下：
                {
                    "streaming_threshold": 100,
                    "scenario_streaming": {
                        "llm_reply_long": "streaming",
                        "wake_response": "non_streaming"
                    },
                    "fallback_to_piper": True,
                    "max_retries": 2,
                    "retry_delay": 1.0,
                    "enable_monitoring": True,
                    "log_decision": True
                }
        """
        self._piper_engine = local_engine
        self._qwen_engine = qwen_engine
        self._realtime_engine = realtime_engine

        self._config = config or {}
        self._streaming_threshold = self._config.get("streaming_threshold", 100)
        self._scenario_streaming = self._config.get("scenario_streaming", {})
        self._fallback_to_piper = self._config.get("fallback_to_piper", True)
        self._max_retries = self._config.get("max_retries", 2)
        self._retry_delay = self._config.get("retry_delay", 1.0)
        self._enable_monitoring = self._config.get("enable_monitoring", True)
        self._log_decision = self._config.get("log_decision", True)

        # 引擎状态
        self._piper_available = local_engine.is_ready()
        self._qwen_available = qwen_engine.is_ready()
        self._realtime_available = realtime_engine.is_ready() if realtime_engine else False

        # 网络状态
        self._last_network_check = 0
        self._network_available = False
        self._network_check_interval = 60

        logger.info("=" * 60)
        logger.info("混合千问 TTS 引擎初始化")
        logger.info("=" * 60)
        logger.info(f"  Piper: {'✅' if self._piper_available else '❌'}")
        logger.info(f"  千问非流式: {'✅' if self._qwen_available else '❌'}")
        logger.info(f"  千问流式: {'✅' if self._realtime_available else '❌'}")
        logger.info(f"  流式阈值: {self._streaming_threshold} 字符")
        logger.info(f"  降级到 Piper: {'是' if self._fallback_to_piper else '否'}")
        logger.info("=" * 60)

    def synthesize(
        self,
        text: str,
        speaker_id: Optional[int] = None,
        scenario: str = "default"
    ) -> np.ndarray:
        """
        合成语音（智能路由）

        Args:
            text: 输入文本
            speaker_id: 说话人ID（可选）
            scenario: 场景类型 (wake_response, llm_reply_long, etc.)

        Returns:
            np.ndarray: 音频数据 (int16, 单声道)
        """
        # 决策使用哪个引擎
        decision = self._route(text, scenario)

        if self._log_decision:
            logger.info(f"[TTS 路由] 文本={text[:30]}... 场景={scenario} → {decision['engine']}")

        # 执行合成
        if decision['engine'] == 'realtime':
            return self._synthesize_realtime(text, scenario)
        elif decision['engine'] == 'qwen':
            return self._synthesize_qwen(text, scenario)
        elif decision['engine'] == 'piper':
            return self._synthesize_piper(text, scenario)
        else:
            raise Exception(f"没有可用的 TTS 引擎: {decision['engine']}")

    def _route(
        self,
        text: str,
        scenario: str
    ) -> dict:
        """
        路由决策：选择使用哪个 TTS 引擎

        Args:
            text: 输入文本
            scenario: 场景类型

        Returns:
            dict: 决策结果 {"engine": "realtime" | "qwen" | "piper"}
        """
        # 1. 检查千问可用性
        self._update_network_status()

        if not self._network_available or not self._qwen_available:
            if self._piper_available:
                return {"engine": "piper", "reason": "network_unavailable"}
            else:
                return {"engine": "none", "reason": "no_engine"}

        # 2. 场景级别配置
        scenario_mode = self._scenario_streaming.get(scenario)
        if scenario_mode:
            if scenario_mode == "streaming" and self._realtime_available:
                return {"engine": "realtime", "reason": "scenario"}
            elif scenario_mode == "non_streaming":
                return {"engine": "qwen", "reason": "scenario"}

        # 3. 文本长度判断
        text_length = len(text)
        if text_length >= self._streaming_threshold and self._realtime_available:
            return {"engine": "realtime", "reason": "text_length"}
        else:
            return {"engine": "qwen", "reason": "default"}

    def _synthesize_qwen(self, text: str, scenario: str) -> np.ndarray:
        """使用千问非流式合成语音"""
        if not self._qwen_available:
            raise Exception("千问引擎不可用")

        for attempt in range(self._max_retries + 1):
            try:
                return self._qwen_engine.synthesize(text)
            except Exception as e:
                logger.warning(f"千问 TTS 失败 (尝试 {attempt + 1}/{self._max_retries + 1}): {e}")

                if attempt < self._max_retries:
                    time.sleep(self._retry_delay)
                else:
                    # 降级到 Piper
                    if self._fallback_to_piper and self._piper_available:
                        logger.info("降级到 Piper TTS")
                        return self._synthesize_piper(text, scenario)
                    else:
                        raise

    def _synthesize_realtime(self, text: str, scenario: str) -> np.ndarray:
        """使用千问流式合成语音"""
        if not self._realtime_available:
            # 降级到非流式
            logger.info("流式引擎不可用，降级到非流式")
            return self._synthesize_qwen(text, scenario)

        for attempt in range(self._max_retries + 1):
            try:
                return self._realtime_engine.synthesize(text)
            except Exception as e:
                logger.warning(f"千问流式 TTS 失败 (尝试 {attempt + 1}/{self._max_retries + 1}): {e}")

                if attempt < self._max_retries:
                    time.sleep(self._retry_delay)
                else:
                    # 降级到非流式
                    logger.info("流式失败，降级到非流式")
                    return self._synthesize_qwen(text, scenario)

    def _synthesize_piper(self, text: str, scenario: str) -> np.ndarray:
        """使用 Piper 合成语音"""
        if not self._piper_available:
            raise Exception("Piper 引擎不可用")

        return self._piper_engine.synthesize(text)

    def _update_network_status(self) -> None:
        """更新网络状态"""
        current_time = time.time()

        # 如果距离上次检查时间不足间隔，跳过
        if current_time - self._last_network_check < self._network_check_interval:
            return

        # 执行网络检查
        self._last_network_check = current_time
        self._network_available = self._qwen_engine.is_ready()

    def get_sample_rate(self) -> int:
        """
        获取采样率

        注意：混合模式下采样率不固定，取决于使用的引擎
        Piper: 22050Hz, 千问: 24000Hz
        """
        # 优先返回 Piper 采样率（更常用）
        if self._piper_available:
            return self._piper_engine.get_sample_rate()
        elif self._qwen_available:
            return self._qwen_engine.get_sample_rate()
        else:
            return 22050  # 默认值

    def is_ready(self) -> bool:
        """检查是否有可用的 TTS 引擎"""
        return self._piper_available or self._qwen_available

    def get_model_info(self) -> dict:
        """获取模型信息"""
        return {
            "engine_type": "HybridQwen",
            "piper_available": self._piper_available,
            "qwen_available": self._qwen_available,
            "realtime_available": self._realtime_available,
            "network_available": self._network_available,
            "streaming_threshold": self._streaming_threshold,
            "fallback_to_piper": self._fallback_to_piper,
            "scenario_streaming": self._scenario_streaming
        }

    def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        speaker_id: Optional[int] = None,
        scenario: str = "default"
    ) -> None:
        """合成语音并保存到文件"""
        audio_data = self.synthesize(text, speaker_id, scenario)

        # 保存为 WAV 文件
        import wave
        with wave.open(output_path, 'wb') as wav_file:
            wav_file.setnchannels(1)  # 单声道
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.get_sample_rate())
            wav_file.writeframes(audio_data.tobytes())

        logger.info(f"音频已保存到: {output_path}")

    def check_health(self) -> bool:
        """检查引擎健康状态"""
        self._update_network_status()
        return self.is_ready()

    def get_engine_status(self) -> dict:
        """获取引擎状态"""
        return {
            "piper": self._piper_available,
            "qwen": self._qwen_available,
            "realtime": self._realtime_available,
            "network": self._network_available,
            "current_preference": "qwen" if self._network_available else "piper"
        }
