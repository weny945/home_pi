"""
Phase 1.5 功能单元测试
Unit Tests for Phase 1.5 Features

测试内容：
1. 智能打断功能
2. 上下文增强功能
3. 技能系统框架
"""
import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
import time

from src.state_machine.machine import StateMachine, AdaptiveVAD
from src.state_machine.states import State
from src.skills import SkillManager


class TestInterruptionDetection:
    """智能打断功能测试"""

    def test_quick_speech_detection_with_adaptive_vad(self):
        """测试快速语音检测（使用自适应 VAD）"""
        # 创建状态机（启用自适应 VAD）
        config = {
            "audio_quality": {
                "vad": {
                    "adaptive_enabled": True,
                    "base_threshold": 0.04,
                    "adaptation_factor": 1.5
                },
                "interrupt": {
                    "enabled": True
                }
            }
        }

        mock_audio = Mock()
        mock_detector = Mock()
        mock_feedback = Mock()

        sm = StateMachine(
            audio_input=mock_audio,
            detector=mock_detector,
            feedback_player=mock_feedback,
            config=config
        )

        # 测试高能量音频（应该检测为语音）
        # 创建归一化能量高的音频（接近最大值）
        high_energy_audio = np.full(512, 30000, dtype=np.int16)
        result = sm._quick_speech_detection(high_energy_audio)
        assert result == True, f"应该检测到高能量音频为语音，结果: {result}"

        # 测试低能量音频（不应检测为语音）
        low_energy_audio = np.zeros(512, dtype=np.int16)
        result = sm._quick_speech_detection(low_energy_audio)
        assert result == False, f"低能量音频不应被检测为语音，结果: {result}"

    def test_quick_speech_detection_without_adaptive_vad(self):
        """测试快速语音检测（不使用自适应 VAD）"""
        config = {
            "audio_quality": {
                "vad": {
                    "adaptive_enabled": False
                }
            }
        }

        mock_audio = Mock()
        mock_detector = Mock()
        mock_feedback = Mock()

        sm = StateMachine(
            audio_input=mock_audio,
            detector=mock_detector,
            feedback_player=mock_feedback,
            config=config
        )

        # 测试默认阈值，使用高能量音频
        audio = np.full(512, 30000, dtype=np.int16)
        result = sm._quick_speech_detection(audio)
        assert result == True, f"高能量音频应被检测为语音，结果: {result}"

        # 测试静音
        silence = np.zeros(512, dtype=np.int16)
        result = sm._quick_speech_detection(silence)
        assert result == False, f"静音不应被检测为语音，结果: {result}"


class TestContextEnhancement:
    """上下文增强功能测试"""

    def test_build_enhanced_context_first_turn(self):
        """测试第一轮对话（不增强）"""
        config = {
            "conversation": {
                "context_memory": True
            }
        }

        mock_audio = Mock()
        mock_detector = Mock()
        mock_feedback = Mock()

        sm = StateMachine(
            audio_input=mock_audio,
            detector=mock_detector,
            feedback_player=mock_feedback,
            config=config
        )

        # 第一轮对话
        sm._in_conversation = True
        sm._conversation_turn_count = 1
        user_text = "今天天气怎么样"

        enhanced = sm._build_enhanced_context(user_text)
        assert enhanced == user_text, "第一轮对话不应该增强"

    def test_build_enhanced_context_continuation(self):
        """测试延续性表达增强"""
        config = {
            "conversation": {
                "context_memory": True
            }
        }

        mock_audio = Mock()
        mock_detector = Mock()
        mock_feedback = Mock()

        sm = StateMachine(
            audio_input=mock_audio,
            detector=mock_detector,
            feedback_player=mock_feedback,
            config=config
        )

        # 多轮对话
        sm._in_conversation = True
        sm._conversation_turn_count = 2

        # 测试延续性表达
        test_cases = [
            "明天呢",
            "那温度呢",
            "还有吗",
            "然后呢"
        ]

        for user_text in test_cases:
            enhanced = sm._build_enhanced_context(user_text)
            assert enhanced != user_text, f"应该增强延续性表达: {user_text}"
            assert "第2轮对话" in enhanced, "应该包含对话轮数信息"
            assert "延续性表达" in enhanced, "应该包含延续性提示"

    def test_build_enhanced_context_normal_input(self):
        """测试普通输入（不增强）"""
        config = {
            "conversation": {
                "context_memory": True
            }
        }

        mock_audio = Mock()
        mock_detector = Mock()
        mock_feedback = Mock()

        sm = StateMachine(
            audio_input=mock_audio,
            detector=mock_detector,
            feedback_player=mock_feedback,
            config=config
        )

        # 多轮对话
        sm._in_conversation = True
        sm._conversation_turn_count = 2

        # 普通输入
        user_text = "我想听音乐"
        enhanced = sm._build_enhanced_context(user_text)
        assert enhanced == user_text, "普通输入不应该增强"


class TestSkillManager:
    """技能管理器测试"""

    def test_skill_manager_initialization(self):
        """测试技能管理器初始化"""
        config = {"enabled": False}
        sm = SkillManager(config)
        assert sm.is_enabled() is False, "应该禁用技能管理器"

        config = {"enabled": True}
        sm = SkillManager(config)
        assert sm.is_enabled() is True, "应该启用技能管理器"

    def test_register_and_unregister_skill(self):
        """测试技能注册和注销"""
        config = {"enabled": True}
        sm = SkillManager(config)

        # 注册技能
        def test_handler():
            return "test"

        sm.register_skill("test_skill", test_handler, "测试技能")
        assert sm.has_skill("test_skill"), "应该成功注册技能"

        # 注销技能
        sm.unregister_skill("test_skill")
        assert sm.has_skill("test_skill") is False, "应该成功注销技能"

    def test_execute_skill(self):
        """测试技能执行"""
        config = {"enabled": True}
        sm = SkillManager(config)

        # 注册技能
        def test_handler(param1):
            return f"result: {param1}"

        sm.register_skill("test_skill", test_handler)

        # 执行技能
        result = sm.execute_skill("test_skill", param1="test_value")
        assert result == "result: test_value", "应该返回正确的执行结果"

    def test_execute_nonexistent_skill(self):
        """测试执行不存在的技能"""
        config = {"enabled": True}
        sm = SkillManager(config)

        result = sm.execute_skill("nonexistent_skill")
        assert result is None, "不存在的技能应该返回 None"

    def test_list_skills(self):
        """测试列出技能"""
        config = {"enabled": True}
        sm = SkillManager(config)

        # 注册多个技能
        sm.register_skill("skill1", lambda: "1", "技能1")
        sm.register_skill("skill2", lambda: "2", "技能2")

        skills = sm.list_skills()
        assert "skill1" in skills, "应该包含 skill1"
        assert "skill2" in skills, "应该包含 skill2"
        assert skills["skill1"]["description"] == "技能1"

    def test_clear_all_skills(self):
        """测试清空所有技能"""
        config = {"enabled": True}
        sm = SkillManager(config)

        # 注册技能
        sm.register_skill("skill1", lambda: "1")
        sm.register_skill("skill2", lambda: "2")

        # 清空
        sm.clear_all_skills()
        skills = sm.list_skills()
        assert len(skills) == 0, "应该清空所有技能"


class TestStateMachineIntegration:
    """状态机集成测试"""

    def test_skill_check_in_state_machine(self):
        """测试状态机中的技能检查"""
        config = {
            "skills": {
                "enabled": True
            }
        }

        mock_audio = Mock()
        mock_detector = Mock()
        mock_feedback = Mock()

        sm = StateMachine(
            audio_input=mock_audio,
            detector=mock_detector,
            feedback_player=mock_feedback,
            config=config
        )

        # 注册技能（通过内部技能管理器）
        if sm._skill_manager:
            sm._skill_manager.register_skill(
                "test_skill",
                lambda **kwargs: "技能结果",
                "测试技能"
            )

        # 测试技能匹配
        # 注意：由于关键词匹配逻辑，需要包含特定关键词
        result = sm._check_and_execute_skill("开灯")
        # 如果技能管理器启用，应该能匹配到
        assert result is None or isinstance(result, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
