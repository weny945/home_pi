"""
混合 TTS 引擎（自动切换远程/本地）
Hybrid TTS Engine with Automatic Failover
"""
import logging
import threading
import time
from typing import Optional
import numpy as np

from .engine import TTSEngine

logger = logging.getLogger(__name__)


class HybridTTSEngine(TTSEngine):
    """
    混合 TTS 引擎

    优先使用远程 TTS，失败时自动切换到本地 TTS
    后台线程定期检测远程 TTS 是否恢复，恢复后自动切回
    """

    def __init__(
        self,
        remote_engine: TTSEngine,
        local_engine: TTSEngine,
        health_check_interval: int = 3600,
        auto_failback: bool = True
    ):
        """
        初始化混合 TTS 引擎

        Args:
            remote_engine: 远程 TTS 引擎
            local_engine: 本地 TTS 引擎
            health_check_interval: 健康检查间隔（秒），默认 1 小时
            auto_failback: 是否自动切回远程 TTS，默认 True
        """
        self._remote_engine = remote_engine
        self._local_engine = local_engine
        self._health_check_interval = health_check_interval
        self._auto_failback = auto_failback

        # 当前使用的引擎（优先远程）
        self._current_engine = "remote" if remote_engine.is_ready() else "local"
        self._remote_available = remote_engine.is_ready()

        logger.info("="*60)
        logger.info("混合 TTS 引擎初始化")
        logger.info("="*60)
        logger.info(f"  远程引擎: {remote_engine.__class__.__name__}")
        logger.info(f"  本地引擎: {local_engine.__class__.__name__}")
        logger.info(f"  当前使用: {'远程' if self._current_engine == 'remote' else '本地'} TTS")
        logger.info(f"  健康检查间隔: {health_check_interval} 秒")
        logger.info(f"  自动切回: {'启用' if auto_failback else '禁用'}")
        logger.info("="*60)

        # 启动后台健康检查线程
        if auto_failback:
            self._health_check_thread = threading.Thread(
                target=self._health_check_loop,
                daemon=True,
                name="TTS-HealthCheck"
            )
            self._health_check_thread.start()
            logger.info("✅ 后台健康检查线程已启动")

    def _health_check_loop(self):
        """后台健康检查循环"""
        logger.info("🔄 后台健康检查线程运行中...")
        while True:
            try:
                # 等待指定间隔
                time.sleep(self._health_check_interval)

                # 执行健康检查
                logger.debug("执行远程 TTS 健康检查...")
                was_available = self._remote_available

                # 检查远程引擎是否可用
                if hasattr(self._remote_engine, 'check_health'):
                    is_available = self._remote_engine.check_health()
                else:
                    is_available = self._remote_engine.is_ready()

                self._remote_available = is_available

                # 如果远程引擎从不可用恢复到可用，且当前使用本地引擎
                if not was_available and is_available and self._current_engine == "local":
                    logger.info("="*60)
                    logger.info("✅ 远程 TTS 已恢复在线！")
                    logger.info("   自动切换回远程 TTS 引擎")
                    logger.info("="*60)
                    self._current_engine = "remote"

                # 记录状态变化
                if was_available != is_available:
                    status = "在线" if is_available else "离线"
                    logger.info(f"📡 远程 TTS 状态变化: {status}")

            except Exception as e:
                logger.error(f"健康检查线程异常: {e}", exc_info=True)

    def synthesize(
        self,
        text: str,
        speaker_id: Optional[int] = None
    ) -> np.ndarray:
        """
        合成语音（自动切换远程/本地）

        Args:
            text: 要合成的文本
            speaker_id: 说话人ID（可选）

        Returns:
            np.ndarray: 音频数据 (16kHz, 16bit, 单声道)
        """
        # 策略：优先使用远程 TTS
        if self._current_engine == "remote" and self._remote_available:
            try:
                logger.debug("使用远程 TTS 合成")
                return self._remote_engine.synthesize(text, speaker_id)

            except Exception as e:
                logger.warning(f"⚠️  远程 TTS 合成失败: {e}")
                logger.info("🔄 自动切换到本地 TTS")
                self._current_engine = "local"
                self._remote_available = False
                # 继续使用本地引擎

        # 使用本地 TTS
        logger.debug("使用本地 TTS 合成")
        try:
            return self._local_engine.synthesize(text, speaker_id)
        except Exception as e:
            logger.error(f"❌ 本地 TTS 合成也失败: {e}")
            raise

    def get_sample_rate(self) -> int:
        """获取采样率"""
        return self._local_engine.get_sample_rate()

    def is_ready(self) -> bool:
        """
        是否已就绪

        Returns:
            bool: 至少有一个引擎可用
        """
        return self._remote_engine.is_ready() or self._local_engine.is_ready()

    def get_model_info(self) -> dict:
        """
        获取模型信息

        Returns:
            dict: 模型信息
        """
        return {
            "engine_type": "Hybrid",
            "current_engine": self._current_engine,
            "remote_available": self._remote_available,
            "remote_engine": self._remote_engine.get_model_info(),
            "local_engine": self._local_engine.get_model_info(),
            "health_check_interval": self._health_check_interval,
            "auto_failback": self._auto_failback
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
            wav_file.setframerate(16000)  # 16kHz
            wav_file.writeframes(audio_data.tobytes())

        logger.info(f"音频已保存到: {output_path}")

    def force_remote(self) -> bool:
        """
        强制切换到远程 TTS（如果可用）

        Returns:
            bool: 切换是否成功
        """
        if self._remote_available:
            self._current_engine = "remote"
            logger.info("✅ 已强制切换到远程 TTS")
            return True
        else:
            logger.warning("⚠️  远程 TTS 不可用，无法切换")
            return False

    def force_local(self):
        """强制切换到本地 TTS"""
        self._current_engine = "local"
        logger.info("✅ 已强制切换到本地 TTS")

    def get_status(self) -> dict:
        """
        获取详细状态信息

        Returns:
            dict: 状态信息
        """
        return {
            "current_engine": self._current_engine,
            "remote_available": self._remote_available,
            "local_ready": self._local_engine.is_ready(),
            "auto_failback_enabled": self._auto_failback,
            "health_check_interval": self._health_check_interval,
            "next_check_in": f"{self._health_check_interval} 秒"
        }
