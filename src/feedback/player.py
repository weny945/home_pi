"""
唤醒反馈播放器抽象层
Feedback Player Abstract Layer
"""
from abc import ABC, abstractmethod
from typing import Optional
import numpy as np


class FeedbackPlayer(ABC):
    """反馈播放器抽象基类"""

    @abstractmethod
    def play_wake_feedback(self) -> None:
        """播放唤醒反馈"""
        pass

    @abstractmethod
    def is_playing(self) -> bool:
        """是否正在播放"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """停止播放"""
        pass

    def play_audio(self, audio_data: np.ndarray) -> None:
        """
        播放音频数据（默认实现，子类可覆盖）

        Args:
            audio_data: 音频数据 (numpy array, int16)
        """
        pass

    def play_alarm_ringtone(self, loop: bool = False, duration: int = 30) -> None:
        """
        播放闹钟铃声（默认实现，子类可覆盖）

        Args:
            loop: 是否循环播放
            duration: 最大播放时长（秒）
        """
        pass

    def is_alarm_playing(self) -> bool:
        """检查闹钟是否正在播放（默认实现，子类可覆盖）"""
        return False

    def stop_alarm_ringtone(self) -> None:
        """停止闹钟铃声（默认实现，子类可覆盖）"""
        pass
