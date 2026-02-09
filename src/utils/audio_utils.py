"""
音频处理工具函数
Audio Processing Utilities

P1-1 优化: 提取公共方法，减少重复代码
"""
import numpy as np
from typing import Union


def calculate_rms_energy(audio: Union[np.ndarray, list]) -> float:
    """
    计算音频的 RMS (Root Mean Square) 能量

    Args:
        audio: 音频数据 (numpy array 或 list)
               支持 int16 或 float32 类型

    Returns:
        float: RMS 能量值

    Examples:
        >>> audio = np.array([100, -100, 200, -200], dtype=np.int16)
        >>> energy = calculate_rms_energy(audio)
        >>> print(f"能量: {energy:.4f}")
    """
    if isinstance(audio, list):
        audio = np.array(audio)

    if len(audio) == 0:
        return 0.0

    # 归一化到 [-1, 1] 范围
    if audio.dtype == np.int16:
        audio_float = audio.astype(float) / 32768.0
    else:
        audio_float = audio.astype(float)

    # 计算 RMS
    rms = np.sqrt(np.mean(audio_float ** 2))
    return float(rms)


def normalize_audio(audio: np.ndarray, target_dtype: type = np.int16) -> np.ndarray:
    """
    归一化音频数据到目标格式

    Args:
        audio: 输入音频数据
        target_dtype: 目标数据类型 (默认 int16)

    Returns:
        np.ndarray: 归一化后的音频数据
    """
    if len(audio) == 0:
        return audio

    # 归一化到 [-1, 1]
    if audio.dtype == np.int16:
        audio_float = audio.astype(float) / 32768.0
    else:
        audio_float = audio.astype(float)

    # 转换到目标格式
    if target_dtype == np.int16:
        return (audio_float * 32767).astype(np.int16)
    elif target_dtype == np.float32:
        return audio_float.astype(np.float32)
    else:
        raise ValueError(f"不支持的目标类型: {target_dtype}")


def calculate_decibels(audio: np.ndarray) -> float:
    """
    计算音频的分贝值 (dB)

    Args:
        audio: 音频数据

    Returns:
        float: 分贝值 (0 = 最大, -inf = 静音)
    """
    rms = calculate_rms_energy(audio)
    if rms == 0:
        return float('-inf')
    return 20 * np.log10(rms)


def detect_silence(
    audio: np.ndarray,
    threshold: float = 0.01,
    min_silence_duration: float = 0.5,
    sample_rate: int = 16000
) -> bool:
    """
    检测音频是否为静音

    Args:
        audio: 音频数据
        threshold: 能量阈值 (低于此值视为静音)
        min_silence_duration: 最小静音时长（秒）
        sample_rate: 采样率

    Returns:
        bool: 是否为静音
    """
    if len(audio) == 0:
        return True

    # 计算每帧的能量
    frame_size = int(sample_rate * 0.02)  # 20ms 帧
    num_frames = len(audio) // frame_size

    if num_frames == 0:
        return calculate_rms_energy(audio) < threshold

    silence_frames = 0
    min_frames = int(min_silence_duration / 0.02)  # 需要的静音帧数

    for i in range(num_frames):
        frame = audio[i * frame_size:(i + 1) * frame_size]
        energy = calculate_rms_energy(frame)
        if energy < threshold:
            silence_frames += 1
        else:
            silence_frames = 0

        if silence_frames >= min_frames:
            return True

    return False
