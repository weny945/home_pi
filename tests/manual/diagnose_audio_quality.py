"""
音频质量诊断脚本
实时显示麦克风音频能量，帮助调试灵敏度问题
"""
import os
import sys
import numpy as np
import time

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.audio import ReSpeakerInput
from src.config import get_config

def diagnose_audio_quality():
    """诊断音频质量"""
    print("=" * 60)
    print("音频质量诊断")
    print("=" * 60)
    print()
    print("此工具将实时显示麦克风音频能量")
    print("用于调试唤醒词灵敏度问题")
    print()
    print("使用方法：")
    print("  1. 保持安静，观察底噪能量（应该很低）")
    print("  2. 说话，观察语音能量（应该明显高于底噪）")
    print("  3. 按 Ctrl+C 退出")
    print()
    print("能量参考：")
    print("  底噪: 0-50")
    print("  正常语音: 500-5000")
    print("  大声说话: 5000-15000")
    print()

    # 加载配置
    config = get_config()
    audio_config = config.get_audio_config()

    # 初始化音频输入
    print("初始化音频输入...")
    audio_input = ReSpeakerInput(
        device_name=audio_config.get('input_device', 'plughw:0,0'),
        sample_rate=audio_config.get('sample_rate', 16000),
        channels=audio_config.get('channels', 1),
        chunk_size=audio_config.get('chunk_size', 512),
        input_gain=audio_config.get('input_gain', 1.0)
    )

    print(f"  设备: {audio_config.get('input_device')}")
    print(f"  采样率: {audio_config.get('sample_rate')} Hz")
    print(f"  增益: {audio_config.get('input_gain')}x")
    print()

    try:
        audio_input.start_stream()
        print("=" * 60)
        print("开始监听音频...")
        print("=" * 60)
        print()

        frame_count = 0
        energies = []
        max_energy = 0

        while True:
            # 读取音频帧
            audio_frame = audio_input.read_chunk()

            if audio_frame is None:
                continue

            frame_count += 1

            # 计算音频能量（RMS）
            energy = np.sqrt(np.mean(audio_frame.astype(np.float32) ** 2))
            energies.append(energy)
            max_energy = max(max_energy, energy)

            # 每 10 帧显示一次（约 0.32 秒）
            if frame_count % 10 == 0:
                # 计算平均能量
                avg_energy = np.mean(energies[-50:]) if len(energies) >= 50 else np.mean(energies)

                # 显示能量条
                bar_length = int(energy / 100)
                bar = "█" * min(bar_length, 60)

                # 判断音频状态
                if energy < 100:
                    status = "静音"
                    color = "\033[90m"  # 灰色
                elif energy < 1000:
                    status = "底噪"
                    color = "\033[37m"  # 白色
                elif energy < 3000:
                    status = "语音"
                    color = "\033[92m"  # 绿色
                else:
                    status = "大声"
                    color = "\033[93m"  # 黄色

                # 清除当前行并显示
                print(f"\r{color}能量: {energy:6.0f} | 平均: {avg_energy:6.0f} | 峰值: {max_energy:6.0f} | {status:4s} | {bar}\033[0m", end="", flush=True)

    except KeyboardInterrupt:
        print("\n\n用户中断")

    finally:
        audio_input.stop_stream()
        print("\n")
        print("=" * 60)
        print("诊断总结")
        print("=" * 60)

        if energies:
            avg_energy = np.mean(energies)
            print(f"平均能量: {avg_energy:.0f}")
            print(f"峰值能量: {max_energy:.0f}")
            print()

            # 给出建议
            if avg_energy < 50:
                print("⚠️  音频能量过低！")
                print("建议：")
                print("  1. 检查麦克风是否正常工作")
                print("  2. 提高 input_gain（当前: {})".format(audio_config.get('input_gain', 1.0)))
                print("  3. 靠近麦克风说话")
            elif avg_energy < 500:
                print("✅ 底噪水平正常")
                print("建议：")
                print("  如果说话时能量低于 1000，考虑提高 input_gain")
            else:
                print("✅ 音频质量良好")
                print()
                print("灵敏度调试建议：")
                print("  - 当前 sensitivity: {}".format(config.get_wakeword_config().get('sensitivity', 0.5)))
                print("  - 如果检测不灵敏，提高 sensitivity 到 0.75-0.85")
                print("  - 如果误报过多，降低 sensitivity 到 0.5-0.6")

        print("\n诊断结束")

if __name__ == "__main__":
    diagnose_audio_quality()
