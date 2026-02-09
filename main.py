"""
主入口
Voice Assistant Main Entry Point

Phase 1.3: 添加对话生成功能（千问 API + TTS 播放）
Phase 1.5: 智能对话交互优化（智能打断 + 上下文增强 + 技能框架）
"""
import logging
import sys
import os
from pathlib import Path

# 内存优化：限制 OpenMP 线程数（节省 ~50 MB 栈空间）
# PyTorch 默认使用所有 CPU 核心，每线程 8 MB 栈
os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('MKL_NUM_THREADS', '2')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')

# 尽早设置 torch 线程数（在导入 torch 相关模块前）
import torch
torch.set_num_threads(2)
if torch.cuda.is_available():
    torch.set_num_threads(2)

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.config import get_config
from src.audio import ReSpeakerInput
from src.wake_word import OpenWakeWordDetector
from src.feedback import AudioFeedbackPlayer, TTSFeedbackPlayer
from src.state_machine import StateMachine

# Phase 1.2 新增
try:
    from src.stt import FunASRSTTEngine
    from src.vad import FunASRVADDetector
    STT_AVAILABLE = True
except ImportError:
    STT_AVAILABLE = False
    FunASRSTTEngine = None
    FunASRVADDetector = None

# Phase 1.3 新增
try:
    from src.llm import QwenLLMEngine
    from src.tts import PiperTTSEngine, RemoteTTSEngine, HybridTTSEngine
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    QwenLLMEngine = None
    PiperTTSEngine = None
    RemoteTTSEngine = None
    HybridTTSEngine = None


def setup_logging(config) -> None:
    """
    配置日志系统

    Args:
        config: 配置对象
    """
    log_config = config.get_logging_config()
    log_level = getattr(logging, log_config.get('level', 'INFO'))
    log_file = log_config.get('file', './logs/assistant.log')

    # 确保日志目录存在
    log_dir = Path(log_file).parent
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # 如果无法在项目目录创建日志，使用 /tmp
        log_file = '/tmp/assistant.log'
        print(f"⚠️  无法创建日志目录 {log_dir}，使用 /tmp/assistant.log")

    # 配置日志格式
    try:
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ],
            force=True  # Python 3.8+ 需要这个参数
        )
    except PermissionError:
        # 如果无法写入日志文件，只使用控制台输出
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ],
            force=True
        )


def main():
    """主函数"""
    try:
        # 1. 加载配置
        print("加载配置文件...")
        config = get_config()
        config.validate()

        # 2. 配置日志
        setup_logging(config)
        logger = logging.getLogger(__name__)
        logger.info("=" * 60)
        logger.info("语音助手系统启动 v1.5.0 (第一阶段 1.5：唤醒词检测 + TTS回复 + 语音识别 + 对话生成 + 智能交互优化)")
        logger.info("=" * 60)

        # 3. 初始化音频输入
        logger.info("初始化音频输入...")
        audio_config = config.get_audio_config()
        audio_input = ReSpeakerInput(
            device_name=audio_config.get('input_device', 'seeed-4mic-voicecard'),
            sample_rate=audio_config.get('sample_rate', 16000),
            channels=audio_config.get('channels', 1),
            chunk_size=audio_config.get('chunk_size', 512),
            input_gain=audio_config.get('input_gain', 1.0)
        )

        # 4. 初始化唤醒词检测器
        logger.info("初始化唤醒词检测器...")
        wakeword_config = config.get_wakeword_config()
        detector = OpenWakeWordDetector(
            model_path=wakeword_config.get('model'),
            threshold=wakeword_config.get('threshold', 0.5)
        )

        # 5. 初始化反馈播放器
        logger.info("初始化反馈播放器...")
        feedback_config = config.get_feedback_config()
        feedback_mode = feedback_config.get('mode', 'beep')

        if feedback_mode == 'tts':
            # Piper TTS 语音回复
            tts_config = feedback_config.get('tts', {})
            feedback_player = TTSFeedbackPlayer(
                messages=tts_config.get('messages', ["我在", "请吩咐", "我在听"]),
                model_path=tts_config.get('model_path', './models/piper/zh_CN-huayan-medium.onnx'),
                length_scale=tts_config.get('length_scale', 1.0),
                noise_scale=tts_config.get('noise_scale', 0.667),
                noise_w_scale=tts_config.get('noise_w_scale', 0.8),
                sentence_silence=tts_config.get('sentence_silence', 0.0),
                text_enhancement=tts_config.get('text_enhancement', {}),
                random_message=tts_config.get('random_message', False),
                cache_audio=tts_config.get('cache_audio', True),
                output_device=audio_config.get('output_device', 'plughw:0,0'),
                volume_gain=tts_config.get('volume_gain', 1.0)
            )
            logger.info(f"使用 Piper TTS 语音回复模式 (语速: {tts_config.get('length_scale', 1.0)})")
            logger.info(f"音频输出设备: {audio_config.get('output_device', 'plughw:0,0')}")
        else:
            # 蜂鸣声或音频文件
            feedback_player = AudioFeedbackPlayer(
                mode=feedback_mode,
                audio_file=feedback_config.get('audio_file'),
                beep_duration_ms=feedback_config.get('beep_duration_ms', 200),
                beep_frequency=feedback_config.get('beep_frequency', 880)
            )
            logger.info(f"使用音频反馈模式: {feedback_mode}")

        # 6. 初始化 STT 和 VAD (Phase 1.2)
        logger.info("=" * 60)
        logger.info("初始化 STT 和 VAD 模块 (Phase 1.2)...")
        stt_engine = None
        vad_detector = None

        stt_config = config.get_section('stt') or {}
        vad_config = config.get_section('vad') or {}
        listening_config = config.get_section('listening') or {}

        if stt_config.get('enabled', False) and STT_AVAILABLE:
            logger.info("初始化 STT 引擎...")
            try:
                # 启动时加载模型，避免首次使用时延迟
                # 注意：fp16=True 在 CPU 上有兼容性问题，暂时不使用
                stt_engine = FunASRSTTEngine(
                    model_name=stt_config.get('model', 'iic/SenseVoiceSmall'),
                    device=stt_config.get('device', 'cpu'),
                    punc_model=stt_config.get('punc_model'),
                    # fp16=True  # 暂时禁用：FunASR + CPU 的 fp16 支持有问题
                    # load_model=True 为默认值，在启动时加载模型
                )
                logger.info("✅ STT 引擎初始化成功（模型已加载）")
            except Exception as e:
                logger.warning(f"STT 引擎初始化失败: {e}")
                logger.warning("语音识别功能将被禁用")

        # 内存优化：删除单独的 VAD 初始化，使用 STT 内置的 VAD
        # FunASRSTTEngine 已经内置了 VAD 模型，无需重复加载
        if vad_config.get('enabled', False) and STT_AVAILABLE and stt_engine:
            logger.info("✅ 使用 STT 内置 VAD 检测器（节省 ~30-50 MB）")
            vad_detector = None  # 使用 STT 内置 VAD
        elif vad_config.get('enabled', False) and STT_AVAILABLE:
            # 仅在 STT 未启用时才单独初始化 VAD
            logger.info("初始化独立 VAD 检测器...")
            try:
                vad_detector = FunASRVADDetector(
                    vad_model=vad_config.get('model', 'fsmn-vad'),
                    device=vad_config.get('device', 'cpu'),
                    load_model=True
                )
                logger.info("✅ VAD 检测器初始化成功")
            except Exception as e:
                logger.warning(f"VAD 检测器初始化失败: {e}")
                logger.warning("将使用超时方式结束录音")
                vad_detector = None

        # 7. 初始化 LLM 引擎 (Phase 1.3)
        logger.info("=" * 60)
        logger.info("初始化 LLM 引擎 (Phase 1.3)...")
        llm_engine = None
        llm_config = config.get_section('llm') or {}

        if llm_config.get('enabled', False) and LLM_AVAILABLE:
            logger.info("初始化 LLM 引擎...")
            try:
                llm_engine = QwenLLMEngine(
                    api_key=llm_config.get('api_key'),
                    model=llm_config.get('model', 'qwen-turbo'),
                    temperature=llm_config.get('temperature', 0.7),
                    max_tokens=llm_config.get('max_tokens', 3000),
                    max_tokens_long=llm_config.get('max_tokens_long', 8000),
                    enable_history=llm_config.get('enable_history', True),
                    max_history=llm_config.get('max_history', 10),
                    system_prompt=llm_config.get('system_prompt'),
                    system_prompt_long=llm_config.get('system_prompt_long'),
                    long_text_keywords=llm_config.get('long_text_keywords')
                )
                model_info = llm_engine.get_model_info()
                logger.info(f"✅ LLM 引擎初始化成功 ({model_info['model']})")
                logger.info(f"   标准模式: {llm_engine._max_tokens} tokens")
                logger.info(f"   长文本模式: {llm_engine._max_tokens_long} tokens")
                if 'system_prompt' in model_info:
                    logger.info(f"   角色设定: {model_info['system_prompt']}")
                if llm_engine._long_text_keywords:
                    logger.info(f"   长文本关键词: {len(llm_engine._long_text_keywords)} 个")
            except Exception as e:
                logger.warning(f"LLM 引擎初始化失败: {e}")
                logger.warning("对话生成功能将被禁用")
        else:
            logger.info("LLM 引擎未启用或不可用")

        # 8. 初始化 TTS 引擎 (Phase 1.3)
        logger.info("=" * 60)
        logger.info("初始化 TTS 引擎 (Phase 1.3)...")
        tts_engine = None
        tts_config_full = config.get_section('tts') or {}

        if tts_config_full and LLM_AVAILABLE:
            logger.info("初始化 TTS 引擎...")
            try:
                engine_type = tts_config_full.get('engine', 'p')

                if engine_type == 'hybrid':
                    # 混合引擎：优先远程，失败自动切换本地
                    logger.info("使用混合 TTS 引擎（远程优先，自动切换）")

                    # 初始化本地 TTS
                    local_config = tts_config_full.get('local', {})
                    text_enhancement = local_config.get('text_enhancement', {})

                    local_engine = PiperTTSEngine(
                        model_path=local_config.get('model_path', './models/piper/zh_CN-huayan-medium.onnx'),
                        length_scale=local_config.get('length_scale', 1.0),
                        noise_scale=local_config.get('noise_scale', 0.667),
                        noise_w_scale=local_config.get('noise_w_scale', 0.8),
                        sentence_silence=local_config.get('sentence_silence', 0.2),
                        text_enhancement=text_enhancement
                    )
                    logger.info("✅ 本地 TTS 引擎初始化成功")
                    logger.info(f"   语速: {local_config.get('length_scale', 1.0)}")
                    logger.info(f"   音色随机性: {local_config.get('noise_scale', 0.667)}")
                    logger.info(f"   韵律变化: {local_config.get('noise_w_scale', 0.8)}")
                    logger.info(f"   句间停顿: {local_config.get('sentence_silence', 0.2)}s")
                    logger.info(f"   文本增强: {'启用' if text_enhancement.get('enabled', True) else '禁用'}")

                    # 初始化远程 TTS（如果启用）
                    remote_config = tts_config_full.get('remote', {})
                    remote_engine = None

                    if remote_config.get('enabled', False):
                        try:
                            remote_engine = RemoteTTSEngine(
                                server_ip=remote_config.get('server_ip', '192.168.2.141'),
                                port=remote_config.get('port', 9880),
                                timeout=remote_config.get('timeout', 60),
                                text_lang=remote_config.get('text_lang', 'zh'),
                                speed=remote_config.get('speed', 1.0),
                                max_text_length=remote_config.get('max_text_length', 100)
                            )
                            logger.info("✅ 远程 TTS 引擎初始化成功")
                        except Exception as e:
                            logger.warning(f"远程 TTS 引擎初始化失败: {e}")
                            logger.warning("将仅使用本地 TTS")
                            remote_engine = None

                    # 创建混合引擎
                    hybrid_config = tts_config_full.get('hybrid', {})
                    if remote_engine:
                        tts_engine = HybridTTSEngine(
                            remote_engine=remote_engine,
                            local_engine=local_engine,
                            health_check_interval=hybrid_config.get('health_check_interval', 3600),
                            auto_failback=hybrid_config.get('auto_failback', True)
                        )
                        logger.info("✅ 混合 TTS 引擎初始化成功")

                        # 显示混合引擎状态
                        model_info = tts_engine.get_model_info()
                        logger.info(f"  当前使用: {model_info['current_engine']} TTS")
                        logger.info(f"  远程可用: {model_info['remote_available']}")
                    else:
                        # 远程引擎初始化失败，只使用本地引擎
                        tts_engine = local_engine
                        logger.info("⚠️  仅使用本地 TTS 引擎（远程不可用）")

                elif engine_type == 'remote':
                    # 仅远程 TTS
                    logger.info("使用远程 TTS 引擎")
                    remote_config = tts_config_full.get('remote', {})
                    tts_engine = RemoteTTSEngine(
                        server_ip=remote_config.get('server_ip', '192.168.2.141'),
                        port=remote_config.get('port', 9880),
                        timeout=remote_config.get('timeout', 60),
                        text_lang=remote_config.get('text_lang', 'zh'),
                        speed=remote_config.get('speed', 1.0),
                        max_text_length=remote_config.get('max_text_length', 100)
                    )
                    logger.info("✅ 远程 TTS 引擎初始化成功")

                else:
                    # 本地 TTS（默认）
                    logger.info("使用本地 TTS 引擎 (Piper)")
                    local_config = tts_config_full.get('local', {})
                    text_enhancement = local_config.get('text_enhancement', {})

                    tts_engine = PiperTTSEngine(
                        model_path=local_config.get('model_path', './models/piper/zh_CN-huayan-medium.onnx'),
                        length_scale=local_config.get('length_scale', 1.0),
                        noise_scale=local_config.get('noise_scale', 0.667),
                        noise_w_scale=local_config.get('noise_w_scale', 0.8),
                        sentence_silence=local_config.get('sentence_silence', 0.2),
                        text_enhancement=text_enhancement
                    )
                    logger.info("✅ TTS 引擎初始化成功")
                    logger.info(f"   语速: {local_config.get('length_scale', 1.0)}")
                    logger.info(f"   音色随机性: {local_config.get('noise_scale', 0.667)}")
                    logger.info(f"   韵律变化: {local_config.get('noise_w_scale', 0.8)}")
                    logger.info(f"   句间停顿: {local_config.get('sentence_silence', 0.2)}s")
                    logger.info(f"   文本增强: {'启用' if text_enhancement.get('enabled', True) else '禁用'}")

            except Exception as e:
                logger.warning(f"TTS 引擎初始化失败: {e}")
                logger.warning("LLM 回复将无法语音播报")
                tts_engine = None
        else:
            logger.info("TTS 引擎未配置或 LLM 不可用")

        # 9. 创建状态机
        logger.info("=" * 60)
        logger.info("创建状态机...")
        logger.info(f"  音频输入: {audio_config.get('input_device', 'default')}")
        logger.info(f"  唤醒词阈值: {wakeword_config.get('threshold', 0.5)}")
        logger.info(f"  STT: {'✅' if stt_engine else '❌'}")
        logger.info(f"  VAD: {'✅' if vad_detector else '❌'}")
        logger.info(f"  LLM: {'✅' if llm_engine else '❌'}")
        logger.info(f"  TTS: {'✅' if tts_engine else '❌'}")

        # 准备回声检测词汇
        wake_words = ["派蒙", "alexa"]  # 默认唤醒词
        wake_reply_messages = []

        # 从配置中读取唤醒回复消息
        if feedback_config and feedback_config.get('mode') == 'tts':
            tts_feedback_config = feedback_config.get('tts', {})
            wake_reply_messages = tts_feedback_config.get('messages', [])
            logger.info(f"  唤醒回复消息: {wake_reply_messages}")

        state_machine = StateMachine(
            audio_input=audio_input,
            detector=detector,
            feedback_player=feedback_player,
            stt_engine=stt_engine,
            vad_detector=vad_detector,
            llm_engine=llm_engine,
            tts_engine=tts_engine,
            max_listening_duration=listening_config.get('max_duration', 10.0) if listening_config else 10.0,
            silence_threshold=listening_config.get('silence_threshold', 1.5) if listening_config else 1.5,
            wake_words=wake_words,
            wake_reply_messages=wake_reply_messages,
            config=config  # Phase 1.4: 添加配置参数
        )

        # 10. 运行状态机
        logger.info("=" * 60)
        logger.info("启动状态机主循环...")
        logger.info("等待唤醒词...")
        logger.info("=" * 60)
        state_machine.run()

    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序异常退出: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
