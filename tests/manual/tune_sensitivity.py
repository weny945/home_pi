"""
Picovoice 灵敏度调优脚本
快速测试不同的灵敏度值
"""
import os
import sys
import numpy as np
import time
import argparse

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.wake_word import PicovoiceDetector
from src.audio import ReSpeakerInput
from src.config import get_config

def _expand_env_var(value: str) -> str:
    """展开环境变量"""
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        env_var = value[2:-1]
        return os.environ.get(env_var, value)
    return value

def test_sensitivity(sensitivity: float, duration: int = 30):
    """
    测试特定灵敏度值

    Args:
        sensitivity: 灵敏度值 (0.0-1.0)
        duration: 测试时长（秒）
    """
    print("=" * 60)
    print(f"测试灵敏度: {sensitivity}")
    print("=" * 60)
    print()

    # 加载配置
    config = get_config()
    wakeword_config = config.get_wakeword_config()
    audio_config = config.get_audio_config()

    # 获取 Access Key
    access_key = wakeword_config.get('access_key', '')
    access_key = _expand_env_var(access_key) if access_key else None

    # 初始化检测器（使用指定的灵敏度）
    detector = PicovoiceDetector(
        keyword_path=wakeword_config.get('model'),
        sensitivity=sensitivity,  # 使用指定的灵敏度
        access_key=access_key,
        model_path=wakeword_config.get('porcupine_model')
    )

    if not detector.is_ready:
        print("❌ 检测器未就绪")
        return False

    # 初始化音频输入
    audio_input = ReSpeakerInput(
        device_name=audio_config.get('input_device', 'plughw:0,0'),
        sample_rate=audio_config.get('sample_rate', 16000),
        channels=audio_config.get('channels', 1),
        chunk_size=audio_config.get('chunk_size', 512),
        input_gain=audio_config.get('input_gain', 1.0)
    )

    print(f"测试时长: {duration} 秒")
    print("请说 '胡桃' 测试唤醒")
    print()

    try:
        audio_input.start_stream()

        frame_count = 0
        detection_count = 0
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > duration:
                break

            # 读取音频帧
            audio_frame = audio_input.read_chunk()
            if audio_frame is None:
                continue

            frame_count += 1

            # 检测唤醒词
            detected = detector.process_frame(audio_frame)

            if detected:
                detection_count += 1
                elapsed_time = time.time() - start_time
                print(f"✅ 检测到唤醒词 #{detection_count}（{elapsed_time:.1f}s / 第 {frame_count} 帧）")

            # 每秒显示一次进度
            if frame_count % 31 == 0:
                remaining = duration - elapsed
                print(f"\r剩余时间: {remaining:.0f}s | 已检测: {detection_count} 次", end="", flush=True)

        print("\n")
        print("-" * 60)
        print(f"测试完成 (灵敏度: {sensitivity})")
        print(f"  测试时长: {duration} 秒")
        print(f"  检测次数: {detection_count} 次")
        print("-" * 60)
        print()

        return detection_count > 0

    except KeyboardInterrupt:
        print("\n\n用户中断")
        return False

    finally:
        audio_input.stop_stream()

def main():
    parser = argparse.ArgumentParser(description='Picovoice 灵敏度调优脚本')
    parser.add_argument('--sensitivity', type=float, default=None,
                        help='测试单个灵敏度值 (0.0-1.0)')
    parser.add_argument('--auto', action='store_true',
                        help='自动测试多个灵敏度值')
    parser.add_argument('--duration', type=int, default=20,
                        help='每次测试时长（秒），默认20秒')

    args = parser.parse_args()

    print("=" * 60)
    print("Picovoice 灵敏度调优工具")
    print("=" * 60)
    print()

    if args.sensitivity is not None:
        # 测试单个灵敏度值
        print(f"测试灵敏度: {args.sensitivity}")
        print()
        test_sensitivity(args.sensitivity, args.duration)

    elif args.auto:
        # 自动测试多个灵敏度值
        print("自动测试模式")
        print()
        print("将依次测试以下灵敏度值：")
        sensitivities = [0.5, 0.65, 0.75, 0.85]
        for s in sensitivities:
            print(f"  - {s}")
        print()
        print(f"每次测试时长: {args.duration} 秒")
        print()
        input("按 Enter 开始测试...")
        print()

        results = {}
        for sensitivity in sensitivities:
            success = test_sensitivity(sensitivity, args.duration)
            results[sensitivity] = success

            if sensitivity < sensitivities[-1]:
                print("准备下一轮测试...")
                time.sleep(2)

        # 显示总结
        print()
        print("=" * 60)
        print("测试总结")
        print("=" * 60)
        for sensitivity, success in results.items():
            status = "✅ 检测成功" if success else "❌ 未检测到"
            print(f"  灵敏度 {sensitivity}: {status}")
        print()
        print("建议：")
        print("  - 选择能稳定检测到唤醒词的最低灵敏度值")
        print("  - 灵敏度过高会导致误报（非唤醒词也被识别）")
        print("  - 推荐范围: 0.65-0.80")
        print()

    else:
        # 交互式模式
        print("交互式测试模式")
        print()
        print("当前配置:")
        config = get_config()
        current_sensitivity = config.get_wakeword_config().get('sensitivity', 0.5)
        print(f"  config.yaml 中的灵敏度: {current_sensitivity}")
        print()
        print("请输入要测试的灵敏度值 (0.0-1.0)")
        print("推荐值: 0.65, 0.75, 0.85")
        print()

        try:
            sensitivity = float(input("灵敏度: "))
            if 0.0 <= sensitivity <= 1.0:
                print()
                test_sensitivity(sensitivity, args.duration)
            else:
                print("❌ 错误：灵敏度必须在 0.0-1.0 之间")
        except ValueError:
            print("❌ 错误：请输入有效的数字")
        except KeyboardInterrupt:
            print("\n\n用户中断")

if __name__ == "__main__":
    main()
