"""
GeekOpen 智能开关控制器（云 MQTT 协议）
GeekOpen Smart Switch Controller - Cloud MQTT Protocol

GeekOpen 云 MQTT 协议规范：
- 订阅主题（接收状态）: /{prefix}/{mac}/publish
- 发布主题（发送命令）: /{prefix}/{mac}/subscribe

设备状态消息格式：
{
  "messageId": "",
  "mac": "D48AFC3AF2EA",
  "type": "Zero-2",
  "version": "2.1.2",
  "wifiLock": 0,
  "keyLock": 0,
  "ip": "192.168.2.135",
  "ssid": "@PHICOMM_EC",
  "key1": 0,  # 按键1状态 (0=关, 1=开)
  "key2": 0,  # 按键2状态 (Zero-2 有2个按键)
  "key3": 0,  # Zero-4 有4个按键
  "key4": 0
}

控制命令格式（推测）：
{
  "key1": 1,  # 1=打开, 0=关闭
  "key2": 0,
  "key3": 0,
  "key4": 0
}
"""
import logging
import json
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from .mqtt_client import MQTTClient

logger = logging.getLogger(__name__)


class SwitchKey(Enum):
    """GeekOpen 开关按键"""
    KEY1 = "key1"
    KEY2 = "key2"
    KEY3 = "key3"
    KEY4 = "key4"


@dataclass
class GeekOpenDevice:
    """GeekOpen 设备定义"""
    mac: str                  # 设备 MAC 地址（用于主题）
    name: str                 # 设备名称（中文，如"客厅灯"）
    location: str = ""        # 位置（如"客厅"）
    key_count: int = 2        # 按键数量 (Zero-2=2, Zero-4=4)
    prefix: str = "bKFSKE"    # 主题前缀（默认）
    uid: str = "qNACgJaGGlTG" # 用户 ID（默认）
    key_mapping: dict = None  # 按键映射 {"key1": "主灯", "key2": "副灯"}

    @property
    def subscribe_topic(self) -> str:
        """订阅主题（接收设备状态）"""
        mac_lower = self.mac.lower()
        return f"/{self.prefix}/{self.uid}/{mac_lower}/subscribe"

    @property
    def publish_topic(self) -> str:
        """发布主题（发送控制命令）"""
        mac_lower = self.mac.lower()
        return f"/{self.prefix}/{self.uid}/{mac_lower}/publish"

    def get_key_name(self, key_index: int) -> str:
        """获取按键名称"""
        return f"key{key_index}"


@dataclass
class GeekOpenSwitchState:
    """GeekOpen 开关状态"""
    mac: str
    key1: bool = False
    key2: bool = False
    key3: bool = False
    key4: bool = False
    last_update: float = 0.0

    def get_key_state(self, key: SwitchKey) -> Optional[bool]:
        """获取指定按键状态"""
        return getattr(self, key.value, None)

    def set_key_state(self, key: SwitchKey, state: bool) -> None:
        """设置按键状态"""
        setattr(self, key.value, state)
        self.last_update = time.time()


class GeekOpenController:
    """
    GeekOpen 智能开关控制器（云 MQTT 协议）

    使用示例：
    ```python
    controller = GeekOpenController(mqtt_client)

    # 注册设备
    controller.register_device(
        mac="D48AFC3AF2EA",
        name="客厅灯",
        key_count=2
    )

    # 控制开关
    controller.turn_on("客厅灯", key=SwitchKey.KEY1)
    controller.turn_off("客厅灯", key=SwitchKey.KEY1)

    # 查询状态
    state = controller.get_state("客厅灯")
    print(f"按键1: {'开' if state.key1 else '关'}")
    ```
    """

    def __init__(
        self,
        mqtt_client: MQTTClient,
        state_change_callback: Optional[Callable[[str, SwitchKey, bool], None]] = None
    ):
        """
        初始化 GeekOpen 控制器

        Args:
            mqtt_client: MQTT 客户端
            state_change_callback: 状态变化回调 (device_name, key, is_on) -> None
        """
        self._mqtt = mqtt_client
        self._devices: Dict[str, GeekOpenDevice] = {}  # name -> device
        self._states: Dict[str, GeekOpenSwitchState] = {}  # mac -> state
        self._state_callback = state_change_callback

        logger.info("✓ GeekOpen 智能开关控制器初始化完成")

    def register_device(
        self,
        mac: str,
        name: str,
        location: str = "",
        key_count: int = 2,
        prefix: str = "bKFSKE",
        uid: str = "qNACgJaGGlTG",
        key_mapping: dict = None
    ) -> bool:
        """
        注册 GeekOpen 设备

        Args:
            mac: 设备 MAC 地址（如 "D48AFC3AF2EA"）
            name: 设备名称（中文）
            location: 位置
            key_count: 按键数量 (Zero-2=2, Zero-4=4)
            prefix: MQTT 主题前缀
            uid: 用户 ID
            key_mapping: 按键映射 {"key1": "主灯", "key2": "副灯"}

        Returns:
            bool: 是否注册成功
        """
        if name in self._devices:
            logger.warning(f"设备已存在: {name}")
            return False

        # 标准化 MAC 地址（转小写，去分隔符）
        mac_clean = mac.lower().replace(":", "").replace("-", "")

        device = GeekOpenDevice(
            mac=mac_clean,
            name=name,
            location=location,
            key_count=key_count,
            prefix=prefix,
            uid=uid,
            key_mapping=key_mapping
        )

        self._devices[name] = device

        # 初始状态
        self._states[mac_clean] = GeekOpenSwitchState(mac=mac_clean)

        # 订阅设备状态主题
        self._mqtt.subscribe(
            device.subscribe_topic,
            lambda topic, payload: self._on_status_message(device, topic, payload)
        )

        logger.info(f"✓ 注册 GeekOpen 设备: {name} ({mac_clean})")
        logger.info(f"  订阅主题: {device.subscribe_topic}")
        logger.info(f"  发布主题: {device.publish_topic}")

        # 发送查询命令获取初始状态
        self._query_state(device)

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
        self._mqtt.unsubscribe(device.subscribe_topic)

        # 删除设备和状态
        del self._devices[name]
        del self._states[device.mac]

        logger.info(f"✓ 注销设备: {name}")
        return True

    def get_device(self, name: str) -> Optional[GeekOpenDevice]:
        """获取设备"""
        return self._devices.get(name)

    def list_devices(self, location: str = "") -> List[GeekOpenDevice]:
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

    def turn_on(self, name: str, key: SwitchKey = SwitchKey.KEY1) -> bool:
        """
        打开开关

        Args:
            name: 设备名称
            key: 按键（默认 KEY1）

        Returns:
            bool: 是否成功
        """
        device = self._devices.get(name)
        if not device:
            logger.error(f"设备不存在: {name}")
            return False

        # 记录当前状态（用于等待状态变化）
        state = self._states.get(device.mac)
        initial_state = state.get_key_state(key) if state else None

        # GeekOpen 协议要求：命令必须包含 type: "event"
        # 并且需要包含所有按键状态
        payload = {
            "type": "event",
            key.value: 1
        }

        # 添加其他按键（保持关闭状态）
        for i in range(1, device.key_count + 1):
            other_key = f"key{i}"
            if other_key not in payload:
                payload[other_key] = 0

        logger.info(f"📤 发送打开命令: {name} - {key.value}")
        logger.debug(f"   命令: {payload}")

        success = self._mqtt.publish(
            device.publish_topic,
            payload
        )

        if not success:
            logger.error(f"❌ 命令发送失败: {name}")
            return False

        # 等待设备返回状态确认（最多 3 秒）
        logger.info(f"⏳ 等待设备确认...")
        for i in range(30):
            time.sleep(0.1)
            state = self._states.get(device.mac)
            if state and state.get_key_state(key) is True:
                # 确认状态已变为打开
                logger.info(f"✅ 设备已确认: {name} - {key.value} 已打开")
                return True

        logger.warning(f"⚠️  未收到设备确认: {name} (超时)")
        return True  # 仍然返回 True，因为命令已发送

    def turn_off(self, name: str, key: SwitchKey = SwitchKey.KEY1) -> bool:
        """
        关闭开关

        Args:
            name: 设备名称
            key: 按键（默认 KEY1）

        Returns:
            bool: 是否成功
        """
        device = self._devices.get(name)
        if not device:
            logger.error(f"设备不存在: {name}")
            return False

        # 记录当前状态（用于等待状态变化）
        state = self._states.get(device.mac)
        initial_state = state.get_key_state(key) if state else None

        # GeekOpen 协议要求：命令必须包含 type: "event"
        # 并且需要包含所有按键状态
        payload = {
            "type": "event",
            key.value: 0
        }

        # 添加其他按键（保持关闭状态）
        for i in range(1, device.key_count + 1):
            other_key = f"key{i}"
            if other_key not in payload:
                payload[other_key] = 0

        logger.info(f"📤 发送关闭命令: {name} - {key.value}")
        logger.debug(f"   命令: {payload}")

        success = self._mqtt.publish(
            device.publish_topic,
            payload
        )

        if not success:
            logger.error(f"❌ 命令发送失败: {name}")
            return False

        # 等待设备返回状态确认（最多 3 秒）
        logger.info(f"⏳ 等待设备确认...")
        for i in range(30):
            time.sleep(0.1)
            state = self._states.get(device.mac)
            if state and state.get_key_state(key) is False:
                # 确认状态已变为关闭
                logger.info(f"✅ 设备已确认: {name} - {key.value} 已关闭")
                return True

        logger.warning(f"⚠️  未收到设备确认: {name} (超时)")
        return True  # 仍然返回 True，因为命令已发送

    def toggle(self, name: str, key: SwitchKey = SwitchKey.KEY1) -> bool:
        """
        切换开关

        Args:
            name: 设备名称
            key: 按键（默认 KEY1）

        Returns:
            bool: 是否成功
        """
        state = self.get_state(name)
        if not state:
            return False

        current_state = state.get_key_state(key)
        if current_state is None:
            return False

        # 根据当前状态决定打开或关闭
        if current_state:
            return self.turn_off(name, key)
        else:
            return self.turn_on(name, key)

    def query_state(self, name: str) -> bool:
        """
        查询状态（发送查询命令）

        Args:
            name: 设备名称

        Returns:
            bool: 是否成功发送查询
        """
        device = self._devices.get(name)
        if not device:
            logger.error(f"设备不存在: {name}")
            return False

        return self._query_state(device)

    def _query_state(self, device: GeekOpenDevice) -> bool:
        """发送查询状态命令"""
        # 发送空 JSON 或查询命令
        # 根据协议，可能需要发送特定的查询命令
        payload = {"type": "info"}

        success = self._mqtt.publish(
            device.publish_topic,
            payload
        )

        if success:
            logger.info(f"✓ 查询状态: {device.name}")

        return success

    def get_state(self, name: str) -> Optional[GeekOpenSwitchState]:
        """
        获取设备状态

        Args:
            name: 设备名称

        Returns:
            GeekOpenSwitchState: 开关状态
        """
        device = self._devices.get(name)
        if not device:
            return None

        return self._states.get(device.mac)

    def is_on(self, name: str, key: SwitchKey = SwitchKey.KEY1) -> Optional[bool]:
        """
        检查设备按键是否打开

        Args:
            name: 设备名称
            key: 按键

        Returns:
            bool: 是否打开（未知返回 None）
        """
        state = self.get_state(name)
        if state and state.last_update > 0:
            return state.get_key_state(key)
        return None

    def _on_status_message(
        self,
        device: GeekOpenDevice,
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
            # 解析 JSON
            if isinstance(payload, str):
                data = json.loads(payload)
            elif isinstance(payload, dict):
                data = payload
            else:
                logger.warning(f"未知的消息格式: {type(payload)}")
                return

            logger.debug(f"收到 {device.name} 状态: {data}")

            # 更新状态
            state = self._states.get(device.mac)
            if not state:
                logger.error(f"找不到设备状态: {device.mac}")
                return

            # 更新各个按键状态
            keys_to_check = [SwitchKey.KEY1, SwitchKey.KEY2, SwitchKey.KEY3, SwitchKey.KEY4]

            for key in keys_to_check:
                if key.value in data:
                    old_is_on = state.get_key_state(key)
                    new_is_on = data[key.value] == 1

                    state.set_key_state(key, new_is_on)

                    # 状态变化回调
                    if self._state_callback and old_is_on != new_is_on:
                        self._state_callback(device.name, key, new_is_on)
                        logger.info(
                            f"状态变化: {device.name} - {key.value} -> "
                            f"{'ON' if new_is_on else 'OFF'}"
                        )

        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
        except Exception as e:
            logger.error(f"状态消息处理失败: {e}")


# ============================================================
# 便捷函数
# ============================================================

def format_geekopen_response(
    action: str,
    device_name: str = "",
    key: SwitchKey = SwitchKey.KEY1,
    key_mapping: dict = None
) -> str:
    """
    格式化 GeekOpen 开关控制回复

    Args:
        action: 动作 (on/off/toggle)
        device_name: 设备名称
        key: 按键
        key_mapping: 按键映射配置 {"key1": "主灯", "key2": "副灯"}

    Returns:
        str: 自然语言回复
    """
    # 默认按键名称
    key_names = {
        SwitchKey.KEY1: "开关1",
        SwitchKey.KEY2: "开关2",
        SwitchKey.KEY3: "开关3",
        SwitchKey.KEY4: "开关4",
    }

    # 如果有 key_mapping，使用配置的名称
    if key_mapping:
        key_name_map = {
            SwitchKey.KEY1: key_mapping.get("key1", "开关1"),
            SwitchKey.KEY2: key_mapping.get("key2", "开关2"),
            SwitchKey.KEY3: key_mapping.get("key3", "开关3"),
            SwitchKey.KEY4: key_mapping.get("key4", "开关4"),
        }
        key_name = key_name_map.get(key, "开关")
    else:
        key_name = key_names.get(key, "开关")

    templates = {
        "on": [
            "好的，已打开{device}",
            f"好的，已打开{device_name}的{key_name}",
        ],
        "off": [
            "好的，已关闭{device}",
            f"好的，已关闭{device_name}的{key_name}",
        ],
    }

    if action not in templates:
        return f"好的，{action}"

    # 随机选择模板
    import random
    template = random.choice(templates[action])

    return template.format(device=device_name)
