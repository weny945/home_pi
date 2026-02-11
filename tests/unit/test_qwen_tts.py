"""
千问 TTS 引擎单元测试
Unit Tests for Qwen TTS Engine
"""
import pytest
import numpy as np
import requests
from unittest.mock import Mock, patch, MagicMock, mock_open
from src.tts.qwen_engine import QwenTTSEngine


@pytest.fixture
def mock_config():
    """Mock 配置"""
    return {
        "provider": "dashscope",
        "dashscope": {
            "api_key": "test-api-key",
            "model": "qwen3-tts-flash",
            "voice": "zhixiaobai",
            "format": "mp3",
            "sample_rate": 24000,
            "volume": 50,
            "rate": 1.0,
            "pitch": 1.0,
            "timeout": 30,
            "retry": 2
        }
    }


@pytest.fixture
def qwen_engine(mock_config):
    """创建 QwenTTSEngine 实例"""
    return QwenTTSEngine(mock_config)


class TestQwenTTSEngine:
    """千问 TTS 引擎测试"""

    def test_init(self, mock_config):
        """测试初始化"""
        engine = QwenTTSEngine(mock_config)

        assert engine._provider == "dashscope"
        assert engine._model == "qwen3-tts-flash"
        assert engine._voice == "zhixiaobai"
        assert engine._sample_rate == 24000
        assert engine._format == "mp3"

    def test_get_sample_rate(self, qwen_engine):
        """测试获取采样率"""
        assert qwen_engine.get_sample_rate() == 24000

    @patch('src.tts.qwen_engine.requests.get')
    def test_is_ready_success(self, mock_get, qwen_engine):
        """测试网络可用性检测 - 成功"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        assert qwen_engine.is_ready() is True

    @patch('src.tts.qwen_engine.requests.get')
    def test_is_ready_failure(self, mock_get, qwen_engine):
        """测试网络可用性检测 - 失败"""
        mock_get.side_effect = Exception("Network error")

        assert qwen_engine.is_ready() is False

    def test_is_ready_no_api_key(self):
        """测试无 API key 时不可用"""
        config = {"provider": "dashscope", "dashscope": {}}
        engine = QwenTTSEngine(config)

        assert engine.is_ready() is False

    @patch('src.tts.qwen_engine.requests.post')
    @patch('src.tts.qwen_engine.tempfile')
    @patch('src.tts.qwen_engine.os')
    def test_synthesize_success(self, mock_os, mock_tempfile, mock_post, qwen_engine):
        """测试合成成功"""
        # Mock HTTP 响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        # 生成有效的 base64 编码数据
        import base64
        test_audio = np.array([1, 2, 3], dtype=np.int16)
        test_audio_b64 = base64.b64encode(test_audio.tobytes()).decode('utf-8')

        mock_response.json.return_value = {
            "output": {
                "task_status": "SUCCESS",
                "audio": test_audio_b64
            }
        }
        mock_post.return_value = mock_response

        # Mock 临时文件
        mock_temp = Mock()
        mock_temp.name = "/tmp/test.mp3"
        mock_temp.write = Mock()
        mock_temp.__enter__ = Mock(return_value=mock_temp)
        mock_temp.__exit__ = Mock(return_value=False)
        mock_tempfile.NamedTemporaryFile.return_value = mock_temp
        mock_os.path.exists.return_value = False

        # Mock _decode_audio 直接返回结果
        with patch.object(qwen_engine, '_decode_audio', return_value=np.array([1, 2, 3], dtype=np.int16)):
            audio = qwen_engine.synthesize("测试文本")

            assert isinstance(audio, np.ndarray)
            assert audio.dtype == np.int16

    @patch('src.tts.qwen_engine.requests.post')
    def test_synthesize_with_retry(self, mock_post, qwen_engine):
        """测试重试机制"""
        # 生成有效的 base64 编码数据
        import base64
        test_audio = np.array([1, 2, 3], dtype=np.int16)
        test_audio_b64 = base64.b64encode(test_audio.tobytes()).decode('utf-8')

        # 第一次超时，第二次成功
        mock_response_timeout = Mock()
        mock_response_timeout.status_code = 200

        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.raise_for_status = Mock()
        mock_response_success.json.return_value = {
            "output": {
                "task_status": "SUCCESS",
                "audio": test_audio_b64
            }
        }

        mock_post.side_effect = [
            requests.exceptions.Timeout("Timeout"),
            mock_response_success
        ]

        # Mock _decode_audio 直接返回结果
        with patch.object(qwen_engine, '_decode_audio', return_value=np.array([1, 2, 3], dtype=np.int16)):
            audio = qwen_engine.synthesize("测试文本")

            assert isinstance(audio, np.ndarray)
            assert mock_post.call_count == 2

    @patch('src.tts.qwen_engine.os')
    def test_decode_audio(self, mock_os, qwen_engine):
        """测试音频解码"""
        import base64
        test_audio = np.array([1, 2, 3, 4, 5], dtype=np.int16)
        test_audio_b64 = base64.b64encode(test_audio.tobytes()).decode('utf-8')
        test_audio_bytes = base64.b64decode(test_audio_b64)

        # Mock pydub 音频处理
        try:
            from pydub import AudioSegment
            # 如果 pydub 已安装，真实测试
            decoded = qwen_engine._decode_audio(test_audio_bytes, "mp3")
            assert isinstance(decoded, np.ndarray)
            assert decoded.dtype == np.int16
        except ImportError:
            # pydub 未安装，跳过测试
            pytest.skip("pydub not installed")

    def test_get_model_info(self, qwen_engine):
        """测试获取模型信息"""
        info = qwen_engine.get_model_info()

        assert info["engine_type"] == "QwenTTS"
        assert info["provider"] == "dashscope"
        assert info["model"] == "qwen3-tts-flash"
        assert info["voice"] == "zhixiaobai"
        assert info["sample_rate"] == 24000

    def test_openai_provider(self):
        """测试 OpenAI 提供商"""
        config = {
            "provider": "openai",
            "openai": {
                "api_key": "test-openai-key",
                "model": "tts-1",
                "voice": "alloy"
            }
        }

        engine = QwenTTSEngine(config)

        assert engine._provider == "openai"
        assert engine._model == "tts-1"
        assert engine._voice == "alloy"

    def test_invalid_provider(self):
        """测试无效提供商"""
        config = {
            "provider": "invalid",
            "invalid": {}
        }

        with pytest.raises(ValueError, match="不支持的 TTS 提供商"):
            QwenTTSEngine(config)
