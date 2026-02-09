"""
智能开关模块单元测试
Unit Tests for Smart Switch Module
"""
import pytest
from unittest.mock import Mock, MagicMock, patch

from src.smart_switch.mqtt_client import MQTTClient, MQTTConfig
from src.smart_switch.switch_controller import (
    SwitchController,
    SwitchDevice,
    SwitchState
)
from src.smart_switch.intent_detector import (
    detect_switch_intent,
    SwitchIntent,
    format_switch_confirm
)


# ============================================================
# MQTT 客户端测试
# ============================================================

class TestMQTTConfig:
    """MQTT 配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = MQTTConfig()
        assert config.broker == "localhost"
        assert config.port == 1883
        assert config.username is None
        assert config.password is None
        assert config.client_id == "voice_assistant"
        assert config.keepalive == 60
        assert config.qos == 1

    def test_custom_config(self):
        """测试自定义配置"""
        config = MQTTConfig(
            broker="192.168.1.100",
            port=8883,
            username="admin",
            password="secret",
            client_id="test_client"
        )
        assert config.broker == "192.168.1.100"
        assert config.port == 8883
        assert config.username == "admin"
        assert config.password == "secret"
        assert config.client_id == "test_client"


class TestMQTTClient:
    """MQTT 客户端测试"""

    @pytest.fixture
    def mock_paho(self):
        """Mock paho-mqtt 库"""
        with patch('src.smart_switch.mqtt_client.mqtt') as mock:
            yield mock

    @pytest.fixture
    def mqtt_client(self, mock_paho):
        """创建 MQTT 客户端实例"""
        config = MQTTConfig(broker="test.local", port=1883)
        return MQTTClient(config)

    def test_init_client(self, mock_paho):
        """测试客户端初始化"""
        config = MQTTConfig(broker="test.local")
        client = MQTTClient(config)

        assert client._config.broker == "test.local"
        assert client._client is not None
        assert not client._connected

    def test_connect_success(self, mqtt_client, mock_paho):
        """测试成功连接"""
        # Mock 连接成功
        mock_client = MagicMock()
        mqtt_client._client = mock_client

        # 模拟连接成功回调
        def on_connect_side_effect(client, userdata, flags, rc):
            mqtt_client._connected = True

        mock_client.on_connect = on_connect_side_effect

        # 调用连接
        result = mqtt_client.connect()

        assert result is True

    def test_publish_message(self, mqtt_client):
        """测试发布消息"""
        mock_client = MagicMock()
        mqtt_client._client = mock_client
        mqtt_client._connected = True

        # Mock 发布成功
        mock_client.publish.return_value.rc = 0  # MQTT_ERR_SUCCESS

        result = mqtt_client.publish("test/topic", "ON")

        assert result is True
        mock_client.publish.assert_called_once()

    def test_publish_dict_payload(self, mqtt_client):
        """测试发布字典负载"""
        mock_client = MagicMock()
        mqtt_client._client = mock_client
        mqtt_client._connected = True

        mock_client.publish.return_value.rc = 0

        import json
        payload = {"POWER": "ON"}
        result = mqtt_client.publish("test/topic", payload)

        assert result is True
        # 验证负载被转换为 JSON 字符串
        call_args = mock_client.publish.call_args
        assert "POWER" in call_args[0][1]


# ============================================================
# 开关控制器测试
# ============================================================

class TestSwitchDevice:
    """开关设备测试"""

    def test_device_properties(self):
        """测试设备属性"""
        device = SwitchDevice(
            device_id="switch_01",
            name="客厅灯",
            location="客厅",
            device_type="light"
        )

        assert device.device_id == "switch_01"
        assert device.name == "客厅灯"
        assert device.location == "客厅"
        assert device.device_type == "light"
        assert device.cmnd_topic == "cmnd/switch_01/POWER"
        assert device.stat_topic == "stat/switch_01/POWER"
        assert device.tele_topic == "tele/switch_01/STATE"


class TestSwitchController:
    """开关控制器测试"""

    @pytest.fixture
    def mock_mqtt_client(self):
        """Mock MQTT 客户端"""
        mock = Mock()
        mock.publish.return_value = True
        mock.subscribe.return_value = True
        return mock

    @pytest.fixture
    def controller(self, mock_mqtt_client):
        """创建开关控制器"""
        return SwitchController(mock_mqtt_client)

    def test_register_device(self, controller, mock_mqtt_client):
        """测试注册设备"""
        result = controller.register_device(
            device_id="switch_01",
            name="客厅灯",
            location="客厅"
        )

        assert result is True
        assert "客厅灯" in controller._devices
        mock_mqtt_client.subscribe.assert_called_once()

    def test_register_duplicate_device(self, controller):
        """测试重复注册设备"""
        controller.register_device("switch_01", "客厅灯")

        result = controller.register_device("switch_02", "客厅灯")

        assert result is False

    def test_turn_on(self, controller, mock_mqtt_client):
        """测试打开开关"""
        controller.register_device("switch_01", "客厅灯")

        result = controller.turn_on("客厅灯")

        assert result is True
        mock_mqtt_client.publish.assert_called_with(
            "cmnd/switch_01/POWER",
            "ON"
        )

    def test_turn_off(self, controller, mock_mqtt_client):
        """测试关闭开关"""
        controller.register_device("switch_01", "客厅灯")

        result = controller.turn_off("客厅灯")

        assert result is True
        mock_mqtt_client.publish.assert_called_with(
            "cmnd/switch_01/POWER",
            "OFF"
        )

    def test_toggle(self, controller, mock_mqtt_client):
        """测试切换开关"""
        controller.register_device("switch_01", "客厅灯")

        result = controller.toggle("客厅灯")

        assert result is True
        mock_mqtt_client.publish.assert_called_with(
            "cmnd/switch_01/POWER",
            "TOGGLE"
        )

    def test_turn_on_nonexistent_device(self, controller):
        """测试控制不存在的设备"""
        result = controller.turn_on("不存在的设备")

        assert result is False

    def test_list_devices(self, controller):
        """测试列出设备"""
        controller.register_device("switch_01", "客厅灯", location="客厅")
        controller.register_device("switch_02", "卧室灯", location="卧室")
        controller.register_device("switch_03", "风扇", location="客厅")

        # 列出所有设备
        all_devices = controller.list_devices()
        assert len(all_devices) == 3

        # 按位置筛选
        living_room_devices = controller.list_devices(location="客厅")
        assert len(living_room_devices) == 2

    def test_state_update(self, controller):
        """测试状态更新"""
        controller.register_device("switch_01", "客厅灯")

        # 初始状态
        state = controller.get_state("客厅灯")
        assert state is not None
        assert state.is_on is False

        # 模拟接收状态消息
        device = controller.get_device("客厅灯")
        controller._on_status_message(device, "stat/switch_01/POWER", "ON")

        # 更新后状态
        updated_state = controller.get_state("客厅灯")
        assert updated_state.is_on is True


# ============================================================
# 意图检测器测试
# ============================================================

class TestSwitchIntentDetector:
    """开关意图检测器测试"""

    def test_detect_turn_on_intent(self):
        """测试检测打开意图"""
        intent = detect_switch_intent("打开客厅灯")

        assert intent is not None
        assert intent.action == "on"
        assert intent.device == "客厅灯"

    def test_detect_turn_off_intent(self):
        """测试检测关闭意图"""
        intent = detect_switch_intent("关闭卧室灯")

        assert intent is not None
        assert intent.action == "off"
        assert intent.device == "卧室灯"

    def test_detect_toggle_intent(self):
        """测试检测切换意图"""
        intent = detect_switch_intent("切换风扇")

        assert intent is not None
        assert intent.action == "toggle"
        assert "风扇" in intent.device

    def test_detect_all_devices(self):
        """测试检测全部设备意图"""
        intent = detect_switch_intent("打开所有灯")

        assert intent is not None
        assert intent.action == "on"
        assert intent.all is True

    def test_detect_location_aware(self):
        """测试检测位置感知意图"""
        intent = detect_switch_intent("打开客厅的灯")

        assert intent is not None
        assert intent.action == "on"
        assert intent.location == "客厅"

    def test_no_switch_intent(self):
        """测试非开关指令"""
        intent = detect_switch_intent("今天天气怎么样")

        assert intent is None

    def test_detect_with_known_devices(self):
        """测试使用已知设备列表检测"""
        known_devices = ["客厅灯", "卧室灯", "风扇"]

        intent = detect_switch_intent("打开风扇", known_devices)

        assert intent is not None
        assert intent.action == "on"
        assert intent.device == "风扇"

    def test_format_switch_confirm(self):
        """测试格式化开关确认回复"""
        intent = SwitchIntent(action="on", device="客厅灯")
        reply = format_switch_confirm(intent, success=True)

        assert "客厅灯" in reply or "打开" in reply


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
