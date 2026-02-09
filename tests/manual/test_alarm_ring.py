#!/usr/bin/env python3
"""
测试闹钟响铃功能
播放闹钟铃声并验证音频输出
"""
import sys
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.feedback.audio_feedback import AudioFeedbackPlayer

def test_alarm_ringtone():
    """测试闹钟铃声"""
    print("=" * 60)
    print("闹钟响铃测试")
    print("=" * 60)

    # 创建反馈播放器
    player = AudioFeedbackPlayer(
        mode="beep",
        output_device="default",  # 使用默认设备
        sample_rate=16000
    )

    print("\n播放闹钟铃声（循环 10 秒）...")
    print("按 Ctrl+C 停止\n")

    try:
        # 播放铃声，循环 10 秒
        player.play_alarm_ringtone(loop=True, duration=10)

        # 等待播放完成
        while player.is_alarm_playing():
            time.sleep(0.5)
            print("🔔 响铃中...")

        print("\n✅ 测试完成")

    except KeyboardInterrupt:
        print("\n停止播放")
        player.stop_alarm_ringtone()

if __name__ == "__main__":
    test_alarm_ringtone()
