"""
简化的 STT 测试脚本
Simple STT Test Script

直接测试 STT 和 VAD 功能，无需交互确认
"""
import sys
import os
import time
from pathlib import Path

# 获取项目根目录
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)


def test_stt_engine():
    """测试 STT 引擎"""
    print("\n" + "=" * 60)
    print("测试 1: FunASR STT 引擎")
    print("=" * 60)

    try:
        from src.stt import FunASRSTTEngine
        from src.config import get_config
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False

    # 加载配置
    config = get_config()
    stt_config = config.get_section('stt')

    print(f"\n配置信息:")
    print(f"  引擎: {stt_config.get('engine')}")
    print(f"  模型: {stt_config.get('model')}")
    print(f"  设备: {stt_config.get('device')}")

    # 初始化引擎
    print("\n📦 初始化 FunASR STT 引擎...")
    print("⚠️  首次运行会自动下载模型 (~200MB)")

    try:
        start_time = time.time()
        engine = FunASRSTTEngine(
            model_name=stt_config.get('model', 'iic/SenseVoiceSmall'),
            device=stt_config.get('device', 'cpu'),
            punc_model=stt_config.get('punc_model'),  # 从配置读取标点模型（可为 None）
            vad_model=None,  # 禁用 VAD 模型以加快测试速度
            load_model=True
        )
        elapsed = time.time() - start_time

        print(f"✅ 引擎初始化成功 (耗时: {elapsed:.2f}s)")

    except Exception as e:
        print(f"❌ 引擎初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 获取模型信息
    print("\n📊 模型信息:")
    model_info = engine.get_model_info()
    print(f"  模型: {model_info['model_name']}")
    print(f"  设备: {model_info['device']}")
    print(f"  就绪: {model_info['is_ready']}")
    print(f"  采样率: {model_info['supported_sample_rate']} Hz")

    # 测试真实音频转录
    print("\n🧪 测试音频转录（真实音频文件）...")
    try:
        import numpy as np

        # 读取真实音频文件
        audio_file = "./test_recording.wav"
        print(f"音频文件: {audio_file}")

        if not Path(audio_file).exists():
            raise FileNotFoundError(f"测试音频文件不存在: {audio_file}")

        print("正在转录...")

        start_time = time.time()
        result_text = engine.transcribe_file(audio_file)
        elapsed = time.time() - start_time

        print(f"\n✅ 转录完成")
        print(f"   识别结果: {result_text}")
        print(f"   耗时: {elapsed:.2f}s")

    except Exception as e:
        print(f"❌ 转录测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n✅ STT 引擎测试通过!")
    return True


def test_vad_detector():
    """测试 VAD 检测器"""
    print("\n" + "=" * 60)
    print("测试 2: FunASR VAD 检测器")
    print("=" * 60)

    try:
        from src.vad import FunASRVADDetector
        from src.config import get_config
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False

    # 加载配置
    config = get_config()
    vad_config = config.get_section('vad')

    # 初始化检测器
    print("\n📦 初始化 FunASR VAD 检测器...")

    try:
        detector = FunASRVADDetector(
            vad_model=vad_config.get('model', 'fsmn-vad'),
            device=vad_config.get('device', 'cpu'),
            load_model=True
        )
        print("✅ VAD 检测器初始化成功")

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 测试语音检测
    print("\n🧪 测试语音活动检测...")
    try:
        import numpy as np

        # 生成测试音频：1秒静音 + 1秒正弦波
        sample_rate = 16000
        silence = np.zeros(sample_rate, dtype=np.int16)
        t = np.linspace(0, 1, sample_rate)
        speech = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
        test_audio = np.concatenate([silence, speech])

        print(f"音频长度: {len(test_audio)/sample_rate:.2f} 秒")
        print("前半段: 静音 (0-1s)")
        print("后半段: 语音 (1-2s)")

        # 检测语音段
        print("\n检测语音段...")
        segments = detector.detect_speech_segments(test_audio)

        print(f"✅ 检测到 {len(segments)} 个语音段")
        for i, (start, end) in enumerate(segments, 1):
            print(f"  段 {i}: {start/1000:.1f}s - {end/1000:.1f}s")

        if len(segments) > 0:
            print(f"\n✅ VAD 检测结果正确")

    except Exception as e:
        print(f"❌ VAD 检测失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n✅ VAD 检测器测试通过!")
    return True


if __name__ == '__main__':
    import os

    print("=" * 60)
    print("🧪 Phase 1.2 简化测试工具")
    print("=" * 60)
    print("\n说明:")
    print("  - 此脚本会自动测试 STT 和 VAD 功能")
    print("  - 无需交互确认")
    print("  - 首次运行会自动下载模型")

    try:
        # 测试 STT
        stt_success = test_stt_engine()

        # 测试 VAD
        vad_success = test_vad_detector()

        # 总结
        print("\n" + "=" * 60)
        print("📊 测试总结")
        print("=" * 60)
        print(f"STT 引擎: {'✅ 通过' if stt_success else '❌ 失败'}")
        print(f"VAD 检测器: {'✅ 通过' if vad_success else '❌ 失败'}")

        if stt_success and vad_success:
            print("\n🎉 所有测试通过！Phase 1.2 准备就绪。")
            sys.exit(0)
        else:
            print("\n⚠️  部分测试失败，请检查错误信息。")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
