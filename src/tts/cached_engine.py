"""
TTS 缓存引擎
TTS Cache Engine with Persistent Storage
"""
import logging
import json
import hashlib
import os
import time
import numpy as np
from typing import Optional, List, Dict
from pathlib import Path

from .engine import TTSEngine

logger = logging.getLogger(__name__)


class CachedTTSEngine(TTSEngine):
    """
    TTS 缓存引擎

    功能：
    - 持久化缓存（文件存储）
    - MD5 哈希键
    - 元数据管理
    - 空间管理（自动清理过期缓存）
    - 预热功能
    """

    def __init__(
        self,
        base_engine: TTSEngine,
        cache_dir: str = "./data/tts_cache",
        max_cache_age_days: int = 30,
        enabled: bool = True
    ):
        """
        初始化缓存引擎

        Args:
            base_engine: 底层 TTS 引擎
            cache_dir: 缓存目录
            max_cache_age_days: 缓存最大保留天数（0=永久）
            enabled: 是否启用缓存
        """
        self._base_engine = base_engine
        self._cache_dir = Path(cache_dir)
        self._max_cache_age_days = max_cache_age_days
        self._enabled = enabled

        # 创建缓存目录
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        # 元数据文件
        self._metadata_file = self._cache_dir / "metadata.json"

        # 加载元数据
        self._metadata = self._load_metadata()

        logger.info("=" * 60)
        logger.info("TTS 缓存引擎初始化")
        logger.info("=" * 60)
        logger.info(f"  缓存目录: {self._cache_dir}")
        logger.info(f"  最大保留天数: {max_cache_age_days if max_cache_age_days > 0 else '永久'}")
        logger.info(f"  状态: {'启用' if enabled else '禁用'}")
        logger.info(f"  当前缓存数: {len(self._metadata)}")
        logger.info("=" * 60)

    def _load_metadata(self) -> Dict:
        """加载元数据"""
        if self._metadata_file.exists():
            try:
                with open(self._metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载缓存元数据失败: {e}")
                return {}
        return {}

    def _save_metadata(self):
        """保存元数据"""
        try:
            with open(self._metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self._metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存缓存元数据失败: {e}")

    def _get_cache_key(self, text: str) -> str:
        """
        生成缓存键（MD5）

        Args:
            text: 输入文本

        Returns:
            str: MD5 哈希值
        """
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        return self._cache_dir / f"{cache_key}.npy"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self._metadata:
            return False

        # 检查文件是否存在
        cache_path = self._get_cache_path(cache_key)
        if not cache_path.exists():
            return False

        # 检查是否过期
        if self._max_cache_age_days > 0:
            timestamp = self._metadata[cache_key].get('timestamp', 0)
            age_seconds = time.time() - timestamp
            age_days = age_seconds / 86400

            if age_days > self._max_cache_age_days:
                logger.debug(f"缓存过期: {cache_key} (age: {age_days:.1f} days)")
                return False

        return True

    def synthesize(
        self,
        text: str,
        speaker_id: Optional[int] = None
    ) -> np.ndarray:
        """
        合成语音（带缓存）

        Args:
            text: 输入文本
            speaker_id: 说话人ID（可选）

        Returns:
            np.ndarray: 音频数据
        """
        if not self._enabled:
            return self._base_engine.synthesize(text, speaker_id)

        # 生成缓存键
        cache_key = self._get_cache_key(text)

        # 检查缓存
        if self._is_cache_valid(cache_key):
            cache_path = self._get_cache_path(cache_key)

            try:
                # 从缓存加载
                audio_data = np.load(cache_path)

                # 更新访问计数和时间戳
                self._metadata[cache_key]['access_count'] += 1
                self._metadata[cache_key]['last_access'] = time.time()
                self._save_metadata()

                logger.debug(f"缓存命中: {text[:30]}... (key: {cache_key[:8]}...)")
                return audio_data

            except Exception as e:
                logger.warning(f"加载缓存失败: {e}")

        # 缓存未命中，调用底层引擎
        logger.debug(f"缓存未命中: {text[:30]}...")
        audio_data = self._base_engine.synthesize(text, speaker_id)

        # 保存到缓存
        try:
            cache_path = self._get_cache_path(cache_key)
            np.save(cache_path, audio_data)

            # 更新元数据
            self._metadata[cache_key] = {
                'text': text,
                'timestamp': time.time(),
                'last_access': time.time(),
                'access_count': 1,
                'sample_rate': self._base_engine.get_sample_rate()
            }
            self._save_metadata()

            logger.debug(f"已缓存: {text[:30]}... (key: {cache_key[:8]}...)")

        except Exception as e:
            logger.warning(f"保存缓存失败: {e}")

        return audio_data

    def get_sample_rate(self) -> int:
        """获取采样率"""
        return self._base_engine.get_sample_rate()

    def is_ready(self) -> bool:
        """是否已就绪"""
        return self._base_engine.is_ready()

    def get_model_info(self) -> dict:
        """获取模型信息"""
        info = self._base_engine.get_model_info()
        # 如果返回的是 dict 类型，创建副本
        if isinstance(info, dict):
            info = info.copy()
        else:
            info = {}
        info['cache_enabled'] = self._enabled
        info['cache_count'] = len(self._metadata)
        info['cache_dir'] = str(self._cache_dir)
        return info

    def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        speaker_id: Optional[int] = None
    ) -> None:
        """合成语音并保存到文件"""
        audio_data = self.synthesize(text, speaker_id)

        # 保存为 WAV 文件
        import wave
        with wave.open(output_path, 'wb') as wav_file:
            wav_file.setnchannels(1)  # 单声道
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self._base_engine.get_sample_rate())
            wav_file.writeframes(audio_data.tobytes())

        logger.info(f"音频已保存到: {output_path}")

    def warmup(self, phrases: List[str]):
        """
        预热缓存（生成常用短语）

        Args:
            phrases: 短语列表
        """
        logger.info("=" * 60)
        logger.info("开始预热 TTS 缓存")
        logger.info("=" * 60)
        logger.info(f"  短语数量: {len(phrases)}")

        success_count = 0
        for i, phrase in enumerate(phrases, 1):
            try:
                logger.info(f"  [{i}/{len(phrases)}] {phrase[:30]}...")
                self.synthesize(phrase)
                success_count += 1
            except Exception as e:
                logger.error(f"  预热失败: {e}")

        logger.info("=" * 60)
        logger.info(f"预热完成: {success_count}/{len(phrases)} 成功")
        logger.info("=" * 60)

    def clean_expired(self):
        """清理过期缓存"""
        if self._max_cache_age_days <= 0:
            logger.info("缓存未设置过期时间，跳过清理")
            return

        logger.info("开始清理过期缓存...")
        expired_keys = []

        for cache_key, meta in self._metadata.items():
            if not self._is_cache_valid(cache_key):
                expired_keys.append(cache_key)

        # 删除过期缓存
        for cache_key in expired_keys:
            try:
                cache_path = self._get_cache_path(cache_key)
                if cache_path.exists():
                    cache_path.unlink()
                del self._metadata[cache_key]
                logger.debug(f"已删除过期缓存: {cache_key[:8]}...")
            except Exception as e:
                logger.warning(f"删除缓存失败: {e}")

        if expired_keys:
            self._save_metadata()
            logger.info(f"清理完成: 删除 {len(expired_keys)} 个过期缓存")
        else:
            logger.info("没有过期缓存需要清理")

    def clear_all(self):
        """清空所有缓存"""
        logger.warning("清空所有缓存...")

        # 删除所有缓存文件
        for cache_key in list(self._metadata.keys()):
            try:
                cache_path = self._get_cache_path(cache_key)
                if cache_path.exists():
                    cache_path.unlink()
            except Exception as e:
                logger.warning(f"删除缓存文件失败: {e}")

        # 清空元数据
        self._metadata = {}
        self._save_metadata()

        logger.info("缓存已清空")

    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        total_size = 0
        for cache_key in self._metadata:
            cache_path = self._get_cache_path(cache_key)
            if cache_path.exists():
                total_size += cache_path.stat().st_size

        return {
            'total_count': len(self._metadata),
            'total_size_mb': total_size / (1024 * 1024),
            'cache_dir': str(self._cache_dir),
            'max_age_days': self._max_cache_age_days,
            'enabled': self._enabled
        }

    def extract_phrases_from_config(self, config: dict) -> List[str]:
        """
        从配置中提取常用短语

        Args:
            config: 配置字典

        Returns:
            List[str]: 短语列表
        """
        phrases = []

        # 1. 反馈消息
        feedback = config.get("feedback", {})
        tts_config = feedback.get("tts", {})
        messages = tts_config.get("messages", [])
        phrases.extend(messages)

        # 2. 重试提示语
        audio_quality = config.get("audio_quality", {})
        retry_prompts = audio_quality.get("retry_prompts", {})
        for prompt_type, prompts in retry_prompts.items():
            if isinstance(prompts, dict):
                for retry_level, level_prompts in prompts.items():
                    if isinstance(level_prompts, list):
                        phrases.extend(level_prompts)

        # 3. 自动收尾
        conversation = config.get("conversation", {})
        auto_farewell = conversation.get("auto_farewell", {})
        farewell_messages = auto_farewell.get("farewell_messages", [])
        phrases.extend(farewell_messages)

        # 去重
        phrases = list(set(phrases))

        logger.info(f"从配置中提取了 {len(phrases)} 个常用短语")
        return phrases
