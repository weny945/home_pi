"""
通用 TTS 反馈播放器实现（支持多种 TTS 引擎）
Generic TTS Feedback Player Implementation (Supports Multiple TTS Engines)
"""
import logging
from pathlib import Path
from typing import Optional, List, Dict
import numpy as np
import threading
import time
import tempfile
import os
import struct
import subprocess

from .player import FeedbackPlayer
from ..tts import create_tts_engine, TTSEngine

logger = logging.getLogger(__name__)


class GenericTTSFeedbackPlayer(FeedbackPlayer):
    """通用 TTS 反馈播放器（支持 Piper、千问、混合引擎等）"""

    def __init__(
        self,
        messages: Optional[List[str]] = None,
        tts_config: Optional[dict] = None,
        random_message: bool = False,
        cache_audio: bool = True,
        output_device: Optional[str] = None,
        volume_gain: float = 1.0
    ):
        """
        初始化通用 TTS 反馈播放器

        Args:
            messages: 回复消息列表
            tts_config: TTS 配置字典（完整配置，包含 engine、local、qwen 等）
            random_message: 是否随机选择消息
            cache_audio: 是否缓存音频文件
            output_device: 音频输出设备名称
            volume_gain: 音量增益
        """
        self._messages = messages or ["我在", "请吩咐", "我在听", "您好", "我在这里"]
        self._random_message = random_message
        self._current_message_index = 0
        self._cache_audio = cache_audio
        self._output_device = output_device
        self._volume_gain = max(0.1, min(volume_gain, 3.0))
        self._tts_config = tts_config or {}

        # 使用工厂函数创建 TTS 引擎
        try:
            logger.info("正在初始化 TTS 引擎...")
            self._tts_engine = create_tts_engine(self._tts_config)
            logger.info("✅ TTS 引擎初始化成功")

            # 获取引擎信息
            engine_info = self._tts_engine.get_model_info() if hasattr(self._tts_engine, 'get_model_info') else {}
            engine_type = engine_info.get('engine_type', 'Unknown')
            logger.info(f"  引擎类型: {engine_type}")

        except Exception as e:
            logger.error(f"TTS 引擎初始化失败: {e}")
            raise

        # 播放状态
        self._is_playing = False

        # 闹钟播放状态
        self._alarm_playing = False
        self._alarm_stop_event = threading.Event()
        self._alarm_thread: Optional[threading.Thread] = None

        # 预加载音频缓存
        if cache_audio and self._can_preload_cache():
            self._preload_audio_cache()

    def _can_preload_cache(self) -> bool:
        """检查是否可以预加载缓存"""
        # 对于 Piper 引擎，预加载缓存以加快启动速度
        # 对于千问/豆包引擎（需联网），不预加载避免启动时网络请求
        engine_name = self._tts_engine.__class__.__name__
        # 仅本地引擎预加载
        return engine_name in ("PiperTTSEngine",)

    def _preload_audio_cache(self) -> None:
        """预加载所有消息的音频缓存"""
        logger.info("预加载音频缓存...")
        cache_dir = Path("./cache/tts_audio")
        cache_dir.mkdir(parents=True, exist_ok=True)

        for message in self._messages:
            cache_file = cache_dir / f"{message}.wav"
            if not cache_file.exists():
                try:
                    logger.debug(f"缓存音频: {message}")
                    self._tts_engine.synthesize_to_file(
                        message,
                        str(cache_file)
                    )
                except Exception as e:
                    logger.warning(f"预加载音频失败 ({message}): {e}")

        logger.info("音频缓存预加载完成")

    def _get_message(self) -> str:
        """
        获取回复消息

        Returns:
            str: 消息文本
        """
        if self._random_message:
            import random
            return random.choice(self._messages)
        else:
            # 按顺序循环使用消息
            message = self._messages[self._current_message_index]
            self._current_message_index = (self._current_message_index + 1) % len(self._messages)
            return message

    def play_wake_feedback(self) -> None:
        """播放唤醒反馈（TTS 语音）"""
        if self._is_playing:
            logger.warning("正在播放中，跳过")
            return

        try:
            self._is_playing = True

            # 获取回复消息
            message = self._get_message()
            logger.info(f"播放唤醒回复: {message}")

            # 尝试从缓存加载
            audio_data = None
            if self._cache_audio:
                audio_data = self._load_from_cache(message)

            # 如果缓存不存在，使用 TTS 合成
            if audio_data is None:
                logger.debug("缓存未命中，使用 TTS 合成")
                audio_data = self._tts_engine.synthesize(message)

            # 播放音频
            self._play_audio(audio_data)

            logger.info("唤醒回复播放完成")

        except Exception as e:
            logger.error(f"播放唤醒回复失败: {e}")
        finally:
            self._is_playing = False

    def _load_from_cache(self, message: str) -> Optional[np.ndarray]:
        """
        从缓存加载音频

        Args:
            message: 消息文本

        Returns:
            np.ndarray: 音频数据，如果缓存不存在返回 None
        """
        try:
            from scipy.io import wavfile

            cache_file = Path("./cache/tts_audio") / f"{message}.wav"
            if cache_file.exists():
                _, audio_data = wavfile.read(str(cache_file))
                logger.debug(f"从缓存加载音频: {message}")
                return audio_data
            return None

        except Exception as e:
            logger.warning(f"加载缓存失败 ({message}): {e}")
            return None

    def _play_audio(self, audio_data: np.ndarray) -> None:
        """
        播放音频数据（使用 aplay，支持自动采样率转换）

        Args:
            audio_data: 音频数据 (numpy array, int16)
        """
        sample_rate = self._tts_engine.get_sample_rate()

        # 应用音量增益
        if self._volume_gain != 1.0:
            # 转换为 float32 进行增益处理
            audio_float = audio_data.astype(np.float32)
            audio_float *= self._volume_gain
            # 限幅避免削波
            audio_float = np.clip(audio_float, -32768, 32767)
            audio_data = audio_float.astype(np.int16)
            logger.debug(f"应用音量增益: {self._volume_gain}x")

        # 计算音频时长（秒）并设置超时（时长 + 5秒缓冲）
        audio_duration = len(audio_data) / sample_rate
        timeout_duration = audio_duration + 5.0

        temp_path = None
        try:
            # 创建临时 WAV 文件
            with tempfile.NamedTemporaryFile(
                suffix='.wav',
                mode='wb',
                delete=False
            ) as temp_file:
                temp_path = temp_file.name

                # 手动写入 WAV 文件头（确保兼容性）
                # RIFF 头
                temp_file.write(b'RIFF')
                temp_file.write(struct.pack('<I', 36 + len(audio_data) * 2))
                temp_file.write(b'WAVE')

                # fmt 子块
                temp_file.write(b'fmt ')
                temp_file.write(struct.pack('<I', 16))
                temp_file.write(struct.pack('<H', 1))
                temp_file.write(struct.pack('<H', 1))
                temp_file.write(struct.pack('<I', sample_rate))
                temp_file.write(struct.pack('<I', sample_rate * 2))
                temp_file.write(struct.pack('<H', 2))
                temp_file.write(struct.pack('<H', 16))

                # data 子块
                temp_file.write(b'data')
                temp_file.write(struct.pack('<I', len(audio_data) * 2))

                # 写入音频数据
                temp_file.write(audio_data.astype(np.int16).tobytes())

            # 构建 aplay 命令
            cmd = ['aplay', '-q']

            if self._output_device:
                cmd.extend(['-D', self._output_device])
                logger.debug(f"使用音频设备: {self._output_device}")

            cmd.append(temp_path)

            logger.debug(f"执行命令: {' '.join(cmd)}")
            logger.debug(f"音频时长: {audio_duration:.2f}s, 超时设置: {timeout_duration:.2f}s")

            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                timeout=timeout_duration
            )

            logger.debug(f"音频播放成功，采样率: {sample_rate} Hz")

        except subprocess.TimeoutExpired:
            logger.error("播放超时")
            raise
        except subprocess.CalledProcessError as e:
            logger.error(f"aplay 播放失败: {e}")
            if e.stderr:
                error_msg = e.stderr.decode('utf-8', errors='ignore')
                logger.error(f"错误输出: {error_msg}")
            raise
        except Exception as e:
            logger.error(f"播放音频失败: {e}")
            raise
        finally:
            # 清理临时文件
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                    logger.debug(f"已清理临时文件: {temp_path}")
                except Exception as e:
                    logger.warning(f"清理临时文件失败: {e}")

    def play_audio(self, audio_data: np.ndarray) -> None:
        """
        公共方法：播放音频数据

        Args:
            audio_data: 音频数据 (numpy array, int16)
        """
        if self._is_playing:
            logger.warning("正在播放中，跳过")
            return

        try:
            self._is_playing = True
            self._play_audio(audio_data)
            logger.info("音频播放完成")
        except Exception as e:
            logger.error(f"播放音频失败: {e}")
            raise
        finally:
            self._is_playing = False

    def is_playing(self) -> bool:
        """是否正在播放"""
        return self._is_playing

    def stop(self) -> None:
        """停止播放"""
        self._is_playing = False
        logger.debug("播放器已停止")

    def set_message(self, message: str) -> None:
        """
        设置单条回复消息

        Args:
            message: 消息文本
        """
        self._messages = [message]
        self._current_message_index = 0
        logger.info(f"回复消息已设置: {message}")

    def set_messages(self, messages: List[str]) -> None:
        """
        设置回复消息列表

        Args:
            messages: 消息列表
        """
        if not messages:
            logger.warning("消息列表为空，未更新")
            return

        self._messages = messages
        self._current_message_index = 0
        logger.info(f"回复消息列表已更新，共 {len(messages)} 条")

    def get_model_info(self) -> dict:
        """
        获取模型信息

        Returns:
            dict: 模型信息
        """
        return self._tts_engine.get_model_info()

    def __del__(self):
        """析构函数"""
        self.stop()
        self.stop_alarm_ringtone()

    # ============================================================
    # 闹钟播放功能
    # ============================================================

    def play_alarm_ringtone(self, loop: bool = False, duration: int = 30) -> None:
        """
        播放闹钟铃声（生成双音调铃声）

        Args:
            loop: 是否循环播放
            duration: 最大播放时长（秒）
        """
        logger.info(f"[闹钟] play_alarm_ringtone 被调用 (loop={loop}, duration={duration})")

        if self._alarm_playing:
            logger.warning("[闹钟] 铃声正在播放中，跳过")
            return

        self._alarm_playing = True
        self._alarm_stop_event.clear()

        logger.info(f"[闹钟] 创建播放线程...")

        # 在独立线程中播放
        self._alarm_thread = threading.Thread(
            target=self._play_alarm_ringtone_internal,
            kwargs={"loop": loop, "duration": duration},
            daemon=True
        )

        logger.info(f"[闹钟] 启动播放线程...")
        self._alarm_thread.start()
        logger.info(f"[闹钟] 播放线程已启动")

    def _play_alarm_ringtone_internal(self, loop: bool, duration: int) -> None:
        """
        内部方法：播放闹钟铃声

        Args:
            loop: 是否循环播放
            duration: 最大播放时长（秒）
        """
        logger.info(f"[闹钟线程] _play_alarm_ringtone_internal 开始执行 (loop={loop}, duration={duration})")

        start_time = time.time()
        play_count = 0

        try:
            # 生成闹钟铃声
            logger.info("[闹钟线程] 生成闹钟铃声...")
            ringtone_data = self._generate_alarm_ringtone()
            sample_rate = self._tts_engine.get_sample_rate()
            logger.info(f"[闹钟线程] 铃声生成完成，时长: {len(ringtone_data) / sample_rate:.2f}秒")

            while not self._alarm_stop_event.is_set():
                # 检查是否超时
                if time.time() - start_time >= duration:
                    logger.info(f"[闹钟线程] 闹钟铃声达到最大时长 ({duration}s)")
                    break

                # 播放铃声
                logger.info(f"[闹钟线程] 播放第 {play_count + 1} 次...")
                self._play_audio(ringtone_data)
                play_count += 1
                logger.info(f"[闹钟线程] 播放完成，已播放 {play_count} 次")

                # 如果不循环，播放一次后退出
                if not loop:
                    logger.info("[闹钟线程] 非循环模式，播放一次后退出")
                    break

        except Exception as e:
            logger.error(f"[闹钟线程] 播放闹钟铃声失败: {e}", exc_info=True)
        finally:
            self._alarm_playing = False
            logger.info(f"[闹钟线程] 闹钟铃声播放结束，共播放 {play_count} 次")

    def _generate_alarm_ringtone(self) -> np.ndarray:
        """
        生成闹钟铃声（双音调交替）

        Returns:
            np.ndarray: 音频数据
        """
        sample_rate = self._tts_engine.get_sample_rate()

        # 生成 2 秒的铃声
        duration_sec = 2.0
        t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), False)

        # 双音调交替：880Hz 和 1108.73Hz（A5 和 C#6）
        tone1 = np.sin(2 * np.pi * 880 * t)
        tone2 = np.sin(2 * np.pi * 1108.73 * t)

        # 每 0.5 秒切换一次音调
        switch_samples = int(sample_rate * 0.5)
        ringtone = np.zeros_like(t)

        for i in range(0, len(t), switch_samples):
            end_idx = min(i + switch_samples, len(t))
            if (i // switch_samples) % 2 == 0:
                ringtone[i:end_idx] = tone1[i:end_idx]
            else:
                ringtone[i:end_idx] = tone2[i:end_idx]

        # 添加渐入渐出效果，避免爆音
        fade_samples = int(sample_rate * 0.05)
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)

        ringtone[:fade_samples] *= fade_in
        ringtone[-fade_samples:] *= fade_out

        # 归一化到 1.0 的幅度
        ringtone = ringtone / np.max(np.abs(ringtone)) * 1.0

        # 转换为 int16
        return (ringtone * 32767).astype(np.int16)

    def is_alarm_playing(self) -> bool:
        """检查闹钟是否正在播放"""
        return self._alarm_playing

    def stop_alarm_ringtone(self) -> None:
        """停止闹钟铃声"""
        if not self._alarm_playing:
            return

        logger.info("停止闹钟铃声")
        self._alarm_stop_event.set()

        # 等待线程结束（最多 2 秒）
        if self._alarm_thread and self._alarm_thread.is_alive():
            self._alarm_thread.join(timeout=2.0)
