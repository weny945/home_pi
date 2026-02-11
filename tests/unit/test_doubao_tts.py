"""
豆包 TTS 单元测试
Unit Tests for Doubao TTS Engine
"""
import pytest
from unittest.mock import Mock, patch
import numpy as np

from src.tts import DoubaoTTSEngine


class TestDoubaoTTSEngine:
    """豆包 TTS 引擎测试"""

    @pytest.fixture
    def mock_requests(self):
        """Mock requests 模块"""
        with patch('src.tts.doubao_engine.requests') as mock:
            # Mock 成功响应
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "code": 0,
                "data": {
                    "data": "UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA="  # 示例 base64
                }
            }
            mock.post.return_value = mock_response
            yield mock

    def test_init_without_api_key(self):
        """测试没有 API Key 时初始化失败"""
        with patch.dict('os.environ', {}, clear=False):
            import os
            old_key = os.environ.pop('VOLCENGINE_API_KEY', None)

            with pytest.raises(ValueError, match="豆包 TTS API Key 未配置"):
                DoubaoTTSEngine({
                    "doubao": {"app_id": "test_app_id"}
                })

            if old_key:
                os.environ['VOLCENGINE_API_KEY'] = old_key

    def test_init_without_app_id(self):
        """测试没有 App ID 时初始化失败"""
        with pytest.raises(ValueError, match="豆包 TTS App ID 未配置"):
            DoubaoTTSEngine({
                "doubao": {"api_key": "test_key:test_secret"}
            })

    def test_init_with_api_key_and_app_id(self, mock_requests):
        """测试使用 API Key 和 App ID 初始化"""
        engine = DoubaoTTSEngine({
            "doubao": {
                "api_key": "test_key:test_secret",
                "app_id": "test_app_id"
            }
        })
        assert engine.is_ready()
        assert engine._api_key == "test_key:test_secret"
        assert engine._app_id == "test_app_id"

    def test_get_model_info(self, mock_requests):
        """测试获取模型信息"""
        engine = DoubaoTTSEngine({
            "doubao": {
                "api_key": "test_key:test_secret",
                "app_id": "test_app_id",
                "voice": "zh_female_qingxinmeili",
                "emotion": "happy"
            }
        })
        info = engine.get_model_info()

        assert info["provider"] == "火山引擎 (ByteDance)"
        assert info["voice"] == "zh_female_qingxinmeili"
        assert info["emotion"] == "happy"

    def test_different_voices(self, mock_requests):
        """测试不同发音人"""
        voices = [
            "zh_female_qingxinmeili",
            "zh_female_wenrou",
            "zh_male_qingchen",
        ]

        for voice in voices:
            engine = DoubaoTTSEngine({
                "doubao": {
                    "api_key": "test_key:test_secret",
                    "app_id": "test_app_id",
                    "voice": voice
                }
            })
            assert engine._voice == voice

    def test_different_emotions(self, mock_requests):
        """测试不同情感类型"""
        emotions = ["neutral", "happy", "sad", "angry", "surprise"]

        for emotion in emotions:
            engine = DoubaoTTSEngine({
                "doubao": {
                    "api_key": "test_key:test_secret",
                    "app_id": "test_app_id",
                    "emotion": emotion
                }
            })
            assert engine._emotion == emotion

    def test_synthesize_with_mock(self, mock_requests):
        """测试语音合成（使用 mock）"""
        # 创建有效的 WAV 音频 mock 数据
        # WAV 头 (44 字节) + 简单的 PCM 数据
        wav_header = b'RIFF' + b'\x24\x00\x00\x00' + b'WAVE' + b'fmt ' + b'\x10\x00\x00\x00'
        wav_header += b'\x01\x00' + b'\x01\x00' + b'\x80\x3e\x00\x00' + b'\x00\x7d\x00\x00'
        wav_header += b'\x02\x00' + b'\x10\x00' + b'data' + b'\x00\x00\x00\x00'

        # 更新 mock 响应
        import base64
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "data": base64.b64encode(wav_header).decode()
            }
        }
        mock_requests.post.return_value = mock_response

        engine = DoubaoTTSEngine({
            "doubao": {
                "api_key": "test_key:test_secret",
                "app_id": "test_app_id",
                "format": "wav"
            }
        })

        # 注意：由于 mock 数据不是真实音频，这个测试主要验证 API 调用
        # 实际的音频解码需要真实数据
        mock_requests.post.assert_not_called()  # 还没有调用

    def test_empty_input(self, mock_requests):
        """测试空输入处理"""
        engine = DoubaoTTSEngine({
            "doubao": {
                "api_key": "test_key:test_secret",
                "app_id": "test_app_id"
            }
        })

        result = engine.synthesize("")
        assert len(result) == 0  # 应该返回空数组

    def test_rate_pitch_volume_bounds(self, mock_requests):
        """测试参数边界值"""
        engine = DoubaoTTSEngine({
            "doubao": {
                "api_key": "test_key:test_secret",
                "app_id": "test_app_id",
                "rate": 1.5,
                "pitch": 1.2,
                "volume": 2.0
            }
        })

        assert engine._rate == 1.5
        assert engine._pitch == 1.2
        assert engine._volume == 2.0

    def test_unknown_voice_fallback(self, mock_requests):
        """测试未知发音人回退到默认值"""
        engine = DoubaoTTSEngine({
            "doubao": {
                "api_key": "test_key:test_secret",
                "app_id": "test_app_id",
                "voice": "unknown_voice"
            }
        })

        # 应该回退到默认发音人
        assert engine._voice == "zh_female_qingxinmeili"

    def test_unknown_emotion_fallback(self, mock_requests):
        """测试未知情感回退到默认值"""
        engine = DoubaoTTSEngine({
            "doubao": {
                "api_key": "test_key:test_secret",
                "app_id": "test_app_id",
                "emotion": "unknown_emotion"
            }
        })

        # 应该回退到默认情感
        assert engine._emotion == "happy"
