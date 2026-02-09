#!/usr/bin/env python3
"""
唤醒词灵敏度测试
测试不同阈值下的识别效果
"""
import sys
import os
import time

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, project_root)

from src.config import get_config
from src.wake_word import create_wake_word_detector
from src.audio import create_audio_input
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

config = get_config()

print("=" * 70)
print("唤醒词灵敏度测试")
print("=" * 70)
print()
print("请将 ReSpeaker 放在 1 米距离")
print("准备测试唤醒词识别...")
print()

# 创建音频输入
audio_input = create_audio_input(config.get_audio_config())

# 创建唤醒词检测器（使用较低阈值）
detector = create_wake_word_detector({
    "engine": "openwakeword",
    "model": "paimon_paimon_zh.ppn",
    "threshold": 0.35,  # 较低阈值
    "model_dir": "./models/openwakeword"
})

print(f"当前阈值: 0.35")
print(f"开始测试，请说唤醒词: '派蒙' 或 'alexa'")
print()

# 启动音频流
audio_input.start_stream()

detection_count = 0
max_detections = 5  # 测试 5 次

try:
    print("监听中... (按 Ctrl+C 停止)")

    while detection_count < max_detections:
        # 读取音频帧
        frame = audio_input.read_frame()

        if frame is None:
            break

        # 检测唤醒词
        result = detector.detect(frame)

        if result:
            detection_count += 1
            print(f"\n✅ 第 {detection_count} 次检测到唤醒词!")
            print(f"   唤醒词: {result.word}")
            print(f"   置信度: {result.score:.3f}")

            if detection_count < max_detections:
                print(f"\n继续测试，请再次说唤醒词...")
                time.sleep(1)  # 避免重复触发

except KeyboardInterrupt:
    print("\n\n测试中断")

finally:
    audio_input.stop_stream()
    print(f"\n{'=' * 70}")
    print(f"测试完成，共检测到 {detection_count} 次唤醒")
    print(f"{'=' * 70}")
