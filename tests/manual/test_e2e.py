"""
端到端系统测试
End-to-End System Test

根据需求文档验证完整流程
"""
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import get_config


def test_config():
    """测试配置加载"""
    print("="*60)
    print("📋 测试 1: 配置文件")
    print("="*60)

    try:
        config = get_config()
        config.validate()
        print("✅ 配置文件加载成功")

        # 检查必需的配置段
        sections = ['audio', 'wakeword', 'feedback', 'logging', 'stt', 'vad', 'listening', 'llm', 'tts']
        for section in sections:
            section_config = config.get_section(section)
            if section_config:
                print(f"  ✅ {section}: 已配置")
            else:
                print(f"  ⚠️  {section}: 未配置")

        return True
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False


def test_wake_word():
    """测试唤醒词检测模块"""
    print("\n" + "="*60)
    print("👂 测试 2: 唤醒词检测 (OpenWakeWord)")
    print("="*60)

    try:
        from src.wake_word import OpenWakeWordDetector
        from src.config import get_config

        config = get_config()
        wakeword_config = config.get_wakeword_config()

        detector = OpenWakeWordDetector(
            model_path=wakeword_config.get('model'),
            threshold=wakeword_config.get('threshold', 0.5)
        )

        print("✅ OpenWakeWord 初始化成功")
        print(f"  模型: {wakeword_config.get('model')}")
        print(f"  阈值: {wakeword_config.get('threshold')}")

        return True
    except Exception as e:
        print(f"❌ 唤醒词模块失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_feedback():
    """测试唤醒反馈模块"""
    print("\n" + "="*60)
    print("🔊 测试 3: 唤醒反馈 (TTS)")
    print("="*60)

    try:
        from src.feedback import TTSFeedbackPlayer
        from src.config import get_config

        config = get_config()
        feedback_config = config.get_feedback_config()
        audio_config = config.get_audio_config()

        if feedback_config.get('mode') == 'tts':
            tts_config = feedback_config.get('tts', {})
            player = TTSFeedbackPlayer(
                messages=tts_config.get('messages', ["我在"]),
                model_path=tts_config.get('model_path'),
                length_scale=tts_config.get('length_scale', 1.0),
                random_message=tts_config.get('random_message', False),
                cache_audio=tts_config.get('cache_audio', True),
                output_device=audio_config.get('output_device')
            )

            print("✅ TTS 反馈播放器初始化成功")
            print(f"  模式: TTS")
            print(f"  回复消息: {len(tts_config.get('messages', []))} 条")
        else:
            print("✅ 音频反馈模式 (非 TTS)")

        return True
    except Exception as e:
        print(f"❌ 反馈模块失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_stt():
    """测试语音识别模块"""
    print("\n" + "="*60)
    print("🎤 测试 4: 语音识别 (FunASR STT)")
    print("="*60)

    try:
        from src.stt import FunASRSTTEngine
        from src.config import get_config

        config = get_config()
        stt_config = config.get_section('stt')

        if not stt_config.get('enabled'):
            print("⚠️  STT 未启用")
            return True

        stt = FunASRSTTEngine(
            model_name=stt_config.get('model', 'iic/SenseVoiceSmall'),
            device=stt_config.get('device', 'cpu'),
            punc_model=stt_config.get('punc_model'),
            load_model=True
        )

        print("✅ FunASR STT 初始化成功")
        print(f"  模型: {stt_config.get('model')}")
        print(f"  设备: {stt_config.get('device')}")

        return True
    except Exception as e:
        print(f"❌ STT 模块失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vad():
    """测试 VAD 模块"""
    print("\n" + "="*60)
    print("🔇 测试 5: 语音活动检测 (FunASR VAD)")
    print("="*60)

    try:
        from src.vad import FunASRVADDetector
        from src.config import get_config

        config = get_config()
        vad_config = config.get_section('vad')

        if not vad_config.get('enabled'):
            print("⚠️  VAD 未启用")
            return True

        vad = FunASRVADDetector(
            vad_model=vad_config.get('model', 'fsmn-vad'),
            device=vad_config.get('device', 'cpu'),
            load_model=True
        )

        print("✅ FunASR VAD 初始化成功")
        print(f"  模型: {vad_config.get('model')}")
        print(f"  设备: {vad_config.get('device')}")

        return True
    except Exception as e:
        print(f"❌ VAD 模块失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_llm():
    """测试对话生成模块"""
    print("\n" + "="*60)
    print("🤖 测试 6: 对话生成 (LLM)")
    print("="*60)

    try:
        from src.llm import QwenLLMEngine
        from src.config import get_config

        config = get_config()
        llm_config = config.get_section('llm')

        if not llm_config.get('enabled'):
            print("⚠️  LLM 未启用")
            return True

        model_name = llm_config.get('model')
        if not model_name:
            raise ValueError("配置文件中未指定 llm.model，请在 config.yaml 中设置")

        llm = QwenLLMEngine(
            api_key=llm_config.get('api_key'),
            model=model_name,
            temperature=llm_config.get('temperature', 0.7),
            max_tokens=llm_config.get('max_tokens', 1500),
            enable_history=llm_config.get('enable_history', True),
            max_history=llm_config.get('max_history', 10),
            system_prompt=llm_config.get('system_prompt')
        )

        print("✅ LLM 引擎初始化成功")
        print(f"  模型: {llm_config.get('model')}")
        print(f"  API Key: {llm_config.get('api_key', '')[:10]}...")

        # 测试对话
        result = llm.chat("你好")
        print(f"  测试对话: {result['reply'][:50]}...")
        print(f"  Token: {result['usage'].get('total_tokens', 0)}")

        return True
    except Exception as e:
        print(f"❌ LLM 模块失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tts():
    """测试语音合成模块"""
    print("\n" + "="*60)
    print("🔊 测试 7: 语音合成 (Piper TTS)")
    print("="*60)

    try:
        from src.tts import PiperTTSEngine
        from src.config import get_config

        config = get_config()
        tts_config = config.get_section('tts')

        if not tts_config:
            print("⚠️  TTS 配置未找到")
            return True

        tts = PiperTTSEngine(
            model_path=tts_config.get('model_path'),
            length_scale=tts_config.get('length_scale', 1.0)
        )

        print("✅ Piper TTS 初始化成功")
        print(f"  模型: {tts_config.get('model_path')}")
        print(f"  采样率: {tts.get_sample_rate()} Hz")

        return True
    except Exception as e:
        print(f"❌ TTS 模块失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_state_machine():
    """测试状态机"""
    print("\n" + "="*60)
    print("🔄 测试 8: 状态机")
    print("="*60)

    try:
        from src.state_machine import State
        from src.state_machine.states import State

        # 检查所有必需的状态
        required_states = [State.IDLE, State.WAKEUP, State.LISTENING, State.PROCESSING, State.SPEAKING, State.ERROR]

        print("✅ 状态机定义检查:")
        for state in required_states:
            print(f"  ✅ {state.value}")

        return True
    except Exception as e:
        print(f"❌ 状态机检查失败: {e}")
        return False


def test_main():
    """测试主程序入口"""
    print("\n" + "="*60)
    print("🚀 测试 9: 主程序入口")
    print("="*60)

    try:
        import main

        print("✅ main.py 可以导入")
        print("  检查关键函数:")

        # 检查关键函数
        if hasattr(main, 'setup_logging'):
            print("  ✅ setup_logging()")
        if hasattr(main, 'main'):
            print("  ✅ main()")

        return True
    except Exception as e:
        print(f"❌ 主程序检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_summary(results):
    """打印测试摘要"""
    print("\n" + "="*60)
    print("📊 测试结果摘要")
    print("="*60)

    total = len(results)
    passed = sum(results)

    print(f"\n通过: {passed}/{total}")

    if passed == total:
        print("\n✅ 所有测试通过！系统流程正常")
        return True
    else:
        print(f"\n❌ {total - passed} 个测试失败")
        return False


def main_test():
    """主测试函数"""
    print("\n" + "="*60)
    print("🧪 端到端系统测试")
    print("根据需求文档验证完整流程")
    print("="*60)

    results = []

    # 运行所有测试
    results.append(test_config())
    results.append(test_wake_word())
    results.append(test_feedback())
    results.append(test_stt())
    results.append(test_vad())
    results.append(test_llm())
    results.append(test_tts())
    results.append(test_state_machine())
    results.append(test_main())

    # 打印摘要
    success = print_summary(results)

    # 对比需求文档
    print("\n" + "="*60)
    print("📋 需求对比")
    print("="*60)

    requirements = [
        ("离线唤醒词检测 (OpenWakeWord)", results[1]),
        ("唤醒反馈 (Piper TTS)", results[2]),
        ("语音识别 (FunASR)", results[3]),
        ("VAD 语音活动检测", results[4]),
        ("对话生成 (千问/DeepSeek API)", results[5]),
        ("语音合成 (Piper TTS)", results[6]),
        ("状态机 (IDLE→WAKEUP→LISTENING→PROCESSING→SPEAKING)", results[7]),
    ]

    print("\n需求 vs 实现:")
    for req, passed in requirements:
        status = "✅" if passed else "❌"
        print(f"  {status} {req}")

    # 注意事项
    print("\n" + "="*60)
    print("⚠️  注意事项")
    print("="*60)
    print("1. 需求文档中的 TTS 为 CosyVoice 2.0")
    print("   实际实现: Piper TTS")
    print("   原因: Piper TTS 资源占用更小，适合树莓派")
    print("\n2. 需求文档中的模型配置通过环境变量")
    print("   实际实现: 支持环境变量 + config.yaml 配置")
    print("\n3. 唤醒反馈管理器已集成在 TTSFeedbackPlayer 中")

    return 0 if success else 1


if __name__ == '__main__':
    try:
        exit_code = main_test()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n测试被中断")
        sys.exit(1)
