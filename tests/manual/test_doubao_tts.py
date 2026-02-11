#!/usr/bin/env python3
"""
豆包 TTS 手动测试脚本
Manual Test Script for Doubao TTS

需要：
1. 火山引擎 API Key (格式: access_key_id:secret_access_key)
2. 火山引擎 App ID

获取方式：https://console.volcengine.com/speech/service
"""
import os
import sys
import tempfile
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.tts import DoubaoTTSEngine
from src.config import get_config


def test_doubao_basic():
    """基础测试"""
    print("=" * 60)
    print("豆包 TTS 基础测试")
    print("=" * 60)

    # 1. 检查 API 配置
    print("\n[1] 检查 API 配置...")

    api_key = os.getenv("VOLCENGINE_API_KEY")
    app_id = os.getenv("VOLCENGINE_APP_ID")

    if not api_key:
        print("❌ 未设置 VOLCENGINE_API_KEY 环境变量")
        print("   请设置: export VOLCENGINE_API_KEY='your-access-key:your-secret-key'")
        return False

    if not app_id:
        print("❌ 未设置 VOLCENGINE_APP_ID 环境变量")
        print("   请设置: export VOLCENGINE_APP_ID='your-app-id'")
        return False

    print(f"✅ API Key: {api_key[:10]}...")
    print(f"✅ App ID: {app_id}")

    # 2. 初始化引擎
    print("\n[2] 初始化豆包 TTS 引擎...")
    try:
        config = {
            "doubao": {
                "api_key": api_key,
                "app_id": app_id,
                "voice": "zh_female_qingxinmeili",
                "emotion": "happy",
                "format": "wav",
                "sample_rate": 24000,
                "rate": 1.0,
                "pitch": 1.0,
            }
        }
        engine = DoubaoTTSEngine(config)
        print("✅ 引擎初始化成功")

        # 显示模型信息
        info = engine.get_model_info()
        print(f"\n📊 模型信息:")
        print(f"   名称: {info['name']}")
        print(f"   提供商: {info['provider']}")
        print(f"   发音人: {info['voice']} ({info['voice_description']})")
        print(f"   情感: {info['emotion']} ({info['emotion_description']})")
        print(f"   格式: {info['format']}")
        print(f"   采样率: {info['sample_rate']} Hz")

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 3. 测试语音合成
    print("\n[3] 测试语音合成...")

    test_texts = [
        "你好，我是豆包语音助手，很高兴为你服务！",
        "今天天气真不错，要不要一起去公园散步？",
        "我觉得这个主意太棒了！",
    ]

    for i, text in enumerate(test_texts, 1):
        print(f"\n   测试 {i}/{len(test_texts)}: {text}")

        try:
            audio = engine.synthesize(text)

            if len(audio) > 0:
                duration = len(audio) / 24000
                print(f"   ✅ 合成成功，时长: {duration:.2f}秒，采样点: {len(audio)}")

                # 保存音频文件
                output_file = f"/tmp/doubao_test_{i}.wav"
                import wave
                with wave.open(output_file, 'wb') as f:
                    f.setnchannels(1)
                    f.setsampwidth(2)
                    f.setframerate(24000)
                    f.writeframes(audio.tobytes())

                print(f"   📁 已保存: {output_file}")
                print(f"   ▶ 播放: aplay {output_file}")
            else:
                print(f"   ❌ 合成失败：返回空音频")

        except Exception as e:
            print(f"   ❌ 合成失败: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)
    return True


def test_different_voices():
    """测试不同发音人"""
    print("\n" + "=" * 60)
    print("豆包 TTS 发音人对比测试")
    print("=" * 60)

    api_key = os.getenv("VOLCENGINE_API_KEY")
    app_id = os.getenv("VOLCENGINE_APP_ID")

    if not api_key or not app_id:
        print("❌ 请先设置环境变量")
        return False

    test_text = "你好，我是语音助手，很高兴为你服务！"

    voices = [
        ("zh_female_qingxinmeili", "清新美丽女声"),
        ("zh_female_wenrou", "温柔女声"),
        ("zh_female_tianmei", "甜美女声"),
        ("zh_female_huoli", "活力女声"),
        ("zh_male_qingchen", "清朗男声"),
    ]

    for voice, description in voices:
        print(f"\n测试: {description} ({voice})")
        print("-" * 40)

        try:
            config = {
                "doubao": {
                    "api_key": api_key,
                    "app_id": app_id,
                    "voice": voice,
                    "emotion": "happy",
                }
            }
            engine = DoubaoTTSEngine(config)
            audio = engine.synthesize(test_text)

            if len(audio) > 0:
                output_file = f"/tmp/doubao_{voice}.wav"
                import wave
                with wave.open(output_file, 'wb') as f:
                    f.setnchannels(1)
                    f.setsampwidth(2)
                    f.setframerate(24000)
                    f.writeframes(audio.tobytes())

                duration = len(audio) / 24000
                print(f"✅ 成功，时长: {duration:.2f}秒")
                print(f"📁 {output_file}")

        except Exception as e:
            print(f"❌ 失败: {e}")

    print("\n" + "=" * 60)
    print("对比播放:")
    for voice, description in voices:
        print(f"  aplay /tmp/doubao_{voice}.wav  # {description}")
    print("=" * 60)

    return True


def test_different_emotions():
    """测试不同情感"""
    print("\n" + "=" * 60)
    print("豆包 TTS 情感对比测试")
    print("=" * 60)

    api_key = os.getenv("VOLCENGINE_API_KEY")
    app_id = os.getenv("VOLCENGINE_APP_ID")

    if not api_key or not app_id:
        print("❌ 请先设置环境变量")
        return False

    test_text = "真的吗？太好了！"

    emotions = [
        ("neutral", "中性"),
        ("happy", "开心"),
        ("sad", "难过"),
        ("surprise", "惊讶"),
    ]

    for emotion, description in emotions:
        print(f"\n测试: {description} ({emotion})")
        print("-" * 40)

        try:
            config = {
                "doubao": {
                    "api_key": api_key,
                    "app_id": app_id,
                    "voice": "zh_female_qingxinmeili",
                    "emotion": emotion,
                }
            }
            engine = DoubaoTTSEngine(config)
            audio = engine.synthesize(test_text)

            if len(audio) > 0:
                output_file = f"/tmp/doubao_emotion_{emotion}.wav"
                import wave
                with wave.open(output_file, 'wb') as f:
                    f.setnchannels(1)
                    f.setsampwidth(2)
                    f.setframerate(24000)
                    f.writeframes(audio.tobytes())

                duration = len(audio) / 24000
                print(f"✅ 成功，时长: {duration:.2f}秒")
                print(f"📁 {output_file}")

        except Exception as e:
            print(f"❌ 失败: {e}")

    print("\n" + "=" * 60)
    print("对比播放:")
    for emotion, description in emotions:
        print(f"  aplay /tmp/doubao_emotion_{emotion}.wav  # {description}")
    print("=" * 60)

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="豆包 TTS 测试脚本")
    parser.add_argument("--test", choices=["basic", "voices", "emotions"],
                       default="basic", help="测试类型")
    args = parser.parse_args()

    if args.test == "basic":
        test_doubao_basic()
    elif args.test == "voices":
        test_different_voices()
    elif args.test == "emotions":
        test_different_emotions()
