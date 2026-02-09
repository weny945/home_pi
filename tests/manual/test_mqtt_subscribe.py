#!/usr/bin/env python3
"""
MQTT 订阅调试 - 测试不同的订阅方式
"""
import sys
import os
import time
import json

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, project_root)

from src.config import get_config
from src.smart_switch.mqtt_client import MQTTClient, MQTTConfig

# 加载配置
config = get_config()
smart_switch_config = config._config.get('smart_switch', {})
mqtt_config_dict = smart_switch_config.get('mqtt', {})

prefix = smart_switch_config.get('prefix', 'bKFSKE')
uid = smart_switch_config.get('uid', 'qNACgJaGGlTG')
devices = smart_switch_config.get('devices', [])

device = devices[0]
mac = device.get('mac', '').lower().replace(":", "").replace("-", "")

# 测试不同的主题模式
test_topics = [
    f"/{prefix}/{uid}/{mac}/publish",  # 精确匹配
    f"/{prefix}/{uid}/+/publish",       # 通配符（匹配任何 MAC）
    f"/{prefix}/#/",                     # 更宽的通配符
    f"{prefix}/{uid}/{mac}/publish",    # 不带前导斜杠
]

print("=" * 70)
print("MQTT 订阅调试 - 测试不同的主题模式")
print("=" * 70)

for i, topic in enumerate(test_topics, 1):
    print(f"\n{'=' * 70}")
    print(f"测试 {i}: {topic}")
    print(f"{'=' * 70}")

    mqtt_config = MQTTConfig(
        broker=mqtt_config_dict.get('broker'),
        port=mqtt_config_dict.get('port'),
        username=mqtt_config_dict.get('username'),
        password=mqtt_config_dict.get('password'),
        client_id=mqtt_config_dict.get('client_id'),
        keepalive=60,
        qos=1,
        protocol=3
    )

    client = MQTTClient(mqtt_config)

    # 消息回调
    received = []
    def on_message(t, p):
        print(f"\n✅✅✅ 收到消息！")
        print(f"   主题: {t}")
        print(f"   内容: {json.dumps(p, indent=2, ensure_ascii=False)}")
        received.append((t, p))

    # 连接
    if not client.connect():
        print("❌ 连接失败")
        client.disconnect()
        continue

    print("✅ 已连接")

    # 订阅
    result = client.subscribe(topic, on_message, qos=1)
    if not result:
        print("❌ 订阅失败")
        client.disconnect()
        continue

    print(f"✅ 已订阅: {topic}")

    # 发送查询命令
    publish_topic = f"/{prefix}/{uid}/{mac}/subscribe"
    print(f"\n发送查询命令到: {publish_topic}")
    client.publish(publish_topic, {"type": "info"})

    # 等待响应
    print(f"\n等待响应 (8秒)...")
    for j in range(8):
        time.sleep(1)
        if received:
            print(f"\n✅ 在第 {j+1} 秒收到消息！")
            break
        print(f"   {j+1}/8秒...", end="\r")

    if received:
        print(f"\n✅✅✅ 成功！主题模式正确：{topic}")
        client.disconnect()
        break
    else:
        print(f"\n❌ 未收到响应")

    client.disconnect()
    time.sleep(1)

print(f"\n{'=' * 70}")
print(f"调试完成")
print(f"{'=' * 70}")
