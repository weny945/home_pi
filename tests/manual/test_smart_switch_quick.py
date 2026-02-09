#!/usr/bin/env python3
"""
快速测试智能开关模块
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_config():
    """测试配置读取"""
    from src.config import ConfigLoader

    config = ConfigLoader("config.yaml")
    switch_config = config.get_section("smart_switch") or {}

    logger.info("=" * 60)
    logger.info("智能开关配置检查")
    logger.info("=" * 60)
    logger.info(f"enabled: {switch_config.get('enabled', False)}")

    if switch_config.get('enabled'):
        mqtt_config = switch_config.get('mqtt', {})
        logger.info(f"MQTT Broker: {mqtt_config.get('broker')}")
        logger.info(f"MQTT Port: {mqtt_config.get('port')}")
        logger.info(f"MQTT Protocol: {mqtt_config.get('protocol', 3)}")

        devices = switch_config.get('devices', [])
        logger.info(f"设备数量: {len(devices)}")
        for dev in devices:
            logger.info(f"  - {dev.get('name')} (MAC: {dev.get('mac')})")
    else:
        logger.warning("智能开关未启用")
        return False

    return True

def test_mqtt_connection():
    """测试 MQTT 连接"""
    from src.smart_switch import MQTTClient
    from src.smart_switch.mqtt_client import MQTTConfig

    switch_config = ConfigLoader("config.yaml").get_section("smart_switch") or {}
    mqtt_config = switch_config.get('mqtt', {})

    logger.info("=" * 60)
    logger.info("MQTT 连接测试")
    logger.info("=" * 60)

    config = MQTTConfig(
        broker=mqtt_config.get('broker'),
        port=mqtt_config.get('port', 1883),
        username=mqtt_config.get('username'),
        password=mqtt_config.get('password'),
        client_id=mqtt_config.get('client_id'),
        protocol=mqtt_config.get('protocol', 3),
        qos=1
    )

    client = MQTTClient(config)

    logger.info("正在连接 MQTT Broker...")
    if client.connect():
        logger.info("✅ MQTT 连接成功")

        # 测试发送命令
        device_mac = "d48afc3af2ea"
        publish_topic = f"/bKFSKE/qNACgJaGGlTG/{device_mac}/subscribe"

        logger.info("发送测试命令: 打开 KEY1...")
        result = client.publish(publish_topic, {"key1": 1})

        if result:
            logger.info("✅ 命令发送成功")
        else:
            logger.error("❌ 命令发送失败")

        client.disconnect()
        return True
    else:
        logger.error("❌ MQTT 连接失败")
        return False

def test_intent_detection():
    """测试意图检测"""
    from src.smart_switch import detect_switch_intent

    logger.info("=" * 60)
    logger.info("意图检测测试")
    logger.info("=" * 60)

    test_cases = [
        "打开客厅灯",
        "关闭客厅灯",
        "客厅灯怎么样",
    ]

    for text in test_cases:
        intent = detect_switch_intent(text)
        if intent:
            logger.info(f"✅ \"{text}\" -> action={intent.action}, device={intent.device}")
        else:
            logger.error(f"❌ \"{text}\" -> 未识别")

    return True

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("智能开关模块测试")
    print("=" * 60 + "\n")

    # 1. 测试配置
    if not test_config():
        print("\n❌ 配置检查失败，请检查 config.yaml")
        sys.exit(1)

    print()

    # 2. 测试意图检测
    test_intent_detection()

    print()

    # 3. 测试 MQTT 连接
    print("是否测试 MQTT 连接？这会实际控制设备。")
    try:
        choice = input("继续测试 MQTT? (y/n): ").strip().lower()
        if choice == 'y':
            test_mqtt_connection()
    except (EOFError, KeyboardInterrupt):
        print("\n跳过 MQTT 测试")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
