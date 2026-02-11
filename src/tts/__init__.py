"""
文本转语音模块
Text-to-Speech Module

支持多种 TTS 引擎：
- Piper: 本地离线 TTS
- Remote: 远程主机 GPT-SoVITS
- Hybrid: 本地 Piper + 远程主机（原有）
- Qwen: 千问 TTS（非流式）[v2.2]
- Qwen Realtime: 千问 TTS（流式）[v2.2]
- Hybrid Qwen: 千问 TTS + Piper + 智能路由 [v2.2]
- Doubao: 豆包 TTS（火山引擎）[v2.3]
- Cached: 带缓存的包装引擎 [v2.2]
"""
import logging
import os
from typing import Optional

from .engine import TTSEngine
from .piper_engine import PiperTTSEngine
from .remote_engine import RemoteTTSEngine
from .hybrid_engine import HybridTTSEngine
from .qwen_engine import QwenTTSEngine
from .qwen_realtime_engine import QwenRealtimeEngine
from .hybrid_qwen_engine import HybridQwenTTSEngine
from .doubao_engine import DoubaoTTSEngine
from .cached_engine import CachedTTSEngine

logger = logging.getLogger(__name__)

__all__ = [
    # 基类
    "TTSEngine",

    # 引擎类
    "PiperTTSEngine",
    "RemoteTTSEngine",
    "HybridTTSEngine",
    "QwenTTSEngine",
    "QwenRealtimeEngine",
    "HybridQwenTTSEngine",
    "DoubaoTTSEngine",
    "CachedTTSEngine",

    # 工厂函数
    "create_tts_engine",
    "create_piper_engine",
    "create_remote_engine",
    "create_hybrid_engine",
    "create_qwen_engine",
    "create_qwen_realtime_engine",
    "create_doubao_engine",
    "create_hybrid_qwen_engine",
    "create_cached_engine",
]


def _expand_env_var(value: str) -> str:
    """展开环境变量"""
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        env_var = value[2:-1]
        return os.environ.get(env_var, value)
    return value


def create_piper_engine(config: dict) -> PiperTTSEngine:
    """
    创建 Piper TTS 引擎

    Args:
        config: 配置字典

    Returns:
        PiperTTSEngine: Piper 引擎实例
    """
    local_config = config.get("local", {})

    # 提取配置参数
    model_path = local_config.get("model_path", "./models/piper/zh_CN-huayan-medium.onnx")
    length_scale = local_config.get("length_scale", 1.0)
    noise_scale = local_config.get("noise_scale", 0.75)
    noise_w_scale = local_config.get("noise_w_scale", 0.8)
    sentence_silence = local_config.get("sentence_silence", 0.2)

    return PiperTTSEngine(
        model_path=model_path,
        length_scale=length_scale,
        noise_scale=noise_scale,
        noise_w_scale=noise_w_scale,
        sentence_silence=sentence_silence
    )


def create_remote_engine(config: dict) -> RemoteTTSEngine:
    """
    创建远程 TTS 引擎（GPT-SoVITS 主机）

    Args:
        config: 配置字典

    Returns:
        RemoteTTSEngine: 远程引擎实例
    """
    remote_config = config.get("remote", {})

    server_ip = remote_config.get("server_ip", "192.168.2.141")
    port = remote_config.get("port", 9880)
    timeout = remote_config.get("timeout", 60)
    text_lang = remote_config.get("text_lang", "zh")
    speed = remote_config.get("speed", 1.0)

    return RemoteTTSEngine(
        server_ip=server_ip,
        port=port,
        timeout=timeout,
        text_lang=text_lang,
        speed=speed
    )


def create_qwen_engine(config: dict) -> QwenTTSEngine:
    """
    创建千问 TTS 引擎（非流式）

    Args:
        config: 配置字典

    Returns:
        QwenTTSEngine: 千问引擎实例
    """
    qwen_config = config.get("qwen", {})

    # 展开环境变量
    if "dashscope" in qwen_config:
        dashscope_config = qwen_config["dashscope"].copy()
        dashscope_config["api_key"] = _expand_env_var(dashscope_config.get("api_key", ""))
        qwen_config["dashscope"] = dashscope_config

    if "openai" in qwen_config:
        openai_config = qwen_config["openai"].copy()
        openai_config["api_key"] = _expand_env_var(openai_config.get("api_key", ""))
        qwen_config["openai"] = openai_config

    return QwenTTSEngine(qwen_config)


def create_qwen_realtime_engine(config: dict) -> Optional[QwenRealtimeEngine]:
    """
    创建千问流式 TTS 引擎

    Args:
        config: 配置字典

    Returns:
        QwenRealtimeEngine: 流式引擎实例，如果不可用则返回 None
    """
    qwen_realtime_config = config.get("qwen_realtime", {})

    if not qwen_realtime_config.get("enabled", True):
        return None

    # 展开环境变量
    if "dashscope" in qwen_realtime_config:
        dashscope_config = qwen_realtime_config["dashscope"].copy()
        dashscope_config["api_key"] = _expand_env_var(dashscope_config.get("api_key", ""))
        qwen_realtime_config["dashscope"] = dashscope_config

    try:
        return QwenRealtimeEngine(qwen_realtime_config)
    except ImportError:
        logger.warning("websockets 库未安装，千问流式 TTS 不可用")
        return None
    except Exception as e:
        logger.error(f"创建千问流式引擎失败: {e}")
        return None


def create_doubao_engine(config: dict) -> DoubaoTTSEngine:
    """
    创建豆包 TTS 引擎（火山引擎）

    Args:
        config: 配置字典

    Returns:
        DoubaoTTSEngine: 豆包引擎实例
    """
    doubao_config = config.get("doubao", {})

    # 展开环境变量
    if "api_key" in doubao_config:
        doubao_config = doubao_config.copy()
        doubao_config["api_key"] = _expand_env_var(doubao_config["api_key"])

    config_with_doubao = config.copy()
    config_with_doubao["doubao"] = doubao_config

    return DoubaoTTSEngine(config_with_doubao)


def create_hybrid_engine(config: dict) -> HybridTTSEngine:
    """
    创建混合 TTS 引擎（本地 Piper + 远程主机）

    Args:
        config: 配置字典

    Returns:
        HybridTTSEngine: 混合引擎实例
    """
    local_engine = create_piper_engine(config)
    remote_engine = create_remote_engine(config)

    hybrid_config = config.get("hybrid", {})
    health_check_interval = hybrid_config.get("health_check_interval", 3600)
    auto_failback = hybrid_config.get("auto_failback", True)

    return HybridTTSEngine(
        remote_engine=remote_engine,
        local_engine=local_engine,
        health_check_interval=health_check_interval,
        auto_failback=auto_failback
    )


def create_hybrid_qwen_engine(config: dict) -> Optional[HybridQwenTTSEngine]:
    """
    创建混合千问 TTS 引擎

    Args:
        config: 配置字典

    Returns:
        HybridQwenTTSEngine: 混合千问引擎实例
    """
    try:
        # 创建底层引擎
        local_engine = create_piper_engine(config)
        qwen_engine = create_qwen_engine(config)
        realtime_engine = create_qwen_realtime_engine(config)

        hybrid_qwen_config = config.get("hybrid_qwen", {})

        return HybridQwenTTSEngine(
            local_engine=local_engine,
            qwen_engine=qwen_engine,
            realtime_engine=realtime_engine,
            config=hybrid_qwen_config
        )
    except Exception as e:
        logger.error(f"创建混合千问引擎失败: {e}")
        return None


def create_cached_engine(
    base_engine: TTSEngine,
    config: dict
) -> CachedTTSEngine:
    """
    创建带缓存的 TTS 引擎

    Args:
        base_engine: 底层 TTS 引擎
        config: 配置字典

    Returns:
        CachedTTSEngine: 缓存引擎实例
    """
    hybrid_qwen_config = config.get("hybrid_qwen", {})
    cache_config = hybrid_qwen_config.get("cache", {})

    cache_dir = cache_config.get("cache_dir", "./data/tts_cache")
    max_cache_age_days = cache_config.get("max_cache_age_days", 30)
    enabled = cache_config.get("enabled", True)

    return CachedTTSEngine(
        base_engine=base_engine,
        cache_dir=cache_dir,
        max_cache_age_days=max_cache_age_days,
        enabled=enabled
    )


def create_tts_engine(config: dict) -> TTSEngine:
    """
    根据配置创建 TTS 引擎（工厂函数）

    支持的引擎类型：
    - "piper": 仅本地 Piper
    - "remote": 仅远程主机 GPT-SoVITS
    - "hybrid": 本地 Piper + 远程主机（原有）
    - "remote-qwen": 仅千问 TTS（非流式）[v2.2]
    - "doubao": 仅豆包 TTS（火山引擎）[v2.3]
    - "hybrid-qwen": 千问 TTS + Piper + 智能路由 [v2.2]

    Args:
        config: TTS 配置字典

    Returns:
        TTSEngine: TTS 引擎实例
    """
    engine_type = config.get("engine", "piper")

    logger.info("=" * 60)
    logger.info(f"创建 TTS 引擎: {engine_type}")
    logger.info("=" * 60)

    # 模式 1: 仅 Piper
    if engine_type == "piper":
        engine = create_piper_engine(config)

    # 模式 2: 仅远程主机
    elif engine_type == "remote":
        engine = create_remote_engine(config)

    # 模式 3: 混合 - 本地主机
    elif engine_type == "hybrid":
        engine = create_hybrid_engine(config)

    # 模式 4: 仅千问 TTS [v2.2]
    elif engine_type == "remote-qwen":
        engine = create_qwen_engine(config)

        # 添加缓存层
        hybrid_qwen_config = config.get("hybrid_qwen", {})
        cache_config = hybrid_qwen_config.get("cache", {})

        if cache_config.get("enabled", True):
            logger.info("添加缓存层")
            engine = create_cached_engine(engine, config)

    # 模式 5: 仅豆包 TTS [v2.3]
    elif engine_type == "doubao":
        engine = create_doubao_engine(config)

        # 添加缓存层（豆包默认启用缓存）
        doubao_cache_config = config.get("doubao", {}).get("cache", {})
        if doubao_cache_config.get("enabled", True):
            logger.info("添加缓存层（豆包 TTS）")
            cache_config = config.copy()
            cache_config["hybrid_qwen"] = {"cache": doubao_cache_config}
            engine = create_cached_engine(engine, cache_config)

    # 模式 6: 混合 - Piper + 千问 [v2.2]
    elif engine_type == "hybrid-qwen":
        engine = create_hybrid_qwen_engine(config)

        # 添加缓存层
        hybrid_qwen_config = config.get("hybrid_qwen", {})
        cache_config = hybrid_qwen_config.get("cache", {})

        if cache_config.get("enabled", True):
            logger.info("添加缓存层")
            engine = create_cached_engine(engine, config)

    else:
        raise ValueError(f"不支持的引擎类型: {engine_type}")

    logger.info(f"✅ TTS 引擎创建完成: {engine.__class__.__name__}")
    logger.info("=" * 60)

    return engine
