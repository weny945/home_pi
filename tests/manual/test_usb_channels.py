"""
测试 ReSpeaker USB Mic Array 的不同音频通道
"""
import os
import sys
import pyaudio
import numpy as np
import wave

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

def test_channels():
    """测试所有 6 个通道"""
    print("=" * 60)
    print("ReSpeaker USB Mic Array 通道测试")
    print("=" * 60)
    print()

    p = pyaudio.PyAudio()

    # 找到 ReSpeaker 设备
    device_index = None
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        device_name = info['name'].lower()
        if 'respeaker' in device_name or 'arrayuac' in device_name:
            device_index = i
            print(f"找到设备: {info['name']}")
            print(f"  设备索引: {i}")
            print(f"  输入通道数: {info['maxInputChannels']}")
            print(f"  默认采样率: {info['defaultSampleRate']}")
            print()
            break

    if device_index is None:
        print("❌ 未找到 ReSpeaker 设备")
        print()
        print("可用设备列表：")
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                print(f"  {i}: {info['name']}")
        p.terminate()
        return

    # 录制所有 6 个通道
    print("开始录制 6 通道音频（3 秒）...")
    print("请说话测试...")
    print()

    try:
        stream = p.open(
            format=pyaudio.paInt16,
            channels=6,  # 6 个通道
            rate=16000,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=512
        )

        frames = []
        for i in range(int(16000 / 512 * 3)):  # 3 秒
            data = stream.read(512)
            frames.append(data)

            # 进度显示
            if i % 10 == 0:
                progress = int((i / (16000 / 512 * 3)) * 100)
                print(f"\r录制进度: {progress}%", end="", flush=True)

        print("\r录制完成！      ")
        print()

        stream.stop_stream()
        stream.close()

        # 保存为 6 通道 WAV 文件
        wf = wave.open('test_6ch.wav', 'wb')
        wf.setnchannels(6)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(16000)
        wf.writeframes(b''.join(frames))
        wf.close()

        print("✅ 已保存 test_6ch.wav")
        print()

        # 分析每个通道的能量
        audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
        audio_data = audio_data.reshape(-1, 6)  # 重塑为 6 通道

        print("=" * 60)
        print("各通道能量分析")
        print("=" * 60)

        channel_names = ["通道 0 (FL)", "通道 1 (FR)", "通道 2 (FC)",
                        "通道 3 (LFE)", "通道 4 (RL)", "通道 5 (RR)"]

        energies = []
        for ch in range(6):
            channel_data = audio_data[:, ch]
            energy = np.sqrt(np.mean(channel_data.astype(np.float32) ** 2))
            energies.append(energy)

            # 能量条
            bar_length = int(energy / 50)
            bar = "█" * min(bar_length, 40)

            print(f"{channel_names[ch]:20s}: {energy:6.0f} {bar}")

        # 找到能量最高的通道
        max_ch = np.argmax(energies)
        print()
        print("-" * 60)
        print(f"能量最高的通道: {channel_names[max_ch]} (能量: {energies[max_ch]:.0f})")
        print("-" * 60)
        print()

        # 给出建议
        print("=" * 60)
        print("分析和建议")
        print("=" * 60)
        print()

        if energies[0] > max(energies[1:]) * 1.2:
            print("✅ 通道 0 能量明显最高")
            print("   → 这是波束成形后的音频（推荐使用）")
            print("   → 当前配置应该是正确的")
        elif max_ch == 0 and energies[0] > 100:
            print("✅ 通道 0 有音频信号")
            print("   → 但其他通道能量相近，可能没有波束成形")
            print("   → 建议升级到 UAC 2.0 模式")
        else:
            print("⚠️  通道 0 不是能量最高的通道")
            print(f"   → 最高能量在 {channel_names[max_ch]}")
            print("   → 可能需要：")
            print("     1. 升级到 UAC 2.0 模式")
            print("     2. 更新固件")
            print("     3. 检查硬件连接")

        print()

        # 平均能量分析
        avg_energy = np.mean(energies)
        if avg_energy < 100:
            print("⚠️  音频能量过低（平均 < 100）")
            print("   建议：")
            print("   - 靠近麦克风说话")
            print("   - 提高音量")
            print("   - 增加 input_gain")
        elif avg_energy < 500:
            print("✅ 音频能量正常（100-500）")
        else:
            print("✅ 音频能量良好（> 500）")

        print()
        print("下一步操作：")
        print("  1. 播放 test_6ch.wav 检查音质")
        print("     （需要支持多通道的播放器，如 Audacity）")
        print("  2. 如果通道 0 效果不佳，尝试升级到 UAC 2.0")
        print("  3. 查看详细指南: docs/RESPEAKER_USB_OPTIMIZATION.md")
        print()

    except Exception as e:
        print(f"❌ 录音失败: {e}")
        print()
        print("可能的原因：")
        print("  1. 设备被占用（停止其他使用麦克风的程序）")
        print("  2. 不支持 6 通道录音（设备可能不是 USB Mic Array）")
        print("  3. USB 连接问题")

    p.terminate()

if __name__ == "__main__":
    test_channels()
