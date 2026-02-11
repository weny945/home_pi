"""
千问 TTS 手动测试脚本
Manual Test Script for Qwen TTS
"""
import os
import sys
import logging
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.tts import QwenTTSEngine, create_qwen_engine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_qwen_tts():
    """测试千问 TTS"""

    # 检查环境变量
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        logger.error("请设置 DASHSCOPE_API_KEY 环境变量")
        return

    # 配置
    config = {
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
    }

    logger.info("=" * 60)
    logger.info("千问 TTS 测试")
    logger.info("=" * 60)

    # 创建引擎
    logger.info("1. 创建引擎...")
    engine = create_qwen_engine(config)

    # 检查可用性
    logger.info("2. 检查可用性...")
    if not engine.is_ready():
        logger.error("引擎不可用，请检查网络和 API key")
        return
    logger.info("✅ 引擎可用")

    # 测试短文本
    logger.info("3. 测试短文本合成...")
    test_texts = [
        "我在",
        "你好，这是千问 TTS 测试",
        "语音助手已经准备好了"
    ]

    for text in test_texts:
        try:
            logger.info(f"  合成: {text}")
            start_time = time.time()
            audio = engine.synthesize(text)
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"  ✅ 成功: {len(audio)} 采样点, 耗时 {elapsed:.1f}ms")
        except Exception as e:
            logger.error(f"  ❌ 失败: {e}")

    # 测试长文本
    logger.info("4. 测试长文本合成...")
    long_text = "今天天气很好，我们来测试一下千问 TTS 的长文本合成效果。" * 5
    try:
        logger.info(f"  文本长度: {len(long_text)} 字符")
        start_time = time.time()
        audio = engine.synthesize(long_text)
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"  ✅ 成功: {len(audio)} 采样点, 耗时 {elapsed:.1f}ms")
    except Exception as e:
        logger.error(f"  ❌ 失败: {e}")

    # 保存音频文件
    logger.info("5. 保存音频文件...")
    output_dir = "test_output"
    os.makedirs(output_dir, exist_ok=True)

    for i, text in enumerate(test_texts[:2], 1):
        try:
            output_path = os.path.join(output_dir, f"qwen_tts_test_{i}.wav")
            engine.synthesize_to_file(text, output_path)
            logger.info(f"  ✅ 已保存: {output_path}")
        except Exception as e:
            logger.error(f"  ❌ 保存失败: {e}")

    # 获取模型信息
    logger.info("6. 模型信息:")
    info = engine.get_model_info()
    for key, value in info.items():
        logger.info(f"  {key}: {value}")

    logger.info("=" * 60)
    logger.info("测试完成")
    logger.info("=" * 60)


def test_different_voices():
    """测试不同发音人"""
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        logger.error("请设置 DASHSCOPE_API_KEY 环境变量")
        return

    voices = ["zhixiaobai", "zhichu", "zhitian", "zhinan", "zhiqi"]
    test_text = "你好，我是语音助手胡桃。"

    logger.info("=" * 60)
    logger.info("测试不同发音人")
    logger.info("=" * 60)

    for voice in voices:
        config = {
            "provider": "dashscope",
            "dashscope": {
                "api_key": "${DASHSCOPE_API_KEY}",
                "model": "qwen3-tts-flash",
                "voice": voice,
                "format": "mp3",
                "sample_rate": 24000
            }
        }

        try:
            logger.info(f"测试发音人: {voice}")
            engine = create_qwen_engine(config)
            audio = engine.synthesize(test_text)

            output_dir = "test_output"
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"voice_{voice}.wav")
            engine.synthesize_to_file(test_text, output_path)

            logger.info(f"  ✅ 成功，已保存: {output_path}")
        except Exception as e:
            logger.error(f"  ❌ 失败: {e}")

    logger.info("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="千问 TTS 手动测试")
    parser.add_argument("--voices", action="store_true", help="测试不同发音人")
    args = parser.parse_args()

    if args.voices:
        test_different_voices()
    else:
        test_qwen_tts()
