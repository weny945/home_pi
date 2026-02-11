"""
音频设备诊断脚本
用于排查 PyAudio 设备访问问题
"""
import pyaudio
import sys

def diagnose_audio_devices():
    """诊断音频设备"""
    print("=" * 60)
    print("音频设备诊断")
    print("=" * 60)
    print()

    try:
        p = pyaudio.PyAudio()
        device_count = p.get_device_count()
        print(f"检测到 {device_count} 个音频设备")
        print()

        input_devices = []
        output_devices = []

        for i in range(device_count):
            try:
                info = p.get_device_info_by_index(i)
                print(f"设备 {i}:")
                print(f"  名称: {info['name']}")
                print(f"  输入通道: {info['maxInputChannels']}")
                print(f"  输出通道: {info['maxOutputChannels']}")
                print(f"  默认采样率: {info['defaultSampleRate']}")
                print()

                if info['maxInputChannels'] > 0:
                    input_devices.append(i)
                if info['maxOutputChannels'] > 0:
                    output_devices.append(i)
            except Exception as e:
                print(f"  错误: {e}")
                print()

        print("=" * 60)
        print("总结")
        print("=" * 60)
        print(f"输入设备: {input_devices}")
        print(f"输出设备: {output_devices}")
        print()

        if not input_devices:
            print("❌ 警告：没有检测到可用的输入设备！")
            print()
            print("可能的原因：")
            print("  1. 麦克风未插入或未被系统识别")
            print("  2. 音频驱动未正确安装")
            print("  3. 需要重启系统以加载驱动")
            print()
            print("解决方法：")
            print("  1. 检查麦克风连接：lsusb")
            print("  2. 检查 ALSA 设备：arecord -l")
            print("  3. 重启系统：sudo reboot")
            print()
            sys.exit(1)
        else:
            print("✅ 检测到可用的输入设备")
            print()
            print("推荐配置 (config.yaml):")
            print(f"  device_index: {input_devices[0]}  # 使用第一个输入设备")
            print("  # 或使用 ALSA 设备名称：")
            print("  # device_name: \"plughw:0,0\"")
            print()

        p.terminate()

    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    diagnose_audio_devices()
