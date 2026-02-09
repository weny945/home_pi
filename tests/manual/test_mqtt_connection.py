#!/usr/bin/env python3
"""
MQTT 连接诊断测试
尝试不同的 Client ID 和协议版本
"""
import sys
import os
import time

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, project_root)

from src.config import get_config
from src.smart_switch.mqtt_client import MQTTClient, MQTTConfig

# 加载配置
config = get_config()
smart_switch_config = config._config.get('smart_switch', {})
mqtt_config_dict = smart_switch_config.get('mqtt', {})

print("=" * 60)
print("MQTT 连接诊断测试")
print("=" * 60)

# 测试配置
test_configs = [
    {
        "name": "配置的 Client ID",
        "client_id": mqtt_config_dict.get('client_id'),
        "protocol": 3
    },
    {
        "name": "动态 Client ID (时间戳)",
        "client_id": f"test_pi_{int(time.time())}",
        "protocol": 3
    },
    {
        "name": "动态 Client ID + MQTTv3.1.1",
        "client_id": f"test_pi_{int(time.time())}",
        "protocol": 4
    },
]

for test in test_configs:
    print(f"\n{'=' * 60}")
    print(f"测试: {test['name']}")
    print(f"{'=' * 60}")
    print(f"Client ID: {test['client_id']}")
    print(f"协议版本: MQTTv{test['protocol']}")

    mqtt_config = MQTTConfig(
        broker=mqtt_config_dict.get('broker'),
        port=mqtt_config_dict.get('port'),
        username=mqtt_config_dict.get('username'),
        password=mqtt_config_dict.get('password'),
        client_id=test['client_id'],
        protocol=test['protocol']
    )

    client = MQTTClient(mqtt_config)

    print("正在连接...")
    success = client.connect()

    if success:
        print("✅ 连接成功!")
        client.disconnect()
        print("✅ 已断开")
        break
    else:
        print("❌ 连接失败")

    time.sleep(1)

print(f"\n{'=' * 60}")
print("诊断完成")
print(f"{'=' * 60}")
