"""
MQTT 客户端封装
MQTT Client Wrapper for Smart Switch Control
"""
import logging
import json
import threading
import time
from typing import Callable, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MQTTConfig:
    """MQTT 配置"""
    broker: str = "localhost"      # Broker 地址
    port: int = 1883               # Broker 端口
    username: Optional[str] = None  # 用户名
    password: Optional[str] = None  # 密码
    client_id: str = "voice_assistant"  # 客户端 ID
    keepalive: int = 60            # 保活时间（秒）
    qos: int = 1                   # 服务质量等级 (0, 1, 2)
    protocol: int = 3              # 协议版本: 3=MQTTv3.1, 4=MQTTv3.1.1, 5=MQTTv5.0


class MQTTClient:
    """
    MQTT 客户端（支持同步和异步模式）

    GeekOpen 开关通常订阅以下主题：
    - cmnd/{device_id}/POWER   : 控制开关 (ON/OFF)
    - stat/{device_id}/POWER   : 查询状态
    - tele/{device_id}/STATE   : 遥测状态

    发布的主题：
    - stat/{device_id}/RESULT  : 命令执行结果
    - tele/{device_id}/STATE   : 状态更新
    """

    def __init__(self, config: MQTTConfig):
        """
        初始化 MQTT 客户端

        Args:
            config: MQTT 配置
        """
        self._config = config
        self._client = None
        self._connected = False
        self._message_callbacks: Dict[str, Callable] = {}
        self._lock = threading.Lock()

        # 尝试导入 paho-mqtt
        try:
            import paho.mqtt.client as mqtt
            self._mqtt = mqtt
        except ImportError:
            logger.error("未安装 paho-mqtt 库，请运行: pip install paho-mqtt")
            raise

        self._init_client()

    def _init_client(self) -> None:
        """初始化 MQTT 客户端"""
        # 根据配置选择协议版本
        # protocol=3 -> MQTTv3.1
        # protocol=4 -> MQTTv3.1.1
        # protocol=5 -> MQTTv5.0
        protocol_map = {
            3: self._mqtt.MQTTv31,
            4: self._mqtt.MQTTv311,
            5: self._mqtt.MQTTv5  # 注意: 是 MQTTv5 不是 MQTTv50
        }
        protocol = protocol_map.get(self._config.protocol, self._mqtt.MQTTv311)

        logger.info(f"使用 MQTT 协议版本: v{self._config.protocol}")

        self._client = self._mqtt.Client(
            client_id=self._config.client_id,
            protocol=protocol,
            reconnect_on_failure=True  # 启用自动重连
        )

        # 设置回调
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.on_publish = self._on_publish

        # 设置认证
        if self._config.username and self._config.password:
            self._client.username_pw_set(
                self._config.username,
                self._config.password
            )

        logger.info(f"MQTT 客户端初始化完成: {self._config.broker}:{self._config.port}")

    def connect(self) -> bool:
        """
        连接到 MQTT Broker

        Returns:
            bool: 是否连接成功
        """
        try:
            self._client.connect(
                self._config.broker,
                port=self._config.port,
                keepalive=self._config.keepalive
            )

            # 启动网络循环（非阻塞）
            self._client.loop_start()

            # 等待连接确认
            for _ in range(20):  # 最多等待 2 秒
                if self._connected:
                    logger.info(f"✅ MQTT 已连接: {self._config.broker}:{self._config.port}")
                    return True
                time.sleep(0.1)

            logger.warning("MQTT 连接超时")
            return False

        except Exception as e:
            logger.error(f"MQTT 连接失败: {e}")
            return False

    def disconnect(self) -> None:
        """断开连接"""
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False
            logger.info("MQTT 已断开连接")

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected

    def publish(
        self,
        topic: str,
        payload: Any,
        qos: int = None,
        retain: bool = False
    ) -> bool:
        """
        发布消息

        Args:
            topic: 主题
            payload: 消息内容（字符串或字典）
            qos: 服务质量等级（默认使用配置值）
            retain: 是否保留消息

        Returns:
            bool: 是否发布成功
        """
        if not self._connected:
            logger.warning("MQTT 未连接，无法发布消息")
            return False

        try:
            # 如果 payload 是字典，转换为 JSON 字符串
            if isinstance(payload, dict):
                payload = json.dumps(payload, ensure_ascii=False)

            qos = qos or self._config.qos

            result = self._client.publish(
                topic,
                payload,
                qos=qos,
                retain=retain
            )

            if result.rc == self._mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"MQTT 发布: {topic} = {payload}")
                return True
            else:
                logger.error(f"MQTT 发布失败: {result.rc}")
                return False

        except Exception as e:
            logger.error(f"MQTT 发布异常: {e}")
            return False

    def subscribe(
        self,
        topic: str,
        callback: Callable[[str, Any], None],
        qos: int = None
    ) -> bool:
        """
        订阅主题

        Args:
            topic: 主题（支持通配符 + 和 #）
            callback: 消息回调函数 (topic, payload) -> None
            qos: 服务质量等级

        Returns:
            bool: 是否订阅成功
        """
        try:
            qos = qos or self._config.qos

            result = self._client.subscribe(topic, qos=qos)

            if result[0] == self._mqtt.MQTT_ERR_SUCCESS:
                with self._lock:
                    self._message_callbacks[topic] = callback

                logger.info(f"MQTT 订阅: {topic} (QoS={qos})")
                return True
            else:
                logger.error(f"MQTT 订阅失败: {result[0]}")
                return False

        except Exception as e:
            logger.error(f"MQTT 订阅异常: {e}")
            return False

    def unsubscribe(self, topic: str) -> bool:
        """
        取消订阅

        Args:
            topic: 主题

        Returns:
            bool: 是否取消成功
        """
        try:
            result = self._client.unsubscribe(topic)

            if result[0] == self._mqtt.MQTT_ERR_SUCCESS:
                with self._lock:
                    self._message_callbacks.pop(topic, None)

                logger.info(f"MQTT 取消订阅: {topic}")
                return True
            else:
                logger.error(f"MQTT 取消订阅失败: {result[0]}")
                return False

        except Exception as e:
            logger.error(f"MQTT 取消订阅异常: {e}")
            return False

    def _on_connect(self, client, userdata, flags, rc) -> None:
        """连接回调"""
        if rc == 0:
            self._connected = True
            logger.info("MQTT 连接成功")
        else:
            self._connected = False
            logger.error(f"MQTT 连接失败，错误码: {rc}")

    def _on_disconnect(self, client, userdata, rc) -> None:
        """断开连接回调"""
        self._connected = False
        if rc != 0:
            logger.warning(f"MQTT 意外断开连接，错误码: {rc}")

    def _on_message(self, client, userdata, msg) -> None:
        """消息接收回调"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')

            # 尝试解析 JSON
            try:
                payload = json.loads(payload)
            except (json.JSONDecodeError, TypeError):
                pass  # 保持原始字符串

            logger.debug(f"MQTT 收到消息: {topic} = {payload}")

            # 查找匹配的回调
            with self._lock:
                # 精确匹配
                if topic in self._message_callbacks:
                    self._message_callbacks[topic](topic, payload)
                    return

                # 通配符匹配
                for pattern, callback in self._message_callbacks.items():
                    if self._match_topic(topic, pattern):
                        callback(topic, payload)
                        return

        except Exception as e:
            logger.error(f"MQTT 消息处理失败: {e}")

    def _on_publish(self, client, userdata, mid) -> None:
        """发布确认回调"""
        logger.debug(f"MQTT 消息已发布: msg_id={mid}")

    def _match_topic(self, topic: str, pattern: str) -> bool:
        """
        匹配主题（支持通配符）

        Args:
            topic: 实际主题
            pattern: 匹配模式（支持 + 和 #）

        Returns:
            bool: 是否匹配
        """
        # 将 MQTT 通配符转换为正则表达式
        # + → 匹配单级
        # # → 匹配多级
        import re

        # 转义特殊字符
        regex = pattern.replace('+', '[^/]+')
        regex = regex.replace('#', '.*')
        regex = f'^{regex}$'

        return re.match(regex, topic) is not None


# ============================================================
# 便捷函数
# ============================================================

def create_mqtt_client_from_config(config: dict) -> MQTTClient:
    """
    从配置字典创建 MQTT 客户端

    Args:
        config: 配置字典

    Returns:
        MQTTClient: MQTT 客户端实例
    """
    mqtt_config = MQTTConfig(
        broker=config.get('broker', 'localhost'),
        port=config.get('port', 1883),
        username=config.get('username'),
        password=config.get('password'),
        client_id=config.get('client_id', 'voice_assistant'),
        keepalive=config.get('keepalive', 60),
        qos=config.get('qos', 1),
        protocol=config.get('protocol', 3)  # 添加协议版本参数
    )

    return MQTTClient(mqtt_config)
