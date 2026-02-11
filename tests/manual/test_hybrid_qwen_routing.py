"""
混合千问 TTS 路由测试脚本
Manual Test Script for Hybrid Qwen TTS Routing
"""
import os
import sys
import logging
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.tts import create_tts_engine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_hybrid_qwen_routing():
    """测试混合千问 TTS 路由"""

    # 检查环境变量
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        logger.warning("未设置 DASHSCOPE_API_KEY，将只使用 Piper")

    # 配置
    config = {
        "engine": "hybrid-qwen",

        "local": {
            "model_path": "./models/piper/zh_CN-huayan-medium.onnx",
            "length_scale": 1.0,
            "noise_scale": 0.75,
            "noise_w_scale": 0.8,
            "sentence_silence": 0.2
        },

        "qwen": {
            "enabled": True,
            "provider": "dashscope",
            "dashscope": {
                "api_key": "${DASHSCOPE_API_KEY}",
                "model": "qwen3-tts-flash",
                "voice": "zhixiaobai",
                "format": "mp3",
                "sample_rate": 24000,
                "volume": 50,
                "rate": 1.0,
                "pitch": 1.0,
                "timeout": 30,
                "retry": 2
            }
        },

        "qwen_realtime": {
            "enabled": True,
            "dashscope": {
                "api_key": "${DASHSCOPE_API_KEY}",
                "url": "wss://dashscope.aliyuncs.com/api-ws/v1/realtime",
                "model": "qwen3-tts-flash-realtime",
                "voice": "zhixiaobai",
                "format": "pcm",
                "sample_rate": 24000,
                "mode": "server_commit",
                "timeout": 30
            }
        },

        "hybrid_qwen": {
            "streaming_threshold": 100,
            "scenario_streaming": {
                "llm_reply_long": "streaming",
                "alarm_cheerword": "streaming",
                "story_telling": "streaming",
                "wake_response": "non_streaming",
                "system_prompt": "non_streaming"
            },
            "fallback_to_piper": True,
            "max_retries": 2,
            "retry_delay": 1.0,
            "enable_monitoring": True,
            "log_decision": True,
            "cache": {
                "enabled": True,
                "warmup_on_startup": True,
                "cache_dir": "./data/tts_cache",
                "max_cache_age_days": 30
            }
        }
    }

    logger.info("=" * 60)
    logger.info("混合千问 TTS 路由测试")
    logger.info("=" * 60)

    # 创建引擎
    logger.info("1. 创建引擎...")
    try:
        engine = create_tts_engine(config)
    except Exception as e:
        logger.error(f"创建引擎失败: {e}")
        return

    # 获取引擎状态
    logger.info("2. 引擎状态:")
    if hasattr(engine, "get_engine_status"):
        status = engine.get_engine_status()
        for key, value in status.items():
            logger.info(f"  {key}: {value}")
    elif hasattr(engine, "get_model_info"):
        info = engine.get_model_info()
        for key, value in info.items():
            logger.info(f"  {key}: {value}")

    # 测试不同场景的路由
    logger.info("3. 测试路由决策:")

    test_cases = [
        {
            "text": "我在",
            "scenario": "wake_response",
            "description": "唤醒回复（短文本，非流式场景）"
        },
        {
            "text": "这是一个短文本测试",
            "scenario": "default",
            "description": "默认短文本（< 100 字符，非流式）"
        },
        {
            "text": "这是一个很长的文本测试，" * 20,  # > 100 字符
            "scenario": "default",
            "description": "长文本（≥ 100 字符，流式）"
        },
        {
            "text": "这是一个故事，讲述了一个勇敢的骑士去冒险的故事。" * 5,
            "scenario": "story_telling",
            "description": "讲故事（场景强制流式）"
        },
        {
            "text": "系统提示音",
            "scenario": "system_prompt",
            "description": "系统提示（场景强制非流式）"
        }
    ]

    output_dir = "test_output"
    os.makedirs(output_dir, exist_ok=True)

    for i, test_case in enumerate(test_cases, 1):
        text = test_case["text"]
        scenario = test_case["scenario"]
        description = test_case["description"]

        logger.info(f"\n  测试 {i}: {description}")
        logger.info(f"    文本长度: {len(text)} 字符")
        logger.info(f"    场景: {scenario}")

        try:
            start_time = time.time()

            # 调用 synthesize 方法（如果引擎支持 scenario 参数）
            if hasattr(engine, "synthesize") and "scenario" in engine.synthesize.__code__.co_varnames:
                audio = engine.synthesize(text, scenario=scenario)
            else:
                audio = engine.synthesize(text)

            elapsed = (time.time() - start_time) * 1000
            logger.info(f"    ✅ 成功: {len(audio)} 采样点, 耗时 {elapsed:.1f}ms")

            # 保存音频文件
            output_path = os.path.join(output_dir, f"test_{i}_{scenario}.wav")
            if hasattr(engine, "synthesize_to_file") and "scenario" in engine.synthesize_to_file.__code__.co_varnames:
                engine.synthesize_to_file(text, output_path, scenario=scenario)
            else:
                engine.synthesize_to_file(text, output_path)
            logger.info(f"    已保存: {output_path}")

        except Exception as e:
            logger.error(f"    ❌ 失败: {e}")

    # 测试缓存
    logger.info("\n4. 测试缓存性能:")
    if hasattr(engine, "_metadata"):
        cache_stats = engine.get_cache_stats()
        logger.info(f"  缓存数量: {cache_stats['total_count']}")
        logger.info(f"  缓存大小: {cache_stats['total_size_mb']:.2f} MB")

        # 测试缓存命中
        logger.info("  测试缓存命中（重复合成相同文本）...")
        test_text = "我在"

        for i in range(3):
            start_time = time.time()
            audio = engine.synthesize(test_text)
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"    第 {i+1} 次: {elapsed:.1f}ms")

    # 测试降级
    logger.info("\n5. 测试降级机制:")
    if api_key:
        logger.info("  （需要手动测试：断网后是否会降级到 Piper）")
    else:
        logger.info("  无 API key，使用 Piper（已自动降级）")

    logger.info("\n" + "=" * 60)
    logger.info("测试完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    test_hybrid_qwen_routing()
