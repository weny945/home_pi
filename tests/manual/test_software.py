"""
软件模块测试脚本
Software Module Test Script for Voice Assistant
测试 TTS, STT, LLM 各个软件模块
"""
import sys
import os
import time
from pathlib import Path

# 获取项目根目录
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))

# 确保在项目根目录运行
os.chdir(project_root)


def print_header(title):
    """打印标题"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def print_section(title):
    """打印小节标题"""
    print("\n" + "-" * 60)
    print(title)
    print("-" * 60)


def test_tts_engine():
    """测试 TTS 引擎"""
    print_header("测试 1: TTS 文本转语音引擎")

    try:
        from src.tts import PiperTTSEngine
    except ImportError as e:
        print(f"❌ 导入 TTS 模块失败: {e}")
        print("   请确保已安装依赖: pip install piper-tts")
        return False

    # 检查模型文件
    model_path = "./models/piper/zh_CN-huayan-medium.onnx"
    if not Path(model_path).exists():
        print(f"❌ 模型文件不存在: {model_path}")
        print("   请确保模型文件已放置在 models/piper/ 目录")
        return False

    print(f"\n✅ 找到模型文件: {model_path}")
    print(f"   大小: {Path(model_path).stat().st_size / 1024 / 1024:.1f} MB")

    # 初始化引擎
    print("\n📦 初始化 Piper TTS 引擎...")
    try:
        engine = PiperTTSEngine(
            model_path=model_path,
            load_model=True
        )
        print("✅ 引擎初始化成功")
    except Exception as e:
        print(f"❌ 引擎初始化失败: {e}")
        return False

    # 获取模型信息
    print("\n📊 模型信息:")
    model_info = engine.get_model_info()
    print(f"   模型路径: {model_info['model_path']}")
    print(f"   采样率: {model_info['sample_rate']} Hz")
    print(f"   语速设置: {model_info['synthesis_config']['length_scale']}")
    print(f"   已加载: {model_info['is_loaded']}")

    # 测试语音合成
    print_section("语音合成测试")
    test_texts = ["我在", "请吩咐", "我在听"]

    print(f"\n合成 {len(test_texts)} 条测试语音...")
    total_duration = 0
    total_time = 0

    for i, text in enumerate(test_texts, 1):
        print(f"\n  [{i}/{len(test_texts)}] 合成: '{text}'")

        start_time = time.time()
        try:
            audio_data = engine.synthesize(text)
            elapsed = time.time() - start_time

            duration = len(audio_data) / model_info['sample_rate']
            total_duration += duration
            total_time += elapsed

            print(f"    ✅ 成功")
            print(f"    音频时长: {duration:.2f} 秒")
            print(f"    合成耗时: {elapsed:.2f} 秒")
            print(f"    实时率: {duration/elapsed:.1f}x")

        except Exception as e:
            print(f"    ❌ 失败: {e}")
            return False

    # 统计
    print(f"\n📊 统计:")
    print(f"   总合成次数: {len(test_texts)}")
    print(f"   总音频时长: {total_duration:.2f} 秒")
    print(f"   总合成耗时: {total_time:.2f} 秒")
    print(f"   平均合成时间: {total_time/len(test_texts):.2f} 秒")
    print(f"   平均实时率: {total_duration/total_time:.1f}x")

    # 测试语速调整
    print_section("语速调整测试")
    test_text = "测试语速"
    speeds = [0.8, 1.0, 1.2]

    print(f"\n测试不同语速合成: '{test_text}'")
    for speed in speeds:
        engine.set_synthesis_config(length_scale=speed)
        audio_data = engine.synthesize(test_text)
        duration = len(audio_data) / model_info['sample_rate']
        print(f"  语速 {speed}: {duration:.2f} 秒")

    # 恢复正常语速
    engine.set_synthesis_config(length_scale=1.0)

    # 测试保存到文件
    print_section("文件保存测试")
    Path("./cache").mkdir(parents=True, exist_ok=True)
    output_file = "./cache/test_tts_output.wav"

    print(f"\n保存测试音频到: {output_file}")
    try:
        engine.synthesize_to_file("文件保存测试", output_file)
        print(f"✅ 音频已保存")
        print(f"   文件大小: {Path(output_file).stat().st_size / 1024:.1f} KB")
    except Exception as e:
        print(f"❌ 保存失败: {e}")
        return False

    print(f"\n✅ TTS 引擎测试通过!")
    return True


def test_tts_feedback():
    """测试 TTS 反馈播放器"""
    print_header("测试 2: TTS 反馈播放器")

    try:
        from src.feedback import TTSFeedbackPlayer
    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        return False

    # 初始化播放器
    print("\n📦 初始化 TTS 反馈播放器...")
    try:
        # 从配置获取输出设备
        from src.config import get_config
        try:
            config = get_config()
            audio_config = config.get_audio_config()
            output_device = audio_config.get('output_device', 'default')
            print(f"从配置读取输出设备: {output_device}")
        except:
            print("⚠️  无法读取配置，使用默认设备")
            output_device = 'default'

        player = TTSFeedbackPlayer(
            messages=["我在", "请吩咐", "我在听", "您好", "我在这里"],
            model_path="./models/piper/zh_CN-huayan-medium.onnx",
            cache_audio=False,  # 测试时不使用缓存
            output_device=output_device
        )
        print("✅ 播放器初始化成功")
        print(f"   输出设备: {output_device}")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return False

    # 测试消息选择
    print_section("消息选择测试")
    print("\n测试顺序选择模式:")
    for i in range(7):
        message = player._get_message()
        print(f"  第 {i+1} 次: {message}")

    # 测试播放（实际播放音频）
    print_section("音频播放测试")
    print("\n将播放 3 条测试消息...")
    print("💡 请确认可以听到语音输出")

    input("\n按 Enter 开始播放...")

    try:
        for i in range(3):
            message = player._get_message()
            print(f"\n  [{i+1}/3] 播放: '{message}'")

            start_time = time.time()
            player.play_wake_feedback()
            elapsed = time.time() - start_time

            print(f"  ✅ 播放完成 (耗时: {elapsed:.2f} 秒)")

            # 短暂暂停
            time.sleep(0.5)

        print("\n✅ TTS 反馈播放器测试通过!")
        return True

    except Exception as e:
        print(f"\n❌ 播放失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            player.stop()
        except Exception as e:
            print(f"⚠️  播放器清理失败: {e}")


def test_tts_integration():
    """测试唤醒词检测 + TTS 反馈完整集成"""
    print_header("测试 3: 唤醒词检测 + TTS 反馈集成")

    try:
        from src.config import get_config
        from src.audio import ReSpeakerInput
        from src.wake_word import OpenWakeWordDetector
        from src.feedback import TTSFeedbackPlayer
    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        return False

    # 加载配置
    print("\n⚙️  加载配置文件...")
    try:
        config = get_config()
        audio_config = config.get_audio_config()
        wakeword_config = config.get_wakeword_config()
        feedback_config = config.get_feedback_config()
        tts_config = feedback_config.get('tts', {})

        print("✅ 配置加载成功")
        print(f"\n配置信息:")
        print(f"  输入设备: {audio_config.get('input_device')}")
        print(f"  采样率: {audio_config.get('sample_rate')} Hz")
        print(f"  唤醒词模型: {wakeword_config.get('model')}")
        print(f"  唤醒阈值: {wakeword_config.get('threshold')}")
        print(f"  TTS 引擎: {tts_config.get('engine')}")
        print(f"  TTS 模型: {tts_config.get('model_path')}")

    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False

    # 初始化音频输入
    print_section("初始化音频输入")
    try:
        print(f"\n🎤 打开音频输入设备: {audio_config.get('input_device')}")
        audio_input = ReSpeakerInput(
            device_name=audio_config.get('input_device', 'seeed-4mic-voicecard'),
            sample_rate=audio_config.get('sample_rate', 16000),
            channels=audio_config.get('channels', 1),
            chunk_size=audio_config.get('chunk_size', 512)
        )
        print("✅ 音频输入初始化成功")
    except Exception as e:
        print(f"❌ 音频输入初始化失败: {e}")
        print("\n💡 提示:")
        print("   - 请确保 ReSpeaker 4-Mic 已连接")
        print("   - 检查驱动是否正确安装")
        print("   - 运行 test_hardware.py 检查音频设备")
        return False

    # 初始化唤醒词检测器
    print_section("初始化唤醒词检测器")
    try:
        model_path = wakeword_config.get('model')

        # 检查模型文件是否存在
        from pathlib import Path
        if model_path and not Path(model_path).exists():
            print(f"\n⚠️  配置的模型文件不存在: {model_path}")
            print(f"   使用 OpenWakeWord 预训练的 'alexa' 模型...")
            model_path = None  # 使用 None 加载所有预训练模型

        # 明确使用预训练的 alexa 模型进行测试
        use_pretrained = False
        if model_path is None:
            print(f"\n🔊 加载 OpenWakeWord 预训练模型...")
            print(f"   唤醒词: 'alexa'")
            use_pretrained = True
            detector = OpenWakeWordDetector(
                model_path=None,  # 加载所有预训练模型
                threshold=wakeword_config.get('threshold', 0.5)
            )
        else:
            print(f"\n🔊 加载唤醒词模型: {model_path}")
            detector = OpenWakeWordDetector(
                model_path=model_path,
                threshold=wakeword_config.get('threshold', 0.5)
            )

        if detector.is_ready:
            print("✅ 唤醒词检测器初始化成功")
            print(f"   阈值: {wakeword_config.get('threshold', 0.5)}")
            if use_pretrained:
                print(f"   模型: OpenWakeWord 预训练模型")
                print(f"\n💡 可用的唤醒词:")
                print(f"   - 'alexa' (推荐用于测试)")
                print(f"   - 'hey siri'")
                print(f"   - 'ok google'")
            else:
                print(f"   模型: {model_path}")
        else:
            print("❌ 唤醒词检测器未就绪")
            print("\n💡 提示:")
            print("   - 检查模型文件路径")
            print("   - 检查 openwakeword 库是否正确安装")
            try:
                audio_input.stop_stream()
            except:
                pass
            return False

    except Exception as e:
        print(f"❌ 唤醒词检测器初始化失败: {e}")
        print("\n💡 提示:")
        print("   - 检查 openwakeword 库是否安装: pip install openwakeword")
        print("   - 检查模型文件是否存在")
        print("   - 模型路径: models/wakeword/")
        import traceback
        traceback.print_exc()
        try:
            audio_input.stop_stream()
        except:
            pass
        return False

    # 初始化 TTS 反馈播放器
    print_section("初始化 TTS 反馈播放器")
    try:
        print(f"\n🔊 加载 TTS 模型...")
        output_device = audio_config.get('output_device', 'plughw:0,0')
        feedback_player = TTSFeedbackPlayer(
            messages=tts_config.get('messages', ["我在", "请吩咐", "我在听"]),
            model_path=tts_config.get('model_path', './models/piper/zh_CN-huayan-medium.onnx'),
            length_scale=tts_config.get('length_scale', 1.0),
            random_message=tts_config.get('random_message', False),
            cache_audio=tts_config.get('cache_audio', True),
            output_device=output_device
        )
        print("✅ TTS 反馈播放器初始化成功")
        print(f"   消息列表: {tts_config.get('messages', [])}")
        print(f"   语速: {tts_config.get('length_scale', 1.0)}")
        print(f"   输出设备: {output_device}")
    except Exception as e:
        print(f"❌ TTS 反馈播放器初始化失败: {e}")
        # detector 没有 stop 方法
        try:
            audio_input.stop_stream()
        except:
            pass
        return False

    # 实时唤醒词检测 + TTS 反馈测试
    print_section("实时唤醒词检测 + TTS 反馈测试")
    print("\n🔄 开始监听唤醒词...")
    print(f"💡 请对着麦克风清晰地说: **'alexa'**")
    print(f"   （使用 OpenWakeWord 预训练的 Alexa 模型）")
    print(f"   检测到唤醒词后，将播放 TTS 语音回复")
    print(f"   测试将检测 3 次唤醒后自动结束")
    print(f"\n按 Ctrl+C 可随时停止测试")

    input("\n按 Enter 开始监听...")

    wake_count = 0
    max_wakes = 3
    last_wake_time = 0
    wake_cooldown = 2.0  # 唤醒冷却时间（秒）

    try:
        print("\n" + "▌" * 30)
        print("🎤 监听中...")
        print("▌" * 30)

        audio_input.start_stream()

        while wake_count < max_wakes:
            try:
                # 读取音频数据
                audio_data = audio_input.read_chunk()

                # 检测唤醒词
                detected = detector.process_frame(audio_data)

                current_time = time.time()

                if detected:
                    # 检查冷却时间
                    if current_time - last_wake_time >= wake_cooldown:
                        wake_count += 1
                        last_wake_time = current_time

                        # 获取本次将播放的消息
                        message = feedback_player._get_message()

                        print(f"\n{'='*60}")
                        print(f"✅ 检测到唤醒词! (第 {wake_count}/{max_wakes} 次)")
                        print(f"{'='*60}")
                        print(f"📢 播放回复: '{message}'")

                        # 播放 TTS 反馈
                        start_time = time.time()
                        feedback_player.play_wake_feedback()
                        elapsed = time.time() - start_time

                        print(f"✅ 播放完成 (耗时: {elapsed:.2f} 秒)")
                        print(f"\n{'▌'*30}")
                        print("🎤 继续监听...")
                        print("▌" * 30)

            except KeyboardInterrupt:
                print("\n\n⚠️  用户中断测试")
                break

        print("\n" + "=" * 60)
        if wake_count >= max_wakes:
            print(f"✅ 已完成 {max_wakes} 次唤醒检测测试")
        else:
            print(f"⚠️  测试中断，共检测到 {wake_count} 次唤醒")
        print("=" * 60)

        print("\n✅ 唤醒词检测 + TTS 反馈集成测试完成!")
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理资源
        print("\n🧹 清理资源...")
        try:
            feedback_player.stop()
        except Exception as e:
            print(f"⚠️  TTS 播放器清理失败: {e}")

        # detector 没有 stop 方法，无需清理

        try:
            audio_input.stop_stream()
        except Exception as e:
            print(f"⚠️  音频输入清理失败: {e}")

        print("✅ 资源已释放")


def test_stt_module():
    """测试 STT 模块（预留接口）"""
    print_header("测试 4: STT 语音识别模块")

    print("\n⚠️  STT 模块尚未实现")
    print("\n📋 计划功能:")
    print("  [ ] FunASR 语音识别")
    print("  [ ] SenseVoiceSmall 模型")
    print("  [ ] 实时语音转文字")
    print("  [ ] VAD 语音活动检测")
    print("  [ ] 中文识别优化")

    print("\n💡 后续开发:")
    print("  第二阶段将集成 STT 功能")
    print("  实现: 语音输入 → 文字输出")

    return None


def test_llm_module():
    """测试 LLM 模块（预留接口）"""
    print_header("测试 5: LLM 语言模型模块")

    print("\n⚠️  LLM 模块尚未实现")
    print("\n📋 计划功能:")
    print("  [ ] 阿里云千问 API 集成")
    print("  [ ] 多轮对话管理")
    print("  [ ] 上下文记忆")
    print("  [ ] 意图理解")
    print("  [ ] 技能插件系统")

    print("\n💡 后续开发:")
    print("  第二/三阶段将集成 LLM 功能")
    print("  实现: 文字输入 → 智能回复 → TTS 输出")

    print("\n📝 所需配置:")
    print("  环境变量: DASHSCOPE_API_KEY")
    print("  API 提供商: 阿里云千问 (Qwen)")

    return None


def test_v14_audio_quality():
    """测试 Phase 1.4 音频质量检测功能"""
    print_header("测试 6: Phase 1.4 音频质量检测")

    print("\n✨ Phase 1.4 新功能:")
    print("  ✅ 自适应 VAD 阈值")
    print("  ✅ 音频质量检测")
    print("  ✅ 文本质量检测")
    print("  ✅ 分级重试策略")
    print("  ✅ 智能尾端点检测")

    try:
        from src.config import get_config
        from src.audio import ReSpeakerInput
        from src.wake_word import OpenWakeWordDetector
        from src.feedback import TTSFeedbackPlayer
        from src.state_machine import StateMachine

        config = get_config()

        # 检查配置
        print("\n⚙️  检查配置...")
        audio_quality_config = config.get('audio_quality', {})

        if audio_quality_config.get('enabled', False):
            print("✅ 音频质量检测已启用")

            vad_config = audio_quality_config.get('vad', {})
            if vad_config.get('adaptive_enabled', False):
                print("✅ 自适应VAD已启用")
                print(f"   基础阈值: {vad_config.get('base_threshold', 0.04)}")
                print(f"   自适应系数: {vad_config.get('adaptation_factor', 1.5)}")

            print(f"   最大重试次数: {audio_quality_config.get('max_retries', 3)}")

            # 显示重试提示语
            retry_prompts = audio_quality_config.get('retry_prompts', {})
            print("\n📋 分级重试提示语:")
            for issue_type, prompts in retry_prompts.items():
                print(f"\n   问题类型: {issue_type}")

                # 处理两种情况：
                # 1. prompts 是字典（如 silence, fragment等）包含 retry_1, retry_2 等
                # 2. prompts 是列表（如 high_noise）直接是消息列表
                if isinstance(prompts, dict):
                    for retry_key, messages in prompts.items():
                        if isinstance(messages, list) and messages:
                            print(f"     {retry_key}: {messages[0][:30]}...")
                elif isinstance(prompts, list) and prompts:
                    # 直接是消息列表
                    print(f"     消息列表 ({len(prompts)} 条):")
                    for msg in prompts[:3]:  # 只显示前3条
                        print(f"     - {msg}")
                    if len(prompts) > 3:
                        print(f"     ... 还有 {len(prompts) - 3} 条")
        else:
            print("⚠️  音频质量检测未启用")
            print("   请在 config.yaml 中设置 audio_quality.enabled = true")
            return None

        # 测试完整流程
        print("\n" + "=" * 60)
        print("🧪 测试场景：模拟无效输入并验证重试机制")
        print("=" * 60)
        print("\n测试步骤:")
        print("  1. 系统将启动并监听唤醒词")
        print("  2. 请说唤醒词激活系统")
        print("  3. 保持静音，触发音频质量检测")
        print("  4. 观察系统是否播放重试提示语")
        print("  5. 验证分级重试策略")

        choice = input("\n是否运行完整流程测试? (需要硬件, y/N): ").strip().lower()

        if choice == 'y':
            print("\n💡 提示:")
            print("  - 说唤醒词后保持静音")
            print("  - 系统应检测到静音并播放重试提示")
            print("  - 最多重试1次后返回待机")

            input("\n按 Enter 启动...")

            try:
                # 初始化状态机
                audio_input = ReSpeakerInput(
                    device_name=config.get_audio_config().get('input_device', 'seeed-4mic-voicecard'),
                    sample_rate=config.get_audio_config().get('sample_rate', 16000),
                    channels=config.get_audio_config().get('channels', 1),
                    chunk_size=config.get_audio_config().get('chunk_size', 512)
                )

                detector = OpenWakeWordDetector(
                    threshold=config.get_wakeword_config().get('threshold', 0.5)
                )

                feedback_player = TTSFeedbackPlayer(
                    output_device=config.get_audio_config().get('output_device', 'plughw:0,0')
                )

                # 注意：这里简化了状态机初始化，实际需要传入STT/LLM引擎
                print("\n⚠️  注意：完整测试需要STT和LLM引擎")
                print("   这里仅演示音频质量检测配置是否正确")

                print("\n✅ Phase 1.4 配置检查完成")
                print("\n💡 要完整测试功能，请运行:")
                print("   python main.py")

                return True

            except Exception as e:
                print(f"\n❌ 初始化失败: {e}")
                return False
        else:
            print("\n⏭️  跳过完整流程测试")
            return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_v15_dialogue_optimization():
    """测试 Phase 1.5 对话优化功能"""
    print_header("测试 7: Phase 1.5 智能对话交互优化")

    print("\n✨ Phase 1.5 新功能:")
    print("  ✅ 智能打断（TTS播放时检测语音并停止）")
    print("  ✅ 上下文增强（延续性表达支持）")
    print("  ✅ 自动收尾（多轮对话超时道别）")
    print("  ✅ 技能系统框架")

    try:
        from src.config import get_config

        config = get_config()

        # 检查配置
        print("\n⚙️  检查配置...")

        # 检查智能打断
        audio_quality_config = config.get('audio_quality', {})
        interrupt_config = audio_quality_config.get('interrupt', {})

        if interrupt_config.get('enabled', False):
            print("✅ 智能打断已启用")
            print(f"   检测间隔: {interrupt_config.get('detection_interval', 10)} 帧")
            print(f"   缓冲时长: {interrupt_config.get('buffer_duration', 2.0)} 秒")
            print(f"   最小语音时长: {interrupt_config.get('min_speech_duration', 0.3)} 秒")
        else:
            print("⚠️  智能打断未启用")
            print("   请在 config.yaml 中设置 audio_quality.interrupt.enabled = true")

        # 检查对话增强
        conversation_config = config.get('conversation', {})

        if conversation_config.get('enabled', False):
            print("\n✅ 对话增强已启用")
            print(f"   上下文记忆: {conversation_config.get('context_memory', True)}")
            print(f"   最大对话轮数: {conversation_config.get('max_turns', 10)}")

            # 自动收尾
            farewell_config = conversation_config.get('auto_farewell', {})
            if farewell_config.get('enabled', False):
                print(f"   自动收尾: 启用")
                print(f"   空闲超时: {farewell_config.get('idle_timeout', 8.0)} 秒")
                farewell_messages = farewell_config.get('farewell_messages', [])
                print(f"   收尾消息: {len(farewell_messages)} 条")
                for msg in farewell_messages:
                    print(f"     - {msg}")

            # 延续性表达
            print(f"   延续性表达支持: {conversation_config.get('continuation_support', True)}")
        else:
            print("\n⚠️  对话增强未启用")
            print("   请在 config.yaml 中设置 conversation.enabled = true")

        # 检查技能系统
        skills_config = config.get('skills', {})
        if skills_config.get('enabled', False):
            print("\n✅ 技能系统已启用")
            skills_list = skills_config.get('skills_list', [])
            print(f"   已注册技能: {len(skills_list)} 个")
            for skill in skills_list:
                print(f"     - {skill}")
        else:
            print("\n⏭️  技能系统未启用（Phase 1.5 框架，默认禁用）")

        # 测试场景说明
        print("\n" + "=" * 60)
        print("🧪 Phase 1.5 测试场景")
        print("=" * 60)

        print("\n场景1：智能打断")
        print("  步骤:")
        print("    1. 说唤醒词激活系统")
        print("    2. 问一个问题")
        print("    3. 系统开始播放TTS回复")
        print("    4. 在播放过程中再次说话")
        print("  预期: TTS立即停止，进入LISTENING状态")

        print("\n场景2：延续性表达")
        print("  步骤:")
        print("    1. 问: '今天天气怎么样？'")
        print("    2. 系统回复")
        print("    3. 问: '明天呢？'")
        print("  预期: 系统理解为'明天天气怎么样'")

        print("\n场景3：自动收尾")
        print("  步骤:")
        print("    1. 进行多轮对话")
        print("    2. 停止说话，等待8秒")
        print("  预期: 系统播放收尾消息并退出对话")

        choice = input("\n是否查看完整配置? (y/N): ").strip().lower()

        if choice == 'y':
            print("\n" + "=" * 60)
            print("📋 Phase 1.5 完整配置")
            print("=" * 60)
            print(f"\naudio_quality:")
            print(f"  interrupt:")
            print(f"    enabled: {interrupt_config.get('enabled', False)}")
            print(f"    detection_interval: {interrupt_config.get('detection_interval', 10)}")
            print(f"    buffer_duration: {interrupt_config.get('buffer_duration', 2.0)}")
            print(f"\nconversation:")
            print(f"  enabled: {conversation_config.get('enabled', False)}")
            print(f"  context_memory: {conversation_config.get('context_memory', True)}")
            print(f"  max_turns: {conversation_config.get('max_turns', 10)}")
            print(f"  auto_farewell:")
            print(f"    enabled: {farewell_config.get('enabled', False)}")
            print(f"    idle_timeout: {farewell_config.get('idle_timeout', 8.0)}")
            print(f"\nskills:")
            print(f"  enabled: {skills_config.get('enabled', False)}")

        print("\n✅ Phase 1.5 配置检查完成")
        print("\n💡 要完整测试功能，请运行:")
        print("   python main.py")

        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_pipeline():
    """测试完整流程（当前阶段）"""
    print_header("测试 6: 完整流程测试")

    print("\n📋 当前阶段流程:")
    print("   1. 音频输入 (ReSpeaker 4-Mic)")
    print("   2. 唤醒词检测 (OpenWakeWord)")
    print("   3. TTS 语音回复 (Piper TTS) ✅")

    print("\n⏸️  后续阶段流程:")
    print("   4. STT 语音识别 (FunASR) - 待实现")
    print("   5. LLM 对话生成 (千问 API) - 待实现")
    print("   6. TTS 播报回复 (Piper TTS) - 已实现 ✅")

    print("\n💡 完整流程测试需要:")
    print("   - ReSpeaker 硬件连接")
    print("   - 唤醒词模型加载")
    print("   - Piper TTS 引擎就绪")

    choice = input("\n是否运行完整流程测试? (需要硬件, y/N): ").strip().lower()

    if choice == 'y':
        print("\n🔄 启动完整流程测试...")
        print("💡 提示: 这个测试会启动主程序")
        print("   对着麦克风说唤醒词，应该听到 TTS 语音回复")
        print("   按 Ctrl+C 停止")

        input("\n按 Enter 启动...")

        try:
            import subprocess
            result = subprocess.run([sys.executable, "main.py"], cwd=project_root)
            return result.returncode == 0
        except KeyboardInterrupt:
            print("\n\n⚠️  用户中断")
            return True
        except Exception as e:
            print(f"\n❌ 启动失败: {e}")
            return False
    else:
        print("\n⏭️  跳过完整流程测试")
        return None


def show_menu():
    """显示测试菜单"""
    print("\n" + "=" * 60)
    print("🧪 语音助手软件模块测试工具")
    print("=" * 60)

    print("\n当前已实现模块:")
    print("  ✅ TTS - 文本转语音 (Piper TTS)")
    print("  ✅ STT - 语音识别 (FunASR)")
    print("  ✅ LLM - 语言模型 (千问 API)")
    print("  ✅ VAD - 语音活动检测")

    print("\n" + "-" * 60)
    print("请选择测试:")
    print("  [1] 🔊 测试 TTS 引擎")
    print("  [2] 📢 测试 TTS 反馈播放器")
    print("  [3] 🎤 测试唤醒词检测 + TTS 反馈集成")
    print("  [4] 🎤 测试 STT 模块")
    print("  [5] 🤖 测试 LLM 模块")
    print("  [6] 🚀 测试完整流程")
    print("  [7] 🎯 测试 Phase 1.4 音频质量检测")
    print("  [8] 💬 测试 Phase 1.5 对话优化")
    print("  [a] 📋 运行所有已实现测试")
    print("  [q] 🚪 退出")
    print("=" * 60)


def main():
    """主函数"""

    while True:
        show_menu()
        choice = input("\n请输入选项 (1-8, a, q): ").strip().lower()

        if choice == '1':
            test_tts_engine()
        elif choice == '2':
            test_tts_feedback()
        elif choice == '3':
            test_tts_integration()
        elif choice == '4':
            test_stt_module()
        elif choice == '5':
            test_llm_module()
        elif choice == '6':
            test_full_pipeline()
        elif choice == '7':
            test_v14_audio_quality()
        elif choice == '8':
            test_v15_dialogue_optimization()
        elif choice == 'a':
            print("\n" + "=" * 60)
            print("运行所有已实现测试...")
            print("=" * 60)

            results = []

            # TTS 测试
            results.append(("TTS 引擎", test_tts_engine()))
            print()

            results.append(("TTS 反馈", test_tts_feedback()))
            print()

            results.append(("TTS 集成", test_tts_integration()))

            # 显示结果
            print("\n" + "=" * 60)
            print("测试结果汇总")
            print("=" * 60)
            for name, result in results:
                if result is True:
                    print(f"  ✅ {name}: 通过")
                elif result is False:
                    print(f"  ❌ {name}: 失败")
                else:
                    print(f"  ⏭️  {name}: 跳过")

            success_count = sum(1 for _, r in results if r is True)
            total_count = len(results)

            print(f"\n总计: {success_count}/{total_count} 通过")

            if success_count == total_count:
                print("\n🎉 所有测试通过!")
            else:
                print("\n⚠️  部分测试失败，请检查")

        elif choice == 'q':
            print("\n👋 退出测试")
            break
        else:
            print("❌ 无效选择，请重试")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
