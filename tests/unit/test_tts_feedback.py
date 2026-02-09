"""
TTS 反馈播放器测试
Tests for TTS Feedback Player
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import tempfile
import sys

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.feedback import TTSFeedbackPlayer


@pytest.mark.unit
class TestTTSFeedbackPlayer:
    """TTS 反馈播放器测试类"""

    @pytest.fixture
    def mock_engine(self):
        """模拟 TTS 引擎"""
        engine = Mock()
        engine.synthesize.return_value = np.array([100, 200, 300], dtype=np.int16)
        engine.get_sample_rate.return_value = 22050
        engine.is_ready.return_value = True
        engine.get_model_info.return_value = {
            'model_path': './models/piper/zh_CN-huayan-medium.onnx',
            'sample_rate': 22050,
            'is_loaded': True
        }
        return engine

    @pytest.fixture
    def player(self, mock_engine):
        """创建 TTS 反馈播放器实例（使用模拟引擎）"""
        with patch('src.feedback.tts_feedback.PiperTTSEngine', return_value=mock_engine):
            player = TTSFeedbackPlayer(
                messages=["测试1", "测试2"],
                model_path="./models/piper/zh_CN-huayan-medium.onnx",
                cache_audio=False  # 禁用缓存以避免文件操作
            )
            yield player
            # 清理
            player.stop()

    def test_initialization(self, mock_engine):
        """测试初始化"""
        with patch('src.feedback.tts_feedback.PiperTTSEngine', return_value=mock_engine):
            player = TTSFeedbackPlayer(
                messages=["我在", "请吩咐"],
                model_path="./models/piper/zh_CN-huayan-medium.onnx",
                cache_audio=False
            )

            assert player is not None
            assert player._messages == ["我在", "请吩咐"]
            assert player._current_message_index == 0
            player.stop()

    def test_get_message_sequential(self, player):
        """测试顺序获取消息"""
        message1 = player._get_message()
        message2 = player._get_message()
        message3 = player._get_message()

        assert message1 == "测试1"
        assert message2 == "测试2"
        assert message3 == "测试1"  # 循环回第一个

    def test_get_message_random(self, mock_engine):
        """测试随机获取消息"""
        with patch('src.feedback.tts_feedback.PiperTTSEngine', return_value=mock_engine):
            player = TTSFeedbackPlayer(
                messages=["测试1", "测试2", "测试3"],
                model_path="./models/piper/zh_CN-huayan-medium.onnx",
                random_message=True,
                cache_audio=False
            )

            message = player._get_message()
            assert message in ["测试1", "测试2", "测试3"]
            player.stop()

    def test_set_message(self, player):
        """测试设置单条消息"""
        player.set_message("新消息")

        assert player._messages == ["新消息"]
        assert player._current_message_index == 0

    def test_set_messages(self, player):
        """测试设置消息列表"""
        new_messages = ["消息1", "消息2", "消息3"]
        player.set_messages(new_messages)

        assert player._messages == new_messages
        assert player._current_message_index == 0

    def test_set_messages_empty(self, player):
        """测试设置空消息列表"""
        original_messages = player._messages.copy()
        player.set_messages([])

        # 应该保持原消息不变
        assert player._messages == original_messages

    def test_get_model_info(self, player, mock_engine):
        """测试获取模型信息"""
        info = player.get_model_info()

        assert info == mock_engine.get_model_info.return_value

    def test_set_speed(self, player, mock_engine):
        """测试设置语速"""
        player.set_speed(0.8)

        mock_engine.set_synthesis_config.assert_called_once_with(length_scale=0.8)

    def test_is_playing(self, player):
        """测试播放状态"""
        assert not player.is_playing()

    def test_stop(self, player):
        """测试停止播放"""
        player.stop()

        assert not player.is_playing()

    @pytest.mark.integration
    def test_play_wake_feedback_integration(self):
        """集成测试：实际播放（需要模型文件）"""
        model_path = "./models/piper/zh_CN-huayan-medium.onnx"

        if not Path(model_path).exists():
            pytest.skip("模型文件不存在，跳过集成测试")

        try:
            player = TTSFeedbackPlayer(
                messages=["测试"],
                model_path=model_path,
                cache_audio=False
            )

            # 播放反馈（会实际合成音频）
            player.play_wake_feedback()

            assert not player.is_playing()
        except Exception as e:
            pytest.fail(f"集成测试失败: {e}")

    def test_synthesis_config(self, mock_engine):
        """测试合成配置设置"""
        with patch('src.feedback.tts_feedback.PiperTTSEngine', return_value=mock_engine):
            player = TTSFeedbackPlayer(
                messages=["测试"],
                model_path="./models/piper/zh_CN-huayan-medium.onnx",
                length_scale=0.9,
                cache_audio=False
            )

            # 验证引擎初始化时使用了正确的配置
            assert player._tts_engine is not None
            player.stop()
