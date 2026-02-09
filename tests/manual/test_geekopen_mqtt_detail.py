#!/usr/bin/env python3
"""
GeekOpen MQTT 详细调试脚本
用于诊断智能开关通信问题
"""
import sys
import time
import json
import logging

# 添加项目路径
sys.path.insert(0, '/home/biwenyuan/PycharmProjects/home_pi')

from src.config import get_config
from src.smart_switch.mqtt_client import MQTTClient, MQTTConfig


# 设置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """主测试函数"""
    print("=" * 60)
    print("GeekOpen MQTT 详细调试")
    print("=" * 60)

    # 加载配置
    config = get_config()
    smart_switch_config = config._config.get('smart_switch', {})
    mqtt_config_dict = smart_switch_config.get('mqtt', {})

    # 打印配置
    print("\n【MQTT 配置】")
    print(f"  Broker: {mqtt_config_dict.get('broker')}")
    print(f"  Port: {mqtt_config_dict.get('port')}")
    print(f"  Username: {mqtt_config_dict.get('username')}")
    print(f"  Client ID: {mqtt_config_dict.get('client_id')}")
    print(f"  Protocol: v{mqtt_config_dict.get('protocol', 3)}")

    protocol_config = smart_switch_config.get('protocol', 'geekopen')
    prefix = smart_switch_config.get('prefix', 'bKFSKE')
    uid = smart_switch_config.get('uid', 'qNACgJaGGlTG')

    print(f"\n【GeekOpen 协议配置】")
    print(f"  Prefix: {prefix}")
    print(f"  UID: {uid}")

    # 获取设备配置
    devices = smart_switch_config.get('devices', [])
    if not devices:
        print("\n❌ 没有配置设备")
        return

    device = devices[0]
    mac = device.get('mac', '').lower().replace(":", "").replace("-", "")
    device_name = device.get('name', 'Unknown')

    print(f"\n【设备配置】")
    print(f"  名称: {device_name}")
    print(f"  MAC: {mac}")
    print(f"  按键数: {device.get('key_count', 2)}")

    # 构建主题
    subscribe_topic = f"/{prefix}/{uid}/{mac}/publish"
    publish_topic = f"/{prefix}/{uid}/{mac}/subscribe"

    print(f"\n【MQTT 主题】")
    print(f"  订阅主题（接收状态）: {subscribe_topic}")
    print(f"  发布主题（发送命令）: {publish_topic}")

    # 创建 MQTT 客户端
    print(f"\n【创建 MQTT 客户端】")
    mqtt_config = MQTTConfig(
        broker=mqtt_config_dict.get('broker', 'localhost'),
        port=mqtt_config_dict.get('port', 1883),
        username=mqtt_config_dict.get('username'),
        password=mqtt_config_dict.get('password'),
        client_id=mqtt_config_dict.get('client_id', 'voice_assistant_debug'),
        keepalive=60,
        qos=1,
        protocol=mqtt_config_dict.get('protocol', 3)
    )

    mqtt_client = MQTTClient(mqtt_config)

    # 消息接收计数器
    received_messages = []

    def on_message(topic, payload):
        """消息回调"""
        print(f"\n📨 收到 MQTT 消息:")
        print(f"   主题: {topic}")
        print(f"   内容: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        received_messages.append({'topic': topic, 'payload': payload, 'time': time.time()})

    # 连接 MQTT
    print(f"\n【连接 MQTT Broker】")
    if not mqtt_client.connect():
        print("❌ MQTT 连接失败")
        return

    print("✅ MQTT 连接成功")

    # 订阅状态主题
    print(f"\n【订阅状态主题】")
    mqtt_client.subscribe(subscribe_topic, on_message, qos=1)
    print(f"✅ 已订阅: {subscribe_topic}")

    # 等待接收初始状态
    print(f"\n【等待设备状态消息】(5秒)")
    time.sleep(5)

    if received_messages:
        print(f"\n✅ 收到 {len(received_messages)} 条状态消息")
        for i, msg in enumerate(received_messages, 1):
            print(f"\n消息 #{i}:")
            print(f"  时间: {time.strftime('%H:%M:%S', time.localtime(msg['time']))}")
            print(f"  主题: {msg['topic']}")
            print(f"  内容: {json.dumps(msg['payload'], indent=4, ensure_ascii=False)}")
    else:
        print(f"\n⚠️  没有收到设备状态消息")
        print("   这可能意味着:")
        print("   - 设备离线")
        print("   - 设备未连接到 MQTT Broker")
        print("   - 主题前缀或 UID 不正确")

    # 发送测试命令
    print(f"\n【发送测试命令】")
    print(f"目标主题: {publish_topic}")

    # 测试不同的命令格式
    test_commands = [
        {
            "name": "❌ 旧格式: 仅按键状态",
            "payload": {"key1": 1}
        },
        {
            "name": "✅ 正确格式: type=event + 按键状态",
            "payload": {"type": "event", "key1": 1, "key2": 0, "key3": 0}
        },
        {
            "name": "✅ 关闭命令: type=event + key1=0",
            "payload": {"type": "event", "key1": 0, "key2": 0, "key3": 0}
        }
    ]

    for i, cmd in enumerate(test_commands, 1):
        print(f"\n--- 测试 {i}: {cmd['name']} ---")
        print(f"Payload: {json.dumps(cmd['payload'], ensure_ascii=False)}")

        result = mqtt_client.publish(publish_topic, cmd['payload'], qos=1)

        if result:
            print(f"✅ 命令已发送")

            # 等待响应
            print(f"等待响应 (3秒)...")
            initial_count = len(received_messages)
            time.sleep(3)

            new_messages = received_messages[initial_count:]
            if new_messages:
                print(f"✅ 收到 {len(new_messages)} 条响应:")
                for msg in new_messages:
                    print(f"   {json.dumps(msg['payload'], indent=2, ensure_ascii=False)}")
            else:
                print(f"⚠️  没有收到响应")

            # 间隔
            if i < len(test_commands):
                time.sleep(1)
        else:
            print(f"❌ 命令发送失败")

    # 查询状态命令
    print(f"\n【发送查询状态命令】")
    query_payload = {"type": "info"}
    print(f"Payload: {json.dumps(query_payload, ensure_ascii=False)}")

    mqtt_client.publish(publish_topic, query_payload, qos=1)
    time.sleep(3)

    # 总结
    print(f"\n【总结】")
    print(f"总共收到 {len(received_messages)} 条消息")

    if received_messages:
        print(f"\n所有收到的消息:")
        for i, msg in enumerate(received_messages, 1):
            print(f"\n{i}. {msg['topic']}")
            print(f"   {json.dumps(msg['payload'], indent=2, ensure_ascii=False)}")

    # 断开连接
    print(f"\n【断开连接】")
    mqtt_client.disconnect()
    print("✅ 已断开")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        print(f"\n❌ 错误: {e}")
