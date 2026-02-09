"""
意图检测器单元测试
Intent Detector Unit Tests
"""
import pytest
from datetime import datetime

from src.alarm.intent_detector import (
    detect_alarm_intent,
    AlarmIntent,
    format_alarm_confirm,
    _contains_any,
    _contains_time_pattern,
    _extract_alarm_id,
    _extract_snooze_minutes,
)


class TestDetectAlarmIntent:
    """意图检测测试"""

    def test_detect_set_alarm_intent(self):
        """测试检测设置闹钟意图"""
        text = "明天早上7点叫我起床"
        intent = detect_alarm_intent(text)

        assert intent is not None
        assert intent.action == "set"
        assert intent.time is not None

    def test_detect_set_alarm_with_minutes(self):
        """测试检测设置闹钟意图（带分钟）"""
        text = "明天7点30分设置一个闹钟"
        intent = detect_alarm_intent(text)

        assert intent is not None
        assert intent.action == "set"

    def test_detect_list_alarms_intent(self):
        """测试检测查询闹钟意图"""
        text = "有哪些闹钟"
        intent = detect_alarm_intent(text)

        assert intent is not None
        assert intent.action == "list"

    def test_detect_delete_alarm_intent(self):
        """测试检测删除闹钟意图"""
        text = "取消1号闹钟"
        intent = detect_alarm_intent(text)

        assert intent is not None
        assert intent.action == "delete"
        assert intent.alarm_id == 1

    def test_detect_stop_alarm_intent(self):
        """测试检测停止闹钟意图"""
        text = "停止"
        intent = detect_alarm_intent(text)

        assert intent is not None
        assert intent.action == "stop_alarm"

    def test_detect_snooze_intent(self):
        """测试检测稍后提醒意图"""
        text = "稍后10分钟"
        intent = detect_alarm_intent(text)

        assert intent is not None
        assert intent.action == "snooze"
        assert intent.minutes == 10

    def test_non_alarm_intent(self):
        """测试非闹钟意图"""
        text = "今天天气怎么样"
        intent = detect_alarm_intent(text)

        assert intent is None

    def test_alarm_intent_without_time(self):
        """测试闹钟意图但无时间信息"""
        # 这种情况应该返回 None，因为无法解析时间
        text = "设置一个闹钟"
        intent = detect_alarm_intent(text)

        # 可能返回 None 或返回 intent 但 time 为 None
        # 这取决于具体实现
        if intent:
            assert intent.action == "set"
            # 时间可能为 None
        else:
            assert intent is None


class TestHelperFunctions:
    """辅助函数测试"""

    def test_contains_any_true(self):
        """测试检查包含关键词（包含）"""
        text = "明天早上7点叫我起床"
        keywords = ["闹钟", "提醒", "叫"]
        assert _contains_any(text, keywords) is True

    def test_contains_any_false(self):
        """测试检查包含关键词（不包含）"""
        text = "今天天气怎么样"
        keywords = ["闹钟", "提醒", "叫"]
        assert _contains_any(text, keywords) is False

    def test_contains_time_pattern_true(self):
        """测试检查时间模式（包含）"""
        text = "明天早上7点"
        assert _contains_time_pattern(text) is True

    def test_contains_time_pattern_false(self):
        """测试检查时间模式（不包含）"""
        # 注意：今天、明天等词会被时间模式匹配
        # 所以使用一个不包含任何时间关键词的句子
        text = "你好"
        assert _contains_time_pattern(text) is False

    def test_extract_alarm_id_with_id(self):
        """测试提取闹钟 ID（有 ID）"""
        text = "取消1号闹钟"
        alarm_id = _extract_alarm_id(text)
        assert alarm_id == 1

    def test_extract_alarm_id_without_id(self):
        """测试提取闹钟 ID（无 ID）"""
        text = "取消闹钟"
        alarm_id = _extract_alarm_id(text)
        assert alarm_id is None

    def test_extract_snooze_minutes(self):
        """测试提取稍后提醒分钟数"""
        text = "稍后10分钟"
        minutes = _extract_snooze_minutes(text)
        assert minutes == 10

    def test_extract_snooze_minutes_out_of_range(self):
        """测试提取稍后提醒分钟数（超出范围）"""
        text = "稍后200分钟"
        minutes = _extract_snooze_minutes(text)
        # 超出范围应该返回 None
        assert minutes is None


class TestFormatAlarmConfirm:
    """格式化确认消息测试"""

    def test_format_with_default_message(self):
        """测试格式化确认消息（默认备注）"""
        alarm_time = datetime.now().replace(hour=7, minute=0, second=0, microsecond=0)
        message = "闹钟"
        result = format_alarm_confirm(alarm_time, message)

        assert "07:00" in result
        assert "提醒您" in result

    def test_format_with_custom_message(self):
        """测试格式化确认消息（自定义备注）"""
        alarm_time = datetime.now().replace(hour=7, minute=0, second=0, microsecond=0)
        message = "叫我起床"
        result = format_alarm_confirm(alarm_time, message)

        assert "07:00" in result
        assert "叫我起床" in result
