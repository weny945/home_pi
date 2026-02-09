#!/usr/bin/env python3
"""
GeekOpen 详细调试 - 加入状态查询
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
device_name = device.get('name', 'Unknown')

subscribe_topic = f"/{prefix}/{uid}/{mac}/publish"
publish_topic = f"/{prefix}/{uid}/{mac}/subscribe"

print("=" * 70)
print(f"GeekOpen 详细调试 - {device_name}")
print("=" * 70)
print(f"订阅主题: {subscribe_topic}")
print(f"发布主题: {publish_topic}")
print()

# 创建 MQTT 客户端
mqtt_config = MQTTConfig(
    broker=mqtt_config_dict.get('broker'),
    port=mqtt_config_dict.get('port'),
    username=mqtt_config_dict.get('username'),
    password=mqtt_config_dict.get('password'),
    client_id=mqtt_config_dict.get('client_id'),  # 必须使用固定的 Client ID
    keepalive=60,
    qos=1,
    protocol=3
)

mqtt_client = MQTTClient(mqtt_config)

# 消息回调
messages = []
def on_message(topic, payload):
    print(f"\n{'=' * 70}")
    print(f"✅✅✅ 收到设备响应！")
    print(f"{'=' * 70}")
    print(f"主题: {topic}")

    if isinstance(payload, dict):
        print(f"\n设备状态:")
        print(f"  MAC: {payload.get('mac')}")
        print(f"  类型: {payload.get('type')}")
        print(f"  版本: {payload.get('version')}")
        print(f"  IP: {payload.get('ip')}")
        print(f"  WiFi: {payload.get('ssid')}")
        print(f"  key1: {'开' if payload.get('key1') == 1 else '关'}")
        print(f"  key2: {'开' if payload.get('key2') == 1 else '关'}")
        print(f"  key3: {'开' if payload.get('key3') == 1 else '关'}")
        print(f"  wifiLock: {payload.get('wifiLock')}")
        print(f"  keyLock: {payload.get('keyLock')}")
    else:
        print(f"内容: {payload}")

    messages.append(payload)

# 连接
print("【1. 连接 MQTT Broker】")
if not mqtt_client.connect():
    print("❌ 连接失败")
    exit(1)
print("✅ 连接成功")

# 订阅
print(f"\n【2. 订阅状态主题】")
mqtt_client.subscribe(subscribe_topic, on_message)
print(f"✅ 已订阅")

time.sleep(1)

# 查询状态
print(f"\n【3. 查询设备状态】")
payload = {"type": "info"}
print(f"发送: {json.dumps(payload, ensure_ascii=False)}")

mqtt_client.publish(publish_topic, payload)

print("\n等待设备响应 (10秒)...")
for i in range(10):
    time.sleep(1)
    if messages:
        print(f"\n✅ 在第 {i+1} 秒收到响应！")
        break
    print(f"   {i+1}/10秒...", end="\r")

if not messages:
    print(f"\n❌ 未收到响应")
    print(f"\n可能原因:")
    print(f"  1. 设备离线 - 请在 GeekOpen App 中检查")
    print(f"  2. 设备未连接到此 MQTT Broker")
    print(f"  3. MAC 地址不正确: {mac}")
    print(f"  4. 主题前缀或 UID 不正确")

# 如果收到响应，继续测试控制
if messages:
    print(f"\n{'=' * 70}")
    print(f"【4. 测试控制开关】")
    print(f"{'=' * 70}")

    # 打开
    print(f"\n发送打开命令...")
    payload = {"type": "event", "key1": 1, "key2": 0, "key3": 0}
    print(f"发送: {json.dumps(payload, ensure_ascii=False)}")

    messages.clear()
    mqtt_client.publish(publish_topic, payload)

    print("\n等待响应 (5秒)...")
    for i in range(5):
        time.sleep(1)
        if messages:
            print(f"\n✅ 收到响应！")
            break
        print(f"   {i+1}/5秒...", end="\r")

    if messages:
        print(f"\n✅✅✅ 控制成功！灯应该打开了！")
    else:
        print(f"\n⚠️  未收到状态更新响应")

    time.sleep(2)

    # 关闭
    print(f"\n发送关闭命令...")
    payload = {"type": "event", "key1": 0, "key2": 0, "key3": 0}
    print(f"发送: {json.dumps(payload, ensure_ascii=False)}")

    messages.clear()
    mqtt_client.publish(publish_topic, payload)

    print("\n等待响应 (5秒)...")
    for i in range(5):
        time.sleep(1)
        if messages:
            print(f"\n✅ 收到响应！")
            break
        print(f"   {i+1}/5秒...", end="\r")

    if messages:
        print(f"\n✅✅✅ 控制成功！灯应该关闭了！")

# 保持连接一段时间
print(f"\n{'=' * 70}")
print(f"保持连接 10 秒，观察是否有更多消息...")
print(f"{'=' * 70}")
time.sleep(10)

# 断开
print(f"\n【断开连接】")
mqtt_client.disconnect()
print(f"✅ 完成")

# 总结
print(f"\n{'=' * 70}")
print(f"总结")
print(f"{'=' * 70}")
print(f"总共收到 {len(messages)} 条消息")
