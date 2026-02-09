#!/usr/bin/env python3
"""
第一阶段完整流程测试
Phase 1 Flow Test: Wake Word Detection → Wake Feedback

测试流程:
1. 唤醒词检测 (Wake Word Detection)
2. 唤醒回复播放 (Wake Feedback)
"""
import sys
import os
from pathlib import Path
import time

# 切换到项目根目录
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

import pyaudio
import numpy as np


def list_audio_devices():
    """列出所有音频设备"""
    p = pyaudio.PyAudio()

    print("\n" + "=" * 60)
    print("音频设备列表")
    print("=" * 60)

    # 输入设备
    print("\n📤 录音设备（麦克风）:")
    input_devices = []
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            name = info['name']
            is_respeaker = 'respeaker' in name.lower() or '4mic' in name.lower() or 'seeed' in name.lower()
            marker = " ✅ [ReSpeaker]" if is_respeaker else ""
            print(f"  [{i}] {name}{marker}")
            input_devices.append((i, name, is_respeaker))

    # 输出设备
    print("\n📥 播放设备（音响）:")
    output_devices = []
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxOutputChannels'] > 0:
            name = info['name']
            is_respeaker = 'respeaker' in name.lower() or 'seeed' in name.lower()
            marker = " ✅ [ReSpeaker]" if is_respeaker else ""
            print(f"  [{i}] {name}{marker}")
            output_devices.append((i, name, is_respeaker))

    p.terminate()
    return input_devices, output_devices


def select_device(devices, device_type):
    """选择设备"""
    print(f"\n请选择{device_type}设备索引:")

    # 优先选择 ReSpeaker 设备
    for idx, name, is_respeaker in devices:
        if is_respeaker:
            print(f"  ✅ 自动检测到 ReSpeaker: [{idx}] {name}")
            choice = input(f"  使用此设备? (Y/n): ").strip().lower()
            if choice != 'n':
                return idx

    # 手动选择
    while True:
        choice = input(f"\n请输入{device_type}设备索引 (直接回车使用第一个): ").strip()
        if choice == "":
            return devices[0][0]
        try:
            device_index = int(choice)
            if any(idx == device_index for idx, _, _ in devices):
                return device_index
            else:
                print(f"❌ 无效的索引")
        except ValueError:
            print(f"❌ 请输入数字")


def generate_beep(frequency=880, duration_ms=200, sample_rate=16000):
    """生成蜂鸣声"""
    duration_sec = duration_ms / 1000.0
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), False)
    tone = np.sin(2 * np.pi * frequency * t)

    # 淡入淡出
    fade_len = int(0.01 * sample_rate)
    fade_in = np.linspace(0, 1, fade_len)
    fade_out = np.linspace(1, 0, fade_len)

    if len(tone) > 2 * fade_len:
        tone[:fade_len] *= fade_in
        tone[-fade_len:] *= fade_out

    return (tone * 32767).astype(np.int16)


def play_beep(audio, stream, frequency=880, duration_ms=200):
    """播放蜂鸣声"""
    try:
        beep_data = generate_beep(frequency, duration_ms)
        stream.write(beep_data.tobytes())
    except Exception as e:
        print(f"❌ 播放蜂鸣声失败: {e}")


def test_phase1_flow():
    """测试第一阶段完整流程"""
    print("=" * 60)
    print("🎯 第一阶段流程测试")
    print("  唤醒词检测 → 唤醒回复")
    print("=" * 60)

    # 1. 导入模块
    print("\n📦 导入模块...")
    try:
        from openwakeword.model import Model
        print("✅ 导入 openwakeword 成功")
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("   请安装: pip install openwakeword")
        return

    # 2. 加载唤醒词模型
    print("\n📦 加载唤醒词模型...")
    try:
        oww_model = Model()
        models = list(oww_model.models.keys())
        print(f"✅ 成功加载 {len(models)} 个唤醒词模型:")
        for m in models:
            print(f"   - {m}")
    except Exception as e:
        print(f"❌ 加载模型失败: {e}")
        return

    print("\n💡 可用的唤醒词:")
    print("   - 'alexa' (推荐，检测准确度高)")
    print("   - 'hey jarvis' (贾维斯)")
    print("   - 'hey mycroft' (迈克洛夫特)")

    # 3. 选择音频设备
    print("\n🎤 选择音频设备...")
    input_devices, output_devices = list_audio_devices()

    if not input_devices:
        print("❌ 没有可用的录音设备")
        return

    if not output_devices:
        print("❌ 没有可用的播放设备")
        return

    input_device_idx = select_device(input_devices, "录音")
    output_device_idx = select_device(output_devices, "播放")

    print(f"\n✅ 录音设备: [{input_device_idx}]")
    print(f"✅ 播放设备: [{output_device_idx}]")

    # 4. 打开音频流
    print("\n🎤 打开音频流...")
    p = pyaudio.PyAudio()

    try:
        input_stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            input_device_index=input_device_idx,
            frames_per_buffer=1280  # 80ms @ 16kHz
        )

        output_stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            output=True,
            output_device_index=output_device_idx
        )

        print("✅ 音频流已打开")

    except Exception as e:
        print(f"❌ 打开音频流失败: {e}")
        p.terminate()
        return

    # 5. 开始测试
    print("\n" + "=" * 60)
    print("🎯 开始测试: 唤醒词 → 唤醒回复")
    print("=" * 60)
    print("\n💡 请说唤醒词（推荐: 'alexa'）")
    print("   说出唤醒词后，应该听到蜂鸣声回复")
    print("\n⏹️  按 Ctrl+C 停止测试")
    print("⏰  将在检测到 3 次唤醒词后自动停止")
    print("=" * 60)

    detection_count = 0
    max_detections = 3
    threshold = 0.5

    try:
        input_stream.start_stream()
        start_time = time.time()

        print("\n" + "-" * 60)
        print("⏳ 监听中...")
        print("-" * 60)

        while detection_count < max_detections:
            # 读取音频数据
            audio_data = input_stream.read(1280, exception_on_overflow=False)
            audio_frame = np.frombuffer(audio_data, dtype=np.int16)

            # 检测唤醒词
            predictions = oww_model.predict(audio_frame)

            # 检查是否检测到唤醒词
            for keyword, score in predictions.items():
                if score > threshold:
                    detection_count += 1
                    elapsed = time.time() - start_time

                    print("\n" + "=" * 60)
                    print(f"✅ 检测到唤醒词! (第 {detection_count} 次)")
                    print("=" * 60)
                    print(f"   关键词: {keyword}")
                    print(f"   置信度: {score:.3f}")
                    print(f"   耗时: {elapsed:.1f} 秒")
                    print("=" * 60)

                    # 播放唤醒回复
                    print("\n🔊 播放唤醒回复（蜂鸣声）...")
                    play_beep(p, output_stream, frequency=880, duration_ms=200)
                    print("✅ 唤醒回复播放完成")

                    print("\n" + "-" * 60)
                    print("⏳ 继续监听...")
                    print("-" * 60)
                    break

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    finally:
        elapsed = time.time() - start_time

        print("\n" + "=" * 60)
        print("📊 测试总结")
        print("=" * 60)
        print(f"   总检测次数: {detection_count}")
        print(f"   运行时长: {elapsed:.1f} 秒")

        if detection_count > 0:
            print("\n✅ 第一阶段流程测试成功!")
            print("   - 唤醒词检测: ✅ 正常")
            print("   - 唤醒回复: ✅ 正常")
        else:
            print("\n⚠️  未检测到唤醒词")
            print("   建议:")
            print("   - 靠近麦克风说话")
            print("   - 发音清晰")
            print("   - 尝试说 'alexa'（检测准确度最高）")

        print("=" * 60)

        # 清理资源
        input_stream.stop_stream()
        input_stream.close()
        output_stream.close()
        p.terminate()


if __name__ == "__main__":
    test_phase1_flow()
