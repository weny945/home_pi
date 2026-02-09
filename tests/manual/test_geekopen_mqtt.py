"""
GeekOpen MQTT 连接测试脚本
用于验证 MQTT 连接和设备控制功能
"""
import json
import time
import logging
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_mqtt_connection():
    """测试 MQTT 连接"""
    from src.smart_switch import MQTTClient
    from src.smart_switch.mqtt_client import MQTTConfig

    # GeekOpen 云 MQTT 配置
    config = MQTTConfig(
        broker="mqtt.geek-smart.cn",
        port=1883,
        username="zYnGFSPNdwJQ",
        password="vGcJsDEPtmJrexDaCB",
        client_id="kBWEJOVeUNmU",  # 使用原始 Client ID
        protocol=3,  # MQTT v3.1 协议
        qos=1
    )

    logger.info("创建 MQTT 客户端...")
    client = MQTTClient(config)

    logger.info("连接到 MQTT Broker...")
    if not client.connect():
        logger.error("❌ MQTT 连接失败")
        return False

    logger.info("✅ MQTT 连接成功")

    # 测试订阅
    device_mac = "d48afc3af2ea"  # 小写
    subscribe_topic = f"/bKFSKE/qNACgJaGGlTG/{device_mac}/publish"
    publish_topic = f"/bKFSKE/qNACgJaGGlTG/{device_mac}/subscribe"

    def on_message(topic, payload):
        logger.info(f"📩 收到消息: {topic}")
        logger.info(f"   内容: {payload}")

    logger.info(f"订阅主题: {subscribe_topic}")
    client.subscribe(subscribe_topic, on_message)

    # 等待一段时间接收状态
    logger.info("等待设备状态消息...")
    time.sleep(2)

    # 发送查询命令
    logger.info("发送查询命令...")
    query_payload = {"type": "info"}
    client.publish(publish_topic, query_payload)

    time.sleep(2)

    # 发送控制命令（打开 key1）
    logger.info("发送控制命令: 打开 KEY1...")
    control_payload = {"key1": 1}
    client.publish(publish_topic, control_payload)

    time.sleep(2)

    # 发送控制命令（关闭 key1）
    logger.info("发送控制命令: 关闭 KEY1...")
    control_payload = {"key1": 0}
    client.publish(publish_topic, control_payload)

    time.sleep(2)

    # 断开连接
    logger.info("断开 MQTT 连接...")
    client.disconnect()

    logger.info("✅ 测试完成")
    return True


def test_geekopen_controller():
    """测试 GeekOpen 控制器"""
    from src.smart_switch import MQTTClient, GeekOpenController, SwitchKey
    from src.smart_switch.mqtt_client import MQTTConfig

    # MQTT 配置
    config = MQTTConfig(
        broker="mqtt.geek-smart.cn",
        port=1883,
        username="zYnGFSPNdwJQ",
        password="vGcJsDEPtmJrexDaCB",
        client_id="kBWEJOVeUNmU",  # 使用原始 Client ID
        protocol=3,  # MQTT v3.1 协议
        qos=1
    )

    logger.info("创建 MQTT 客户端...")
    mqtt_client = MQTTClient(config)

    logger.info("连接到 MQTT Broker...")
    if not mqtt_client.connect():
        logger.error("❌ MQTT 连接失败")
        return False

    logger.info("✅ MQTT 连接成功")

    # 创建控制器
    logger.info("创建 GeekOpen 控制器...")
    controller = GeekOpenController(mqtt_client)

    # 注册设备
    logger.info("注册设备...")
    controller.register_device(
        mac="D48AFC3AF2EA",
        name="测试灯",
        location="客厅",
        key_count=2,
        prefix="bKFSKE",
        uid="qNACgJaGGlTG"
    )

    # 等待状态同步
    logger.info("等待设备状态同步...")
    time.sleep(3)

    # 查询状态
    logger.info("查询设备状态...")
    state = controller.get_state("测试灯")
    if state:
        logger.info(f"✅ 设备状态: KEY1={'开' if state.key1 else '关'}, KEY2={'开' if state.key2 else '关'}")

    # 控制测试
    logger.info("\n=== 开始控制测试 ===")

    # 打开 KEY1
    logger.info("打开 KEY1...")
    if controller.turn_on("测试灯", SwitchKey.KEY1):
        logger.info("✅ 命令已发送")
    time.sleep(2)

    # 查询状态
    state = controller.get_state("测试灯")
    if state:
        logger.info(f"   当前状态: KEY1={'开' if state.key1 else '关'}")

    # 关闭 KEY1
    logger.info("关闭 KEY1...")
    if controller.turn_off("测试灯", SwitchKey.KEY1):
        logger.info("✅ 命令已发送")
    time.sleep(2)

    # 查询状态
    state = controller.get_state("测试灯")
    if state:
        logger.info(f"   当前状态: KEY1={'开' if state.key1 else '关'}")

    # 断开连接
    logger.info("\n断开 MQTT 连接...")
    mqtt_client.disconnect()

    logger.info("✅ 测试完成")
    return True


def test_intent_detection():
    """测试意图检测"""
    from src.smart_switch import detect_switch_intent

    test_cases = [
        ("打开客厅灯", "on", "客厅灯"),
        ("关闭卧室灯", "off", "卧室灯"),
        ("客厅灯怎么样", "query", "客厅灯"),
        ("切换风扇", "toggle", "风扇"),
    ]

    logger.info("=== 测试意图检测 ===\n")

    for text, expected_action, expected_device in test_cases:
        intent = detect_switch_intent(text)
        if intent:
            logger.info(f"输入: {text}")
            logger.info(f"  动作: {intent.action} (期望: {expected_action})")
            logger.info(f"  设备: {intent.device} (期望: {expected_device})")
            match = (intent.action == expected_action and
                     expected_device in intent.device)
            logger.info(f"  结果: {'✅ 匹配' if match else '❌ 不匹配'}\n")
        else:
            logger.info(f"输入: {text}")
            logger.info(f"  结果: ❌ 未识别到意图\n")


if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("GeekOpen MQTT 测试脚本")
    print("=" * 60)
    print()
    print("请选择测试类型：")
    print("1. MQTT 连接测试")
    print("2. GeekOpen 控制器测试")
    print("3. 意图检测测试")
    print("4. 全部测试")
    print()

    choice = input("请输入选项 (1-4): ").strip()

    if choice == "1":
        test_mqtt_connection()
    elif choice == "2":
        test_geekopen_controller()
    elif choice == "3":
        test_intent_detection()
    elif choice == "4":
        test_intent_detection()
        print("\n" + "=" * 60 + "\n")
        test_mqtt_connection()
        print("\n" + "=" * 60 + "\n")
        test_geekopen_controller()
    else:
        logger.error("无效选项")
        sys.exit(1)
