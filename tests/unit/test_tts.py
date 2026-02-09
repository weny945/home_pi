"""
Piper TTS 引擎测试
Tests for Piper TTS Engine
"""
import pytest
import numpy as np
from pathlib import Path
import tempfile
import sys

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.tts import PiperTTSEngine, TTSEngine


@pytest.mark.unit
class TestPiperTTSEngine:
    """Piper TTS 引擎测试类"""

    @pytest.fixture
    def model_path(self):
        """获取测试模型路径"""
        return "./models/piper/zh_CN-huayan-medium.onnx"

    @pytest.fixture
    def engine(self, model_path):
        """创建 TTS 引擎实例"""
        engine = PiperTTSEngine(
            model_path=model_path,
            load_model=True
        )
        yield engine
        # 清理
        del engine

    def test_engine_initialization(self, model_path):
        """测试引擎初始化"""
        engine = PiperTTSEngine(
            model_path=model_path,
            load_model=False
        )

        assert engine is not None
        assert not engine.is_ready()
        del engine

    def test_engine_load_model(self, engine):
        """测试模型加载"""
        assert engine.is_ready()
        assert engine.get_sample_rate() == 22050

    def test_synthesize(self, engine):
        """测试语音合成"""
        text = "你好"
        audio_data = engine.synthesize(text)

        assert isinstance(audio_data, np.ndarray)
        assert audio_data.dtype == np.int16
        assert len(audio_data) > 0

    def test_synthesize_different_texts(self, engine):
        """测试合成不同文本"""
        texts = ["我在", "请吩咐", "我在听"]

        for text in texts:
            audio_data = engine.synthesize(text)
            assert isinstance(audio_data, np.ndarray)
            assert len(audio_data) > 0

    def test_synthesize_to_file(self, engine):
        """测试合成到文件"""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            output_path = f.name

        try:
            text = "测试"
            engine.synthesize_to_file(text, output_path)

            # 验证文件存在
            assert Path(output_path).exists()

            # 验证文件大小
            assert Path(output_path).stat().st_size > 0
        finally:
            # 清理
            Path(output_path).unlink(missing_ok=True)

    def test_get_model_info(self, engine):
        """测试获取模型信息"""
        info = engine.get_model_info()

        assert isinstance(info, dict)
        assert 'model_path' in info
        assert 'sample_rate' in info
        assert 'is_loaded' in info
        assert info['is_loaded'] is True

    def test_set_synthesis_config(self, engine):
        """测试设置合成配置"""
        # 设置不同的语速
        engine.set_synthesis_config(length_scale=0.8)

        # 验证配置已更新
        info = engine.get_model_info()
        assert info['synthesis_config']['length_scale'] == 0.8

    def test_synthesize_with_speed(self, engine):
        """测试不同语速的合成"""
        text = "测试"

        # 正常语速
        audio_normal = engine.synthesize(text)

        # 更快语速
        engine.set_synthesis_config(length_scale=0.8)
        audio_fast = engine.synthesize(text)

        # 恢复正常语速
        engine.set_synthesis_config(length_scale=1.0)

        # 更快的语音应该更短
        assert len(audio_fast) < len(audio_normal)

    def test_error_handling_model_not_found(self):
        """测试模型文件不存在的错误处理"""
        with pytest.raises(FileNotFoundError):
            PiperTTSEngine(
                model_path="./nonexistent/model.onnx",
                load_model=False
            )

    def test_error_handling_synthesize_without_load(self):
        """测试未加载模型时合成的错误处理"""
        engine = PiperTTSEngine(
            model_path="./models/piper/zh_CN-huayan-medium.onnx",
            load_model=False
        )

        with pytest.raises(RuntimeError):
            engine.synthesize("测试")

        del engine

    def test_abstract_interface(self):
        """测试抽象接口"""
        # 确保无法直接实例化抽象类
        with pytest.raises(TypeError):
            TTSEngine()
