#!/usr/bin/env python3
"""
简单的 GeekOpen 开关控制测试
直接尝试控制灯，不等待响应
"""
import sys
import os
import time
import json

# 添加项目根目录到 Python 路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, project_root)

from src.config import get_config
from src.smart_switch.mqtt_client import MQTTClient, MQTTConfig
import logging

logging.basicConfig(level=logging.INFO)


def main():
    # 加载配置
    config = get_config()
    smart_switch_config = config._config.get('smart_switch', {})
    mqtt_config_dict = smart_switch_config.get('mqtt', {})

    # GeekOpen 协议配置
    prefix = smart_switch_config.get('prefix', 'bKFSKE')
    uid = smart_switch_config.get('uid', 'qNACgJaGGlTG')
    devices = smart_switch_config.get('devices', [])

    if not devices:
        print("❌ 没有配置设备")
        return

    device = devices[0]
    mac = device.get('mac', '').lower().replace(":", "").replace("-", "")
    device_name = device.get('name', 'Unknown')
    key_count = device.get('key_count', 2)

    # 构建主题
    subscribe_topic = f"/{prefix}/{uid}/{mac}/publish"
    publish_topic = f"/{prefix}/{uid}/{mac}/subscribe"

    print("=" * 60)
    print(f"GeekOpen 开关控制测试 - {device_name}")
    print("=" * 60)
    print(f"发布主题: {publish_topic}")
    print(f"订阅主题: {subscribe_topic}")
    print()

    # 创建 MQTT 客户端
    mqtt_config = MQTTConfig(
        broker=mqtt_config_dict.get('broker', 'localhost'),
        port=mqtt_config_dict.get('port', 1883),
        username=mqtt_config_dict.get('username'),
        password=mqtt_config_dict.get('password'),
        client_id=mqtt_config_dict.get('client_id', f"test_{int(time.time())}"),  # 使用配置的 Client ID
        keepalive=60,
        qos=1,
        protocol=3
    )

    mqtt_client = MQTTClient(mqtt_config)

    # 消息回调
    messages = []
    def on_message(topic, payload):
        print(f"\n✅ 收到设备响应:")
        print(f"   主题: {topic}")
        if isinstance(payload, dict):
            print(f"   key1: {'开' if payload.get('key1') == 1 else '关'}")
            print(f"   key2: {'开' if payload.get('key2') == 1 else '关'}")
            print(f"   key3: {'开' if payload.get('key3') == 1 else '关'}")
        else:
            print(f"   内容: {payload}")
        messages.append(payload)

    # 连接
    print("【连接 MQTT Broker】")
    if not mqtt_client.connect():
        print("❌ 连接失败")
        return
    print("✅ 连接成功")

    # 订阅
    mqtt_client.subscribe(subscribe_topic, on_message)
    print(f"✅ 已订阅状态主题")

    # 等待一下
    time.sleep(1)

    # 发送打开命令
    print(f"\n【发送打开命令】")
    payload = {"type": "event", "key1": 1, "key2": 0, "key3": 0}
    print(f"命令: {json.dumps(payload, ensure_ascii=False)}")

    result = mqtt_client.publish(publish_topic, payload)
    if result:
        print("✅ 命令已发送")
        print("请观察灯是否打开...")

        # 等待响应
        print("\n等待设备响应 (5秒)...")
        for i in range(5):
            time.sleep(1)
            if messages:
                break
            print(f"   {i+1}/5秒...")

        if messages:
            print(f"\n✅ 成功！收到设备响应")
        else:
            print(f"\n⚠️  未收到设备响应")
            print(f"   请检查:")
            print(f"   1. 设备是否在线（在 GeekOpen App 中查看）")
            print(f"   2. 设备是否连接到同一网络")
    else:
        print("❌ 命令发送失败")

    # 等待 2 秒观察
    print(f"\n保持连接 2 秒...")
    time.sleep(2)

    # 关闭命令
    print(f"\n【发送关闭命令】")
    payload = {"type": "event", "key1": 0, "key2": 0, "key3": 0}
    print(f"命令: {json.dumps(payload, ensure_ascii=False)}")

    result = mqtt_client.publish(publish_topic, payload)
    if result:
        print("✅ 命令已发送")
        print("请观察灯是否关闭...")

        print("\n等待设备响应 (5秒)...")
        messages.clear()
        for i in range(5):
            time.sleep(1)
            if messages:
                break
            print(f"   {i+1}/5秒...")

        if messages:
            print(f"\n✅ 成功！收到设备响应")
        else:
            print(f"\n⚠️  未收到设备响应")
    else:
        print("❌ 命令发送失败")

    # 断开
    print(f"\n【断开连接】")
    mqtt_client.disconnect()
    print("✅ 完成")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
