"""
缓存 TTS 引擎单元测试
Unit Tests for Cached TTS Engine
"""
import pytest
import numpy as np
import json
import time
from pathlib import Path
from unittest.mock import Mock
from src.tts.cached_engine import CachedTTSEngine


@pytest.fixture
def mock_base_engine():
    """Mock 底层引擎"""
    engine = Mock()
    engine.is_ready.return_value = True
    engine.synthesize.return_value = np.array([1, 2, 3, 4, 5], dtype=np.int16)
    engine.get_sample_rate.return_value = 22050
    return engine


@pytest.fixture
def cache_dir(tmp_path):
    """缓存目录"""
    cache_path = tmp_path / "tts_cache"
    cache_path.mkdir(parents=True, exist_ok=True)
    return str(cache_path)


@pytest.fixture
def cached_engine(mock_base_engine, cache_dir):
    """创建缓存引擎"""
    return CachedTTSEngine(
        base_engine=mock_base_engine,
        cache_dir=cache_dir,
        max_cache_age_days=30,
        enabled=True
    )


class TestCachedTTSEngine:
    """缓存 TTS 引擎测试"""

    def test_init(self, mock_base_engine, cache_dir):
        """测试初始化"""
        engine = CachedTTSEngine(
            base_engine=mock_base_engine,
            cache_dir=cache_dir,
            max_cache_age_days=7,
            enabled=True
        )

        assert engine._base_engine == mock_base_engine
        assert str(engine._cache_dir) == cache_dir
        assert engine._max_cache_age_days == 7
        assert engine._enabled is True

    def test_synthesize_cache_miss(self, cached_engine, mock_base_engine):
        """测试缓存未命中"""
        audio = cached_engine.synthesize("测试文本")

        assert isinstance(audio, np.ndarray)
        mock_base_engine.synthesize.assert_called_once()

        # 验证缓存文件已创建
        cache_key = cached_engine._get_cache_key("测试文本")
        cache_path = cached_engine._get_cache_path(cache_key)
        assert cache_path.exists()

    def test_synthesize_cache_hit(self, cached_engine, mock_base_engine):
        """测试缓存命中"""
        # 第一次调用 - 缓存未命中
        audio1 = cached_engine.synthesize("测试文本")
        assert mock_base_engine.synthesize.call_count == 1

        # 第二次调用 - 缓存命中
        audio2 = cached_engine.synthesize("测试文本")
        assert mock_base_engine.synthesize.call_count == 1  # 没有增加

        # 验证返回相同的音频
        assert np.array_equal(audio1, audio2)

    def test_synthesize_disabled_cache(self, mock_base_engine, cache_dir):
        """测试禁用缓存"""
        engine = CachedTTSEngine(
            base_engine=mock_base_engine,
            cache_dir=cache_dir,
            enabled=False
        )

        # 第一次调用
        engine.synthesize("测试文本")
        assert mock_base_engine.synthesize.call_count == 1

        # 第二次调用 - 仍然调用底层引擎（缓存禁用）
        engine.synthesize("测试文本")
        assert mock_base_engine.synthesize.call_count == 2

    def test_get_sample_rate(self, cached_engine):
        """测试获取采样率"""
        assert cached_engine.get_sample_rate() == 22050

    def test_is_ready(self, cached_engine):
        """测试是否就绪"""
        assert cached_engine.is_ready() is True

    def test_get_model_info(self, cached_engine):
        """测试获取模型信息"""
        info = cached_engine.get_model_info()

        assert info["cache_enabled"] is True
        assert "cache_count" in info
        assert "cache_dir" in info

    def test_warmup(self, cached_engine, mock_base_engine):
        """测试预热"""
        phrases = ["短语1", "短语2", "短语3"]

        cached_engine.warmup(phrases)

        # 验证所有短语都已合成
        assert mock_base_engine.synthesize.call_count == 3

        # 验证缓存文件已创建
        for phrase in phrases:
            cache_key = cached_engine._get_cache_key(phrase)
            cache_path = cached_engine._get_cache_path(cache_key)
            assert cache_path.exists()

    def test_clean_expired(self, cached_engine, cache_dir):
        """测试清理过期缓存"""
        # 创建一个过期的缓存条目
        cache_key = cached_engine._get_cache_key("过期文本")
        cache_path = cached_engine._get_cache_path(cache_key)
        np.save(cache_path, np.array([1, 2, 3], dtype=np.int16))

        # 修改元数据为过期时间戳
        old_timestamp = time.time() - (40 * 86400)  # 40 天前
        cached_engine._metadata[cache_key] = {
            "text": "过期文本",
            "timestamp": old_timestamp,
            "last_access": old_timestamp,
            "access_count": 1,
            "sample_rate": 22050
        }
        cached_engine._save_metadata()

        # 设置最大保留天数为 30 天
        cached_engine._max_cache_age_days = 30

        # 清理过期缓存
        cached_engine.clean_expired()

        # 验证过期缓存已删除
        assert not cache_path.exists()
        assert cache_key not in cached_engine._metadata

    def test_clear_all(self, cached_engine, cache_dir):
        """测试清空所有缓存"""
        # 创建一些缓存
        cached_engine.synthesize("文本1")
        cached_engine.synthesize("文本2")

        assert len(cached_engine._metadata) > 0

        # 清空
        cached_engine.clear_all()

        assert len(cached_engine._metadata) == 0

    def test_get_cache_stats(self, cached_engine):
        """测试获取缓存统计"""
        # 创建一些缓存
        cached_engine.synthesize("文本1")
        cached_engine.synthesize("文本2")

        stats = cached_engine.get_cache_stats()

        assert stats["total_count"] == 2
        assert stats["total_size_mb"] > 0
        assert "cache_dir" in stats

    def test_extract_phrases_from_config(self, cached_engine):
        """测试从配置提取短语"""
        config = {
            "feedback": {
                "tts": {
                    "messages": ["我在", "请吩咐", "我在听"]
                }
            },
            "audio_quality": {
                "retry_prompts": {
                    "silence": {
                        "retry_1": ["再说一遍"]
                    }
                }
            },
            "conversation": {
                "auto_farewell": {
                    "farewell_messages": ["好的，那先这样吧", "嗯，好的"]
                }
            }
        }

        phrases = cached_engine.extract_phrases_from_config(config)

        assert len(phrases) > 0
        assert "我在" in phrases
        assert "请吩咐" in phrases

    def test_get_cache_key(self, cached_engine):
        """测试缓存键生成"""
        key1 = cached_engine._get_cache_key("相同文本")
        key2 = cached_engine._get_cache_key("相同文本")
        key3 = cached_engine._get_cache_key("不同文本")

        # 相同文本应该产生相同的键
        assert key1 == key2

        # 不同文本应该产生不同的键
        assert key1 != key3

    def test_is_cache_valid(self, cached_engine):
        """测试缓存有效性检查"""
        # 创建一个有效的缓存
        cached_engine.synthesize("有效文本")
        cache_key = cached_engine._get_cache_key("有效文本")

        assert cached_engine._is_cache_valid(cache_key) is True

    def test_synthesize_to_file(self, cached_engine, tmp_path):
        """测试合成到文件"""
        output_path = tmp_path / "output.wav"

        cached_engine.synthesize_to_file("测试文本", str(output_path))

        assert output_path.exists()

    def test_cache_persistence(self, mock_base_engine, cache_dir):
        """测试缓存持久化"""
        # 创建引擎并生成缓存
        engine1 = CachedTTSEngine(
            base_engine=mock_base_engine,
            cache_dir=cache_dir,
            max_cache_age_days=30,
            enabled=True
        )

        engine1.synthesize("持久化测试")

        # 创建新引擎实例（应该加载之前的缓存）
        mock_base_engine.reset_mock()
        engine2 = CachedTTSEngine(
            base_engine=mock_base_engine,
            cache_dir=cache_dir,
            max_cache_age_days=30,
            enabled=True
        )

        # 应该从缓存加载，不调用底层引擎
        engine2.synthesize("持久化测试")
        assert mock_base_engine.synthesize.call_count == 0
