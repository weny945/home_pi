"""
音频反馈播放器实现
Audio Feedback Player Implementation
"""
import logging
import time
import threading
import wave
from pathlib import Path
from typing import Optional
import numpy as np
import pyaudio

from .player import FeedbackPlayer

logger = logging.getLogger(__name__)


class AudioFeedbackPlayer(FeedbackPlayer):
    """音频反馈播放器"""

    def __init__(
        self,
        mode: str = "beep",
        audio_file: str = None,
        sample_rate: int = 16000,
        output_device: str = "plughw:0,0",
        beep_duration_ms: int = 200,
        beep_frequency: int = 880
    ):
        """
        初始化反馈播放器

        Args:
            mode: 反馈模式 ("beep" 蜂鸣声 或 "audio_file" 音频文件)
            audio_file: 音频文件路径 (WAV格式)
            sample_rate: 采样率
            output_device: 输出设备名称
            beep_duration_ms: 蜂鸣声持续时间 (毫秒)
            beep_frequency: 蜂鸣声频率 (Hz)
        """
        self._mode = mode
        self._audio_file = audio_file
        self._sample_rate = sample_rate
        self._output_device = output_device
        self._beep_duration_ms = beep_duration_ms
        self._beep_frequency = beep_frequency

        # P0-1 优化: 在初始化时创建一次 PyAudio 实例并复用
        self._audio: Optional[pyaudio.PyAudio] = pyaudio.PyAudio()
        self._stream = None
        self._is_playing = False

        # 闹钟响铃相关
        self._alarm_playing = False
        self._alarm_stop_event = threading.Event()
        self._alarm_thread: Optional[threading.Thread] = None

        # 预加载音频数据
        self._audio_data: Optional[np.ndarray] = None
        if audio_file and Path(audio_file).exists():
            self._load_audio_file(audio_file)

        # 获取输出设备索引
        self._output_device_index = self._get_device_index(output_device)
        if self._output_device_index is not None:
            logger.info(f"✓ 使用音频输出设备: {output_device} (索引: {self._output_device_index})")
        else:
            logger.warning(f"⚠️ 未找到音频设备 '{output_device}'，将使用默认设备")

    def _get_device_index(self, device_name: str) -> Optional[int]:
        """
        获取音频设备的索引

        Args:
            device_name: 设备名称 (如 "default", "pulse", "0", "1")

        Returns:
            int: 设备索引，如果未找到返回 None（使用默认设备）
        """
        # 如果是纯数字，直接作为索引
        if device_name.isdigit():
            idx = int(device_name)
            logger.info(f"使用设备索引: {idx}")
            return idx

        # "default" 或特殊名称返回 None，让 PyAudio 使用默认设备
        if device_name in ["default", "sysdefault"]:
            logger.info(f"使用默认设备: {device_name}")
            return None

        try:
            p = pyaudio.PyAudio()

            # 遍历所有输出设备
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info['maxOutputChannels'] > 0:
                    logger.debug(f"  设备 {i}: {info['name']}")

                    # 检查设备名称是否匹配
                    # 支持部分匹配（如 "pulse" 会匹配 "pulse"）
                    if device_name.lower() in info['name'].lower():
                        p.terminate()
                        logger.info(f"找到匹配设备: {info['name']} (索引: {i})")
                        return i

            p.terminate()
            logger.warning(f"未找到设备 '{device_name}'，将使用默认设备")
            return None

        except Exception as e:
            logger.error(f"获取音频设备索引失败: {e}")
            return None

    def _load_audio_file(self, file_path: str) -> None:
        """
        加载音频文件

        Args:
            file_path: 音频文件路径
        """
        try:
            # 这里简化处理，实际应该使用 wave 或 soundfile 库
            logger.info(f"加载音频文件: {file_path}")
            # TODO: 实现音频文件加载
            # from scipy.io import wavfile
            # self._sample_rate, self._audio_data = wavfile.read(file_path)
        except Exception as e:
            logger.error(f"加载音频文件失败: {e}")

    def _generate_beep(self) -> np.ndarray:
        """
        生成蜂鸣声

        Returns:
            np.ndarray: 音频数据
        """
        duration_sec = self._beep_duration_ms / 1000.0
        t = np.linspace(0, duration_sec, int(self._sample_rate * duration_sec), False)

        # 生成正弦波
        tone = np.sin(2 * np.pi * self._beep_frequency * t)

        # 应用淡入淡出
        fade_len = int(0.01 * self._sample_rate)  # 10ms fade
        fade_in = np.linspace(0, 1, fade_len)
        fade_out = np.linspace(1, 0, fade_len)

        if len(tone) > 2 * fade_len:
            tone[:fade_len] *= fade_in
            tone[-fade_len:] *= fade_out

        # 转换为 16-bit PCM
        audio_data = (tone * 32767).astype(np.int16)

        return audio_data

    def play_wake_feedback(self) -> None:
        """播放唤醒反馈"""
        if self._is_playing:
            logger.warning("正在播放中，跳过")
            return

        try:
            self._is_playing = True

            if self._mode == "beep":
                audio_data = self._generate_beep()
                self._play_audio(audio_data)

            elif self._mode == "audio_file":
                if self._audio_data is not None:
                    self._play_audio(self._audio_data)
                else:
                    logger.warning("音频文件未加载，使用蜂鸣声")
                    audio_data = self._generate_beep()
                    self._play_audio(audio_data)

            logger.info("唤醒反馈播放完成")

        except Exception as e:
            logger.error(f"播放反馈失败: {e}")
        finally:
            self._is_playing = False

    def _play_audio(self, audio_data: np.ndarray) -> None:
        """
        播放音频数据

        P0-1 优化: 复用 PyAudio 实例，只打开/关闭音频流

        Args:
            audio_data: 音频数据 (numpy array, int16)
        """
        if self._audio is None:
            logger.warning("PyAudio 实例未初始化，尝试创建")
            self._audio = pyaudio.PyAudio()

        try:
            # 打开音频流，使用指定的输出设备
            device_params = {
                'format': pyaudio.paInt16,
                'channels': 1,
                'rate': self._sample_rate,
                'output': True
            }

            # 如果找到了设备索引，使用它
            if self._output_device_index is not None:
                device_params['output_device_index'] = self._output_device_index
                logger.debug(f"使用设备索引: {self._output_device_index}")

            # P0-1 优化: 复用 PyAudio 实例，只创建流
            self._stream = self._audio.open(**device_params)

            # 播放音频
            self._stream.write(audio_data.tobytes())

        finally:
            # P0-1 优化: 只关闭流，不终止 PyAudio 实例
            if self._stream:
                self._stream.close()
                self._stream = None

    def is_playing(self) -> bool:
        """是否正在播放"""
        return self._is_playing

    def stop(self) -> None:
        """
        停止播放并释放资源

        P0-1 优化: 终止 PyAudio 实例，释放所有资源
        """
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception as e:
                logger.error(f"停止播放失败: {e}")
            finally:
                self._stream = None

        # P0-1 优化: 终止 PyAudio 实例，释放资源
        if self._audio:
            try:
                self._audio.terminate()
                logger.debug("PyAudio 实例已终止")
            except Exception as e:
                logger.error(f"终止音频失败: {e}")
            finally:
                self._audio = None

        self._is_playing = False

    def __del__(self):
        """析构函数"""
        self.stop()
        self.stop_alarm_ringtone()

    # ============================================================
    # 闹钟响铃功能 (Phase 1.7)
    # ============================================================

    def play_audio(self, audio_data: np.ndarray) -> None:
        """
        播放音频数据

        Args:
            audio_data: 音频数据 (numpy array, int16)
        """
        self._play_audio(audio_data)

    def play_alarm_ringtone(self, loop: bool = False, duration: int = 30) -> None:
        """
        播放闹钟铃声

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
            # 生成或加载铃声
            logger.info("[闹钟线程] 生成闹钟铃声...")
            ringtone_data = self._generate_alarm_ringtone()
            logger.info(f"[闹钟线程] 铃声生成完成，时长: {len(ringtone_data) / self._sample_rate:.2f}秒")

            while not self._alarm_stop_event.is_set():
                # 检查是否超时
                if time.time() - start_time >= duration:
                    logger.info(f"闹钟铃声达到最大时长 ({duration}s)")
                    break

                # 播放铃声
                logger.info(f"播放第 {play_count + 1} 次...")
                self._play_audio(ringtone_data)
                play_count += 1
                logger.info(f"播放完成，已播放 {play_count} 次")

                # 如果不循环，播放一次后退出
                if not loop:
                    logger.info("非循环模式，播放一次后退出")
                    break

        except Exception as e:
            logger.error(f"播放闹钟铃声失败: {e}", exc_info=True)
        finally:
            self._alarm_playing = False
            logger.info(f"闹钟铃声播放结束，共播放 {play_count} 次")

    def _generate_alarm_ringtone(self) -> np.ndarray:
        """
        生成闹钟铃声（双音调交替）

        Returns:
            np.ndarray: 音频数据
        """
        # 生成 2 秒的铃声
        duration_sec = 2.0
        t = np.linspace(0, duration_sec, int(self._sample_rate * duration_sec), False)

        # 双音调交替：880Hz 和 1108.73Hz（A5 和 C#6）
        tone1 = np.sin(2 * np.pi * 880 * t)
        tone2 = np.sin(2 * np.pi * 1108.73 * t)

        # 每 0.5 秒切换一次音调
        switch_samples = int(self._sample_rate * 0.5)
        ringtone = np.zeros_like(t)
        for i in range(len(t)):
            block = i // switch_samples
            if block % 2 == 0:
                ringtone[i] = tone1[i]
            else:
                ringtone[i] = tone2[i]

        # 应用淡入淡出
        fade_len = int(0.05 * self._sample_rate)  # 50ms fade
        fade_in = np.linspace(0, 1, fade_len)
        fade_out = np.linspace(1, 0, fade_len)

        if len(ringtone) > 2 * fade_len:
            ringtone[:fade_len] *= fade_in
            ringtone[-fade_len:] *= fade_out

        # 转换为 16-bit PCM
        audio_data = (ringtone * 0.5 * 32767).astype(np.int16)

        return audio_data

    def is_alarm_playing(self) -> bool:
        """检查闹钟是否正在播放"""
        return self._alarm_playing

    def stop_alarm_ringtone(self) -> None:
        """停止闹钟铃声"""
        if not self._alarm_playing:
            return

        logger.info("停止闹钟铃声")
        self._alarm_stop_event.set()

        if self._alarm_thread:
            self._alarm_thread.join(timeout=1.0)
            self._alarm_thread = None

        self._alarm_playing = False
