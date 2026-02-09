"""
音频反馈播放器测试
Tests for Audio Feedback Player
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.feedback.audio_feedback import AudioFeedbackPlayer


@pytest.mark.unit
class TestAudioFeedbackPlayer:
    """音频反馈播放器测试类"""

    def test_init_beep_mode(self):
        """测试初始化蜂鸣模式"""
        player = AudioFeedbackPlayer(mode="beep")
        assert player._mode == "beep"
        assert player._is_playing is False

    def test_init_audio_file_mode(self):
        """测试初始化音频文件模式"""
        player = AudioFeedbackPlayer(mode="audio_file", audio_file="test.wav")
        assert player._mode == "audio_file"
        assert player._audio_file == "test.wav"

    def test_generate_beep(self):
        """测试生成蜂鸣声"""
        player = AudioFeedbackPlayer(
            mode="beep",
            sample_rate=16000,
            beep_duration_ms=200,
            beep_frequency=880
        )

        beep_data = player._generate_beep()

        # 验证数据类型和形状
        assert isinstance(beep_data, np.ndarray)
        assert beep_data.dtype == np.int16

        # 验证长度 (200ms @ 16kHz = 3200 samples)
        expected_length = int(16000 * 0.2)
        assert len(beep_data) == expected_length

        # 验证音量范围 (16-bit PCM)
        assert np.max(np.abs(beep_data)) <= 32767

    @patch('src.feedback.audio_feedback.pyaudio.PyAudio')
    def test_play_wake_feedback_beep(self, mock_pyaudio_class):
        """测试播放蜂鸣反馈"""
        # Mock PyAudio
        mock_pyaudio = MagicMock()
        mock_stream = MagicMock()
        mock_pyaudio.open.return_value = mock_stream
        mock_pyaudio_class.return_value = mock_pyaudio

        player = AudioFeedbackPlayer(mode="beep")
        player.play_wake_feedback()

        # 验证播放完成
        assert player._is_playing is False

    @patch('src.feedback.audio_feedback.pyaudio.PyAudio')
    def test_is_playing(self, mock_pyaudio_class):
        """测试 is_playing 方法"""
        player = AudioFeedbackPlayer(mode="beep")
        assert player.is_playing() is False

    @patch('src.feedback.audio_feedback.pyaudio.PyAudio')
    def test_stop(self, mock_pyaudio_class):
        """测试停止播放"""
        mock_pyaudio = MagicMock()
        mock_stream = MagicMock()
        mock_pyaudio.open.return_value = mock_stream
        mock_pyaudio_class.return_value = mock_pyaudio

        player = AudioFeedbackPlayer(mode="beep")
        player.play_wake_feedback()
        player.stop()

        assert player._is_playing is False
        assert player._stream is None
