"""
语音助手系统异常定义
Voice Assistant Exception Definitions

P1-2 优化: 定义具体异常类型，提高错误定位能力
"""


class VoiceAssistantError(Exception):
    """语音助手基础异常类"""
    pass


class AudioError(VoiceAssistantError):
    """音频处理相关异常"""
    pass


class AudioDeviceError(AudioError):
    """音频设备异常（设备未找到、无法打开等）"""
    pass


class AudioQualityError(AudioError):
    """音频质量异常（能量过低、噪音过大等）"""
    pass


class ModelNotReadyError(VoiceAssistantError):
    """模型未就绪异常"""
    pass


class ModelLoadError(VoiceAssistantError):
    """模型加载失败异常"""
    pass


class ModelInferenceError(VoiceAssistantError):
    """模型推理失败异常"""
    pass


class WakeWordError(VoiceAssistantError):
    """唤醒词检测异常"""
    pass


class STTError(VoiceAssistantError):
    """语音识别异常"""
    pass


class TTSError(VoiceAssistantError):
    """语音合成异常"""
    pass


class LLMError(VoiceAssistantError):
    """语言模型异常"""
    pass


class NetworkError(VoiceAssistantError):
    """网络连接异常"""
    pass


class ConfigError(VoiceAssistantError):
    """配置错误异常"""
    pass


class StateMachineError(VoiceAssistantError):
    """状态机异常"""
    pass


class AlarmError(VoiceAssistantError):
    """闹钟功能异常"""
    pass


class MusicError(VoiceAssistantError):
    """音乐播放异常"""
    pass
