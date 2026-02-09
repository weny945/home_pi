"""
配置加载器测试
Tests for Config Loader
"""
import pytest
import tempfile
from pathlib import Path
import yaml

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.config_loader import ConfigLoader, get_config, reset_config


@pytest.mark.unit
class TestConfigLoader:
    """配置加载器测试类"""

    @pytest.fixture
    def temp_config(self):
        """创建临时配置文件"""
        config_data = {
            'audio': {
                'input_device': 'test_device',
                'sample_rate': 16000,
                'channels': 1,
                'chunk_size': 512
            },
            'wakeword': {
                'engine': 'openwakeword',
                'model': 'test.ppn',
                'threshold': 0.5
            },
            'feedback': {
                'enabled': True,
                'mode': 'beep'
            },
            'logging': {
                'level': 'INFO',
                'file': './logs/test.log'
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.safe_dump(config_data, f)
            temp_path = f.name

        yield temp_path

        # 清理
        Path(temp_path).unlink(missing_ok=True)

    def test_load_config(self, temp_config):
        """测试加载配置"""
        loader = ConfigLoader(temp_config)
        assert loader._config is not None
        assert loader.get('audio.input_device') == 'test_device'

    def test_get_nested_value(self, temp_config):
        """测试获取嵌套配置值"""
        loader = ConfigLoader(temp_config)
        assert loader.get('audio.sample_rate') == 16000
        assert loader.get('audio.channels') == 1

    def test_get_with_default(self, temp_config):
        """测试获取不存在的配置值时返回默认值"""
        loader = ConfigLoader(temp_config)
        assert loader.get('nonexistent.key', 'default') == 'default'

    def test_set_value(self, temp_config):
        """测试设置配置值"""
        loader = ConfigLoader(temp_config)
        loader.set('audio.sample_rate', 48000)
        assert loader.get('audio.sample_rate') == 48000

    def test_get_section(self, temp_config):
        """测试获取配置段"""
        loader = ConfigLoader(temp_config)
        audio_config = loader.get_section('audio')
        assert audio_config['sample_rate'] == 16000
        assert audio_config['channels'] == 1

    def test_validate(self, temp_config):
        """测试配置验证"""
        loader = ConfigLoader(temp_config)
        assert loader.validate() is True

    def test_validate_missing_section(self, temp_config):
        """测试缺少必需配置段"""
        # 创建不完整的配置
        incomplete_data = {'audio': {'sample_rate': 16000}}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.safe_dump(incomplete_data, f)
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)
            with pytest.raises(ValueError):
                loader.validate()
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_get_audio_config(self, temp_config):
        """测试获取音频配置"""
        loader = ConfigLoader(temp_config)
        audio_config = loader.get_audio_config()
        assert audio_config['sample_rate'] == 16000

    def test_get_wakeword_config(self, temp_config):
        """测试获取唤醒词配置"""
        loader = ConfigLoader(temp_config)
        ww_config = loader.get_wakeword_config()
        assert ww_config['engine'] == 'openwakeword'

    def test_singleton_pattern(self, temp_config):
        """测试单例模式"""
        reset_config()
        loader1 = get_config(temp_config)
        loader2 = get_config()
        assert loader1 is loader2

    def test_save_config(self):
        """测试保存配置"""
        config_data = {'test': {'key': 'value'}}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)
            loader.set('test.new_key', 'new_value')
            loader.save()

            # 重新加载验证
            loader2 = ConfigLoader(temp_path)
            assert loader2.get('test.new_key') == 'new_value'
        finally:
            Path(temp_path).unlink(missing_ok=True)
