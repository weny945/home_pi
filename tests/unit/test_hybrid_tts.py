"""
测试混合 TTS 引擎
验证远程/本地自动切换功能
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import time
import logging
from src.tts import PiperTTSEngine, RemoteTTSEngine, HybridTTSEngine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_local_tts():
    """测试本地 TTS（Piper）"""
    print("\n" + "="*60)
    print("测试 1: 本地 TTS (Piper)")
    print("="*60)

    try:
        engine = PiperTTSEngine(
            model_path="./models/piper/zh_CN-huayan-medium.onnx",
            length_scale=1.0
        )
        print(f"✅ 本地 TTS 初始化成功")
        print(f"   模型信息: {engine.get_model_info()}")

        # 测试合成
        text = "你好，这是本地语音合成测试。"
        print(f"\n🎤 合成文本: {text}")

        audio = engine.synthesize(text)
        print(f"✅ 合成成功: {len(audio)} 采样点")
        print(f"   采样率: {engine.get_sample_rate()} Hz")

        return True
    except Exception as e:
        print(f"❌ 本地 TTS 测试失败: {e}")
        return False


def test_remote_tts():
    """测试远程 TTS（GPT-SoVITS API）"""
    print("\n" + "="*60)
    print("测试 2: 远程 TTS (GPT-SoVITS API)")
    print("="*60)

    # 配置：修改为你的服务器 IP
    SERVER_IP = "192.168.2.141"  # ⚠️ 修改为你的电脑IP

    try:
        engine = RemoteTTSEngine(
            server_ip=SERVER_IP,
            port=9880,
            timeout=60,
            text_lang="zh",
            speed=1.0
        )
        print(f"✅ 远程 TTS 初始化成功")
        print(f"   模型信息: {engine.get_model_info()}")

        # 测试健康检查
        print("\n📡 健康检查...")
        is_available = engine.check_health()
        print(f"   服务器状态: {'在线 ✅' if is_available else '离线 ❌'}")

        if not is_available:
            print("⚠️  远程服务器不可用，跳过合成测试")
            return False

        # 测试合成
        text = "你好，这是远程语音合成测试。"
        print(f"\n🎤 合成文本: {text}")

        audio = engine.synthesize(text)
        print(f"✅ 合成成功: {len(audio)} 采样点")
        print(f"   采样率: {engine.get_sample_rate()} Hz")

        return True
    except Exception as e:
        print(f"❌ 远程 TTS 测试失败: {e}")
        return False


def test_hybrid_tts():
    """测试混合 TTS（自动切换）"""
    print("\n" + "="*60)
    print("测试 3: 混合 TTS（自动切换远程/本地）")
    print("="*60)

    # 配置：修改为你的服务器 IP
    SERVER_IP = "192.168.2.141"  # ⚠️ 修改为你的电脑IP

    try:
        # 初始化本地引擎
        local_engine = PiperTTSEngine(
            model_path="./models/piper/zh_CN-huayan-medium.onnx",
            length_scale=1.0
        )
        print("✅ 本地引擎初始化成功")

        # 初始化远程引擎
        remote_engine = None
        try:
            remote_engine = RemoteTTSEngine(
                server_ip=SERVER_IP,
                port=9880,
                timeout=10,  # 短超时用于快速测试
                text_lang="zh",
                speed=1.0
            )
            print("✅ 远程引擎初始化成功")
        except Exception as e:
            print(f"⚠️  远程引擎初始化失败: {e}")
            print("   将使用本地引擎")

        # 创建混合引擎
        hybrid_engine = HybridTTSEngine(
            remote_engine=remote_engine if remote_engine else local_engine,
            local_engine=local_engine,
            health_check_interval=30,  # 30秒检查一次（测试用）
            auto_failback=True
        )

        print("\n" + "-"*60)
        print("混合引擎状态:")
        print("-"*60)
        status = hybrid_engine.get_status()
        for key, value in status.items():
            print(f"  {key}: {value}")

        # 测试合成（应该自动选择可用引擎）
        print("\n" + "-"*60)
        print("测试 1: 首次合成（应该使用可用引擎）")
        print("-"*60)
        text1 = "这是第一次测试，混合引擎应该自动选择可用的TTS。"
        print(f"🎤 合成文本: {text1}")

        audio1 = hybrid_engine.synthesize(text1)
        print(f"✅ 合成成功: {len(audio1)} 采样点")
        print(f"   当前使用: {status['current_engine']} TTS")

        # 如果使用的是本地引擎，手动切换到远程测试
        if remote_engine and remote_engine.is_ready():
            print("\n" + "-"*60)
            print("测试 2: 强制切换到远程 TTS")
            print("-"*60)
            hybrid_engine.force_remote()

            text2 = "这是第二次测试，强制使用远程TTS。"
            print(f"🎤 合成文本: {text2}")

            audio2 = hybrid_engine.synthesize(text2)
            print(f"✅ 合成成功: {len(audio2)} 采样点")

            print("\n" + "-"*60)
            print("测试 3: 强制切换到本地 TTS")
            print("-"*60)
            hybrid_engine.force_local()

            text3 = "这是第三次测试，强制使用本地TTS。"
            print(f"🎤 合成文本: {text3}")

            audio3 = hybrid_engine.synthesize(text3)
            print(f"✅ 合成成功: {len(audio3)} 采样点")

        # 模拟远程故障场景（仅在远程可用时）
        if remote_engine and remote_engine.is_ready():
            print("\n" + "-"*60)
            print("测试 4: 模拟远程故障场景")
            print("-"*60)
            print("注意：此测试需要关闭远程服务器来触发自动切换")

        print("\n✅ 混合 TTS 测试完成")
        return True

    except Exception as e:
        print(f"❌ 混合 TTS 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_failover_simulation():
    """模拟故障切换场景"""
    print("\n" + "="*60)
    print("测试 4: 模拟故障切换")
    print("="*60)
    print("此测试需要手动操作:")
    print("1. 启动远程 TTS 服务器")
    print("2. 运行此测试")
    print("3. 在测试过程中关闭远程服务器")
    print("4. 观察是否自动切换到本地 TTS")
    print("5. 重新启动远程服务器")
    print("6. 观察是否自动切回远程 TTS（最多等待1小时）")

    response = input("\n是否继续? (y/n): ")
    if response.lower() != 'y':
        print("跳过此测试")
        return

    # 实现故障切换测试
    # （由于需要手动操作，这里提供框架代码）
    print("\n提示：观察日志中的以下信息:")
    print("  - ⚠️  远程 TTS 合成失败")
    print("  - 🔄 自动切换到本地 TTS")
    print("  - ✅ 远程 TTS 已恢复在线")
    print("  - ✅ 自动切换回远程 TTS 引擎")


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("  混合 TTS 引擎测试")
    print("="*60)

    # 测试 1: 本地 TTS
    result1 = test_local_tts()

    # 测试 2: 远程 TTS
    result2 = test_remote_tts()

    # 测试 3: 混合 TTS
    if result1:  # 只有本地TTS可用时才测试混合引擎
        result3 = test_hybrid_tts()

    # 测试 4: 故障切换模拟
    test_failover_simulation()

    print("\n" + "="*60)
    print("  测试总结")
    print("="*60)
    print(f"  本地 TTS: {'✅ 通过' if result1 else '❌ 失败'}")
    print(f"  远程 TTS: {'✅ 通过' if result2 else '❌ 失败（可能是服务器未启动）'}")
    print("="*60)

    if result1:
        print("\n✅ 本地 TTS 可用，系统可以正常运行")
    else:
        print("\n⚠️  本地 TTS 不可用，请检查模型文件")

    if result2:
        print("✅ 远程 TTS 可用，混合引擎将优先使用远程 TTS")
    else:
        print("⚠️  远程 TTS 不可用，混合引擎将使用本地 TTS")

    print("\n提示：如果远程 TTS 不可用，请检查:")
    print("  1. 服务器 IP 地址是否正确")
    print("  2. GPT-SoVITS API 服务是否已启动")
    print("  3. 防火墙是否放行 9880 端口")
    print("  4. 网络连接是否正常")


if __name__ == "__main__":
    main()
