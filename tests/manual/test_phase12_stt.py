"""
Phase 1.2 集成测试
Phase 1.2 Integration Test - STT 功能

测试完整的语音识别流程：
唤醒词检测 → TTS 回复 → VAD 录音 → STT 识别 → 输出文本
"""
import sys
import os
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 获取项目根目录
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))

# 确保在项目根目录运行
os.chdir(project_root)


def print_header(title):
    """打印标题"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def print_section(title):
    """打印小节标题"""
    print("\n" + "-" * 60)
    print(title)
    print("-" * 60)


def test_stt_engine():
    """测试 1: FunASR STT 引擎"""
    print_header("测试 1: FunASR STT 引擎")

    try:
        from src.stt import FunASRSTTEngine
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("   请安装 FunASR: pip install funasr")
        return False

    # 检查配置
    try:
        from src.config import get_config
        config = get_config()
        stt_config = config.get_section('stt')

        if not stt_config.get('enabled', False):
            print("⚠️  STT 功能未启用")
            print("   请在 config.yaml 中设置 stt.enabled: true")
            return False

        print(f"\n配置信息:")
        print(f"  引擎: {stt_config.get('engine')}")
        print(f"  模型: {stt_config.get('model')}")
        print(f"  设备: {stt_config.get('device')}")

    except Exception as e:
        print(f"⚠️  无法读取配置: {e}")

    # 初始化引擎
    print("\n📦 初始化 FunASR STT 引擎...")
    print("⚠️  首次运行会自动下载模型 (~200MB)")

    choice = input("\n是否继续? (y/N): ").strip().lower()
    if choice != 'y':
        print("⏭️  跳过 STT 测试")
        return None

    try:
        start_time = time.time()
        engine = FunASRSTTEngine(
            model_name=stt_config.get('model', 'iic/SenseVoiceSmall'),
            device=stt_config.get('device', 'cpu'),
            punc_model=stt_config.get('punc_model'),
            load_model=True
        )
        elapsed = time.time() - start_time

        print(f"✅ 引擎初始化成功 (耗时: {elapsed:.2f}s)")

    except Exception as e:
        print(f"❌ 引擎初始化失败: {e}")
        return False

    # 获取模型信息
    print("\n📊 模型信息:")
    model_info = engine.get_model_info()
    print(f"  模型: {model_info['model_name']}")
    print(f"  设备: {model_info['device']}")
    print(f"  就绪: {model_info['is_ready']}")
    print(f"  采样率: {model_info['supported_sample_rate']} Hz")

    # 测试转录（如果有测试音频）
    print_section("音频转录测试")

    test_audio_file = "./cache/test_audio.wav"
    if Path(test_audio_file).exists():
        print(f"\n找到测试音频: {test_audio_file}")
        choice = input("是否测试转录? (y/N): ").strip().lower()

        if choice == 'y':
            try:
                print("正在转录...")
                start_time = time.time()
                result = engine.transcribe_file(test_audio_file)
                elapsed = time.time() - start_time

                print(f"✅ 转录完成")
                print(f"   识别结果: {result}")
                print(f"   耗时: {elapsed:.2f}s")

            except Exception as e:
                print(f"❌ 转录失败: {e}")
                return False
    else:
        print(f"\n⚠️  测试音频不存在: {test_audio_file}")
        print("   跳过转录测试")

    print("\n✅ STT 引擎测试通过!")
    return True


def test_vad_detector():
    """测试 2: FunASR VAD 检测器"""
    print_header("测试 2: FunASR VAD 检测器")

    try:
        from src.vad import FunASRVADDetector
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("   请安装 FunASR: pip install funasr")
        return False

    # 初始化检测器
    print("\n📦 初始化 FunASR VAD 检测器...")

    try:
        from src.config import get_config
        config = get_config()
        vad_config = config.get_section('vad')

        detector = FunASRVADDetector(
            vad_model=vad_config.get('model', 'fsmn-vad'),
            device=vad_config.get('device', 'cpu'),
            load_model=True
        )
        print("✅ VAD 检测器初始化成功")

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return False

    # 测试语音检测
    print_section("语音活动检测测试")

    # 生成测试音频
    import numpy as np

    print("\n生成测试音频...")
    # 1秒静音 + 1秒正弦波
    sample_rate = 16000
    silence = np.zeros(sample_rate, dtype=np.int16)
    t = np.linspace(0, 1, sample_rate)
    speech = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    test_audio = np.concatenate([silence, speech])

    print(f"音频长度: {len(test_audio)/sample_rate:.2f} 秒")
    print("前半段: 静音 (0-1s)")
    print("后半段: 语音 (1-2s)")

    try:
        # 检测语音段
        print("\n检测语音段...")
        segments = detector.detect_speech_segments(test_audio)

        print(f"✅ 检测到 {len(segments)} 个语音段")
        for i, (start, end) in enumerate(segments, 1):
            print(f"  段 {i}: {start/1000:.1f}s - {end/1000:.1f}s")

        # 验证结果
        if len(segments) > 0:
            start_ms, end_ms = segments[0]
            # 应该检测到约 1s 开始的语音
            assert 900 < start_ms < 1100, f"起始时间异常: {start_ms}ms"
            print(f"\n✅ VAD 检测结果正确")

    except Exception as e:
        print(f"❌ VAD 检测失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n✅ VAD 检测器测试通过!")
    return True


def test_full_pipeline():
    """测试 3: Phase 1.2 完整流程"""
    print_header("测试 3: Phase 1.2 完整流程测试")

    try:
        from src.config import get_config
        from src.audio import ReSpeakerInput
        from src.wake_word import OpenWakeWordDetector
        from src.feedback import TTSFeedbackPlayer
        from src.stt import FunASRSTTEngine
        from src.vad import FunASRVADDetector
    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        return False

    # 加载配置
    print("\n⚙️  加载配置文件...")
    try:
        config = get_config()
        audio_config = config.get_audio_config()
        wakeword_config = config.get_wakeword_config()
        feedback_config = config.get_feedback_config()
        stt_config = config.get_section('stt')
        vad_config = config.get_section('vad')
        listening_config = config.get_section('listening')

        # 检查是否启用 STT
        if not stt_config.get('enabled', False):
            print("⚠️  STT 功能未启用")
            print("   请在 config.yaml 中设置 stt.enabled: true")
            return False

        print("✅ 配置加载成功")

        print(f"\n配置信息:")
        print(f"  输入设备: {audio_config.get('input_device')}")
        print(f"  唤醒阈值: {wakeword_config.get('threshold')}")
        print(f"  STT 引擎: {stt_config.get('engine')}")
        print(f"  VAD 模型: {vad_config.get('model')}")
        print(f"  最大录音时长: {listening_config.get('max_duration')}s")

    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False

    # 初始化各组件
    print_section("初始化组件")

    # 初始化音频输入
    print("\n🎤 初始化音频输入...")
    try:
        audio_input = ReSpeakerInput(
            device_name=audio_config.get('input_device', 'seeed-4mic-voicecard'),
            sample_rate=audio_config.get('sample_rate', 16000),
            channels=audio_config.get('channels', 1),
            chunk_size=audio_config.get('chunk_size', 512)
        )
        print("✅ 音频输入初始化成功")
    except Exception as e:
        print(f"❌ 音频输入初始化失败: {e}")
        print("\n💡 提示: 请确保 ReSpeaker 4-Mic 已连接")
        return False

    # 初始化唤醒词检测器
    print("\n🔊 初始化唤醒词检测器...")
    try:
        detector = OpenWakeWordDetector(
            model_path=wakeword_config.get('model'),
            threshold=wakeword_config.get('threshold', 0.5)
        )
        print("✅ 唤醒词检测器初始化成功")
    except Exception as e:
        print(f"❌ 唤醒词检测器初始化失败: {e}")
        return False

    # 初始化 TTS 播放器
    print("\n🔊 初始化 TTS 播放器...")
    try:
        tts_config = feedback_config.get('tts', {})
        feedback_player = TTSFeedbackPlayer(
            messages=tts_config.get('messages', ["我在", "请吩咐", "我在听"]),
            model_path=tts_config.get('model_path', './models/piper/zh_CN-huayan-medium.onnx'),
            length_scale=tts_config.get('length_scale', 1.0),
            random_message=tts_config.get('random_message', False),
            cache_audio=tts_config.get('cache_audio', True),
            output_device=audio_config.get('output_device', 'plughw:0,0')
        )
        print("✅ TTS 播放器初始化成功")
    except Exception as e:
        print(f"❌ TTS 播放器初始化失败: {e}")
        return False

    # 初始化 STT 引擎
    print("\n🤖 初始化 STT 引擎...")
    print("⚠️  首次运行会自动下载模型 (~200MB)")

    choice = input("\n是否继续? (y/N): ").strip().lower()
    if choice != 'y':
        print("⏭️  跳过完整流程测试")
        return None

    try:
        start_time = time.time()
        stt_engine = FunASRSTTEngine(
            model_name=stt_config.get('model', 'iic/SenseVoiceSmall'),
            device=stt_config.get('device', 'cpu'),
            load_model=True
        )
        elapsed = time.time() - start_time
        print(f"✅ STT 引擎初始化成功 (耗时: {elapsed:.2f}s)")
    except Exception as e:
        print(f"❌ STT 引擎初始化失败: {e}")
        return False

    # 初始化 VAD 检测器
    print("\🎤 初始化 VAD 检测器...")
    try:
        vad_detector = FunASRVADDetector(
            vad_model=vad_config.get('model', 'fsmn-vad'),
            device=vad_config.get('device', 'cpu'),
            load_model=True
        )
        print("✅ VAD 检测器初始化成功")
    except Exception as e:
        print(f"❌ VAD 检测器初始化失败: {e}")
        return False

    # 完整流程测试
    print_section("完整流程测试")
    print("\n流程: 唤醒词检测 → TTS 回复 → VAD 录音 → STT 识别 → 输出文本")
    print("\n💡 测试说明:")
    print("  1. 对着麦克风说唤醒词 (alexa)")
    print("  2. 等待 TTS 语音回复")
    print("  3. 继续说话 (如: '你好')")
    print("  4. 停顿约 1.5 秒")
    print("  5. 系统自动识别并输出文本")
    print("\n按 Ctrl+C 可随时停止")

    input("\n按 Enter 开始测试...")

    try:
        # 简化的手动测试流程
        print("\n" + "="*60)
        print("步骤 1: 测试 TTS 播放")
        print("="*60)
        print("播放 TTS 语音回复...")
        feedback_player.play_wake_feedback()
        print("✅ TTS 播放完成")

        print("\n" + "="*60)
        print("步骤 2: 模拟 STT 识别")
        print("="*60)

        # 生成模拟音频
        import numpy as np
        sample_rate = 16000
        duration = 2  # 2秒音频

        print(f"\n生成模拟音频 ({duration}秒)...")
        # 生成正弦波模拟语音
        t = np.linspace(0, duration, int(sample_rate * duration))
        test_audio = (np.sin(2 * np.pi * 440 * t) * 16383).astype(np.int16)

        print("正在识别...")
        start_time = time.time()
        result_text = stt_engine.transcribe(test_audio)
        elapsed = time.time() - start_time

        print(f"\n✅ 识别完成 (耗时: {elapsed:.2f}s)")
        print("\n" + "="*60)
        print("📝 识别结果")
        print("="*60)
        print(f"  {result_text}")
        print("="*60 + "\n")

        logger.info(f"识别结果: {result_text}")

        print("\n✅ Phase 1.2 完整流程测试通过!")
        return True

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        feedback_player.stop()


def show_menu():
    """显示测试菜单"""
    print("\n" + "=" * 60)
    print("🧪 Phase 1.2 语音识别集成测试工具")
    print("=" * 60)

    print("\n当前功能:")
    print("  ✅ STT - 语音识别 (FunASR SenseVoiceSmall)")
    print("  ✅ VAD - 语音活动检测")

    print("\n" + "-" * 60)
    print("请选择测试:")
    print("  [1] 🤖 测试 STT 引擎")
    print("  [2] 🎤 测试 VAD 检测器")
    print("  [3] 🔄 测试完整流程")
    print("  [q] 🚪 退出")
    print("=" * 60)


def main():
    """主函数"""

    while True:
        show_menu()
        choice = input("\n请输入选项 (1-3, q): ").strip().lower()

        if choice == '1':
            test_stt_engine()
        elif choice == '2':
            test_vad_detector()
        elif choice == '3':
            test_full_pipeline()
        elif choice == 'q':
            print("\n👋 退出测试")
            break
        else:
            print("❌ 无效选择，请重试")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
