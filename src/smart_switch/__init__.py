"""
智能开关模块
Smart Switch Module for Voice Assistant

支持 GeekOpen 智能开关的云 MQTT 协议控制
"""

from .mqtt_client import MQTTClient
from .switch_controller import SwitchController  # 标准 Tasmota 协议
from .geekopen_controller import (
    GeekOpenController,
    GeekOpenDevice,
    GeekOpenSwitchState,
    SwitchKey,
    format_geekopen_response
)
from .intent_detector import detect_switch_intent, SwitchIntent

__all__ = [
    "MQTTClient",
    "SwitchController",
    "GeekOpenController",
    "GeekOpenDevice",
    "GeekOpenSwitchState",
    "SwitchKey",
    "detect_switch_intent",
    "SwitchIntent",
    "format_geekopen_response",
]
