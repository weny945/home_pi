"""
STT 引擎单元测试
Unit Tests for STT Engine
"""
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 测试数据路径
TEST_DATA_DIR = Path(__file__).parent.parent / "data"


class TestFunASRSTTEngine:
    """FunASR STT 引擎测试"""

    def test_initialization(self):
        """测试引擎初始化"""
        # FunASR 可能未安装，跳过测试
        pytest.importorskip("funasr")

        from src.stt import FunASRSTTEngine

        engine = FunASRSTTEngine(
            model_name="iic/SenseVoiceSmall",
            device="cpu",
            load_model=False  # 不加载模型，快速测试
        )

        assert engine is not None
        assert engine._model_name == "iic/SenseVoiceSmall"
        assert engine._device == "cpu"

    def test_model_info(self):
        """测试获取模型信息"""
        pytest.importorskip("funasr")

        from src.stt import FunASRSTTEngine

        engine = FunASRSTTEngine(
            model_name="iic/SenseVoiceSmall",
            device="cpu",
            load_model=False
        )

        info = engine.get_model_info()

        assert isinstance(info, dict)
        assert info["model_name"] == "iic/SenseVoiceSmall"
        assert info["device"] == "cpu"
        assert "is_ready" in info

    @patch('src.stt.funasr_engine.AutoModel')
    def test_load_model(self, mock_auto_model):
        """测试模型加载"""
        pytest.importorskip("funasr")

        from src.stt import FunASRSTTEngine

        # Mock AutoModel
        mock_model_instance = MagicMock()
        mock_auto_model.return_value = mock_model_instance

        engine = FunASRSTTEngine(
            model_name="iic/SenseVoiceSmall",
            device="cpu",
            load_model=False
        )

        assert not engine.is_ready()

        engine.load_model()

        assert engine.is_ready()
        assert engine._model == mock_model_instance
        mock_auto_model.assert_called_once()

    @patch('src.stt.funasr_engine.AutoModel')
    def test_transcribe(self, mock_auto_model):
        """测试音频转录"""
        pytest.importorskip("funasr")

        from src.stt import FunASRSTTEngine

        # Mock 模型和识别结果
        mock_model_instance = MagicMock()
        mock_model_instance.generate.return_value = [
            {"text": "你好世界"}
        ]
        mock_auto_model.return_value = mock_model_instance

        engine = FunASRSTTEngine(
            model_name="iic/SenseVoiceSmall",
            device="cpu",
            load_model=False
        )

        # 强制设置为就绪
        engine._model = mock_model_instance
        engine._ready = True

        # 创建测试音频数据
        audio_data = np.random.randint(-32768, 32767, size=16000, dtype=np.int16)

        # 转录
        result = engine.transcribe(audio_data)

        assert result == "你好世界"
        mock_model_instance.generate.assert_called_once()

    @patch('src.stt.funasr_engine.AutoModel')
    def test_transcribe_file_not_found(self, mock_auto_model):
        """测试转录不存在的文件"""
        pytest.importorskip("funasr")

        from src.stt import FunASRSTTEngine

        mock_model_instance = MagicMock()
        mock_auto_model.return_value = mock_model_instance

        engine = FunASRSTTEngine(
            model_name="iic/SenseVoiceSmall",
            device="cpu",
            load_model=False
        )

        engine._model = mock_model_instance
        engine._ready = True

        # 文件不存在
        with pytest.raises(FileNotFoundError):
            engine.transcribe_file("/nonexistent/file.wav")

    @patch('src.stt.funasr_engine.AutoModel')
    def test_transcribe_model_not_ready(self, mock_auto_model):
        """测试模型未就绪时的转录"""
        pytest.importorskip("funasr")

        from src.stt import FunASRSTTEngine

        engine = FunASRSTTEngine(
            model_name="iic/SenseVoiceSmall",
            device="cpu",
            load_model=False
        )

        # 模型未加载
        audio_data = np.random.randint(-32768, 32767, size=16000, dtype=np.int16)

        with pytest.raises(RuntimeError, match="模型未加载"):
            engine.transcribe(audio_data)

    def test_get_supported_sample_rate(self):
        """测试获取支持的采样率"""
        pytest.importorskip("funasr")

        from src.stt import FunASRSTTEngine

        engine = FunASRSTTEngine(
            model_name="iic/SenseVoiceSmall",
            device="cpu",
            load_model=False
        )

        sample_rate = engine.get_supported_sample_rate()
        assert sample_rate == 16000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
