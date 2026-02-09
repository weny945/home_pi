#!/usr/bin/env python3
"""
测试反向主题订阅
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

config = get_config()
smart_switch_config = config._config.get('smart_switch', {})
mqtt_config_dict = smart_switch_config.get('mqtt', {})

prefix = smart_switch_config.get('prefix', 'bKFSKE')
uid = smart_switch_config.get('uid', 'qNACgJaGGlTG')
devices = smart_switch_config.get('devices', [])

device = devices[0]
mac = device.get('mac', '').lower().replace(":", "").replace("-", "")

# 正常理解
topic_publish = f"/{prefix}/{uid}/{mac}/publish"
topic_subscribe = f"/{prefix}/{uid}/{mac}/subscribe"

print("=" * 70)
print("测试：反向主题订阅")
print("=" * 70)
print()
print("正常理解:")
print(f"  订阅（接收状态）: {topic_publish}")
print(f"  发布（发送命令）: {topic_subscribe}")
print()
print("可能的真实情况:")
print(f"  订阅（接收响应）: {topic_subscribe}")
print(f"  发布（发送命令）: {topic_publish}")
print()

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

received = []
def on_message(t, p):
    print(f"\n{'=' * 70}")
    print(f"✅✅✅ 收到消息！")
    print(f"{'=' * 70}")
    print(f"主题: {t}")
    print(f"内容: {json.dumps(p, indent=2, ensure_ascii=False)}")
    received.append((t, p))

# 连接
print("【1. 连接 MQTT】")
if not client.connect():
    print("❌ 连接失败")
    exit(1)
print("✅ 已连接")

# 尝试两种订阅方式
print(f"\n【2. 尝试反向订阅】")
print(f"订阅: {topic_subscribe}")

result = client.subscribe(topic_subscribe, on_message, qos=1)
if result:
    print(f"✅ 订阅成功")

    # 发送到 publish 主题
    print(f"\n发送命令到: {topic_publish}")
    client.publish(topic_publish, {"type": "info"})

    print("\n等待响应 (10秒)...")
    for i in range(10):
        time.sleep(1)
        if received:
            print(f"\n✅ 反向主题正确！")
            break
        print(f"   {i+1}/10秒...", end="\r")

    if received:
        print(f"\n{'=' * 70}")
        print(f"✅✅✅ 找到问题了！主题是反的！")
        print(f"{'=' * 70}")
        print(f"正确配置:")
        print(f"  订阅主题: {topic_subscribe}")
        print(f"  发布主题: {topic_publish}")
        client.disconnect()
        exit(0)
    else:
        print(f"\n❌ 反向主题也没有响应")

client.disconnect()
print(f"\n{'=' * 70}")
print(f"调试完成")
print(f"{'=' * 70}")
