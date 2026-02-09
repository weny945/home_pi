"""
全局测试配置
Global Test Configuration
"""
import pytest
import numpy as np


def pytest_configure(config):
    """配置 pytest 标记"""
    config.addinivalue_line("markers", "unit: 单元测试")


@pytest.fixture
def sample_audio_frame():
    """
    生成示例音频帧

    Returns:
        np.ndarray: 音频数据 (16kHz, 16bit, 512 frames)
    """
    return np.random.randint(-1000, 1000, size=512, dtype=np.int16)


@pytest.fixture
def sample_audio_long():
    """
    生成较长的示例音频（用于唤醒词测试）

    Returns:
        np.ndarray: 音频数据 (16kHz, 16bit, 3秒)
    """
    return np.random.randint(-5000, 5000, size=16000 * 3, dtype=np.int16)
