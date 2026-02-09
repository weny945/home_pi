"""
Piper TTS 集成测试
Phase 1.1 Integration Test - Piper TTS
"""
import sys
import os
import time
from pathlib import Path

# 获取项目根目录
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))

# 确保在项目根目录运行
os.chdir(project_root)

import logging
from src.config import get_config
from src.tts import PiperTTSEngine
from src.feedback import TTSFeedbackPlayer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_piper_engine():
    """测试 Piper TTS 引擎"""
    print("\n" + "=" * 60)
    print("测试 1: Piper TTS 引擎")
    print("=" * 60)

    try:
        # 初始化引擎
        print("\n初始化 Piper TTS 引擎...")
        engine = PiperTTSEngine(
            model_path="./models/piper/zh_CN-huayan-medium.onnx",
            load_model=True
        )
        print("✅ Piper TTS 引擎初始化成功")

        # 获取模型信息
        model_info = engine.get_model_info()
        print(f"\n模型信息:")
        print(f"  模型路径: {model_info['model_path']}")
        print(f"  采样率: {model_info['sample_rate']} Hz")
        print(f"  已加载: {model_info['is_loaded']}")
        print(f"  语速: {model_info['synthesis_config']['length_scale']}")

        # 测试合成
        print("\n测试语音合成...")
        test_texts = ["我在", "请吩咐", "我在听", "您好", "我在这里"]

        for text in test_texts:
            audio_data = engine.synthesize(text)
            duration = len(audio_data) / model_info['sample_rate']
            print(f"  '{text}' -> {len(audio_data)} samples ({duration:.2f}s)")

        print("✅ 语音合成测试成功")

        # 测试不同语速
        print("\n测试不同语速...")
        speeds = [0.8, 1.0, 1.2]
        text = "测试语速"

        for speed in speeds:
            engine.set_synthesis_config(length_scale=speed)
            audio_data = engine.synthesize(text)
            duration = len(audio_data) / model_info['sample_rate']
            print(f"  语速 {speed}: {duration:.2f}s")

        # 恢复正常语速
        engine.set_synthesis_config(length_scale=1.0)

        print("✅ 语速测试成功")

        # 测试保存到文件
        print("\n测试保存音频文件...")
        Path("./cache").mkdir(parents=True, exist_ok=True)
        test_file = "./cache/test_tts_output.wav"
        engine.synthesize_to_file("测试保存功能", test_file)
        print(f"  音频已保存: {test_file}")
        print("✅ 文件保存测试成功")

        print("\n" + "=" * 60)
        print("✅ 所有引擎测试通过!")
        print("=" * 60)

        return engine

    except Exception as e:
        print(f"\n❌ Piper TTS 引擎测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_tts_feedback_player():
    """测试 TTS 反馈播放器"""
    print("\n" + "=" * 60)
    print("测试 2: TTS 反馈播放器")
    print("=" * 60)

    try:
        # 初始化播放器
        print("\n初始化 TTS 反馈播放器...")
        player = TTSFeedbackPlayer(
            messages=["我在", "请吩咐", "我在听", "您好", "我在这里"],
            model_path="./models/piper/zh_CN-huayan-medium.onnx",
            cache_audio=False  # 不使用缓存，直接合成
        )
        print("✅ TTS 反馈播放器初始化成功")

        # 获取模型信息
        model_info = player.get_model_info()
        print(f"\n模型信息:")
        print(f"  模型路径: {model_info['model_path']}")

        # 测试消息获取
        print("\n测试消息顺序获取...")
        for i in range(7):
            message = player._get_message()
            print(f"  第 {i+1} 次: {message}")

        print("✅ 消息顺序测试成功")

        # 测试播放（不实际播放，只测试合成）
        print("\n测试唤醒反馈合成...")
        print("  合成并播放 5 条回复消息:")

        for i in range(5):
            message = player._get_message()
            print(f"  [{i+1}/5] '{message}'... ", end="", flush=True)
            start_time = time.time()

            # 合成音频（不播放）
            audio_data = player._tts_engine.synthesize(message)
            duration = len(audio_data) / player._tts_engine.get_sample_rate()
            elapsed = time.time() - start_time

            print(f"✓ ({duration:.2f}s 音频, {elapsed:.2f}s 合成)")

        print("✅ 反馈合成测试成功")

        print("\n" + "=" * 60)
        print("✅ 所有反馈播放器测试通过!")
        print("=" * 60)

        return player

    except Exception as e:
        print(f"\n❌ TTS 反馈播放器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_integration():
    """完整集成测试"""
    print("\n" + "=" * 60)
    print("测试 3: 完整集成测试")
    print("=" * 60)

    try:
        # 加载配置
        print("\n加载配置...")
        config = get_config()
        feedback_config = config.get_feedback_config()
        tts_config = feedback_config.get('tts', {})

        print(f"  反馈模式: {feedback_config.get('mode')}")
        print(f"  TTS 引擎: {tts_config.get('engine')}")
        print(f"  模型路径: {tts_config.get('model_path')}")
        print(f"  语速: {tts_config.get('length_scale')}")

        # 创建 TTS 反馈播放器
        print("\n创建 TTS 反馈播放器...")
        player = TTSFeedbackPlayer(
            messages=tts_config.get('messages', ["我在", "请吩咐", "我在听"]),
            model_path=tts_config.get('model_path', './models/piper/zh_CN-huayan-medium.onnx'),
            length_scale=tts_config.get('length_scale', 1.0),
            random_message=tts_config.get('random_message', False),
            cache_audio=tts_config.get('cache_audio', True)
        )
        print("✅ TTS 反馈播放器创建成功")

        # 模拟唤醒回复
        print("\n模拟 5 次唤醒回复...")
        for i in range(5):
            print(f"\n第 {i+1} 次唤醒:")
            player.play_wake_feedback()

        print("\n✅ 集成测试成功")

        print("\n" + "=" * 60)
        print("✅ 完整集成测试通过!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("Piper TTS 集成测试")
    print("第一阶段 1.1: 唤醒词检测 + TTS 语音回复")
    print("=" * 60)

    # 测试 1: 引擎测试
    engine = test_piper_engine()
    if engine is None:
        print("\n❌ 引擎测试失败，终止后续测试")
        return

    # 测试 2: 反馈播放器测试
    player = test_tts_feedback_player()
    if player is None:
        print("\n❌ 反馈播放器测试失败，终止后续测试")
        return

    # 测试 3: 完整集成测试
    test_integration()

    print("\n" + "=" * 60)
    print("✅ 所有测试完成!")
    print("=" * 60)
    print("\n提示:")
    print("  - 如果听到语音播放，说明音频输出正常")
    print("  - 可以运行 'python main.py' 进行完整系统测试")
    print("  - 对着麦克风说唤醒词，应该听到 TTS 语音回复")
    print()


if __name__ == '__main__':
    main()
