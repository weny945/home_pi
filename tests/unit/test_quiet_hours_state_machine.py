"""
夜间免打扰功能测试（状态机静默时段）
Quiet Hours Feature Tests for State Machine
"""
import pytest
from datetime import datetime, time
from unittest.mock import Mock, MagicMock, patch
from src.state_machine.machine import StateMachine


class TestQuietHoursInStateMachine:
    """状态机静默时段测试"""

    def test_is_in_quiet_hours_night(self):
        """测试夜间时段检测"""
        # 创建状态机（带静默时段配置）
        config = {
            "quiet_hours": {
                "enabled": True,
                "start": "23:00",
                "end": "06:00"
            }
        }

        # Mock 依赖
        audio_input = Mock()
        detector = Mock()
        feedback_player = Mock()

        state_machine = StateMachine(
            audio_input=audio_input,
            detector=detector,
            feedback_player=feedback_player,
            config=config
        )

        # 检查静默时段
        assert state_machine._quiet_hours is not None
        assert state_machine._quiet_hours == (time(23, 0), time(6, 0))

    def test_is_in_quiet_hours_cross_day(self):
        """测试跨日静默时段判断"""
        config = {
            "quiet_hours": {
                "enabled": True,
                "start": "23:00",
                "end": "06:00"
            }
        }

        audio_input = Mock()
        detector = Mock()
        feedback_player = Mock()

        state_machine = StateMachine(
            audio_input=audio_input,
            detector=detector,
            feedback_player=feedback_player,
            config=config
        )

        # 测试不同时间
        test_cases = [
            (22, 0, False),   # 晚上10点 - 不在静默时段
            (23, 0, True),    # 晚上11点 - 在静默时段
            (2, 0, True),     # 凌晨2点 - 在静默时段
            (6, 0, True),     # 早上6点 - 在静默时段
            (6, 1, False),    # 早上6:01 - 不在静默时段
            (7, 0, False),    # 早上7点 - 不在静默时段
        ]

        for hour, minute, expected in test_cases:
            with patch('src.state_machine.machine.datetime') as mock_datetime:
                # 模拟当前时间
                mock_now = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
                mock_datetime.now.return_value = mock_now

                result = state_machine._is_in_quiet_hours()
                assert result == expected, f"{hour:02d}:{minute:02d} should be quiet={expected}"

    def test_update_idle_skips_wake_word_in_quiet_hours(self):
        """测试静默时段内跳过唤醒词检测"""
        config = {
            "quiet_hours": {
                "enabled": True,
                "start": "23:00",
                "end": "06:00"
            }
        }

        audio_input = Mock()
        detector = Mock()
        feedback_player = Mock()

        state_machine = StateMachine(
            audio_input=audio_input,
            detector=detector,
            feedback_player=feedback_player,
            config=config
        )
        state_machine._running = True

        # 模拟在静默时段内（凌晨2点）
        with patch('src.state_machine.machine.datetime') as mock_datetime:
            mock_now = datetime.now().replace(hour=2, minute=0, second=0, microsecond=0)
            mock_datetime.now.return_value = mock_now

            # 调用 _update_idle
            state_machine._update_idle()

            # 验证检测器没有被调用（因为在静默时段）
            assert detector.process_frame.call_count == 0

    def test_update_idle_normal_outside_quiet_hours(self):
        """测试非静默时段正常检测唤醒词"""
        config = {
            "quiet_hours": {
                "enabled": True,
                "start": "23:00",
                "end": "06:00"
            }
        }

        audio_input = Mock()
        detector = Mock()
        feedback_player = Mock()

        state_machine = StateMachine(
            audio_input=audio_input,
            detector=detector,
            feedback_player=feedback_player,
            config=config
        )
        state_machine._running = True

        # 模拟在非静默时段（早上7点）
        with patch('src.state_machine.machine.datetime') as mock_datetime:
            mock_now = datetime.now().replace(hour=7, minute=0, second=0, microsecond=0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.time.side_effect = lambda: mock_now.time()

            # Mock audio frame
            audio_frame = b"fake_audio_data"
            audio_input.read_chunk.return_value = audio_frame

            # 调用 _update_idle
            state_machine._update_idle()

            # 验证检测器被调用（因为不在静默时段）
            assert detector.process_frame.call_count > 0

    def test_quiet_hours_disabled(self):
        """测试禁用静默时段"""
        config = {
            "quiet_hours": {
                "enabled": False
            }
        }

        audio_input = Mock()
        detector = Mock()
        feedback_player = Mock()

        state_machine = StateMachine(
            audio_input=audio_input,
            detector=detector,
            feedback_player=feedback_player,
            config=config
        )

        # 验证静默时段未设置
        assert state_machine._quiet_hours is None
        assert state_machine._is_in_quiet_hours() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
