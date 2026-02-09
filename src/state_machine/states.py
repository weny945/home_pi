"""
状态定义
State Definitions for Voice Assistant State Machine
"""
from enum import Enum


class State(Enum):
    """系统状态枚举"""

    IDLE = "idle"           # 监听唤醒词中
    WAKEUP = "wakeup"       # 播放唤醒反馈中
    LISTENING = "listening"  # 录制用户语音中（第二阶段）
    PROCESSING = "processing"  # 处理中（第二阶段）
    SPEAKING = "speaking"   # 播报回复中（第二阶段）
    ERROR = "error"         # 错误状态

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"State.{self.name}"
