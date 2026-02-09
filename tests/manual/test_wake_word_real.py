#!/usr/bin/env python3
"""
实时唤醒词检测测试
"""
import sys
import pyaudio
import numpy as np
from pathlib import Path
from openwakeword.model import Model

# 配置
SAMPLE_RATE = 16000
CHUNK_SIZE = 1280  # 80ms @ 16kHz
CHANNELS = 1
FORMAT = pyaudio.paInt16

def list_audio_devices():
    """列出所有音频设备"""
    import pyaudio
    p = pyaudio.PyAudio()

    print("=" * 60)
    print("📋 可用的录音设备")
    print("=" * 60)

    input_devices = []
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            input_devices.append(i)
            name = info['name']
            is_respeaker = 'respeaker' in name.lower() or '4mic' in name.lower() or 'seeed' in name.lower()
            marker = " ✅ [ReSpeaker]" if is_respeaker else ""
            print(f"  [{i}] {name}{marker}")

    p.terminate()
    return input_devices

def select_device():
    """选择录音设备"""
    devices = list_audio_devices()

    print("\n" + "=" * 60)
    print("请选择录音设备索引")
    print("=" * 60)

    # 自动检测 ReSpeaker
    import pyaudio
    p = pyaudio.PyAudio()
    respeaker_device = None
    for i in devices:
        info = p.get_device_info_by_index(i)
        name = info['name'].lower()
        if 'respeaker' in name or '4mic' in name or 'seeed' in name:
            respeaker_device = i
            break
    p.terminate()

    if respeaker_device is not None:
        info = pyaudio.PyAudio().get_device_info_by_index(respeaker_device)
        print(f"\n✅ 自动检测到 ReSpeaker: [{respeaker_device}] {info['name']}")
        choice = input("  使用此设备? (Y/n): ").strip().lower()
        if choice in ('', 'y', 'yes'):
            return respeaker_device

    while True:
        try:
            user_input = input(f"\n请输入录音设备索引 (直接回车使用默认设备 [{devices[0]}]): ").strip()
            if not user_input:
                return devices[0]

            device_index = int(user_input)
            if device_index in devices:
                return device_index
            else:
                print(f"❌ 无效的索引，请选择: {devices}")
        except ValueError:
            print(f"❌ 请输入有效的数字")
        except KeyboardInterrupt:
            print("\n\n👋 用户取消")
            sys.exit(0)

def main():
    print("=" * 60)
    print("🎯 实时唤醒词检测测试")
    print("=" * 60)

    # 选择设备
    device_index = select_device()

    # 加载模型
    print("\n📦 加载 OpenWakeWord 模型...")
    model = Model()
    models = list(model.models.keys())
    print(f"✅ 已加载 {len(models)} 个唤醒词模型:")
    for m in models:
        print(f"   - {m}")
    print()
    print("💡 可用的唤醒词:")
    print("   - 'alexa' (亚马逊 Alexa)")
    print("   - 'hey jarvis' (贾维斯)")
    print("   - 'hey mycroft' (迈克洛夫特)")
    print("   - 'hey rhasspy' (Rhasspy)")
    print()

    # 打开音频流
    print(f"🎤 打开音频流 (设备: {device_index})...")
    p = pyaudio.PyAudio()

    try:
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=CHUNK_SIZE
        )
        print("✅ 音频流已打开")
    except Exception as e:
        print(f"❌ 无法打开音频流: {e}")
        p.terminate()
        sys.exit(1)

    print("\n" + "=" * 60)
    print("🎯 开始监听唤醒词...")
    print("=" * 60)
    print("💡 请对着麦克风说唤醒词（例如: 'alexa', 'hey jarvis'）")
    print("⏹️  按 Ctrl+C 停止监听")
    print("=" * 60)
    print()

    detection_count = 0
    start_time = None

    try:
        stream.start_stream()
        import time
        start_time = time.time()

        while True:
            # 读取音频数据
            audio_data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            audio_frame = np.frombuffer(audio_data, dtype=np.int16)

            # 预测
            predictions = model.predict(audio_frame)

            # 检查是否有唤醒词被检测到
            for keyword, score in predictions.items():
                if score > 0.5:  # 阈值
                    detection_count += 1
                    elapsed = time.time() - start_time

                    print("\n" + "=" * 60)
                    print(f"✅ 检测到唤醒词!")
                    print("=" * 60)
                    print(f"   关键词: {keyword}")
                    print(f"   置信度: {score:.3f}")
                    print(f"   第 {detection_count} 次")
                    print(f"   耗时: {elapsed:.1f} 秒")
                    print("=" * 60)
                    print()

    except KeyboardInterrupt:
        elapsed = time.time() - start_time if start_time else 0

        print("\n" + "=" * 60)
        print("📊 测试结束")
        print("=" * 60)
        print(f"   总检测次数: {detection_count}")
        print(f"   运行时长: {elapsed:.1f} 秒")
        if detection_count > 0:
            print(f"   ✅ 唤醒词检测正常工作!")
        else:
            print(f"   ⚠️  未检测到唤醒词，请:")
            print(f"      - 检查麦克风是否正常")
            print(f"      - 确保发音清晰")
            print(f"      - 尝试其他唤醒词 ('alexa', 'hey jarvis')")
        print("=" * 60)

    finally:
        print("\n👋 清理资源...")
        stream.stop_stream()
        stream.close()
        p.terminate()
        print("✅ 完成")

if __name__ == "__main__":
    main()
