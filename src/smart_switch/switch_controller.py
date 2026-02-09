"""
智能开关控制器
Smart Switch Controller

支持 GeekOpen 智能开关（MQTT/TOTA 协议）

控制命令示例：
- 开灯: "cmnd/{device_id}/POWER" -> "ON"
- 关灯: "cmnd/{device_id}/POWER" -> "OFF"
- 查询: "cmnd/{device_id}/POWER" -> ""
- 切换: "cmnd/{device_id}/POWER" -> "TOGGLE"

状态主题：
- "stat/{device_id}/POWER" -> "ON" / "OFF"
- "tele/{device_id}/STATE" -> {"POWER": "ON"}
"""
import logging
import json
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from .mqtt_client import MQTTClient

logger = logging.getLogger(__name__)


class SwitchAction(Enum):
    """开关动作"""
    ON = "ON"           # 打开
    OFF = "OFF"         # 关闭
    TOGGLE = "TOGGLE"   # 切换


@dataclass
class SwitchDevice:
    """开关设备定义"""
    device_id: str           # 设备 ID（用于 MQTT 主题）
    name: str                # 设备名称（中文，如"客厅灯"）
    location: str = ""       # 位置（如"客厅"）
    device_type: str = "light"  # 设备类型 (light/fan/socket/etc)

    @property
    def cmnd_topic(self) -> str:
        """命令主题"""
        return f"cmnd/{self.device_id}/POWER"

    @property
    def stat_topic(self) -> str:
        """状态主题"""
        return f"stat/{self.device_id}/POWER"

    @property
    def tele_topic(self) -> str:
        """遥测主题"""
        return f"tele/{self.device_id}/STATE"


@dataclass
class SwitchState:
    """开关状态"""
    device_id: str
    is_on: bool
    last_update: float  # 时间戳


class SwitchController:
    """
    智能开关控制器

    使用示例：
    ```python
    controller = SwitchController(mqtt_client)

    # 注册设备
    controller.register_device(
        device_id="switch_01",
        name="客厅灯",
        location="客厅"
    )

    # 控制开关
    controller.turn_on("客厅灯")
    controller.turn_off("客厅灯")

    # 查询状态
    state = controller.get_state("客厅灯")
    print(f"客厅灯: {'开' if state.is_on else '关'}")
    ```
    """

    def __init__(
        self,
        mqtt_client: MQTTClient,
        state_change_callback: Optional[Callable[[str, bool], None]] = None
    ):
        """
        初始化开关控制器

        Args:
            mqtt_client: MQTT 客户端
            state_change_callback: 状态变化回调 (device_name, is_on) -> None
        """
        self._mqtt = mqtt_client
        self._devices: Dict[str, SwitchDevice] = {}  # name -> device
        self._states: Dict[str, SwitchState] = {}    # device_id -> state
        self._state_callback = state_change_callback

        logger.info("✓ 智能开关控制器初始化完成")

    def register_device(
        self,
        device_id: str,
        name: str,
        location: str = "",
        device_type: str = "light"
    ) -> bool:
        """
        注册开关设备

        Args:
            device_id: 设备 ID（用于 MQTT 主题）
            name: 设备名称（中文）
            location: 位置
            device_type: 设备类型

        Returns:
            bool: 是否注册成功
        """
        if name in self._devices:
            logger.warning(f"设备已存在: {name}")
            return False

        device = SwitchDevice(
            device_id=device_id,
            name=name,
            location=location,
            device_type=device_type
        )

        self._devices[name] = device

        # 初始状态未知
        self._states[device_id] = SwitchState(
            device_id=device_id,
            is_on=False,
            last_update=0
        )

        # 订阅状态主题
        self._mqtt.subscribe(
            device.stat_topic,
            lambda topic, payload: self._on_status_message(device, topic, payload)
        )

        logger.info(f"✓ 注册设备: {name} ({device_id})")
        return True

    def unregister_device(self, name: str) -> bool:
        """
        注销设备

        Args:
            name: 设备名称

        Returns:
            bool: 是否注销成功
        """
        if name not in self._devices:
            logger.warning(f"设备不存在: {name}")
            return False

        device = self._devices[name]

        # 取消订阅
        self._mqtt.unsubscribe(device.stat_topic)

        # 删除设备和状态
        del self._devices[name]
        del self._states[device.device_id]

        logger.info(f"✓ 注销设备: {name}")
        return True

    def get_device(self, name: str) -> Optional[SwitchDevice]:
        """获取设备"""
        return self._devices.get(name)

    def list_devices(self, location: str = "") -> List[SwitchDevice]:
        """
        列出所有设备

        Args:
            location: 筛选位置（为空则列出所有）

        Returns:
            list: 设备列表
        """
        devices = list(self._devices.values())

        if location:
            devices = [d for d in devices if d.location == location]

        return devices

    def turn_on(self, name: str) -> bool:
        """
        打开开关

        Args:
            name: 设备名称

        Returns:
            bool: 是否成功
        """
        device = self._devices.get(name)
        if not device:
            logger.error(f"设备不存在: {name}")
            return False

        success = self._mqtt.publish(
            device.cmnd_topic,
            SwitchAction.ON.value
        )

        if success:
            logger.info(f"✓ 打开: {name}")

        return success

    def turn_off(self, name: str) -> bool:
        """
        关闭开关

        Args:
            name: 设备名称

        Returns:
            bool: 是否成功
        """
        device = self._devices.get(name)
        if not device:
            logger.error(f"设备不存在: {name}")
            return False

        success = self._mqtt.publish(
            device.cmnd_topic,
            SwitchAction.OFF.value
        )

        if success:
            logger.info(f"✓ 关闭: {name}")

        return success

    def toggle(self, name: str) -> bool:
        """
        切换开关

        Args:
            name: 设备名称

        Returns:
            bool: 是否成功
        """
        device = self._devices.get(name)
        if not device:
            logger.error(f"设备不存在: {name}")
            return False

        success = self._mqtt.publish(
            device.cmnd_topic,
            SwitchAction.TOGGLE.value
        )

        if success:
            logger.info(f"✓ 切换: {name}")

        return success

    def query_state(self, name: str) -> bool:
        """
        查询状态（发送空消息查询）

        Args:
            name: 设备名称

        Returns:
            bool: 是否成功发送查询
        """
        device = self._devices.get(name)
        if not device:
            logger.error(f"设备不存在: {name}")
            return False

        success = self._mqtt.publish(
            device.cmnd_topic,
            ""  # 空消息查询状态
        )

        if success:
            logger.info(f"✓ 查询状态: {name}")

        return success

    def get_state(self, name: str) -> Optional[SwitchState]:
        """
        获取设备状态

        Args:
            name: 设备名称

        Returns:
            SwitchState: 开关状态
        """
        device = self._devices.get(name)
        if not device:
            return None

        return self._states.get(device.device_id)

    def is_on(self, name: str) -> Optional[bool]:
        """
        检查设备是否打开

        Args:
            name: 设备名称

        Returns:
            bool: 是否打开（未知返回 None）
        """
        state = self.get_state(name)
        if state and state.last_update > 0:
            return state.is_on
        return None

    def turn_on_all(self, location: str = "") -> int:
        """
        打开所有设备

        Args:
            location: 位置筛选（为空则控制所有）

        Returns:
            int: 成功控制的数量
        """
        devices = self.list_devices(location)
        count = 0

        for device in devices:
            if self.turn_on(device.name):
                count += 1

        return count

    def turn_off_all(self, location: str = "") -> int:
        """
        关闭所有设备

        Args:
            location: 位置筛选（为空则控制所有）

        Returns:
            int: 成功控制的数量
        """
        devices = self.list_devices(location)
        count = 0

        for device in devices:
            if self.turn_off(device.name):
                count += 1

        return count

    def _on_status_message(
        self,
        device: SwitchDevice,
        topic: str,
        payload: any
    ) -> None:
        """
        状态消息回调

        Args:
            device: 设备
            topic: 主题
            payload: 消息内容
        """
        try:
            import time

            # 解析状态
            is_on = False

            if isinstance(payload, str):
                is_on = payload.upper() == SwitchAction.ON.value
            elif isinstance(payload, dict):
                is_on = payload.get('POWER', '').upper() == SwitchAction.ON.value

            # 更新状态
            old_state = self._states.get(device.device_id)
            old_is_on = old_state.is_on if old_state else None

            self._states[device.device_id] = SwitchState(
                device_id=device.device_id,
                is_on=is_on,
                last_update=time.time()
            )

            # 状态变化回调
            if self._state_callback and old_is_on != is_on:
                self._state_callback(device.name, is_on)

            logger.debug(
                f"状态更新: {device.name} -> "
                f"{'ON' if is_on else 'OFF'}"
            )

        except Exception as e:
            logger.error(f"状态消息处理失败: {e}")


# ============================================================
# 便捷函数
# ============================================================

def format_switch_response(action: str, device_name: str = "") -> str:
    """
    格式化开关控制回复

    Args:
        action: 动作 (on/off/toggle)
        device_name: 设备名称

    Returns:
        str: 自然语言回复
    """
    templates = {
        "on": [
            "好的，已打开{device}",
            "好的，{device}已打开",
            "已为您打开{device}",
        ],
        "off": [
            "好的，已关闭{device}",
            "好的，{device}已关闭",
            "已为您关闭{device}",
        ],
        "toggle": [
            "好的，已切换{device}",
        ],
        "all_on": [
            "好的，已打开所有设备",
            "已为您打开所有设备",
        ],
        "all_off": [
            "好的，已关闭所有设备",
            "已为您关闭所有设备",
        ],
    }

    if action not in templates:
        return f"好的，{action}"

    # 随机选择模板
    import random
    template = random.choice(templates[action])

    return template.format(device=device_name)
