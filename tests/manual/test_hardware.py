"""
硬件测试脚本
Hardware Test Script for ReSpeaker
"""
import sys
import os
from pathlib import Path

# 获取项目根目录
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))

# 确保在项目根目录运行
os.chdir(project_root)

import pyaudio
import wave
import numpy as np


def list_audio_devices():
    """列出所有音频设备"""
    audio = pyaudio.PyAudio()

    print("\n" + "=" * 60)
    print("音频设备列表")
    print("=" * 60)

    # 输入设备
    print("\n📤 录音设备（麦克风）:")
    input_devices = []
    for i in range(audio.get_device_count()):
        info = audio.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            name = info['name']
            # 检测 ReSpeaker
            is_respeaker = 'respeaker' in name.lower() or '4mic' in name.lower() or 'seeed' in name.lower()
            marker = " ✅ [ReSpeaker]" if is_respeaker else ""
            print(f"  [{i}] {name}{marker}")
            input_devices.append((i, name, is_respeaker))

    # 输出设备
    print("\n📥 播放设备（音响）:")
    output_devices = []
    for i in range(audio.get_device_count()):
        info = audio.get_device_info_by_index(i)
        if info['maxOutputChannels'] > 0:
            name = info['name']
            # 检测 ReSpeaker
            is_respeaker = 'respeaker' in name.lower() or 'seeed' in name.lower()
            marker = " ✅ [ReSpeaker]" if is_respeaker else ""
            print(f"  [{i}] {name}{marker}")
            output_devices.append((i, name, is_respeaker))

    audio.terminate()

    return input_devices, output_devices


def select_device(devices, device_type):
    """
    选择设备

    Args:
        devices: 设备列表 [(index, name, is_respeaker), ...]
        device_type: 设备类型 ("录音" 或 "播放")

    Returns:
        int: 设备索引
    """
    print(f"\n请选择{device_type}设备索引:")

    # 优先选择 ReSpeaker 设备
    for idx, name, is_respeaker in devices:
        if is_respeaker:
            print(f"  ✅ 自动检测到 ReSpeaker: [{idx}] {name}")
            choice = input(f"  使用此设备? (Y/n): ").strip().lower()
            if choice != 'n':
                return idx

    # 如果没有 ReSpeaker 或用户拒绝，手动选择
    print(f"\n可用的{device_type}设备:")
    for idx, name, is_respeaker in devices:
        marker = " [ReSpeaker]" if is_respeaker else ""
        print(f"  [{idx}] {name}{marker}")

    while True:
        choice = input(f"\n请输入{device_type}设备索引 (直接回车使用默认): ").strip()

        if choice == "":
            # 使用第一个设备
            if devices:
                selected_idx, selected_name, _ = devices[0]
                print(f"  使用默认设备: [{selected_idx}] {selected_name}")
                return selected_idx
            else:
                print("  ❌ 没有可用设备")
                return None

        try:
            idx = int(choice)
            # 验证索引
            for device_idx, name, _ in devices:
                if device_idx == idx:
                    print(f"  ✅ 已选择: [{idx}] {name}")
                    return idx
            print(f"  ❌ 索引 {idx} 无效，请重新输入")
        except ValueError:
            print("  ❌ 输入无效，请输入数字索引")


def test_microphone():
    """测试麦克风录音"""
    print("\n" + "=" * 60)
    print("测试 1: 麦克风录音")
    print("=" * 60)

    # 显示设备列表
    input_devices, _ = list_audio_devices()

    if not input_devices:
        print("\n❌ 未找到录音设备")
        return

    # 选择设备
    device_index = select_device(input_devices, "录音")
    if device_index is None:
        return

    # 录音参数
    sample_rate = 16000
    channels = 1
    chunk_size = 512
    record_seconds = 3
    output_file = "./test_recording.wav"

    print(f"\n📝 录音参数:")
    print(f"  设备索引: {device_index}")
    print(f"  采样率: {sample_rate} Hz")
    print(f"  通道: {channels}")
    print(f"  时长: {record_seconds} 秒")
    print(f"  保存到: {output_file}")

    input("\n按 Enter 开始录音...")

    # 初始化 PyAudio
    audio = pyaudio.PyAudio()

    # 打开音频流
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=channels,
        rate=sample_rate,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=chunk_size
    )

    print("\n🎤 录音中... 请说话")

    frames = []
    for i in range(int(sample_rate / chunk_size * record_seconds)):
        data = stream.read(chunk_size)
        frames.append(data)
        # 显示进度
        if i % 10 == 0:
            print(f"  录音进度: {i * chunk_size / sample_rate:.1f}/{record_seconds} 秒")

    print("\n✅ 录音完成!")

    # 停止流
    stream.stop_stream()
    stream.close()
    audio.terminate()

    # 保存为 WAV 文件
    wf = wave.open(output_file, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
    wf.setframerate(sample_rate)
    wf.writeframes(b''.join(frames))
    wf.close()

    print(f"✅ 音频已保存到: {output_file}")

    # 显示音频信息
    audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
    rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
    max_value = np.max(np.abs(audio_data))
    print(f"\n📊 音频信息:")
    print(f"  RMS 音量: {rms:.2f}")
    print(f"  最大音量: {max_value}")
    print(f"  采样数: {len(audio_data)}")

    if rms < 10:
        print("  ⚠️  音量较低，请检查麦克风位置")
    else:
        print("  ✅ 音量正常")


def test_speaker():
    """测试音响播放"""
    print("\n" + "=" * 60)
    print("测试 2: 音响播放")
    print("=" * 60)

    # 显示设备列表
    _, output_devices = list_audio_devices()

    if not output_devices:
        print("\n❌ 未找到播放设备")
        return

    # 选择设备
    device_index = select_device(output_devices, "播放")
    if device_index is None:
        return

    # 检查是否有录制的音频文件
    recording_file = "./test_recording.wav"

    if os.path.exists(recording_file):
        print(f"\n✅ 找到录制的音频: {recording_file}")
        print("请选择播放内容:")
        print("  [1] 🎤 播放录制的音频（推荐）")
        print("  [2] 🔊 播放测试蜂鸣声")
        choice = input("\n请选择 (1/2，直接回车默认1): ").strip()

        if choice == '' or choice == '1':
            # 播放录制的音频
            print(f"\n🔊 播放录制的音频: {recording_file}")
            input("\n按 Enter 开始播放...")

            try:
                # 读取 WAV 文件
                wf = wave.open(recording_file, 'rb')
                sample_rate = wf.getframerate()
                frames = wf.readframes(wf.getnframes())

                # 初始化 PyAudio
                audio = pyaudio.PyAudio()

                # 打开音频流
                stream = audio.open(
                    format=audio.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=sample_rate,
                    output=True,
                    output_device_index=device_index
                )

                print("\n🔊 播放中...")

                # 播放音频
                stream.write(frames)

                print("✅ 播放完成!")

                # 清理
                stream.stop_stream()
                stream.close()
                audio.terminate()
                wf.close()

            except Exception as e:
                print(f"❌ 播放失败: {e}")
                return

        else:
            # 播放测试蜂鸣声
            _play_test_tone(device_index)
    else:
        print(f"\n⚠️  未找到录制的音频: {recording_file}")
        print("   将播放测试蜂鸣声")
        input("\n按 Enter 播放测试蜂鸣声...")
        _play_test_tone(device_index)


def _play_test_tone(device_index):
    """播放测试蜂鸣声"""
    # 生成测试音频（1秒的蜂鸣声）
    sample_rate = 16000
    duration = 1  # 秒
    frequency = 880  # Hz (A5音)

    t = np.linspace(0, duration, int(sample_rate * duration), False)
    tone = np.sin(2 * np.pi * frequency * t)

    # 应用淡入淡出
    fade_len = int(0.05 * sample_rate)
    fade_in = np.linspace(0, 1, fade_len)
    fade_out = np.linspace(1, 0, fade_len)

    if len(tone) > 2 * fade_len:
        tone[:fade_len] *= fade_in
        tone[-fade_len:] *= fade_out

    # 转换为 16-bit PCM
    audio_data = (tone * 32767).astype(np.int16)

    print(f"\n📝 播放参数:")
    print(f"  设备索引: {device_index}")
    print(f"  频率: {frequency} Hz")
    print(f"  时长: {duration} 秒")
    print(f"  采样率: {sample_rate} Hz")

    # 初始化 PyAudio
    audio = pyaudio.PyAudio()

    # 打开音频流
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=sample_rate,
        output=True,
        output_device_index=device_index
    )

    print("\n🔊 播放测试蜂鸣声...")

    stream.write(audio_data.tobytes())

    print("✅ 播放完成!")

    stream.stop_stream()
    stream.close()
    audio.terminate()


def test_wake_word():
    """测试唤醒词检测"""
    print("\n" + "=" * 60)
    print("测试 3: 唤醒词检测")
    print("=" * 60)

    try:
        from openwakeword.model import Model
    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        print("   请确保已安装依赖: pip install openwakeword")
        return

    try:
        # 初始化 openwakeword 模型（自动加载所有预训练模型）
        print("\n📦 加载 OpenWakeWord 模型...")
        oww_model = Model()

        models = list(oww_model.models.keys())
        print(f"✅ 成功加载 {len(models)} 个唤醒词模型:")
        for m in models:
            print(f"   - {m}")
    except Exception as e:
        print(f"❌ 加载模型失败: {e}")
        print("\n💡 提示: 请运行模型下载脚本")
        print("   python3 tests/manual/download_www_models.py")
        return

    print("\n💡 可用的唤醒词:")
    print("   - 'alexa' (亚马逊 Alexa)")
    print("   - 'hey jarvis' (贾维斯)")
    print("   - 'hey mycroft' (迈克洛夫特)")
    print("   - 'hey rhasspy' (Rhasspy)")
    print("   - 'timer' (定时器)")
    print("   - 'weather' (天气)")

    # 选择录音设备
    print("\n选择录音设备:")
    input_devices, _ = list_audio_devices()
    device_index = select_device(input_devices, "录音")
    if device_index is None:
        return

    # 初始化 PyAudio
    print(f"\n🎤 打开音频流 (设备索引: {device_index})...")
    p = pyaudio.PyAudio()

    try:
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=1280  # 80ms @ 16kHz
        )
        print("✅ 音频流已打开")
    except Exception as e:
        print(f"❌ 无法打开音频流: {e}")
        p.terminate()
        return

    print("\n" + "=" * 60)
    print("🎯 开始监听唤醒词...")
    print("=" * 60)
    print("💡 请对着麦克风说唤醒词（例如: 'alexa', 'hey jarvis'）")
    print("⏹️  按 Ctrl+C 停止监听")
    print("⏰  30秒后自动停止（或检测到3次后停止）")
    print("=" * 60)

    detection_count = 0
    max_detections = 3

    try:
        import time
        start_time = time.time()
        stream.start_stream()

        print("\n" + "-" * 40)

        while detection_count < max_detections and (time.time() - start_time) < 30:
            # 读取音频数据
            audio_data = stream.read(1280, exception_on_overflow=False)
            audio_frame = np.frombuffer(audio_data, dtype=np.int16)

            # 预测
            predictions = oww_model.predict(audio_frame)

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
                    print("-" * 40)
                    print("💡 继续监听...")
                    break

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    finally:
        print(f"\n📊 测试结束")
        print(f"   总检测次数: {detection_count}")
        if detection_count > 0:
            print("   ✅ 唤醒词检测正常工作!")
        else:
            print("   ℹ️  未检测到唤醒词（可能需要：\n"
                  "      1. 靠近麦克风说话\n"
                  "      2. 发音清晰\n"
                  "      3. 尝试其他唤醒词 ('alexa', 'hey jarvis')）")

        stream.stop_stream()
        stream.close()
        p.terminate()


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🎛️  ReSpeaker 硬件测试工具")
    print("=" * 60)

    while True:
        print("\n" + "-" * 60)
        print("请选择测试:")
        print("  [1] 📤 测试麦克风录音")
        print("  [2] 📥 测试音响播放")
        print("  [3] 🎯 测试唤醒词识别")
        print("  [4] ✅ 运行全部测试")
        print("  [l] 📋 查看设备列表")
        print("  [q] 🚪 退出")

        choice = input("\n请输入选项 (1-4, l, q): ").strip().lower()

        if choice == '1':
            test_microphone()
        elif choice == '2':
            test_speaker()
        elif choice == '3':
            test_wake_word()
        elif choice == '4':
            test_microphone()
            print("\n" + "-" * 60)
            test_speaker()
            print("\n" + "-" * 60)
            test_wake_word()
        elif choice == 'l':
            list_audio_devices()
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
