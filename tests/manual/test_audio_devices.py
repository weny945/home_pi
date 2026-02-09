#!/usr/bin/env python3
"""
测试音频设备
列出所有可用的 PyAudio 设备并尝试播放测试音
"""
import pyaudio
import numpy as np
import time

def list_audio_devices():
    """列出所有音频设备"""
    print("=" * 60)
    print("可用的音频设备")
    print("=" * 60)

    p = pyaudio.PyAudio()

    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)

        if info['maxOutputChannels'] > 0:
            print(f"\n设备 #{i}:")
            print(f"  名称: {info['name']}")
            print(f"  最大输出通道: {info['maxOutputChannels']}")
            print(f"  默认采样率: {int(info['defaultSampleRate'])} Hz")

            # 检查是否是我们要找的设备
            if 'ArrayUAC10' in info['name'] or 'USB' in info['name'].upper():
                print(f"  ⭐ 这是 USB 音频设备 (ReSpeaker)")
            elif 'HDMI' in info['name'].upper() or 'vc4hdmi' in info['name'].lower():
                print(f"  ⭐ 这是 HDMI 音频设备")

    p.terminate()

def test_device_playback(device_index=None):
    """测试设备播放"""
    print("\n" + "=" * 60)
    print("测试音频播放")
    print("=" * 60)

    p = pyaudio.PyAudio()

    try:
        # 生成 1 秒的 440Hz 测试音
        sample_rate = 16000
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        tone = np.sin(2 * np.pi * 440 * t)
        audio_data = (tone * 0.5 * 32767).astype(np.int16)

        # 打开音频流
        stream_params = {
            'format': pyaudio.paInt16,
            'channels': 1,
            'rate': sample_rate,
            'output': True
        }

        if device_index is not None:
            stream_params['output_device_index'] = device_index
            print(f"使用设备索引: {device_index}")
        else:
            print("使用默认设备")

        stream = p.open(**stream_params)

        print("播放 1 秒测试音 (440Hz)...")
        stream.write(audio_data.tobytes())
        print("✅ 播放完成")

        stream.close()
        p.terminate()

    except Exception as e:
        print(f"❌ 播放失败: {e}")
        p.terminate()

if __name__ == "__main__":
    # 列出所有设备
    list_audio_devices()

    # 测试每个输出设备
    p = pyaudio.PyAudio()
    output_devices = []

    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxOutputChannels'] > 0:
            output_devices.append(i)

    p.terminate()

    print(f"\n找到 {len(output_devices)} 个输出设备")

    # 测试每个设备
    for device_index in output_devices:
        print(f"\n测试设备 #{device_index}...")
        test_device_playback(device_index)
        time.sleep(0.5)

    print("\n" + "=" * 60)
    print("测试完成！请确认哪个设备能听到声音")
    print("=" * 60)
