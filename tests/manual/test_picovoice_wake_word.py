"""
Picovoice 唤醒词测试脚本
"""
import os
import sys
import numpy as np
import time

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.wake_word import PicovoiceDetector
from src.audio import ReSpeakerInput
from src.config import get_config

def test_picovoice():
    """测试 Picovoice 唤醒词检测"""

    # 加载环境变量
    env_file = os.path.join(os.path.dirname(__file__), "../../.env.sh")
    print(f"环境变量文件: {env_file}")

    print("=" * 60)
    print("Picovoice 唤醒词测试")
    print("=" * 60)

    # 加载配置
    config = get_config()
    wakeword_config = config.get_wakeword_config()

    # 获取 Access Key（展开环境变量）
    access_key = wakeword_config.get('access_key', '')
    if access_key.startswith('${') and access_key.endswith('}'):
        env_var = access_key[2:-1]
        access_key = os.environ.get(env_var, '')
        print(f"Access Key (from env): {access_key[:20]}...")
    else:
        print(f"Access Key: {access_key[:20]}...")

    # 初始化检测器
    print("\n初始化 Picovoice 检测器...")
    detector = PicovoiceDetector(
        keyword_path=wakeword_config.get('model'),
        sensitivity=wakeword_config.get('sensitivity', 0.5),
        access_key=access_key,
        model_path=wakeword_config.get('porcupine_model')
    )

    if not detector.is_ready:
        print("❌ 检测器未就绪")
        return False

    print("✅ 检测器就绪")
    print(f"  帧大小: {detector.frame_length}")
    print(f"  采样率: {detector.sample_rate}")

    # 初始化音频输入
    print("\n初始化音频输入...")
    audio_config = config.get_audio_config()
    audio_input = ReSpeakerInput(
        device_name=audio_config.get('input_device', 'default'),
        sample_rate=audio_config.get('sample_rate', 16000),
        channels=audio_config.get('channels', 1),
        chunk_size=audio_config.get('chunk_size', 512),
        input_gain=audio_config.get('input_gain', 1.0)
    )

    print(f"  音频设备: {audio_config.get('input_device')}")
    print(f"  块大小: {audio_config.get('chunk_size')}")

    # 开始测试
    print("\n" + "=" * 60)
    print("开始监听唤醒词（说'胡桃'）...")
    print("按 Ctrl+C 退出")
    print("=" * 60)

    try:
        audio_input.start_stream()

        frame_count = 0
        start_time = time.time()

        while True:
            # 读取音频帧
            audio_frame = audio_input.read_chunk()

            if audio_frame is None:
                continue

            frame_count += 1

            # 每 100 帧显示一次状态
            if frame_count % 100 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed
                print(f"运行中... 已处理 {frame_count} 帧 ({fps:.1f} fps)")

            # 检测唤醒词
            detected = detector.process_frame(audio_frame)

            if detected:
                print(f"\n✅✅✅ 检测到唤醒词！（第 {frame_count} 帧）")
                print("=" * 60)
                break

    except KeyboardInterrupt:
        print("\n\n用户中断")

    finally:
        audio_input.stop_stream()
        print("测试结束")

if __name__ == "__main__":
    test_picovoice()
