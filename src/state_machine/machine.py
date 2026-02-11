"""
状态机实现
State Machine Implementation for Voice Assistant

Phase 1.3: 添加对话生成功能（千问 API + TTS 播放）
Phase 1.4: 添加智能语音质量检测与交互优化
  - 自适应 VAD 阈值
  - 音频质量检测
  - 文本质量检测
  - 分级重试策略
  - 智能尾端点检测
Phase 1.5: 智能对话交互优化
  - 智能打断（TTS 播放时检测语音）
  - 上下文增强
  - 技能系统框架
Phase 1.7: 闹钟功能
  - 自然语言时间解析
  - 闹钟持久化存储
  - 闹钟触发和响铃
"""
import logging
import random
import time
import numpy as np
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime, time as datetime_time
from collections import deque

from .states import State
from ..audio.microphone import MicrophoneInput
from ..wake_word.detector import WakeWordDetector
from ..feedback.player import FeedbackPlayer
# P1-1 优化: 导入音频处理工具函数
from ..utils.audio_utils import calculate_rms_energy
# P1-2 优化: 导入自定义异常类
from ..exceptions import (
    AudioError,
    AudioQualityError,
    ModelNotReadyError,
    STTError,
    TTSError,
    LLMError,
    StateMachineError
)
# P2-2 优化: 导入资源管理器
from ..utils.resource_manager import get_resource_manager
# P2-4 优化: 导入性能监控器
from ..utils.performance_monitor import get_performance_monitor, Timer
# P2-5 优化: 导入状态转换优化器
from ..utils.state_optimizer import get_transition_optimizer

# Phase 1.5: 技能系统
try:
    from ..skills import SkillManager
    SKILLS_AVAILABLE = True
except ImportError:
    SKILLS_AVAILABLE = False
    SkillManager = None

logger = logging.getLogger(__name__)

# P2-3 优化: 缓存常用字符串常量，避免重复创建
SEPARATOR_LINE = "=" * 60
DIVIDER_LINE = "-" * 40
STATE_SEPARATOR = "=" * 60


class AdaptiveVAD:
    """自适应 VAD 阈值管理器 (Phase 1.4)"""

    def __init__(self, config: dict):
        """
        初始化自适应 VAD

        Args:
            config: 配置字典
        """
        self._base_threshold = config.get("base_threshold", 0.04)
        self._noise_samples = []  # 存储环境噪音样本
        self._max_samples = config.get("noise_window_size", 100)
        self._adaptation_factor = config.get("adaptation_factor", 1.5)
        self._reset_interval = config.get("reset_interval", 300)
        self._last_reset_time = time.time()

        logger.info(f"AdaptiveVAD 初始化: base_threshold={self._base_threshold}, "
                   f"adaptation_factor={self._adaptation_factor}")

    def update_noise_floor(self, audio_chunk: np.ndarray) -> float:
        """
        更新环境底噪估计

        Args:
            audio_chunk: 音频块（静音期间采集）

        Returns:
            float: 当前估计的底噪能量
        """
        # P1-1 优化: 使用公共函数计算 RMS 能量
        energy = calculate_rms_energy(audio_chunk)

        # 更新底噪样本
        self._noise_samples.append(energy)
        if len(self._noise_samples) > self._max_samples:
            self._noise_samples.pop(0)

        # 定期重置底噪估计
        if time.time() - self._last_reset_time > self._reset_interval:
            self._noise_samples = []
            self._last_reset_time = time.time()
            logger.info("AdaptiveVAD: 重置底噪估计")

        # 计算底噪平均值
        noise_floor = np.mean(self._noise_samples) if self._noise_samples else 0
        return noise_floor

    def get_adaptive_threshold(self) -> float:
        """
        获取自适应阈值

        Returns:
            float: 动态调整后的阈值
        """
        if not self._noise_samples:
            return self._base_threshold

        noise_floor = np.mean(self._noise_samples)
        # 阈值 = 底噪 × 自适应系数
        adaptive_threshold = max(self._base_threshold, noise_floor * self._adaptation_factor)
        return adaptive_threshold

    def reset(self) -> None:
        """重置底噪估计（用于环境变化时）"""
        self._noise_samples = []
        self._last_reset_time = time.time()
        logger.info("AdaptiveVAD: 底噪估计已重置")

    def get_noise_floor(self) -> float:
        """获取当前底噪估计"""
        return np.mean(self._noise_samples) if self._noise_samples else 0.0


class StateMachine:
    """语音助手状态机 (Phase 1.5 - 智能对话交互优化)"""

    def __init__(
        self,
        audio_input: MicrophoneInput,
        detector: WakeWordDetector,
        feedback_player: FeedbackPlayer,
        stt_engine: Optional['Any'] = None,
        vad_detector: Optional['Any'] = None,
        llm_engine: Optional['Any'] = None,
        tts_engine: Optional['Any'] = None,
        max_listening_duration: float = 10.0,
        silence_threshold: float = 1.5,
        wake_words: Optional[list[str]] = None,
        wake_reply_messages: Optional[list[str]] = None,
        config: Optional[dict] = None
    ):
        """
        初始化状态机

        Args:
            audio_input: 音频输入
            detector: 唤醒词检测器
            feedback_player: 反馈播放器
            stt_engine: STT 引擎 (Phase 1.2)
            vad_detector: VAD 检测器 (Phase 1.2)
            llm_engine: LLM 引擎 (Phase 1.3)
            tts_engine: TTS 引擎 (Phase 1.3)
            max_listening_duration: 最大录音时长（秒）
            silence_threshold: 静音阈值（秒）
            wake_words: 唤醒词列表（用于回声检测）
            wake_reply_messages: 唤醒回复消息列表（用于回声检测）
            config: 配置字典 (Phase 1.4)
        """
        self._current_state: State = State.IDLE
        self._audio_input = audio_input
        self._detector = detector
        self._feedback_player = feedback_player

        # Phase 1.2 新增
        self._stt_engine = stt_engine
        self._vad_detector = vad_detector
        self._max_listening_duration = max_listening_duration
        self._silence_threshold = silence_threshold

        # Phase 1.3 新增
        self._llm_engine = llm_engine
        self._tts_engine = tts_engine

        # Phase 1.4 新增：配置
        self._config = config or {}

        # P2-2 优化: 初始化资源管理器
        self._resource_manager = get_resource_manager()
        # 注意：不注册 state_machine 为可清理资源
        # 状态机是长期运行的核心组件，不应该被自动清理

        # P2-4 优化: 初始化性能监控器
        self._perf_monitor = get_performance_monitor(enabled=True)

        # P2-5 优化: 初始化状态转换优化器
        self._transition_optimizer = get_transition_optimizer()

        # 录音相关
        # P0-2 优化: 使用环形缓冲区，自动清理旧数据，防止内存无限增长
        # 最大长度 400 帧 ≈ 13 秒 @ 16kHz (每帧 512 样本)
        # 确保即使录音时间过长，内存占用也可控
        self._recorded_audio: deque = deque(maxlen=400)
        self._last_speech_time: Optional[float] = None

        # 多轮对话模式
        self._in_conversation = False  # 是否在多轮对话中
        self._conversation_turn_count = 0  # 当前对话轮数
        self._max_conversation_idle = 8.0  # 多轮对话最大空闲时间（秒）

        # TTS 播放完成时间戳（用于计算停顿）
        self._tts_playback_end_time: Optional[float] = None

        # Phase 1.7: 闹钟响铃标志（用于在闹钟响铃时直接识别语音）
        self._alarm_ringing = False

        # Phase 1.8: 音乐播放状态标志
        self._music_playing = False  # 音乐是否正在播放
        self._music_control_mode = False  # 是否在音乐控制模式
        self._music_control_keywords = [
            "停止", "关闭", "停下",
            "大声", "大声点", "声音大", "调大",
            "小声", "小声点", "声音小", "调小",
            "下一首", "换一个", "切歌", "换个",
            "暂停", "停一下", "继续", "恢复"
        ]

        # Phase 1.8: 音乐播放器
        music_config = self._config.get("music", {})
        if music_config.get("enabled", False):
            try:
                from ..music import MusicPlayer

                library_config = music_config.get("library", {})
                player_config = music_config.get("player", {})

                self._music_player = MusicPlayer(
                    music_dir=library_config.get("path", "./assets/music"),
                    output_device=player_config.get("output_device", "plughw:0,0"),
                    initial_volume=player_config.get("initial_volume", 0.7)
                )
                logger.info("✓ 音乐播放器已启用")
            except ImportError as e:
                logger.warning(f"音乐模块导入失败: {e}")
                self._music_player = None
            except Exception as e:
                logger.error(f"音乐播放器初始化失败: {e}")
                self._music_player = None
        else:
            self._music_player = None
            logger.info("音乐播放功能未启用")

        # Phase 1.4 新增：自适应 VAD
        audio_quality_config = self._config.get("audio_quality", {})
        vad_config = audio_quality_config.get("vad", {})
        if vad_config.get("adaptive_enabled", False):
            self._adaptive_vad = AdaptiveVAD(vad_config)
            logger.info("✓ 自适应 VAD 已启用")
        else:
            self._adaptive_vad = None

        # Phase 1.4 新增：重试计数器
        self._retry_count = 0

        # Phase 1.5 新增：智能打断
        interrupt_config = audio_quality_config.get("interrupt", {})
        self._interrupt_enabled = interrupt_config.get("enabled", False)
        self._interrupt_detection_interval = interrupt_config.get("detection_interval", 10)  # 帧数
        self._interrupt_buffer_duration = interrupt_config.get("buffer_duration", 2.0)  # 秒
        self._interrupt_check_counter = 0  # 检测计数器
        self._interrupt_buffer = []  # 打断缓冲音频

        if self._interrupt_enabled:
            logger.info(f"✓ 智能打断已启用 (检测间隔: {self._interrupt_detection_interval} 帧)")

        # Phase 1.5 新增：上下文增强配置
        conversation_config = self._config.get("conversation", {})
        self._context_memory_enabled = conversation_config.get("context_memory", True)
        self._auto_farewell_enabled = conversation_config.get("auto_farewell", {}).get("enabled", True)
        self._farewell_idle_timeout = conversation_config.get("auto_farewell", {}).get("idle_timeout", 8.0)
        self._farewell_messages = conversation_config.get("auto_farewell", {}).get("farewell_messages", [])

        if self._context_memory_enabled:
            logger.info("✓ 上下文记忆已启用")
        if self._auto_farewell_enabled:
            logger.info(f"✓ 自动收尾已启用 (超时: {self._farewell_idle_timeout}s)")

        # Phase 1.5 新增：技能系统
        skills_config = self._config.get("skills", {})
        if skills_config.get("enabled", False) and SKILLS_AVAILABLE:
            self._skill_manager = SkillManager(skills_config)
            logger.info("✓ 技能系统已启用")
        else:
            self._skill_manager = None
            logger.info("技能系统未启用")

        # Phase 1.7 新增：闹钟管理器
        alarm_config = self._config.get("alarm", {})
        if alarm_config.get("enabled", False):
            try:
                from ..alarm import AlarmManager
                from ..alarm.alarm_storage import Alarm

                # 初始化闹钟管理器
                storage_config = alarm_config.get("storage", {})
                check_config = alarm_config.get("check", {})

                self._alarm_manager = AlarmManager(
                    storage=None,  # 使用默认存储
                    ringtone_callback=self._on_alarm_triggered,
                    check_interval=check_config.get("interval", 1.0)
                )

                # 启动后台检查线程
                self._alarm_manager.start_background_check()

                logger.info("✓ 闹钟管理器已启用")
            except ImportError as e:
                logger.warning(f"闹钟模块导入失败: {e}")
                self._alarm_manager = None
            except Exception as e:
                logger.error(f"闹钟管理器初始化失败: {e}")
                self._alarm_manager = None
        else:
            self._alarm_manager = None
            logger.info("闹钟功能未启用")

        # 智能开关管理器 - GeekOpen 云 MQTT 开关控制
        switch_config = self._config.get("smart_switch", {})
        logger.info(f"智能开关配置: enabled={switch_config.get('enabled', False)}")

        if switch_config.get("enabled", False):
            try:
                from ..smart_switch import MQTTClient, GeekOpenController, SwitchKey
                from ..smart_switch.mqtt_client import create_mqtt_client_from_config

                logger.info("正在初始化智能开关模块...")

                # 初始化 MQTT 客户端
                mqtt_config = switch_config.get("mqtt", {})
                logger.info(f"MQTT 配置: broker={mqtt_config.get('broker')}, port={mqtt_config.get('port')}")

                self._mqtt_client = create_mqtt_client_from_config(mqtt_config)

                # 连接 MQTT Broker
                logger.info("正在连接 MQTT Broker...")
                if self._mqtt_client.connect():
                    logger.info("✓ MQTT 连接成功")

                    # 初始化 GeekOpen 开关控制器
                    self._switch_controller = GeekOpenController(self._mqtt_client)

                    # 注册设备
                    devices = switch_config.get("devices", [])
                    protocol = switch_config.get("protocol", "geekopen")
                    prefix = switch_config.get("prefix", "bKFSKE")
                    uid = switch_config.get("uid", "qNACgJaGGlTG")

                    logger.info(f"准备注册 {len(devices)} 个设备...")
                    for dev in devices:
                        self._switch_controller.register_device(
                            mac=dev.get("mac", ""),
                            name=dev.get("name", ""),
                            location=dev.get("location", ""),
                            key_count=dev.get("key_count", 2),
                            prefix=prefix,
                            uid=uid,
                            key_mapping=dev.get("key_mapping")
                        )

                    logger.info(f"✓ GeekOpen 智能开关管理器已启用 (已注册 {len(devices)} 个设备)")
                else:
                    logger.error("MQTT 连接失败，智能开关功能未启用")
                    self._switch_controller = None
                    self._mqtt_client = None

            except ImportError as e:
                logger.warning(f"智能开关模块导入失败: {e}")
                logger.warning("请检查是否安装了 paho-mqtt: pip install paho-mqtt")
                self._switch_controller = None
                self._mqtt_client = None
            except Exception as e:
                logger.error(f"智能开关管理器初始化失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
                self._switch_controller = None
                self._mqtt_client = None
        else:
            self._switch_controller = None
            self._mqtt_client = None
            logger.info("智能开关功能未启用 (config.yaml 中 smart_switch.enabled=false)")

        # 回声检测词汇表
        self._echo_detection_words = []

        # 添加唤醒词
        if wake_words:
            self._echo_detection_words.extend(wake_words)
        else:
            # 默认唤醒词
            self._echo_detection_words.extend(["胡桃", "alexa", "小爱", "siri", "天猫精灵"])

        # 添加唤醒回复消息
        if wake_reply_messages:
            self._echo_detection_words.extend(wake_reply_messages)
        else:
            # 默认回复消息（与配置文件一致）
            self._echo_detection_words.extend(["我在", "请吩咐", "我在听", "您好", "我在这里"])

        logger.info(f"回声检测词汇表: {self._echo_detection_words}")

        # 🔧 唤醒词检测控制标志（借鉴小爱同学等商业产品的做法）
        # 检测到唤醒词后立即禁用检测，对话完成后延迟重新启用
        self._wakeword_detection_enabled = True  # 是否启用唤醒词检测
        self._wakeword_resume_time: Optional[float] = None  # 恢复检测的时间戳

        # Phase 1.7: 夜间静默时段（防止被唤醒）
        quiet_hours_config = self._config.get("quiet_hours", {})
        if quiet_hours_config.get("enabled", False):
            try:
                start_str = quiet_hours_config.get("start", "23:00")
                end_str = quiet_hours_config.get("end", "06:00")
                start_hour, start_minute = map(int, start_str.split(":"))
                end_hour, end_minute = map(int, end_str.split(":"))
                self._quiet_hours = (datetime_time(start_hour, start_minute),
                                    datetime_time(end_hour, end_minute))
                logger.info(f"✓ 夜间静默时段已启用: {start_str} - {end_str}")
            except Exception as e:
                logger.warning(f"静默时段配置解析失败: {e}")
                self._quiet_hours = None
        else:
            self._quiet_hours = None

        self._running = False
        self._state_start_time: Optional[float] = None

        logger.info("状态机初始化完成 (Phase 1.5 - 智能对话交互优化)")

    @property
    def current_state(self) -> State:
        """当前状态"""
        return self._current_state

    def transition_to(self, new_state: State) -> None:
        """
        状态转换

        P2-5 优化: 使用状态转换优化器验证和执行转换

        Args:
            new_state: 新状态
        """
        if self._current_state == new_state:
            return

        old_state = self._current_state

        # P2-5 优化: 使用状态转换优化器
        if not self._transition_optimizer.is_allowed(old_state.name, new_state.name):
            logger.error(f"❌ 不允许的状态转换: {old_state} → {new_state}")
            return

        # 执行转换
        self._current_state = new_state
        self._state_start_time = time.time()

        logger.info(f"状态转换: {old_state} → {new_state}")

        # 状态进入处理
        self._on_state_enter(new_state)

    def _on_state_enter(self, state: State) -> None:
        """
        状态进入处理

        Args:
            state: 进入的状态
        """
        if state == State.WAKEUP:
            # 第一次唤醒：播放反馈并进入对话模式
            logger.info("播放唤醒反馈...")
            self._feedback_player.play_wake_feedback()

        elif state == State.LISTENING:
            # 🔧 关键优化：清空音频输入缓冲区，丢弃积累的数据
            # 在 IDLE 状态期间可能积累了音频帧，需要清空避免误触发
            logger.info("🧹 清空音频输入缓冲区...")
            clear_count = 0
            while True:
                try:
                    frame = self._audio_input.read()
                    if frame is None:
                        break
                    clear_count += 1
                    if clear_count >= 50:  # 最多清空 50 帧，避免阻塞
                        break
                except:
                    break
            if clear_count > 0:
                logger.info(f"✅ 已清空 {clear_count} 帧音频数据")

            # **重要：添加额外的停顿，让TTS回声完全消散**
            # 特别是多轮对话时，上一轮的TTS回声可能还没完全消散
            if self._in_conversation and self._conversation_turn_count > 1:
                pause_duration = 0.5  # 额外停顿0.5秒
                logger.info(f"⏸️ 多轮对话：额外停顿 {pause_duration}s 让回声消散")
                time.sleep(pause_duration)

            # 开始录音
            if self._in_conversation:
                logger.info(f"开始录音（多轮对话 第{self._conversation_turn_count}轮）...")
            else:
                logger.info("开始录音（首次对话）...")

            # P0-2 优化: 清空环形缓冲区
            self._recorded_audio.clear()
            self._last_speech_time = None

            # 重置语音帧计数器
            if hasattr(self, '_speech_frame_count'):
                self._speech_frame_count = 0

        elif state == State.PROCESSING:
            # 处理录音：STT 识别 + LLM 生成
            logger.info("开始处理用户输入...")
            self._process_user_input()

        elif state == State.SPEAKING:
            # TTS 播放在 _process_user_input 中已经开始
            # 此状态仅用于等待播放完成
            if self._in_conversation:
                logger.info(f"等待 TTS 播放完成（第{self._conversation_turn_count}轮）...")
            else:
                logger.info("等待 TTS 播放完成（首次对话）...")

        elif state == State.IDLE:
            # 退出多轮对话模式
            if self._in_conversation:
                logger.info("退出多轮对话模式")
                self._in_conversation = False
                self._conversation_turn_count = 0

            # 退出音乐控制模式
            if hasattr(self, '_music_control_mode') and self._music_control_mode:
                logger.info("退出音乐控制模式")
                self._music_control_mode = False

            # 🔧 延迟恢复唤醒词检测（借鉴小爱同学等商业产品的做法）
            # 等待 1.5 秒让音频稳定，避免 TTS 回声或残留音频触发误检测
            resume_delay = 1.5  # 秒
            self._wakeword_resume_time = time.time() + resume_delay
            logger.info(f"⏰ 唤醒词检测将在 {resume_delay} 秒后恢复")

    def start(self) -> None:
        """启动状态机"""
        if self._running:
            logger.warning("状态机已在运行")
            return

        self._running = True
        self._current_state = State.IDLE
        self._state_start_time = time.time()

        logger.info("状态机启动")

    def stop(self) -> None:
        """停止状态机"""
        self._running = False

        # 停止闹钟后台检查线程
        if self._alarm_manager:
            self._alarm_manager.stop_background_check()

        # P2-2 优化: 清理资源
        self._cleanup_resources()

        logger.info("状态机停止")

    def _cleanup_resources(self) -> None:
        """P2-2 优化: 清理状态机资源"""
        try:
            # 清理录音缓冲区
            if hasattr(self, '_recorded_audio'):
                self._recorded_audio.clear()

            # 清理打断缓冲区
            if hasattr(self, '_interrupt_buffer'):
                self._interrupt_buffer = []

            # 停止播放器
            if self._feedback_player:
                self._feedback_player.stop()

            # 断开 MQTT 连接
            if hasattr(self, '_mqtt_client') and self._mqtt_client:
                self._mqtt_client.disconnect()
                logger.info("MQTT 已断开连接")

            logger.info("🧹 状态机资源已清理")
        except Exception as e:
            logger.error(f"清理资源时出错: {e}")

    def update(self) -> None:
        """
        更新状态机（在主循环中调用）
        """
        if not self._running:
            return

        # Phase 1.7: 优先检查闹钟（在任何状态都可能触发）
        if self._alarm_manager:
            self._alarm_manager.check_and_trigger()

        # 根据当前状态执行相应逻辑
        if self._current_state == State.IDLE:
            self._update_idle()
        elif self._current_state == State.WAKEUP:
            self._update_wakeup()
        elif self._current_state == State.LISTENING:
            self._update_listening()
        elif self._current_state == State.PROCESSING:
            # PROCESSING 状态在 _on_state_enter 中同步处理
            pass
        elif self._current_state == State.SPEAKING:
            self._update_speaking()
        elif self._current_state == State.ERROR:
            self._update_error()

    def _update_idle(self) -> None:
        """
        IDLE 状态更新：监听唤醒词

        P0-4 优化: 批量处理音频帧，减少函数调用开销
        每次处理多帧（默认3帧 ≈ 100ms），降低 CPU 占用
        """
        # P0-4 优化: 批量处理多帧，减少 read_chunk() 调用开销
        frames_to_process = 3  # 约 100ms @ 16kHz (每帧 32ms)

        for frame_idx in range(frames_to_process):
            try:
                # 读取音频帧
                audio_frame = self._audio_input.read_chunk()

                # 第一帧才需要更新音乐播放状态（避免重复检查）
                if frame_idx == 0:
                    if self._music_player:
                        self._music_playing = self._music_player.is_playing()

                    # Phase 1.7: 检查闹钟是否在响铃
                    # 如果闹钟正在响铃，跳过静默时段检查，但仍需要唤醒词
                    if self._alarm_ringing:
                        # 检查闹钟是否仍在播放（可能已自动停止）
                        if not self._feedback_player.is_alarm_playing():
                            logger.info("✅ 闹钟铃声已自动停止")
                            self._alarm_ringing = False
                        else:
                            # 每10秒记录一次，避免日志刷屏
                            if int(time.time()) % 10 == 0:
                                logger.info("🔔 闹钟响铃中，可以说'胡桃，停止'")
                        # 跳过静默时段检查，继续进行正常的唤醒词检测
                    else:
                        # Phase 1.7: 检查是否在静默时段（夜间免打扰）
                        if self._quiet_hours and self._is_in_quiet_hours():
                            # 静默时段内，跳过唤醒词检测
                            # 每10分钟记录一次日志（INFO 级别）
                            current_time = time.time()
                            if not hasattr(self, '_last_quiet_log_time'):
                                self._last_quiet_log_time = 0

                            if current_time - self._last_quiet_log_time >= 600:
                                now = datetime.now()
                                logger.info(f"🌙 静默时段中，暂停唤醒词检测 ({now.strftime('%H:%M')})")
                                self._last_quiet_log_time = current_time
                            return  # 跳过本次批量处理

                        # 🔧 检查唤醒词检测是否启用（借鉴小爱同学等商业产品的做法）
                        # 在对话流程中禁用检测，避免误触发
                        if not self._wakeword_detection_enabled:
                            # 检查是否到了恢复检测的时间
                            if self._wakeword_resume_time and time.time() >= self._wakeword_resume_time:
                                # 🔧 关键：恢复前先清空检测器内部缓冲区
                                logger.info("🧹 清空检测器内部缓冲区...")
                                silence_frame = np.zeros(512, dtype=np.int16)
                                clear_frames = 100  # 约 3.2 秒 @ 16kHz

                                # 临时禁用日志
                                wakeword_logger = logging.getLogger('src.wake_word.openwakeword_detector')
                                old_level = wakeword_logger.level
                                wakeword_logger.setLevel(logging.ERROR)

                                try:
                                    for _ in range(clear_frames):
                                        self._detector.process_frame(silence_frame)
                                finally:
                                    wakeword_logger.setLevel(old_level)

                                # 恢复检测
                                self._wakeword_detection_enabled = True
                                self._wakeword_resume_time = None
                                logger.info("✅ 唤醒词检测已恢复")
                            else:
                                # 还未到恢复时间，跳过检测
                                return  # 跳过本次批量处理

                    # Phase 1.8: 音乐播放时，提高检测灵敏度
                    # 临时调整阈值（如果检测器支持）
                    if self._music_playing:
                        # 音乐播放时，每30秒记录一次状态
                        if int(time.time()) % 30 == 0:
                            logger.info("🎵 音乐播放中，等待控制指令（唤醒词检测启用）")

                # Phase 1.4: 更新自适应 VAD 底噪估计（每帧更新）
                if self._adaptive_vad:
                    noise_floor = self._adaptive_vad.update_noise_floor(audio_frame)
                    # P1-4 优化: 每 5 秒记录一次底噪水平（只在第一帧检查），添加级别检查
                    if frame_idx == 0 and int(time.time()) % 5 == 0 and len(audio_frame) > 0 and logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"环境底噪: {noise_floor:.4f}, 阈值: {self._adaptive_vad.get_adaptive_threshold():.4f}")

                # 🔧 优化：移除启动缓冲期逻辑
                # 缓冲区已在检测到唤醒词时清空，无需启动缓冲期

                # 检测唤醒词（每帧都需要检测）
                detected = self._detector.process_frame(audio_frame)
                if detected:
                    # 🔧 立即禁用唤醒词检测（借鉴小爱同学等商业产品的做法）
                    # 避免在对话流程中误触发
                    self._wakeword_detection_enabled = False
                    logger.info("🔇 唤醒词检测已禁用（对话流程中）")

                    # Phase 1.8: 如果音乐正在播放，使用音乐控制模式
                    if self._music_playing:
                        logger.info("🎵 音乐播放中检测到唤醒词，进入音乐控制模式")
                        self._handle_music_control()
                    else:
                        # 正常唤醒流程
                        logger.info(SEPARATOR_LINE)
                        logger.info("🎤 检测到唤醒词！")
                        logger.info(SEPARATOR_LINE)

                        # 进入对话模式
                        self._in_conversation = True
                        self._conversation_turn_count = 1
                        # Phase 1.4: 重置重试计数器
                        self._retry_count = 0

                        self.transition_to(State.WAKEUP)
                        break  # 检测到唤醒词，停止批量处理

            except Exception as e:
                logger.error(f"IDLE 状态更新失败（第{frame_idx+1}帧）: {e}")
                if frame_idx == 0:  # 只在第一帧出错时转换到 ERROR 状态
                    self.transition_to(State.ERROR)
                break  # 出错后停止批量处理

    def _update_wakeup(self) -> None:
        """
        WAKEUP 状态更新
        播放唤醒反馈后转换到 LISTENING
        """
        # 检查反馈播放是否完成
        if not self._feedback_player.is_playing():
            # 播放完成，进入 LISTENING 状态
            logger.info("✅ 唤醒反馈播放完成")
            logger.info("🎧 开始监听用户语音...")
            self.transition_to(State.LISTENING)

    def _update_listening(self) -> None:
        """
        LISTENING 状态更新：VAD 录音

        使用音频能量检测用户语音活动，自动判断录音开始和结束
        Phase 1.4: 集成自适应 VAD 阈值和智能尾端点检测
        """
        try:
            # 读取音频帧
            audio_frame = self._audio_input.read_chunk()

            # 记录音频
            self._recorded_audio.append(audio_frame)

            # P1-1 优化: 使用公共函数计算 RMS 能量
            # 使用音频能量检测语音活动（实时检测）
            rms_energy = calculate_rms_energy(audio_frame)

            # Phase 1.4: 使用自适应 VAD 阈值
            config = self._config.get("audio_quality", {})
            if self._adaptive_vad:
                energy_threshold = self._adaptive_vad.get_adaptive_threshold()
            else:
                energy_threshold = 0.04  # 默认阈值

            # Phase 1.4: 最小有效语音时长（过滤瞬态噪音）
            min_speech_duration = config.get("min_speech_duration", 0.3)

            # 连续帧检测，避免瞬态噪音触发
            if not hasattr(self, '_speech_frame_count'):
                self._speech_frame_count = 0
            if not hasattr(self, '_speech_start_time'):
                self._speech_start_time = None

            if rms_energy > energy_threshold:
                self._speech_frame_count += 1
                # 记录语音开始时间
                if self._speech_frame_count == 1:
                    self._speech_start_time = time.time()
            else:
                # 检查是否满足最小语音时长
                if self._speech_start_time is not None:
                    speech_duration = time.time() - self._speech_start_time
                    if speech_duration >= min_speech_duration:
                        # 满足最小语音时长，记录为有效语音
                        if self._last_speech_time is None:
                            logger.info(f"检测到有效语音开始 (能量: {rms_energy:.4f}, 时长: {speech_duration:.2f}s)")
                        self._last_speech_time = time.time()

                # 重置计数器
                self._speech_frame_count = 0
                self._speech_start_time = None

            # 需要连续 3 帧（约 100ms）超过阈值才认为是语音
            min_speech_frames = 3

            if self._speech_frame_count >= min_speech_frames and self._last_speech_time is None:
                # 检测到语音（但不一定是有效语音，还需检查时长）
                self._last_speech_time = time.time()

            # 检查录音结束条件
            current_time = time.time()
            state_duration = self.get_state_duration()

            # 条件1: 超过最大录音时长
            if state_duration >= self._max_listening_duration:
                logger.info(f"录音达到最大时长 ({self._max_listening_duration}s)")
                self.transition_to(State.PROCESSING)

            # 条件2: 检测到语音后静音超过阈值
            elif self._last_speech_time is not None:
                # Phase 1.4: 使用智能尾端点阈值（比基础超时更长）
                smart_silence_threshold = config.get("smart_silence_threshold", 2.0)
                silence_duration = current_time - self._last_speech_time
                if silence_duration >= smart_silence_threshold:
                    logger.info(f"检测到静音 ({silence_duration:.1f}s)")
                    self.transition_to(State.PROCESSING)

            # 条件3: 多轮对话模式 - 检测是否应该退出对话
            elif self._in_conversation and self._conversation_turn_count > 1:
                # Phase 1.5: 使用配置的空闲超时时间
                idle_timeout = self._farewell_idle_timeout if self._auto_farewell_enabled else self._max_conversation_idle

                if state_duration >= idle_timeout and self._last_speech_time is None:
                    # 多轮对话超时
                    if self._auto_farewell_enabled and self._farewell_messages:
                        # 播放自动收尾消息
                        logger.info(f"多轮对话超时 ({idle_timeout}s)，播放收尾消息")
                        farewell_message = random.choice(self._farewell_messages)
                        print(f"\n👋 {farewell_message}\n")

                        # 播放 TTS 收尾消息
                        self._play_tts_prompt(farewell_message)

                        # P0-3 优化: 等待播放完成，期间检查闹钟
                        while self._feedback_player.is_playing():
                            time.sleep(0.01)
                            # 优化：在播放期间仍然检查闹钟
                            if self._alarm_manager:
                                self._alarm_manager.check_and_trigger()

                    # 返回 IDLE
                    logger.info("多轮对话结束，返回待机模式")
                    print(f"\n🔚 对话结束，返回待机模式\n")
                    self._in_conversation = False
                    self._conversation_turn_count = 0
                    # Phase 1.4: 重置重试计数器
                    self._retry_count = 0

                    # Phase 1.5: 重置 LLM 对话历史
                    if self._llm_engine and hasattr(self._llm_engine, 'reset_conversation'):
                        self._llm_engine.reset_conversation()
                        logger.info("LLM 对话历史已重置")

                    # 🔧 优化：移除冷却期，允许立即再次唤醒
                    # 缓冲区已在检测到唤醒词时清空，无需冷却期

                    self.transition_to(State.IDLE)

        except Exception as e:
            logger.error(f"LISTENING 状态更新失败: {e}")
            self.transition_to(State.ERROR)

    def _update_error(self) -> None:
        """ERROR 状态更新"""
        # 等待一段时间后返回 IDLE
        if self.get_state_duration() > 1.0:
            self.transition_to(State.IDLE)

    def _update_speaking(self) -> None:
        """
        SPEAKING 状态更新：播放 TTS 回复

        Phase 1.5: 添加智能打断功能 - 在播放过程中检测语音活动
        """
        # Phase 1.5: 检测打断（在播放过程中）
        if self._feedback_player.is_playing() and self._interrupt_enabled:
            # 每隔 N 帧检测一次语音活动
            self._interrupt_check_counter += 1

            if self._interrupt_check_counter >= self._interrupt_detection_interval:
                self._interrupt_check_counter = 0

                # 快速检测是否有语音输入
                try:
                    audio_frame = self._audio_input.read_chunk()
                    has_speech = self._quick_speech_detection(audio_frame)

                    if has_speech:
                        # 检测到语音，停止播放
                        logger.info("🛑 检测到用户语音，停止 TTS 播放")
                        print(f"\n🛑 检测到打断，停止播放\n")

                        # 停止 TTS 播放
                        self._feedback_player.stop()

                        # 录制用户在打断时的语音（缓冲）
                        self._record_interrupt_audio(audio_frame)

                        # 进入 LISTENING 状态，等待完整输入
                        self.transition_to(State.LISTENING)
                        return
                except Exception as e:
                    logger.error(f"打断检测失败: {e}")

        # 检查 TTS 播放是否完成
        if not self._feedback_player.is_playing():
            # 记录播放完成时间戳（只记录一次）
            if self._tts_playback_end_time is None:
                self._tts_playback_end_time = time.time()
                logger.info("✅ TTS 播放完成")

            # **添加停顿时间，让回声消散**
            pause_duration = 1.5  # 停顿时间（秒）- 增加到1.5秒让回声完全消散

            # 计算从播放完成到现在的时间
            time_since_playback_end = time.time() - self._tts_playback_end_time

            # 检查是否已经停顿足够时间
            if time_since_playback_end < pause_duration:
                # 还在停顿中，等待
                return

            # 停顿完成
            logger.info(f"⏸️ 停顿完成 ({pause_duration}s)")

            if self._in_conversation:
                # 多轮对话模式：继续下一轮
                self._conversation_turn_count += 1
                logger.info(SEPARATOR_LINE)
                logger.info(f"🔄 进入第 {self._conversation_turn_count} 轮对话")
                logger.info(SEPARATOR_LINE)

                # 清除播放完成时间戳
                self._tts_playback_end_time = None

                # 进入 LISTENING，不播放唤醒反馈
                self.transition_to(State.LISTENING)
            else:
                # 单次对话：返回 IDLE
                logger.info(SEPARATOR_LINE)
                logger.info("🔄 返回 IDLE 状态，等待下一次唤醒")
                logger.info(SEPARATOR_LINE)

                # 清除播放完成时间戳
                self._tts_playback_end_time = None

                self.transition_to(State.IDLE)

    # ============================================================
    # Phase 1.5: 智能打断方法
    # ============================================================

    def _quick_speech_detection(self, audio_frame: np.ndarray) -> bool:
        """
        快速语音检测（用于打断检测）

        Args:
            audio_frame: 音频帧

        Returns:
            bool: 是否检测到语音
        """
        # 使用自适应 VAD 阈值
        if self._adaptive_vad:
            threshold = self._adaptive_vad.get_adaptive_threshold()
        else:
            threshold = 0.04  # 默认阈值

        # P1-1 优化: 使用公共函数计算 RMS 能量
        energy = calculate_rms_energy(audio_frame)

        # 简单判断：能量超过阈值
        return energy > threshold

    def _record_interrupt_audio(self, first_frame: np.ndarray) -> None:
        """
        录制打断时的语音

        Args:
            first_frame: 已检测到语音的第一帧
        """
        max_buffer_duration = self._interrupt_buffer_duration
        max_frames = int(max_buffer_duration * 16000 / 512)

        self._interrupt_buffer = [first_frame]
        logger.info(f"开始录制打断语音（最多 {max_buffer_duration}s）...")

        # 继续录制后续音频
        for i in range(max_frames - 1):
            try:
                audio_frame = self._audio_input.read_chunk()
                self._interrupt_buffer.append(audio_frame)

                # 检测静音（简化处理）
                if self._adaptive_vad:
                    threshold = self._adaptive_vad.get_adaptive_threshold()
                else:
                    threshold = 0.04

                # P1-1 优化: 使用公共函数计算 RMS 能量
                energy = calculate_rms_energy(audio_frame)

                # 如果能量持续低于阈值，提前停止
                if energy < threshold and i > 10:  # 至少录制 10 帧
                    logger.info(f"检测到静音，停止录制（已录制 {i+1} 帧）")
                    break

            except Exception as e:
                logger.error(f"打断录制失败: {e}")
                break

        logger.info(f"打断语音录制完成，共 {len(self._interrupt_buffer)} 帧")

        # P0-2 优化: 将缓冲音频合并到录音列表（deque 支持 extend）
        if hasattr(self, '_recorded_audio'):
            # 将打断时的音频添加到现有录音中
            self._recorded_audio.extend(self._interrupt_buffer)
        else:
            # 创建新的 deque（保持 maxlen 限制）
            self._recorded_audio = deque(self._interrupt_buffer, maxlen=400)

    # ============================================================
    # Phase 1.5: 上下文增强方法
    # ============================================================

    def _build_enhanced_context(self, user_text: str) -> str:
        """
        构建增强的对话上下文（用于延续性表达支持）

        Args:
            user_text: 用户当前输入

        Returns:
            str: 增强后的输入（如果是延续性表达）
        """
        # 如果不是多轮对话，直接返回原文本
        if not self._in_conversation or self._conversation_turn_count <= 1:
            return user_text

        # 检测延续性表达模式
        continuation_patterns = [
            "呢", "吗", "那", "还有", "然后", "接下来"
        ]

        # 清理文本
        cleaned_text = user_text.strip()

        # 检查是否为延续性表达
        is_continuation = any(
            cleaned_text.endswith(pattern) or cleaned_text.startswith(pattern)
            for pattern in continuation_patterns
        )

        # 如果是延续性表达，添加上下文提示
        if is_continuation and self._context_memory_enabled:
            enhanced_prompt = f"[这是第{self._conversation_turn_count}轮对话] {cleaned_text}\n(请根据之前的对话历史理解用户的省略或延续性表达)"
            logger.info(f"检测到延续性表达，已增强上下文")
            return enhanced_prompt

        return user_text

    # ============================================================
    # Phase 1.5: 技能系统方法
    # ============================================================

    def _check_and_execute_skill(self, user_text: str) -> Optional[str]:
        """
        检查并执行技能（Phase 1.5 框架）

        Args:
            user_text: 用户输入文本

        Returns:
            str: 技能执行结果（如果匹配了技能），否则返回 None
        """
        if not self._skill_manager or not self._skill_manager.is_enabled():
            return None

        # 简单的技能匹配逻辑（Phase 1.5 框架）
        # 实际应用中可以使用更复杂的 NLP 匹配

        # 定义关键词到技能的映射
        skill_keywords = {
            "control_light": ["开灯", "关灯", "打开灯", "关闭灯"],
            "play_music": ["播放音乐", "放歌", "听歌"],
            "get_weather": ["天气", "气温", "温度"],
        }

        for skill_name, keywords in skill_keywords.items():
            if any(keyword in user_text for keyword in keywords):
                logger.info(f"检测到技能调用: {skill_name}")
                result = self._skill_manager.execute_skill(skill_name, user_input=user_text)
                return result

        return None

    # ============================================================
    # Phase 1.4: 音频和文本质量检测方法
    # ============================================================

    def _check_audio_quality(self, audio: np.ndarray) -> dict:
        """
        检测音频质量

        Args:
            audio: 音频数据

        Returns:
            dict: 检测结果
            {
                "is_valid": bool,      # 音频是否有效
                "issue_type": str,     # 问题类型 ("silence" | "noise" | None)
                "reason": str          # 原因说明
            }
        """
        config = self._config.get("audio_quality", {})
        min_duration = config.get("min_duration", 0.5)
        min_energy = config.get("min_energy", 0.01)

        # 1. 检查音频长度
        audio_duration = len(audio) / 16000
        if audio_duration < min_duration:
            return {
                "is_valid": False,
                "issue_type": "silence",
                "reason": f"音频太短 ({audio_duration:.2f}s < {min_duration}s)"
            }

        # 2. P1-1 优化: 使用公共函数检查音频能量
        avg_energy = calculate_rms_energy(audio)

        if avg_energy < min_energy:
            return {
                "is_valid": False,
                "issue_type": "silence",
                "reason": f"音频能量太低 ({avg_energy:.4f} < {min_energy})"
            }

        # 3. 通过检测
        return {
            "is_valid": True,
            "issue_type": None,
            "reason": ""
        }

    def _check_text_quality(self, text: str) -> dict:
        """
        检测文本质量

        Args:
            text: 待检测文本

        Returns:
            dict: 检测结果
            {
                "is_valid": bool,      # 文本是否有效
                "issue_type": str,     # 问题类型 ("fragment" | "semantic" | "garbage" | None)
                "reason": str          # 原因说明
            }
        """
        import re

        config = self._config.get("text_quality", {})

        # 0. 清理 STT 特殊标签和噪音
        # 移除 <|语言标签|>, <|EMO_*|>, <|Speech|>, <|withitn|> 等标签
        cleaned_text = re.sub(r'<\|[^|]+\|>', '', text)
        cleaned_text = cleaned_text.strip()

        # 如果清理后为空，直接返回无效
        if not cleaned_text:
            return {
                "is_valid": False,
                "issue_type": "garbage",
                "reason": "识别结果为空或仅含标签"
            }

        # 1. 检查是否包含有效中文内容
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', cleaned_text)
        min_length = config.get("min_length", 1)  # 默认至少1个汉字

        if len(chinese_chars) == 0:
            # 没有中文字符，检查是否为有意义的英文
            # 注意：要从清理后的文本检测，避免标签中的英文被计入
            english_words = re.findall(r'[a-zA-Z]+', cleaned_text)
            # 纯英文必须至少2个单词
            if len(english_words) < 2:
                return {
                    "is_valid": False,
                    "issue_type": "garbage",
                    "reason": f"无有效中文内容，英文单词过少 (英文词数: {len(english_words)})"
                }
            # 英文单词总长度至少5个字符
            if len(''.join(english_words)) < 5:
                return {
                    "is_valid": False,
                    "issue_type": "garbage",
                    "reason": "英文内容过短"
                }
        else:
            # 有中文，按汉字数量计算长度
            if len(chinese_chars) < min_length:
                return {
                    "is_valid": False,
                    "issue_type": "fragment",
                    "reason": f"文本太短 (汉字数: {len(chinese_chars)} < {min_length})"
                }

        # 2. 检查重复字符（使用清理标点后的版本）
        cleaned_for_check = cleaned_text.replace(" ", "").replace("，", "").replace("。", "")
        cleaned_for_check = cleaned_for_check.replace("？", "").replace("！", "").replace("、", "")

        if len(cleaned_for_check) >= 2 and len(set(cleaned_for_check)) == 1:
            return {
                "is_valid": False,
                "issue_type": "fragment",
                "reason": f"重复字符: {cleaned_for_check}"
            }

        # 3. 检查无效词汇
        invalid_words = config.get("invalid_words", [])
        # 使用清理标点后的版本来匹配无效词汇
        if cleaned_for_check in invalid_words:
            return {
                "is_valid": False,
                "issue_type": "semantic",
                "reason": f"无效词汇: {cleaned_text}"
            }

        # 4. 检查是否为混合语言乱码（如 "어", "그 좋아", "没有么问"）
        # 如果包含多种语言标签或明显乱码模式
        if re.search(r'[가-힣]+', text):  # 包含韩文
            # 韩文通常不是我们预期的输入
            korean_chars = re.findall(r'[가-힣]+', text)
            if len(''.join(korean_chars)) > len(chinese_chars):
                return {
                    "is_valid": False,
                    "issue_type": "garbage",
                    "reason": "检测到韩文内容，可能为误识别"
                }

        # 5. 通过检测
        logger.debug(f"文本质量检测通过: 中文{len(chinese_chars)}字, 总长度{len(cleaned_text)}")
        return {
            "is_valid": True,
            "issue_type": None,
            "reason": ""
        }

    def _handle_invalid_input(self, issue_type: str) -> None:
        """
        处理无效输入：播放提示并重试（分级重试策略）

        Args:
            issue_type: 问题类型 ("silence" | "fragment" | "semantic" | "garbage")
        """
        config = self._config.get("audio_quality", {})
        max_retries = config.get("max_retries", 3)

        # 增加重试计数
        if not hasattr(self, '_retry_count'):
            self._retry_count = 0
        self._retry_count += 1

        # max_retries = 0 表示不重试，第一次失败就返回 IDLE（不播放提示）
        if max_retries == 0:
            # 不重试模式：直接返回 IDLE，不播放任何提示
            self._retry_count = 0
            logger.info(f"max_retries=0，不重试，直接返回 IDLE")

            # 🔧 优化：移除冷却期，允许立即再次唤醒

            self.transition_to(State.IDLE)
            return
        elif self._retry_count > max_retries:
            # 达到最大重试次数：返回 IDLE（播放最终提示）
            self._retry_count = 0
            logger.info(f"达到最大重试次数 ({max_retries})，返回 IDLE")
            print(f"\n🔚 超过最大重试次数，返回待机模式\n")

            # 播放最终提示
            final_message = self._get_retry_prompt(max_retries, issue_type)
            self._play_tts_prompt(final_message)

            # P0-3 优化: 等待播放完成，期间检查闹钟
            while self._feedback_player.is_playing():
                time.sleep(0.01)
                # 优化：在播放期间仍然检查闹钟
                if self._alarm_manager:
                    self._alarm_manager.check_and_trigger()

            # 🔧 优化：移除冷却期，允许立即再次唤醒

            self.transition_to(State.IDLE)
        else:
            # 第 1 或 2 次失败：根据次数给出不同提示
            prompt = self._get_retry_prompt(self._retry_count, issue_type)
            logger.info(f"重试 {self._retry_count}/{max_retries}: {prompt}")
            print(f"\n🔔 {prompt}\n")

            self._play_tts_prompt(prompt)

            # P0-3 优化: 等待播放完成，期间检查闹钟
            while self._feedback_player.is_playing():
                time.sleep(0.01)
                # 优化：在播放期间仍然检查闹钟
                if self._alarm_manager:
                    self._alarm_manager.check_and_trigger()

            # 重新进入 LISTENING
            self.transition_to(State.LISTENING)

    def _get_retry_prompt(self, retry_count: int, issue_type: str) -> str:
        """
        根据重试次数和问题类型获取分级提示语

        Args:
            retry_count: 当前重试次数 (1, 2, 或 3)
            issue_type: 问题类型

        Returns:
            str: 提示语
        """
        config = self._config.get("audio_quality", {})
        retry_prompts = config.get("retry_prompts", {})

        # 获取该问题类型的分级提示
        type_prompts = retry_prompts.get(issue_type, {})
        count_key = f"retry_{retry_count}"

        # 如果有配置对应次数的提示，使用配置
        if count_key in type_prompts:
            prompts = type_prompts[count_key]
        else:
            # 使用默认提示
            if retry_count < 3:
                prompts = ["抱歉，没听清，能再说一遍吗？"]
            else:
                prompts = ["抱歉暂时无法识别，我们换个话题吧"]

        # 随机选择
        return random.choice(prompts)

    def _play_tts_prompt(self, text: str) -> None:
        """播放 TTS 提示"""
        if self._tts_engine:
            try:
                audio = self._tts_engine.synthesize(text)
                self._feedback_player.play_audio(audio)
            except Exception as e:
                logger.error(f"TTS 提示播放失败: {e}")

    # ============================================================
    # Phase 1.3: 原有方法
    # ============================================================

    def _process_user_input(self) -> None:
        """
        处理用户输入：STT 识别 + LLM 生成 + TTS 合成

        Phase 1.3: 完整的对话生成流程
        Phase 1.4: 集成音频质量检测和分级重试策略
        Phase 1.8: 音乐控制模式（简化流程）
        """
        logger.info(SEPARATOR_LINE)
        logger.info("🔄 开始处理用户输入...")
        logger.info(SEPARATOR_LINE)

        # Phase 1.8: 音乐控制模式（简化流程）
        if hasattr(self, '_music_control_mode') and self._music_control_mode:
            logger.info("🎵 音乐控制模式：使用简化流程")
            self._process_music_control_input()
            return

        # 正常流程
        """
        处理用户输入：STT 识别 + LLM 生成 + TTS 合成

        Phase 1.3: 完整的对话生成流程
        Phase 1.4: 集成音频质量检测和分级重试策略
        """
        logger.info(SEPARATOR_LINE)
        logger.info("🔄 开始处理用户输入...")
        logger.info(SEPARATOR_LINE)

        # Step 1: 音频质量检测 (Phase 1.4 新增)
        audio_quality_config = self._config.get("audio_quality", {})
        if audio_quality_config.get("enabled", True):
            # 合并所有音频帧
            if self._recorded_audio:
                full_audio = np.concatenate(self._recorded_audio)
            else:
                logger.warning("没有录音数据")
                self._handle_invalid_input("silence")
                return

            # 音频质量检测
            audio_result = self._check_audio_quality(full_audio)
            if not audio_result["is_valid"]:
                logger.warning(f"音频质量检测失败: {audio_result['reason']}")
                self._handle_invalid_input(audio_result["issue_type"])
                return
        else:
            # 兼容旧逻辑：合并音频
            if self._recorded_audio:
                full_audio = np.concatenate(self._recorded_audio)
            else:
                logger.warning("没有录音数据")
                self.transition_to(State.IDLE)
                return

        # Step 2: STT 语音识别
        if not self._stt_engine:
            logger.warning("STT 引擎未配置，跳过识别")
            print("\n📝 识别结果: (STT 未配置)")
            self.transition_to(State.IDLE)
            return

        try:
            logger.info("[1/3] STT 语音识别...")

            # P2-4 优化: 性能监控
            with Timer('stt.transcribe'):
                # 调用 STT 引擎识别
                audio_duration = len(full_audio) / 16000
                logger.info(f"  音频长度: {audio_duration:.2f}s")
                logger.info(f"  采样点数: {len(full_audio)}")

                user_text = self._stt_engine.transcribe(full_audio)

            # 清理 FunASR 输出中的标签（Phase 1.2 修复）
            user_text = self._clean_funasr_output(user_text)

            # 检测回声词汇（唤醒词 + 回复消息）
            if self._in_conversation and self._conversation_turn_count > 1:
                for echo_word in self._echo_detection_words:
                    if echo_word.lower() in user_text.lower():
                        logger.warning(f"检测到回声词汇 '{echo_word}'，忽略本次识别")
                        print(f"\n🔔 检测到回声（{echo_word}），继续等待用户说话...\n")
                        self.transition_to(State.LISTENING)
                        return

            # Step 3: 文本质量检测 (Phase 1.4 新增)
            text_quality_config = self._config.get("text_quality", {})
            if text_quality_config.get("enabled", True):
                text_result = self._check_text_quality(user_text)
                if not text_result["is_valid"]:
                    logger.warning(f"文本质量检测失败: {text_result['reason']}")
                    self._handle_invalid_input(text_result["issue_type"])
                    return

            # 重试成功，清零计数器
            if hasattr(self, '_retry_count') and self._retry_count > 0:
                logger.info(f"✅ 重试成功，清零重试计数器")
                self._retry_count = 0

            # 输出识别结果
            print("\n" + "="*60)
            print("📝 识别结果")
            print("="*60)
            print(f"  用户: {user_text}")
            print("="*60 + "\n")

            logger.info(f"  ✅ 识别完成: {user_text}")

            # 上下文感知意图检测：根据当前状态调整优先级
            # 如果闹钟正在响铃，优先检测闹钟意图
            if self._alarm_ringing and self._alarm_manager:
                logger.debug("闹钟响铃中，优先检测闹钟意图")
                alarm_intent = self._check_alarm_intent(user_text)
                if alarm_intent:
                    self._handle_alarm_intent(alarm_intent)
                    return

            # 智能开关意图检测（优先级最高）
            if self._switch_controller:
                switch_intent = self._check_switch_intent(user_text)
                if switch_intent:
                    # 处理开关意图
                    self._handle_switch_intent(switch_intent)
                    return  # 跳过正常的 LLM 流程
            else:
                logger.debug("智能开关控制器未初始化，跳过开关意图检测")

            # Phase 1.8: 检查是否为音乐播放意图
            if self._music_player:
                music_intent = self._check_music_intent(user_text)
                if music_intent:
                    # 处理音乐意图
                    self._handle_music_intent(music_intent)
                    return  # 跳过正常的 LLM 流程

            # Phase 1.7: 检查是否为闹钟意图（非响铃状态）
            if not self._alarm_ringing and self._alarm_manager:
                alarm_intent = self._check_alarm_intent(user_text)
                if alarm_intent:
                    # 处理闹钟意图
                    self._handle_alarm_intent(alarm_intent)
                    return  # 跳过正常的 LLM 流程

            # Phase 1.5: 检查是否为技能调用
            skill_result = self._check_and_execute_skill(user_text)
            if skill_result is not None:
                # 技能执行成功，直接使用技能结果作为回复
                llm_reply = skill_result
                print("\n" + "="*60)
                print("🔧 技能执行")
                print("="*60)
                print(f"  结果: {llm_reply}")
                print("="*60 + "\n")

                # 跳过 LLM 生成，直接进入 TTS 播放
                # 注意：这里需要处理 TTS 播放，代码结构需要调整
                # Phase 1.5 框架版本：暂时使用 LLM 包装
                logger.info("技能执行完成，生成 TTS 回复...")

                # 使用 LLM 生成更自然的回复（可选）
                # 或者直接使用技能结果
                try:
                    audio_data = self._tts_engine.synthesize(llm_reply)
                    logger.info(f"  ✅ 合成完成")
                    self._feedback_player.play_audio(audio_data)
                    self.transition_to(State.SPEAKING)
                    return
                except TTSError as e:
                    # P1-2 优化: 使用具体的异常类型
                    logger.error(f"TTS 合成失败: {e}")
                    self.transition_to(State.ERROR)
                    return
                except Exception as e:
                    logger.exception(f"TTS 播放失败（未预期错误）: {e}")
                    self.transition_to(State.ERROR)
                    return

        except STTError as e:
            # P1-2 优化: 使用具体的异常类型
            logger.error(f"STT 识别失败: {e}")
            print(f"\n❌ 识别失败: {e}")
            self.transition_to(State.ERROR)
            return
        except AudioQualityError as e:
            logger.error(f"音频质量检测失败: {e}")
            print(f"\n❌ 音频质量不合格: {e}")
            self.transition_to(State.ERROR)
            return
        except Exception as e:
            logger.exception(f"STT 处理失败（未预期错误）: {e}")
            print(f"\n❌ 处理失败: {e}")
            self.transition_to(State.ERROR)
            return

        # Step 2: LLM 对话生成
        if not self._llm_engine:
            logger.warning("LLM 引擎未配置，跳过对话生成")
            print("\n🤖 回复: (LLM 未配置)")
            self.transition_to(State.IDLE)
            return

        try:
            logger.info("[2/3] LLM 对话生成...")

            # Phase 1.5: 构建增强的上下文（支持延续性表达）
            enhanced_input = self._build_enhanced_context(user_text)

            # 添加当前日期信息（第一轮对话时）
            if self._conversation_turn_count == 1:
                from datetime import datetime, time as datetime_time
                current_date = datetime.now()
                date_info = f"【当前日期：{current_date.year}年{current_date.month}月{current_date.day}日，星期{['一','二','三','四','五','六','日'][current_date.weekday()]}】"
                enhanced_input = f"{date_info}\n{enhanced_input}"
                logger.debug(f"添加日期信息: {date_info}")

            # P2-4 优化: 性能监控
            with Timer('llm.chat'):
                # 调用 LLM
                result = self._llm_engine.chat(enhanced_input)
                llm_reply = result["reply"]

            # 输出生成结果
            print("\n" + "="*60)
            print("🤖 生成回复")
            print("="*60)
            print(f"  助手: {llm_reply}")
            if result.get("usage"):
                print(f"  Token: {result['usage'].get('total_tokens', 0)}")
            print("="*60 + "\n")

            logger.info(f"  ✅ 生成完成")
            logger.info(f"  回复长度: {len(llm_reply)} 字符")

        except LLMError as e:
            # P1-2 优化: 使用具体的异常类型
            logger.error(f"LLM 生成失败: {e}")
            print(f"\n❌ 生成失败: {e}")
            self.transition_to(State.ERROR)
            return
        except Exception as e:
            # 检查是否为网络连接错误
            error_msg = str(e)
            if any(keyword in error_msg for keyword in ['Network is unreachable', 'ConnectionError', 'Failed to establish', 'Errno 101', 'Errno 113']):
                # 网络不可达，使用友好的提示
                friendly_msg = "抱歉，现在胡桃在遨游太空，不在服务区"
                logger.error(f"网络连接失败: {e}")
                print(f"\n🌌 {friendly_msg}")

                # 播放 TTS 提示
                try:
                    audio_data = self._tts_engine.synthesize(friendly_msg)
                    self._feedback_player.play_audio(audio_data)
                    logger.info("已播放网络错误提示")
                except Exception as tts_error:
                    logger.error(f"TTS 播放失败: {tts_error}")

                self.transition_to(State.IDLE)
                return
            else:
                # 其他未知错误
                logger.exception(f"LLM 处理失败（未预期错误）: {e}")
                print(f"\n❌ 处理失败: {e}")
                self.transition_to(State.ERROR)
                return

        # Step 3: TTS 语音合成
        if not self._tts_engine:
            logger.warning("TTS 引擎未配置，跳过语音播放")
            print("\n🔊 语音播报: (TTS 未配置)")
            self.transition_to(State.IDLE)
            return

        try:
            logger.info("[3/3] TTS 语音合成...")
            logger.info(f"  文本: {llm_reply[:50]}...")

            # P2-4 优化: 性能监控
            with Timer('tts.synthesize'):
                audio_data = self._tts_engine.synthesize(llm_reply)

            logger.info(f"  ✅ 合成完成")
            logger.info(f"  音频长度: {len(audio_data)} 采样点")
            logger.info(f"  播放时长: {len(audio_data)/self._tts_engine.get_sample_rate():.2f}s")

            # 播放 TTS 音频
            logger.info("🔊 播放语音回复...")
            self._feedback_player.play_audio(audio_data)

            # 转换到 SPEAKING 状态
            logger.info("✅ 进入 SPEAKING 状态")
            self.transition_to(State.SPEAKING)

        except TTSError as e:
            # P1-2 优化: 使用具体的异常类型
            logger.error(f"TTS 合成失败: {e}")
            print(f"\n❌ 语音合成失败: {e}")
            self.transition_to(State.ERROR)
        except AudioError as e:
            logger.error(f"音频播放失败: {e}")
            print(f"\n❌ 播放失败: {e}")
            self.transition_to(State.ERROR)
        except Exception as e:
            logger.exception(f"TTS 处理失败（未预期错误）: {e}")
            print(f"\n❌ 处理失败: {e}")
            self.transition_to(State.ERROR)

    def run(self) -> None:
        """
        运行状态机主循环（阻塞）
        """
        self.start()

        try:
            # 启动音频流
            self._audio_input.start_stream()

            logger.info("状态机主循环启动...")
            logger.info("等待唤醒词...")

            while self._running:
                self.update()

                # 避免CPU占用过高
                time.sleep(0.001)

        except KeyboardInterrupt:
            logger.info("收到中断信号，停止状态机")
        except Exception as e:
            logger.error(f"状态机运行异常: {e}", exc_info=True)
        finally:
            # 清理资源
            self._audio_input.stop_stream()
            self._feedback_player.stop()
            self.stop()

    def get_state_duration(self) -> float:
        """
        获取当前状态持续时间

        Returns:
            float: 持续时间（秒）
        """
        if self._state_start_time is None:
            return 0.0

        return time.time() - self._state_start_time

    # ============================================================
    # Phase 1.7: 闹钟功能方法
    # ============================================================

    def _on_alarm_triggered(self, alarm) -> None:
        """
        闹钟触发回调（在独立线程中调用）

        Args:
            alarm: 闹钟对象
        """
        try:
            # 设置响铃标志
            self._alarm_ringing = True

            logger.info(SEPARATOR_LINE)
            logger.info(f"⏰ 闹钟触发: {alarm.message}")
            logger.info(SEPARATOR_LINE)

            # 检查是否使用打气词（theme != "铃声"）
            if hasattr(alarm, 'theme') and alarm.theme not in [None, "", "铃声"]:
                # 使用打气词
                logger.info(f"使用打气词模式，主题: {alarm.theme}")
                self._play_alarm_cheerword(alarm)
            else:
                # 使用传统铃声
                logger.info("使用传统铃声模式")
                logger.info("播放闹钟铃声，可以直接说'停止'或'稍后提醒'")
                self._feedback_player.play_alarm_ringtone(loop=True, duration=30)

            # 注意：闹钟响铃会在独立线程中播放
            # 用户可以通过语音指令"停止"或"稍后提醒"来控制
            # 由于设置了 _alarm_ringing 标志，在 IDLE 状态下会跳过静默时段检查

        except Exception as e:
            logger.error(f"闹钟响铃失败: {e}")
            self._alarm_ringing = False

    def _play_alarm_cheerword(self, alarm) -> None:
        """
        播放闹钟打气词（分段生成和播放）

        Args:
            alarm: 闹钟对象
        """
        try:
            from ..alarm.cheerword_generator import CheerwordGenerator
            from ..feedback.long_text_player import ChunkedTTSPlayer

            theme = getattr(alarm, 'theme', '起床')
            logger.info(f"正在生成 '{theme}' 主题的打气词...")

            # 生成打气词
            generator = CheerwordGenerator(self._llm_engine)
            cheerword = generator.generate_cheerword(theme, duration=30)

            logger.info(f"打气词生成完成（长度: {len(cheerword)} 字）")
            logger.debug(f"打气词内容: {cheerword[:100]}...")

            # 使用分段播放器播放
            player = ChunkedTTSPlayer(self._tts_engine, self._stop_event)
            player.play_long_text(cheerword, chunk_by_sentence=True)

            logger.info("✅ 打气词播放完成")

        except Exception as e:
            logger.error(f"打气词播放失败: {e}")
            # 回退到铃声播放
            logger.info("回退到传统铃声播放")
            self._feedback_player.play_alarm_ringtone(loop=True, duration=30)

    # ============================================================
    # Phase 1.8: 音乐播放功能方法
    # ============================================================

    def _check_music_intent(self, user_text: str):
        """
        检查是否为音乐播放意图

        Args:
            user_text: 用户输入文本

        Returns:
            MusicIntent: 音乐意图对象，如果不是音乐相关返回 None
        """
        try:
            from ..music.music_intent_detector import detect_music_intent
            return detect_music_intent(user_text)
        except ImportError:
            logger.warning("音乐意图检测器导入失败")
            return None
        except Exception as e:
            logger.error(f"音乐意图检测失败: {e}")
            return None

    def _handle_music_intent(self, music_intent) -> None:
        """
        处理音乐播放意图

        Args:
            music_intent: 音乐意图对象
        """
        from ..music.music_intent_detector import format_music_response

        action = music_intent.action
        llm_reply = ""

        try:
            if action == "play":
                # 播放音乐
                if music_intent.keyword:
                    # 尝试搜索指定歌曲
                    track = self._music_player.get_library().get_track_by_name(music_intent.keyword)
                    if track:
                        self._music_player.play_track(track)
                        llm_reply = format_music_response("play", track.name)
                    else:
                        # 未找到指定歌曲，播放随机音乐
                        track = self._music_player.play_random()
                        if track:
                            llm_reply = f"未找到《{music_intent.keyword}》，为您随机播放《{track.name}》"
                        else:
                            llm_reply = "抱歉，没有可用的音乐文件"
                else:
                    # 随机播放
                    track = self._music_player.play_random()
                    if track:
                        llm_reply = format_music_response("play", track.name)
                    else:
                        llm_reply = "抱歉，音乐库中没有可用的音乐文件"

                print(f"\n🎵 {llm_reply}\n")

            elif action == "pause":
                # 暂停播放
                if self._music_player.is_playing():
                    self._music_player.pause()
                    self._music_playing = False  # 更新播放状态
                    llm_reply = format_music_response("pause")
                else:
                    llm_reply = "当前没有在播放音乐"

                print(f"\n🎵 {llm_reply}\n")

            elif action == "resume":
                # 恢复播放
                if self._music_player.is_paused():
                    self._music_player.resume()
                    llm_reply = format_music_response("resume")
                else:
                    llm_reply = "音乐未暂停，无需恢复"

                print(f"\n🎵 {llm_reply}\n")

            elif action == "stop":
                # 停止播放
                if self._music_player.is_playing() or self._music_player.is_paused():
                    self._music_player.stop()
                    self._music_playing = False  # 更新播放状态
                    llm_reply = format_music_response("stop")
                else:
                    llm_reply = "当前没有在播放音乐"

                print(f"\n🎵 {llm_reply}\n")

            elif action == "volume_up":
                # 增大音量
                self._music_player.volume_up()
                volume = self._music_player.get_volume()
                llm_reply = f"好的，音量已调大到 {int(volume * 100)}%"
                print(f"\n🎵 {llm_reply}\n")

            elif action == "volume_down":
                # 减小音量
                self._music_player.volume_down()
                volume = self._music_player.get_volume()
                llm_reply = f"好的，音量已调小到 {int(volume * 100)}%"
                print(f"\n🎵 {llm_reply}\n")

            elif action == "next":
                # 下一首（尚未实现）
                llm_reply = "抱歉，暂不支持切歌功能"
                print(f"\n🎵 {llm_reply}\n")

            else:
                logger.warning(f"未知的音乐意图: {action}")
                return

            # 播放 TTS 回复
            if llm_reply and self._tts_engine:
                self._play_tts_prompt(llm_reply)

                # P0-3 优化: 等待播放完成（重要：避免音乐和TTS同时播放），期间检查闹钟
                while self._feedback_player.is_playing():
                    time.sleep(0.01)
                    # 优化：在播放期间仍然检查闹钟
                    if self._alarm_manager:
                        self._alarm_manager.check_and_trigger()

                # 额外等待 0.5 秒，确保音频缓冲区清空
                time.sleep(0.5)

            # 根据操作决定下一步
            if action in ["play", "resume"]:
                # 播放音乐：确保音乐播放状态为 True
                self._music_playing = True  # 重要：标记音乐正在播放
                logger.info("🎵 音乐开始播放，后续唤醒将进入音乐控制模式")
                print(f"\n🎵 音乐播放中，再次唤醒可控制：停止、暂停、音量\n")

                # 🔧 优化：缓冲区已在唤醒时清空，无需冷却期

                # 退出音乐控制模式（如果在该模式下）
                if hasattr(self, '_music_control_mode'):
                    self._music_control_mode = False

                self.transition_to(State.IDLE)

            elif action in ["stop", "pause"]:
                # 停止或暂停：音乐停止，后续唤醒将进入对话模式
                self._music_playing = False  # 重要：标记音乐已停止
                logger.info("🎵 音乐停止，后续唤醒将进入对话模式")
                print(f"\n💬 音乐已停止，后续唤醒进入对话模式\n")

                # 退出音乐控制模式
                # 🔧 优化：缓冲区已在唤醒时清空，无需冷却期

                # 退出音乐控制模式
                if hasattr(self, '_music_control_mode'):
                    self._music_control_mode = False

                self.transition_to(State.IDLE)

            elif action in ["volume_up", "volume_down", "next"]:
                # 音量调节或切歌：保持音乐控制模式，让用户可以继续控制
                # 检查音乐是否还在播放
                if self._music_player and self._music_player.is_playing():
                    # 音乐还在播放，保持音乐控制模式
                    logger.info("🎵 音乐继续播放，保持音乐控制模式")
                    print(f"\n🎵 音乐继续播放，保持控制模式\n")

                    # 🔧 优化：移除冷却期，允许快速连续控制
                    # 短暂停顿，让用户准备
                    time.sleep(0.3)

                    # 重新进入 LISTENING（继续监听控制命令）
                    self.transition_to(State.LISTENING)
                else:
                    # 音乐停止了，退出音乐控制模式
                    self._music_playing = False
                    logger.info("🎵 音乐停止，后续唤醒将进入对话模式")
                    print(f"\n💬 音乐已停止，后续唤醒进入对话模式\n")

                    # 🔧 优化：缓冲区已在唤醒时清空，无需冷却期

                    if hasattr(self, '_music_control_mode'):
                        self._music_control_mode = False

                    self.transition_to(State.IDLE)

            else:
                # 其他操作也返回 IDLE
                # 🔧 优化：缓冲区已在唤醒时清空，无需冷却期

                # 退出音乐控制模式（如果在该模式下）
                if hasattr(self, '_music_control_mode'):
                    self._music_control_mode = False

                self.transition_to(State.IDLE)

        except Exception as e:
            logger.error(f"处理音乐意图失败: {e}")
            print(f"\n❌ 处理音乐请求失败: {e}\n")

            # 🔧 优化：缓冲区已在唤醒时清空，无需冷却期

            self.transition_to(State.IDLE)

    def _clean_funasr_output(self, text: str) -> str:
        """
        清理 FunASR 输出中的标签

        FunASR 输出格式示例：
        <|zh|><|NEUTRAL|><|Speech|><|withitn|>设定5分钟后的闹钟。。

        Args:
            text: FunASR 原始输出

        Returns:
            str: 清理后的文本
        """
        if not text:
            return text

        import re

        # 匹配 <|zh|>...<|zh|> 模式并提取文本
        # FunASR 格式: <|语言|><|情感|><|Speech|><|withitn|>实际文本
        pattern = r'<\|[^|]+\|([^<>]+)\|[^|]+\|>'
        matches = re.findall(pattern, text)

        if matches:
            cleaned_text = ''.join(matches)
            logger.debug(f"清理 FunASR 标签: {text[:50]}... -> {cleaned_text[:50]}")
            return cleaned_text

        # 回退方案：移除所有标签标记
        text_without_tags = re.sub(r'<[^>]+>', '', text)
        if text_without_tags != text:
            logger.debug(f"移除 HTML 标签: {text[:50]}... -> {text_without_tags[:50]}...")
            return text_without_tags

        return text

    def _handle_music_control(self) -> None:
        """
        音乐控制模式：快速录音并识别控制命令

        在音乐播放时，跳过唤醒反馈，直接进入简化流程
        """
        logger.info("🎵 进入音乐控制模式")
        print(f"\n🎵 [音乐控制模式] 请说控制命令：停止、暂停、音量大/小\n")

        # 播放简短提示音（让用户知道进入控制模式）
        # 使用短促的蜂鸣声
        try:
            # 生成两声短蜂鸣，表示进入控制模式
            import numpy as np
            beep_duration = 0.1  # 100ms
            sample_rate = 16000
            t = np.linspace(0, beep_duration, int(sample_rate * beep_duration), False)
            tone = np.sin(2 * np.pi * 880 * t)  # 880Hz
            audio_data = (tone * 0.3 * 32767).astype(np.int16)

            # 播放两声短蜂鸣
            self._feedback_player._play_audio(audio_data)
            time.sleep(0.15)
            self._feedback_player._play_audio(audio_data)
        except Exception as e:
            logger.debug(f"播放提示音失败（不影响功能）: {e}")

        # 直接进入 LISTENING 状态（跳过 WAKEUP）
        self._in_conversation = True
        self._conversation_turn_count = 1
        self._music_control_mode = True  # 标记为音乐控制模式
        self.transition_to(State.LISTENING)

    def _process_music_control_input(self) -> None:
        """
        处理音乐控制输入（简化模式）

        只识别音乐控制命令，忽略歌词等干扰
        注意：音乐控制模式是一次性的，识别失败直接退出，不重试
        """
        # Step 1: 合并音频
        if self._recorded_audio:
            full_audio = np.concatenate(self._recorded_audio)
        else:
            logger.warning("没有录音数据")
            self._exit_music_control_mode()
            return

        # Step 2: STT 识别
        if not self._stt_engine:
            logger.warning("STT 引擎未配置")
            self._exit_music_control_mode()
            return

        try:
            logger.info("[音乐模式] STT 识别...")
            user_text = self._stt_engine.transcribe(full_audio)
            user_text = self._clean_funasr_output(user_text)

            print("\n" + "="*60)
            print("📝 识别结果")
            print("="*60)
            print(f"  用户: {user_text}")
            print("="*60 + "\n")

            # Step 3: 使用简化的音乐控制检测器
            from ..music.music_intent_detector import detect_music_control

            music_intent = detect_music_control(user_text)

            if music_intent:
                # 是明确的音乐控制命令
                logger.info(f"🎵 识别到音乐控制命令: {music_intent.action}")
                self._handle_music_intent(music_intent)
            else:
                # 不是控制命令，直接退出音乐控制模式
                logger.info("🎵 未识别到控制命令，退出音乐控制模式")
                print(f"\n🎵 未识别到控制命令")
                print(f"💡 提示：请清晰地说「停止」「暂停」「大声点」「小声点」\n")
                self._exit_music_control_mode()

        except Exception as e:
            logger.error(f"音乐控制模式处理失败: {e}")
            self._exit_music_control_mode()

    def _exit_music_control_mode(self) -> None:
        """退出音乐控制模式"""
        if hasattr(self, '_music_control_mode'):
            self._music_control_mode = False
        self._in_conversation = False
        self._conversation_turn_count = 0

        # 如果音乐还在播放，提示用户
        if self._music_playing:
            logger.info("🎵 退出音乐控制模式，音乐继续播放")
            print(f"\n🎵 退出音乐控制模式，音乐继续播放，再次唤醒可继续控制\n")
        else:
            logger.info("💬 退出音乐控制模式，进入对话模式")
            print(f"\n💬 退出音乐控制模式，进入对话模式\n")

        self.transition_to(State.IDLE)

    def _is_in_quiet_hours(self) -> bool:
        """
        检查当前时间是否在静默时段内

        Returns:
            bool: 是否在静默时段内
        """
        if not self._quiet_hours:
            return False

        now = datetime.now()
        current_time = now.time()
        start_time, end_time = self._quiet_hours

        # 处理跨日情况（如 23:00 - 06:00）
        if start_time > end_time:
            # 跨日：当前时间 >= start_time 或 <= end_time
            return current_time >= start_time or current_time <= end_time
        else:
            # 同日：start_time <= 当前时间 <= end_time
            return start_time <= current_time <= end_time

    def _check_alarm_intent(self, user_text: str):
        """
        检查是否为闹钟意图

        Args:
            user_text: 用户输入文本

        Returns:
            AlarmIntent: 闹钟意图对象，如果不是闹钟相关返回 None
        """
        try:
            from ..alarm.intent_detector import detect_alarm_intent
            # 传递 LLM 引擎，用于复杂时间表达解析
            return detect_alarm_intent(user_text, llm_engine=self._llm_engine)
        except ImportError:
            logger.warning("闹钟意图检测器导入失败")
            return None
        except Exception as e:
            logger.error(f"闹钟意图检测失败: {e}")
            return None

    def _handle_alarm_intent(self, alarm_intent) -> None:
        """
        处理闹钟意图

        Args:
            alarm_intent: 闹钟意图对象
        """
        from ..alarm.intent_detector import format_alarm_confirm

        action = alarm_intent.action
        llm_reply = ""

        try:
            if action == "set":
                # 设置闹钟
                # 传递已解析的 datetime 对象和原始消息
                alarm = self._alarm_manager.add_alarm(
                    time_text=None,  # 不需要，因为我们已经有 alarm_time
                    message=alarm_intent.message,
                    alarm_time=alarm_intent.time  # 使用已解析的时间
                )

                if alarm:
                    llm_reply = format_alarm_confirm(alarm.time, alarm.message)
                    print(f"\n⏰ {llm_reply}\n")
                else:
                    llm_reply = "抱歉，设置闹钟失败，请检查时间格式"
                    print(f"\n❌ {llm_reply}\n")

            elif action == "delete":
                # 删除闹钟
                if alarm_intent.alarm_id:
                    success = self._alarm_manager.delete_alarm(alarm_intent.alarm_id)
                    if success:
                        llm_reply = f"已删除 {alarm_intent.alarm_id} 号闹钟"
                        print(f"\n✅ {llm_reply}\n")
                    else:
                        llm_reply = f"删除失败，未找到 {alarm_intent.alarm_id} 号闹钟"
                        print(f"\n❌ {llm_reply}\n")
                else:
                    llm_reply = "请告诉我需要删除哪个闹钟的编号"
                    print(f"\n❓ {llm_reply}\n")

            elif action == "list":
                # 查询闹钟列表
                alarms = self._alarm_manager.list_alarms()

                if not alarms:
                    llm_reply = "当前没有设置任何闹钟"
                else:
                    # 格式化列表
                    alarm_list = "\n".join([str(alarm) for alarm in alarms])
                    print(f"\n📋 闹钟列表：\n{alarm_list}\n")

                    # 语音回复
                    count = len(alarms)
                    llm_reply = f"当前有 {count} 个闹钟"

            elif action == "stop_alarm":
                # 停止闹钟铃声
                self._feedback_player.stop_alarm_ringtone()
                self._alarm_ringing = False  # 清除响铃标志
                llm_reply = "好的，闹钟已停止"
                print(f"\n✅ {llm_reply}\n")

            elif action == "snooze":
                # 稍后提醒
                minutes = alarm_intent.minutes or 10
                # 这里需要获取最近触发的闹钟 ID
                # 简化处理：提示用户
                llm_reply = f"好的，{minutes} 分钟后再提醒您"
                print(f"\n⏰ {llm_reply}\n")

            else:
                logger.warning(f"未知的闹钟意图: {action}")
                return

            # 播放 TTS 回复
            if llm_reply and self._tts_engine:
                self._play_tts_prompt(llm_reply)

                # P0-3 优化: 等待播放完成，期间检查闹钟
                while self._feedback_player.is_playing():
                    time.sleep(0.01)
                    # 优化：在播放期间仍然检查闹钟
                    if self._alarm_manager:
                        self._alarm_manager.check_and_trigger()

            # 返回 LISTENING 状态（如果是查询/删除操作）
            # 或者返回 IDLE 状态（如果是设置闹钟）
            if action in ["list", "delete"]:
                self.transition_to(State.LISTENING)
            else:
                # 设置闹钟后返回 IDLE
                # 🔧 优化：缓冲区已在唤醒时清空，无需冷却期

                self.transition_to(State.IDLE)

        except Exception as e:
            logger.error(f"处理闹钟意图失败: {e}")
            print(f"\n❌ 处理闹钟请求失败: {e}\n")
            self.transition_to(State.IDLE)

    # ============================================================
    # 智能开关控制方法
    # ============================================================

    def _check_switch_intent(self, user_text: str):
        """
        检查是否为智能开关控制意图

        Args:
            user_text: 用户输入文本

        Returns:
            SwitchIntent: 开关意图对象，如果不是开关相关返回 None
        """
        try:
            from ..smart_switch import detect_switch_intent

            # 获取已知设备名称列表
            known_devices = []
            if self._switch_controller:
                known_devices = [d.name for d in self._switch_controller.list_devices()]

            return detect_switch_intent(user_text, known_devices)
        except ImportError:
            logger.warning("智能开关意图检测器导入失败")
            return None
        except Exception as e:
            logger.error(f"智能开关意图检测失败: {e}")
            return None

    def _handle_switch_intent(self, switch_intent) -> None:
        """
        处理智能开关控制意图（GeekOpen 协议）

        Args:
            switch_intent: 开关意图对象
        """
        from ..smart_switch import GeekOpenController, SwitchKey, format_geekopen_response

        action = switch_intent.action
        device = switch_intent.device
        llm_reply = ""

        try:
            success = False
            key = SwitchKey.KEY1  # 默认使用 KEY1

            # 获取设备配置，包括 key_mapping
            device_obj = self._switch_controller.get_device(device)

            # 如果找不到设备，使用第一个已注册设备作为默认
            if device_obj is None:
                devices = self._switch_controller.list_devices()
                if devices:
                    device_obj = devices[0]
                    logger.info(f"设备 '{device}' 未找到，使用默认设备: {device_obj.name}")
                    device = device_obj.name  # 更新设备名称

            key_mapping = device_obj.key_mapping if device_obj else None

            if action == "on":
                # 打开开关
                if switch_intent.all:
                    # 打开所有设备的 KEY1
                    devices = self._switch_controller.list_devices()
                    count = 0
                    already_on = 0
                    for dev in devices:
                        # 检查当前状态
                        state = self._switch_controller.get_state(dev.name)
                        if state and state.get_key_state(key):
                            already_on += 1
                        elif self._switch_controller.turn_on(dev.name, key):
                            count += 1
                    if count > 0:
                        llm_reply = f"好的，已打开 {count} 个设备"
                        if already_on > 0:
                            llm_reply += f"（{already_on} 个设备已经是开启状态）"
                    else:
                        llm_reply = f"所有设备已经是开启状态"
                    success = count > 0
                else:
                    # 检查当前状态
                    state = self._switch_controller.get_state(device)
                    if state and state.get_key_state(key):
                        # 已经是开启状态
                        llm_reply = f"{device}已经是开启状态"
                        success = True
                    else:
                        success = self._switch_controller.turn_on(device, key)
                        if success:
                            llm_reply = format_geekopen_response("on", device, key, key_mapping)
                        else:
                            llm_reply = f"抱歉，找不到设备: {device}"

            elif action == "off":
                # 关闭开关
                if switch_intent.all:
                    # 关闭所有设备的 KEY1
                    devices = self._switch_controller.list_devices()
                    count = 0
                    already_off = 0
                    for dev in devices:
                        # 检查当前状态
                        state = self._switch_controller.get_state(dev.name)
                        if state and not state.get_key_state(key):
                            already_off += 1
                        elif self._switch_controller.turn_off(dev.name, key):
                            count += 1
                    if count > 0:
                        llm_reply = f"好的，已关闭 {count} 个设备"
                        if already_off > 0:
                            llm_reply += f"（{already_off} 个设备已经是关闭状态）"
                    else:
                        llm_reply = f"所有设备已经是关闭状态"
                    success = count > 0
                else:
                    # 检查当前状态
                    state = self._switch_controller.get_state(device)
                    if state and not state.get_key_state(key):
                        # 已经是关闭状态
                        llm_reply = f"{device}已经是关闭状态"
                        success = True
                    else:
                        success = self._switch_controller.turn_off(device, key)
                        if success:
                            llm_reply = format_geekopen_response("off", device, key, key_mapping)
                        else:
                            llm_reply = f"抱歉，找不到设备: {device}"

            elif action == "toggle":
                # 切换开关
                success = self._switch_controller.toggle(device, key)
                if success:
                    llm_reply = format_geekopen_response("toggle", device, key, key_mapping)
                else:
                    llm_reply = f"抱歉，找不到设备: {device}"

            elif action == "query":
                # 查询状态
                state = self._switch_controller.get_state(device)
                if state and state.last_update > 0:
                    is_on = state.get_key_state(key)
                    status = "已打开" if is_on else "已关闭"
                    llm_reply = f"{device}{status}"
                    success = True
                elif state:
                    llm_reply = f"{device}状态未知"
                else:
                    llm_reply = f"抱歉，找不到设备: {device}"

            print(f"\n💡 {llm_reply}\n")

            # 播放 TTS 回复
            if llm_reply and self._tts_engine:
                self._play_tts_prompt(llm_reply)

                # P0-3 优化: 等待播放完成，期间检查闹钟
                while self._feedback_player.is_playing():
                    time.sleep(0.01)
                    if self._alarm_manager:
                        self._alarm_manager.check_and_trigger()

            # 🔧 优化：缓冲区已在唤醒时清空，无需冷却期

            self.transition_to(State.IDLE)

        except Exception as e:
            logger.error(f"处理智能开关意图失败: {e}")
            print(f"\n❌ 处理智能开关请求失败: {e}\n")
            self.transition_to(State.IDLE)
