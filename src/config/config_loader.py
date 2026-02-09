"""
配置加载器
Configuration Loader for Voice Assistant System

P2-1 优化: 添加配置验证、默认值管理和性能优化
"""
import os
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Callable
import yaml

logger = logging.getLogger(__name__)


# 配置验证规则和默认值
CONFIG_SCHEMA = {
    'audio': {
        'sample_rate': {'default': 16000, 'type': int, 'range': (8000, 48000)},
        'channels': {'default': 1, 'type': int, 'range': (1, 2)},
        'chunk_size': {'default': 512, 'type': int, 'range': (256, 4096)},
        'format': {'default': 'int16', 'type': str, 'options': ['int16', 'float32']},
    },
    'wakeword': {
        'threshold': {'default': 0.5, 'type': float, 'range': (0.0, 1.0)},
        'model_dir': {'default': './models/openwakeword', 'type': str},
    },
    'listening': {
        'max_duration': {'default': 10, 'type': int, 'range': (1, 60)},
        'silence_threshold': {'default': 1.5, 'type': float, 'range': (0.5, 5.0)},
        'min_speech_duration': {'default': 0.5, 'type': float, 'range': (0.1, 2.0)},
    },
    'audio_quality': {
        'min_duration': {'default': 0.5, 'type': float, 'range': (0.1, 2.0)},
        'min_energy': {'default': 0.01, 'type': float, 'range': (0.001, 0.1)},
        'max_retries': {'default': 3, 'type': int, 'range': (0, 5)},
    },
    'llm': {
        'temperature': {'default': 0.7, 'type': float, 'range': (0.0, 1.0)},
        'max_tokens': {'default': 3000, 'type': int, 'range': (100, 8000)},
        'max_history': {'default': 10, 'type': int, 'range': (0, 50)},
    },
}


class ConfigLoader:
    """YAML 配置文件加载器（P2-1 优化版）"""

    def __init__(self, config_path: str = None):
        """
        初始化配置加载器

        Args:
            config_path: 配置文件路径，默认为 ./config.yaml
        """
        if config_path is None:
            # 查找配置文件
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config.yaml"

        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        # P2-1 优化: 添加配置缓存，提高访问性能
        self._cache: Dict[str, Any] = {}
        self._cache_enabled = True

        if self.config_path.exists():
            self.load()
            self._apply_defaults()
            self._validate_config()
        else:
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

    def load(self) -> None:
        """加载配置文件"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f) or {}
        # P2-1 优化: 加载后清空缓存
        self._cache.clear()

    def save(self) -> None:
        """保存配置到文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(self._config, f, allow_unicode=True, default_flow_style=False)
        # P2-1 优化: 保存后清空缓存
        self._cache.clear()

    def _apply_defaults(self) -> None:
        """P2-1 优化: 应用默认值到缺失的配置项"""
        for section, keys in CONFIG_SCHEMA.items():
            if section not in self._config:
                self._config[section] = {}

            for key, schema in keys.items():
                if key not in self._config[section]:
                    default_value = schema['default']
                    self._config[section][key] = default_value
                    logger.debug(f"应用默认值: {section}.{key} = {default_value}")

    def _validate_config(self) -> None:
        """P2-1 优化: 验证配置值的有效性"""
        errors = []

        for section, keys in CONFIG_SCHEMA.items():
            if section not in self._config:
                continue

            for key, schema in keys.items():
                if key not in self._config[section]:
                    continue

                value = self._config[section][key]
                expected_type = schema['type']

                # 类型检查
                if not isinstance(value, expected_type):
                    try:
                        # 尝试类型转换
                        value = expected_type(value)
                        self._config[section][key] = value
                        logger.warning(f"配置值类型转换: {section}.{key} -> {expected_type.__name__}")
                    except (ValueError, TypeError):
                        errors.append(f"{section}.{key}: 期望类型 {expected_type.__name__}, 实际为 {type(value).__name__}")
                        continue

                # 范围检查
                if 'range' in schema:
                    min_val, max_val = schema['range']
                    if not (min_val <= value <= max_val):
                        errors.append(f"{section}.{key}: 值 {value} 超出范围 [{min_val}, {max_val}]")

                # 选项检查
                if 'options' in schema:
                    if value not in schema['options']:
                        errors.append(f"{section}.{key}: 值 '{value}' 不在允许的选项中 {schema['options']}")

        if errors:
            error_msg = "配置验证失败:\n" + "\n".join(errors)
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info("✅ 配置验证通过")

    def reload(self) -> None:
        """P2-1 优化: 重新加载配置文件"""
        logger.info("重新加载配置文件...")
        self.load()
        self._apply_defaults()
        self._validate_config()
        logger.info("✅ 配置重新加载完成")

    def clear_cache(self) -> None:
        """P2-1 优化: 清空配置缓存"""
        self._cache.clear()
        logger.debug("配置缓存已清空")

    def get(self, key: str, default: Any = None, use_cache: bool = True) -> Any:
        """保存配置到文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(self._config, f, allow_unicode=True, default_flow_style=False)

    def get(self, key: str, default: Any = None, use_cache: bool = True) -> Any:
        """
        获取配置项（支持点分隔的嵌套键）

        P2-1 优化: 支持缓存以提高性能

        Args:
            key: 配置键，如 "audio.sample_rate"
            default: 默认值
            use_cache: 是否使用缓存（默认 True）

        Returns:
            配置值
        """
        # P2-1 优化: 检查缓存
        if use_cache and self._cache_enabled:
            if key in self._cache:
                return self._cache[key]

        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                value = default
                break

        # P2-1 优化: 更新缓存
        if use_cache and self._cache_enabled:
            self._cache[key] = value

        return value

    def set(self, key: str, value: Any, validate: bool = True) -> None:
        """
        设置配置项（支持点分隔的嵌套键）

        P2-1 优化: 支持验证和缓存清理

        Args:
            key: 配置键
            value: 配置值
            validate: 是否验证值（默认 True）
        """
        keys = key.split('.')
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

        # P2-1 优化: 清理相关缓存
        if key in self._cache:
            del self._cache[key]

        # P2-1 优化: 可选验证
        if validate:
            try:
                self._validate_config()
            except ValueError as e:
                logger.warning(f"配置值验证失败: {e}")

    def get_with_schema(self, key: str, default: Any = None) -> Any:
        """
        获取配置项（使用 schema 定义的默认值）

        P2-1 优化: 优先使用 schema 定义的默认值

        Args:
            key: 配置键
            default: 回退默认值（仅在 schema 中无定义时使用）

        Returns:
            配置值
        """
        # 尝试从 schema 获取默认值
        keys = key.split('.')
        if len(keys) == 2:
            section, config_key = keys
            if section in CONFIG_SCHEMA and config_key in CONFIG_SCHEMA[section]:
                schema_default = CONFIG_SCHEMA[section][config_key]['default']
                return self.get(key, schema_default)

        return self.get(key, default)

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        获取整个配置段

        Args:
            section: 配置段名称

        Returns:
            配置字典
        """
        return self._config.get(section, {})

    @property
    def config(self) -> Dict[str, Any]:
        """获取完整配置"""
        return self._config

    def validate(self) -> bool:
        """
        验证配置完整性（基础验证）

        Returns:
            bool: 是否有效
        """
        required_sections = ['audio', 'wakeword', 'feedback', 'logging']

        for section in required_sections:
            if section not in self._config:
                raise ValueError(f"缺少必需的配置段: {section}")

        return True

    def get_schema(self) -> Dict[str, Any]:
        """
        P2-1 优化: 获取配置模式定义

        Returns:
            配置模式字典
        """
        return CONFIG_SCHEMA.copy()

    def get_audio_config(self) -> Dict[str, Any]:
        """获取音频配置"""
        return self.get_section('audio')

    def get_wakeword_config(self) -> Dict[str, Any]:
        """获取唤醒词配置"""
        return self.get_section('wakeword')

    def get_feedback_config(self) -> Dict[str, Any]:
        """获取反馈配置"""
        return self.get_section('feedback')

    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self.get_section('logging')


# 全局配置实例
_config_instance: ConfigLoader = None


def get_config(config_path: str = None) -> ConfigLoader:
    """
    获取全局配置实例（单例模式）

    Args:
        config_path: 配置文件路径

    Returns:
        ConfigLoader: 配置实例
    """
    global _config_instance

    if _config_instance is None:
        _config_instance = ConfigLoader(config_path)

    return _config_instance


def reset_config() -> None:
    """重置全局配置（主要用于测试）"""
    global _config_instance
    _config_instance = None
