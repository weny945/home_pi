"""
豆包 TTS 引擎测试（V3 HTTP 单向流式 API - 模型 2.0）
Doubao TTS Engine Test (Volcengine - Model 2.0)

测试环境变量：
- DOUBAO_ACCESS_KEY: 火山引擎 Access Token
- DOUBAO_APP_ID: 火山引擎 APP ID

运行测试：
    python tests/manual/test_doubao_v3_tts.py
"""
import os
import sys
import logging
import time
import numpy as np
import wave
import tempfile
import subprocess

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

from src.tts.doubao_engine import DoubaoTTSEngine

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_doubao_tts():
    """测试豆包 TTS 引擎"""

    # 检查环境变量
    access_key = os.getenv("DOUBAO_ACCESS_KEY")
    app_id = os.getenv("DOUBAO_APP_ID")

    if not access_key or not app_id:
        logger.error("请设置环境变量 DOUBAO_ACCESS_KEY 和 DOUBAO_APP_ID")
        logger.info("获取方式：https://console.volcengine.com/speech/service")
        return False

    logger.info("=" * 60)
    logger.info("豆包 TTS 引擎测试（V3 HTTP 单向流式 - 模型 2.0）")
    logger.info("=" * 60)

    # 创建配置
    config = {
        "doubao": {
            "api_key": access_key,
            "app_id": app_id,
            "resource_id": "seed-tts-1.0",  # 先尝试模型 1.0
            "model": "",  # 不设置 model 参数（可选）
            "voice": "zh_female_shuangkuaisisi_moon_bigtts",  # 模型 1.0 发音人
            "format": "pcm",  # 使用 PCM 格式，无需 pydub
            "sample_rate": 24000,
            "speed": 0,
            "volume": 0,
            "timeout": 30,
            "retry": 2,
        }
    }

    try:
        # 初始化引擎
        logger.info("初始化豆包 TTS 引擎...")
        engine = DoubaoTTSEngine(config)

        # 打印引擎信息
        info = engine.get_model_info()
        logger.info(f"引擎信息: {info}")

        # 检查是否就绪
        if not engine.is_ready():
            logger.error("引擎未就绪")
            return False

        logger.info("引擎就绪")

        # 测试合成
        test_texts = [
            "你好，我是胡桃，很高兴为你服务。",
            "今天天气真不错，适合出去散步。",
            "测试一下语音合成的效果，看看质量如何。",
        ]

        for i, text in enumerate(test_texts, 1):
            logger.info(f"\n测试 {i}/{len(test_texts)}: {text}")

            start_time = time.time()

            # 合成语音
            audio_data = engine.synthesize(text)

            elapsed = time.time() - start_time

            logger.info(f"合成完成，耗时: {elapsed:.2f}秒")
            logger.info(f"音频数据: {len(audio_data)} 采样点, {len(audio_data) / 24000:.2f}秒")

            # 保存到临时文件并播放
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                temp_path = f.name

                # 写入 WAV 文件
                with wave.open(temp_path, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(24000)
                    wf.writeframes(audio_data.tobytes())

            logger.info(f"已保存到: {temp_path}")

            # 播放音频
            logger.info("播放音频...")
            try:
                subprocess.run(['aplay', '-q', temp_path], check=True)
                logger.info("播放完成")
            except subprocess.CalledProcessError as e:
                logger.error(f"播放失败: {e}")
            except FileNotFoundError:
                logger.warning("未找到 aplay 命令，跳过播放")

            # 清理临时文件
            try:
                os.unlink(temp_path)
            except:
                pass

            time.sleep(0.5)

        logger.info("\n" + "=" * 60)
        logger.info("所有测试完成！")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_doubao_tts()
    sys.exit(0 if success else 1)
