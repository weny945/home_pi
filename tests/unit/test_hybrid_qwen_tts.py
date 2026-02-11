"""
混合千问 TTS 引擎单元测试
Unit Tests for Hybrid Qwen TTS Engine
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch
from src.tts.hybrid_qwen_engine import HybridQwenTTSEngine
from src.tts.piper_engine import PiperTTSEngine


@pytest.fixture
def mock_piper_engine():
    """Mock Piper 引擎"""
    engine = Mock(spec=PiperTTSEngine)
    engine.is_ready.return_value = True
    engine.synthesize.return_value = np.array([1, 2, 3], dtype=np.int16)
    engine.get_sample_rate.return_value = 22050
    return engine


@pytest.fixture
def mock_qwen_engine():
    """Mock 千问引擎"""
    engine = Mock()
    engine.is_ready.return_value = True
    engine.synthesize.return_value = np.array([4, 5, 6], dtype=np.int16)
    engine.get_sample_rate.return_value = 24000
    return engine


@pytest.fixture
def mock_realtime_engine():
    """Mock 流式引擎"""
    engine = Mock()
    engine.is_ready.return_value = True
    engine.synthesize.return_value = np.array([7, 8, 9], dtype=np.int16)
    return engine


@pytest.fixture
def hybrid_engine(mock_piper_engine, mock_qwen_engine, mock_realtime_engine):
    """创建混合引擎"""
    config = {
        "streaming_threshold": 100,
        "scenario_streaming": {
            "llm_reply_long": "streaming",
            "wake_response": "non_streaming"
        },
        "fallback_to_piper": True,
        "max_retries": 2,
        "log_decision": False
    }

    return HybridQwenTTSEngine(
        local_engine=mock_piper_engine,
        qwen_engine=mock_qwen_engine,
        realtime_engine=mock_realtime_engine,
        config=config
    )


class TestHybridQwenTTSEngine:
    """混合千问 TTS 引擎测试"""

    def test_init(self, mock_piper_engine, mock_qwen_engine, mock_realtime_engine):
        """测试初始化"""
        config = {
            "streaming_threshold": 100,
            "fallback_to_piper": True
        }

        engine = HybridQwenTTSEngine(
            local_engine=mock_piper_engine,
            qwen_engine=mock_qwen_engine,
            realtime_engine=mock_realtime_engine,
            config=config
        )

        assert engine._piper_engine == mock_piper_engine
        assert engine._qwen_engine == mock_qwen_engine
        assert engine._realtime_engine == mock_realtime_engine
        assert engine._streaming_threshold == 100
        assert engine._fallback_to_piper is True

    def test_route_short_text(self, hybrid_engine):
        """测试短文本路由（< 100 字符）"""
        decision = hybrid_engine._route("短文本", "default")

        assert decision["engine"] == "qwen"

    def test_route_long_text(self, hybrid_engine):
        """测试长文本路由（≥ 100 字符）"""
        long_text = "这是一个很长的文本" * 20  # > 100 字符
        decision = hybrid_engine._route(long_text, "default")

        assert decision["engine"] == "realtime"

    def test_route_scenario_streaming(self, hybrid_engine):
        """测试场景级别路由 - 流式"""
        decision = hybrid_engine._route("短文本", "llm_reply_long")

        assert decision["engine"] == "realtime"
        assert decision["reason"] == "scenario"

    def test_route_scenario_non_streaming(self, hybrid_engine):
        """测试场景级别路由 - 非流式"""
        long_text = "这是一个很长的文本" * 20
        decision = hybrid_engine._route(long_text, "wake_response")

        assert decision["engine"] == "qwen"
        assert decision["reason"] == "scenario"

    def test_synthesize_with_qwen(self, hybrid_engine):
        """测试使用千问合成"""
        audio = hybrid_engine.synthesize("短文本", scenario="default")

        assert isinstance(audio, np.ndarray)
        mock_qwen = hybrid_engine._qwen_engine
        mock_qwen.synthesize.assert_called_once()

    def test_synthesize_with_realtime(self, hybrid_engine):
        """测试使用流式合成"""
        long_text = "这是一个很长的文本" * 20
        audio = hybrid_engine.synthesize(long_text, scenario="default")

        assert isinstance(audio, np.ndarray)
        mock_realtime = hybrid_engine._realtime_engine
        mock_realtime.synthesize.assert_called_once()

    def test_synthesize_fallback_to_piper(self, hybrid_engine):
        """测试降级到 Piper"""
        # 模拟千问失败
        hybrid_engine._qwen_engine.synthesize.side_effect = Exception("Qwen failed")
        hybrid_engine._realtime_engine.synthesize.side_effect = Exception("Realtime failed")

        # 模拟网络不可用
        hybrid_engine._network_available = False
        hybrid_engine._qwen_available = False
        hybrid_engine._realtime_available = False

        audio = hybrid_engine.synthesize("测试文本", scenario="default")

        assert isinstance(audio, np.ndarray)
        mock_piper = hybrid_engine._piper_engine
        mock_piper.synthesize.assert_called_once()

    def test_get_sample_rate(self, hybrid_engine):
        """测试获取采样率"""
        # 优先返回 Piper 采样率
        assert hybrid_engine.get_sample_rate() == 22050

    def test_get_sample_rate_without_piper(self, mock_qwen_engine, mock_realtime_engine):
        """测试无 Piper 时返回千问采样率"""
        mock_piper_engine = Mock()
        mock_piper_engine.is_ready.return_value = False
        mock_piper_engine.get_sample_rate.return_value = 22050

        engine = HybridQwenTTSEngine(
            local_engine=mock_piper_engine,
            qwen_engine=mock_qwen_engine,
            realtime_engine=mock_realtime_engine,
            config={}
        )

        assert engine.get_sample_rate() == 24000

    def test_is_ready(self, hybrid_engine):
        """测试是否就绪"""
        assert hybrid_engine.is_ready() is True

    def test_is_ready_no_engines(self, mock_piper_engine, mock_qwen_engine):
        """测试所有引擎都不可用"""
        mock_piper_engine.is_ready.return_value = False
        mock_qwen_engine.is_ready.return_value = False

        engine = HybridQwenTTSEngine(
            local_engine=mock_piper_engine,
            qwen_engine=mock_qwen_engine,
            realtime_engine=None,
            config={}
        )

        assert engine.is_ready() is False

    def test_get_model_info(self, hybrid_engine):
        """测试获取模型信息"""
        info = hybrid_engine.get_model_info()

        assert info["engine_type"] == "HybridQwen"
        assert info["piper_available"] is True
        assert info["qwen_available"] is True
        assert info["realtime_available"] is True
        assert info["streaming_threshold"] == 100

    def test_get_engine_status(self, hybrid_engine):
        """测试获取引擎状态"""
        status = hybrid_engine.get_engine_status()

        assert "piper" in status
        assert "qwen" in status
        assert "realtime" in status
        assert "network" in status

    def test_synthesize_to_file(self, hybrid_engine, tmp_path):
        """测试合成到文件"""
        output_path = tmp_path / "output.wav"

        hybrid_engine.synthesize_to_file("测试文本", str(output_path))

        assert output_path.exists()
