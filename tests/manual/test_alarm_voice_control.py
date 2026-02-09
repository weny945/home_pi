"""
闹钟语音控制测试
Alarm Voice Control Test

验证闹钟响铃时可以通过语音控制
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime, time
from unittest.mock import Mock, patch, MagicMock
from src.state_machine.machine import StateMachine
from src.alarm.alarm_storage import Alarm


def test_alarm_voice_control_in_quiet_hours():
    """测试静默时段内闹钟响铃时的语音控制"""
    print("=" * 70)
    print("测试：静默时段内闹钟响铃时的语音控制")
    print("=" * 70)

    # 配置：启用静默时段（23:00-06:00）
    config = {
        "quiet_hours": {
            "enabled": True,
            "start": "23:00",
            "end": "06:00"
        },
        "audio_quality": {},
        "text_quality": {},
        "conversation": {},
    }

    # Mock 依赖
    audio_input = Mock()
    detector = Mock()
    feedback_player = Mock()

    # 创建状态机
    state_machine = StateMachine(
        audio_input=audio_input,
        detector=detector,
        feedback_player=feedback_player,
        config=config
    )
    state_machine._running = True

    # 验证静默时段已设置
    assert state_machine._quiet_hours == (time(23, 0), time(6, 0))
    print("✓ 静默时段已设置: 23:00 - 06:00")

    # 模拟凌晨2点（在静默时段内）
    with patch('src.state_machine.machine.datetime') as mock_datetime:
        mock_now = datetime.now().replace(hour=2, minute=0, second=0, microsecond=0)
        mock_datetime.now.return_value = mock_now

        print(f"\n当前时间: {mock_now.strftime('%H:%M')} (静默时段内)")

        # 测试1：没有闹钟响铃时，唤醒词检测应该被跳过
        print("\n测试1：没有闹钟响铃")
        state_machine._alarm_ringing = False

        # 调用 _update_idle
        state_machine._update_idle()

        # 验证检测器没有被调用（因为在静默时段且没有闹钟）
        if detector.process_frame.call_count == 0:
            print("✓ 静默时段内，唤醒词检测被跳过（符合预期）")
        else:
            print("✗ 静默时段内，唤醒词检测仍然在工作")

        # 重置 mock
        detector.reset_mock()

        # 测试2：闹钟响铃时，唤醒词检测应该工作
        print("\n测试2：闹钟响铃中")
        state_machine._alarm_ringing = True

        # Mock 音频帧
        audio_frame = b"fake_audio_data"
        audio_input.read_chunk.return_value = audio_frame

        # 调用 _update_idle
        state_machine._update_idle()

        # 验证检测器被调用（因为闹钟在响铃，跳过静默时段检查）
        if detector.process_frame.call_count > 0:
            print(f"✓ 闹钟响铃时，唤醒词检测正常工作（调用次数: {detector.process_frame.call_count}）")
        else:
            print("✗ 闹钟响铃时，唤醒词检测未工作")

        print("\n" + "=" * 70)
        print("结论：")
        print("  - 静默时段内，唤醒词检测被禁用")
        print("  - 但闹钟响铃时，唤醒词检测恢复正常")
        print("  - 用户可以说'派蒙，停止'来控制闹钟")
        print("=" * 70)


def test_alarm_stop_intent():
    """测试停止闹钟的意图识别"""
    print("\n" + "=" * 70)
    print("测试：停止闹钟的意图识别")
    print("=" * 70)

    from src.alarm.intent_detector import detect_alarm_intent

    test_cases = [
        ("停止", "stop_alarm"),
        ("停下", "stop_alarm"),
        ("别响了", "stop_alarm"),
        ("够", None),  # 这个不应该被识别
        ("派蒙，停止", "stop_alarm"),  # 带唤醒词
    ]

    print("\n意图识别测试：")
    for text, expected_action in test_cases:
        intent = detect_alarm_intent(text)

        if expected_action:
            if intent and intent.action == expected_action:
                print(f"✓ '{text}' → {intent.action}")
            else:
                print(f"✗ '{text}' → 期望 {expected_action}, 实际 {intent.action if intent else 'None'}")
        else:
            if intent is None:
                print(f"✓ '{text}' → 未识别（符合预期）")
            else:
                print(f"✗ '{text}' → {intent.action} (不应该被识别)")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    test_alarm_voice_control_in_quiet_hours()
    test_alarm_stop_intent()
