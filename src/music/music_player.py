"""
音乐播放器 - Music Player
支持本地音乐播放、暂停、停止、音量控制
Phase 1.8
"""
import logging
import threading
import time
import os
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# 尝试导入 pygame 用于音乐播放
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    logger.warning("pygame 未安装，音乐播放功能将受限")

from .music_library import Track, MusicLibrary

# 全局变量（修复：移到模块级别）
PYGAME_AVAILABLE = PYGAME_AVAILABLE


class MusicPlayer:
    """音乐播放器"""

    def __init__(
        self,
        music_dir: str = "./assets/music",
        output_device: str = "plughw:0,0",
        initial_volume: float = 0.7
    ):
        """
        初始化音乐播放器

        Args:
            music_dir: 音乐文件目录
            output_device: 输出设备名称
            initial_volume: 初始音量 (0.0-1.0)
        """
        self._music_library = MusicLibrary(music_dir)
        self._output_device = output_device
        self._volume = initial_volume

        # 播放状态
        self._current_track: Optional[Track] = None
        self._is_playing = False
        self._is_paused = False
        self._playback_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # 初始化 pygame mixer
        self._mixer_initialized = False
        if PYGAME_AVAILABLE:
            try:
                logger.info("正在初始化 pygame mixer...")

                # 设置环境变量以使用指定的 ALSA 设备
                # SDL_AUDIODRIVER: 使用 ALSA 音频驱动
                # AUDIODEV: 指定音频输出设备
                os.environ['SDL_AUDIODRIVER'] = 'alsa'
                if output_device:
                    os.environ['AUDIODEV'] = output_device
                    logger.info(f"  设置音频设备: {output_device}")

                # 尝试使用默认参数初始化（让 pygame 自动选择音频设备）
                pygame.mixer.init()
                pygame.mixer.music.set_volume(self._volume)
                self._mixer_initialized = True
                logger.info("✓ pygame mixer 初始化成功")
                logger.info(f"  音频驱动: {pygame.mixer.get_init()}")
                logger.info(f"  预设缓冲: {pygame.mixer.get_num_channels()} 通道")
            except pygame.error as e:
                logger.error(f"pygame mixer 初始化失败 (pygame.error): {e}")
                logger.error("可能原因：音频设备被占用或不可用")
                logger.error(f"尝试使用的设备: {output_device}")
                logger.error("音乐播放功能将无法使用")
                import traceback
                logger.error(traceback.format_exc())
            except Exception as e:
                logger.error(f"pygame mixer 初始化失败: {e}")
                logger.error(f"尝试使用的设备: {output_device}")
                logger.error("音乐播放功能将无法使用")
                import traceback
                logger.error(traceback.format_exc())
        else:
            logger.warning("pygame 未安装，音乐播放功能将无法使用")
            logger.warning("请安装 pygame: pip install pygame")

        logger.info(f"音乐播放器初始化完成 (音量: {self._volume}, mixer={self._mixer_initialized})")

    def play_random(self) -> Optional[Track]:
        """
        播放随机曲目

        Returns:
            Track: 播放的曲目，失败返回 None
        """
        track = self._music_library.get_random_track()
        if not track:
            logger.warning("没有可用的音乐文件")
            return None

        return self.play_track(track)

    def play_track(self, track: Track) -> Optional[Track]:
        """
        播放指定曲目

        Args:
            track: 要播放的曲目

        Returns:
            Track: 实际播放的曲目
        """
        if not PYGAME_AVAILABLE or not self._mixer_initialized:
            logger.error("pygame 不可用或未初始化，无法播放音乐")
            logger.error("请安装 pygame: pip install pygame")
            return None

        # 停止当前播放
        self.stop()

        # 检查文件是否存在
        if not Path(track.path).exists():
            logger.error(f"音乐文件不存在: {track.path}")
            return None

        try:
            # 加载并播放音乐
            pygame.mixer.music.load(track.path)
            pygame.mixer.music.play()

            self._current_track = track
            self._is_playing = True
            self._is_paused = False
            self._stop_event.clear()

            logger.info(f"▶️  开始播放: {track}")

            return track

        except Exception as e:
            logger.error(f"播放失败 ({track.name}): {e}")
            return None

    def pause(self) -> None:
        """暂停播放"""
        if self._is_playing and not self._is_paused:
            if PYGAME_AVAILABLE:
                pygame.mixer.music.pause()
            self._is_paused = True
            logger.info("⏸️  播放已暂停")

    def resume(self) -> None:
        """恢复播放"""
        if self._is_paused:
            if PYGAME_AVAILABLE:
                pygame.mixer.music.unpause()
            self._is_paused = False
            logger.info("▶️  恢复播放")

    def stop(self) -> None:
        """停止播放"""
        if self._is_playing:
            if PYGAME_AVAILABLE:
                pygame.mixer.music.stop()
            self._is_playing = False
            self._is_paused = False
            self._stop_event.set()
            logger.info("⏹️  播放已停止")

    def set_volume(self, volume: float) -> None:
        """
        设置音量

        Args:
            volume: 音量值 (0.0-1.0)
        """
        self._volume = max(0.0, min(1.0, volume))

        if PYGAME_AVAILABLE:
            pygame.mixer.music.set_volume(self._volume)

        logger.info(f"🔊 音量设置为: {int(self._volume * 100)}%")

    def get_volume(self) -> float:
        """获取当前音量"""
        return self._volume

    def volume_up(self, increment: float = 0.1) -> None:
        """
        增加音量

        Args:
            increment: 增量 (默认 0.1 = 10%)
        """
        new_volume = self._volume + increment
        self.set_volume(new_volume)

    def volume_down(self, decrement: float = 0.1) -> None:
        """
        减少音量

        Args:
            decrement: 减量 (默认 0.1 = 10%)
        """
        new_volume = self._volume - decrement
        self.set_volume(new_volume)

    def is_playing(self) -> bool:
        """是否正在播放"""
        return self._is_playing and not self._is_paused

    def is_paused(self) -> bool:
        """是否已暂停"""
        return self._is_paused

    def get_current_track(self) -> Optional[Track]:
        """获取当前播放的曲目"""
        return self._current_track

    def get_library(self) -> MusicLibrary:
        """获取音乐库对象"""
        return self._music_library

    def wait_until_finished(self) -> None:
        """等待播放完成"""
        if PYGAME_AVAILABLE:
            while pygame.mixer.music.get_busy() and not self._stop_event.is_set():
                time.sleep(0.1)

    def get_status(self) -> dict:
        """
        获取播放器状态

        Returns:
            dict: 状态信息
        """
        return {
            'is_playing': self.is_playing(),
            'is_paused': self.is_paused(),
            'current_track': self._current_track.name if self._current_track else None,
            'volume': int(self._volume * 100)
        }
