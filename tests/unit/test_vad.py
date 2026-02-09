"""
VAD 检测器单元测试
Unit Tests for VAD Detector
"""
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 尝试导入 FunASR，如果失败则跳过所有测试
try:
    from funasr import AutoModel
    FUNASR_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    FUNASR_AVAILABLE = False

# 测试数据路径
TEST_DATA_DIR = Path(__file__).parent.parent / "data"


@pytest.mark.skipif(not FUNASR_AVAILABLE, reason="FunASR not installed")
class TestFunASRVADDetector:
    """FunASR VAD 检测器测试"""

    def test_initialization(self):
        """测试VAD检测器初始化"""
        from src.vad import FunASRVADDetector

        detector = FunASRVADDetector(
            vad_model="fsmn-vad",
            device="cpu",
            load_model=False  # 不加载模型，快速测试
        )

        assert detector is not None
        assert detector._vad_model == "fsmn-vad"
        assert detector._device == "cpu"

    @patch('funasr.AutoModel')
    def test_load_model(self, mock_auto_model):
        """测试VAD模型加载"""
        from src.vad import FunASRVADDetector

        # Mock AutoModel
        mock_model_instance = MagicMock()
        mock_auto_model.return_value = mock_model_instance

        detector = FunASRVADDetector(
            vad_model="fsmn-vad",
            device="cpu",
            load_model=False
        )

        assert not detector.is_ready()

        detector.load_model()

        assert detector.is_ready()
        assert detector._model == mock_model_instance
        mock_auto_model.assert_called_once()

    @patch('funasr.AutoModel')
    def test_is_speech(self, mock_auto_model):
        """测试语音检测"""
        from src.vad import FunASRVADDetector

        # Mock 模型和检测结果
        mock_model_instance = MagicMock()
        mock_model_instance.generate.return_value = [
            {"is_speech": True}
        ]
        mock_auto_model.return_value = mock_model_instance

        detector = FunASRVADDetector(
            vad_model="fsmn-vad",
            device="cpu",
            load_model=False
        )

        detector._model = mock_model_instance
        detector._ready = True

        # 创建测试音频
        audio_chunk = np.random.randint(-32768, 32767, size=1600, dtype=np.int16)

        # 检测语音
        result = detector.is_speech(audio_chunk)

        assert result is True
        mock_model_instance.generate.assert_called_once()

    @patch('funasr.AutoModel')
    def test_is_speech_not_speech(self, mock_auto_model):
        """测试静音检测"""
        from src.vad import FunASRVADDetector

        mock_model_instance = MagicMock()
        mock_model_instance.generate.return_value = [
            {"is_speech": False}
        ]
        mock_auto_model.return_value = mock_model_instance

        detector = FunASRVADDetector(
            vad_model="fsmn-vad",
            device="cpu",
            load_model=False
        )

        detector._model = mock_model_instance
        detector._ready = True

        # 创建静音音频
        silence_chunk = np.zeros(1600, dtype=np.int16)

        result = detector.is_speech(silence_chunk)

        assert result is False

    @patch('funasr.AutoModel')
    def test_process_stream(self, mock_auto_model):
        """测试流式处理"""
        from src.vad import FunASRVADDetector

        mock_model_instance = MagicMock()
        # Mock 不同块的检测结果
        mock_model_instance.generate.side_effect = [
            [{"is_speech": True}],
            [{"is_speech": True}],
            [{"is_speech": False}],
            [{"is_speech": False}],
        ]
        mock_auto_model.return_value = mock_model_instance

        detector = FunASRVADDetector(
            vad_model="fsmn-vad",
            device="cpu",
            load_model=False
        )

        detector._model = mock_model_instance
        detector._ready = True

        # 创建多个音频块
        chunks = [
            np.random.randint(-32768, 32767, size=1600, dtype=np.int16)
            for _ in range(4)
        ]

        # 处理流
        results = detector.process_stream(chunks)

        assert len(results) == 4
        assert results[0] is True
        assert results[1] is True
        assert results[2] is False
        assert results[3] is False

    @patch('funasr.AutoModel')
    def test_detect_speech_segments(self, mock_auto_model):
        """测试语音段检测"""
        from src.vad import FunASRVADDetector

        mock_model_instance = MagicMock()
        # 前3个块有语音，后3个块没有
        mock_model_instance.generate.side_effect = [
            [{"is_speech": True}],
            [{"is_speech": True}],
            [{"is_speech": True}],
            [{"is_speech": False}],
            [{"is_speech": False}],
            [{"is_speech": False}],
        ]
        mock_auto_model.return_value = mock_model_instance

        detector = FunASRVADDetector(
            vad_model="fsmn-vad",
            device="cpu",
            load_model=False
        )

        detector._model = mock_model_instance
        detector._ready = True

        # 创建测试音频（模拟6个块）
        audio_data = np.random.randint(-32768, 32767, size=1600*6, dtype=np.int16)

        # 检测语音段
        segments = detector.detect_speech_segments(audio_data)

        # 应该检测到一个语音段（0-3块）
        assert len(segments) == 1
        start_ms, end_ms = segments[0]
        assert start_ms == 0  # 第0块开始
        assert end_ms == 300  # 第3块结束（3 * 100ms）

    @patch('funasr.AutoModel')
    def test_get_speech_duration(self, mock_auto_model):
        """测试语音时长计算"""
        from src.vad import FunASRVADDetector

        mock_model_instance = MagicMock()
        mock_model_instance.generate.side_effect = [
            [{"is_speech": True}],
            [{"is_speech": True}],
            [{"is_speech": True}],
            [{"is_speech": False}],
            [{"is_speech": False}],
            [{"is_speech": False}],
        ]
        mock_auto_model.return_value = mock_model_instance

        detector = FunASRVADDetector(
            vad_model="fsmn-vad",
            device="cpu",
            load_model=False
        )

        detector._model = mock_model_instance
        detector._ready = True

        # 创建测试音频（6个块，其中前3个有语音）
        audio_data = np.random.randint(-32768, 32767, size=1600*6, dtype=np.int16)

        # 计算语音时长
        duration = detector.get_speech_duration(audio_data)

        # 3个块有语音，每个块100ms，总共300ms = 0.3秒
        assert duration == 0.3

    def test_is_ready(self):
        """测试就绪状态"""
        from src.vad import FunASRVADDetector

        detector = FunASRVADDetector(
            vad_model="fsmn-vad",
            device="cpu",
            load_model=False
        )

        assert not detector.is_ready()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
