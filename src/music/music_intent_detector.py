"""
音乐意图检测器 - Music Intent Detector
识别用户的音乐播放、暂停、音量调节等意图
Phase 1.8
"""
import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class MusicIntent:
    """音乐意图"""
    action: str  # "play", "pause", "resume", "stop", "volume_up", "volume_down"
    keyword: Optional[str] = None  # 搜索关键词（用于点歌）
    message: str = ""  # 原始用户输入


# 播放关键词
PLAY_KEYWORDS = [
    "播放", "来点", "放首歌", "听歌", "音乐", "小曲",
    "烘托氛围", "背景音乐", "配乐"
]

# 暂停关键词
PAUSE_KEYWORDS = [
    "暂停", "停一下", "等等"
]

# 恢复关键词
RESUME_KEYWORDS = [
    "继续", "恢复", "接着播"
]

# 停止关键词
STOP_KEYWORDS = [
    "停止", "关掉", "别播了", "不听了", "关闭", "停下"
]

# 音量增大关键词
VOLUME_UP_KEYWORDS = [
    "大声点", "声音大点", "音量大点", "响一点",
    "放大音量", "增加音量", "调大音量", "调大声", "大声"
]

# 音量减小关键词
VOLUME_DOWN_KEYWORDS = [
    "小声点", "声音小点", "音量小点", "轻一点",
    "减小音量", "降低音量", "调小音量", "调小声", "小声"
]

# 下一首关键词
NEXT_KEYWORDS = [
    "下一首", "换一个", "换歌", "切歌", "换一首", "换个"
]


def detect_music_intent(text: str) -> Optional[MusicIntent]:
    """
    检测音乐意图（完整模式，包含播放功能）

    Args:
        text: 用户输入文本

    Returns:
        MusicIntent: 音乐意图对象，如果不是音乐相关则返回 None
    """
    if not text:
        return None

    text = text.strip()

    # 1. 检测音量调节意图（优先级最高）
    if _contains_any(text, VOLUME_UP_KEYWORDS):
        logger.info("检测到音量增大意图")
        return MusicIntent(action="volume_up", message=text)

    if _contains_any(text, VOLUME_DOWN_KEYWORDS):
        logger.info("检测到音量减小意图")
        return MusicIntent(action="volume_down", message=text)

    # 2. 检测暂停意图
    if _contains_any(text, PAUSE_KEYWORDS):
        # 需要确保不是"停止"意图
        if not _contains_any(text, STOP_KEYWORDS):
            logger.info("检测到暂停意图")
            return MusicIntent(action="pause", message=text)

    # 3. 检测恢复意图
    if _contains_any(text, RESUME_KEYWORDS):
        logger.info("检测到恢复意图")
        return MusicIntent(action="resume", message=text)

    # 4. 检测停止意图
    if _contains_any(text, STOP_KEYWORDS):
        logger.info("检测到停止意图")
        return MusicIntent(action="stop", message=text)

    # 5. 检测播放意图
    if _contains_any(text, PLAY_KEYWORDS):
        # 提取搜索关键词（去掉播放关键词）
        keyword = _extract_keyword(text, PLAY_KEYWORDS)

        logger.info(f"检测到播放意图: 关键词='{keyword}'")
        return MusicIntent(action="play", keyword=keyword, message=text)

    # 6. 不是音乐相关意图
    return None


def detect_music_control(text: str) -> Optional[MusicIntent]:
    """
    检测音乐控制意图（简化模式，仅检测控制命令）

    在音乐播放时使用，只识别明确的控制命令，忽略歌词等干扰

    Args:
        text: 用户输入文本

    Returns:
        MusicIntent: 音乐控制意图，如果不是控制命令则返回 None
    """
    if not text:
        return None

    text = text.strip()

    # 优先级：停止 > 音量 > 下一首 > 暂停

    # 1. 停止命令（最高优先级）
    # 即使在歌词中，只要明确出现"停止"就识别
    for keyword in STOP_KEYWORDS:
        if keyword in text:
            logger.info(f"[音乐模式] 检测到停止命令: '{text}'")
            return MusicIntent(action="stop", message=text)

    # 2. 音量调节命令
    for keyword in VOLUME_UP_KEYWORDS:
        if keyword in text:
            logger.info(f"[音乐模式] 检测到音量增大命令: '{text}'")
            return MusicIntent(action="volume_up", message=text)

    for keyword in VOLUME_DOWN_KEYWORDS:
        if keyword in text:
            logger.info(f"[音乐模式] 检测到音量减小命令: '{text}'")
            return MusicIntent(action="volume_down", message=text)

    # 3. 下一首命令
    for keyword in NEXT_KEYWORDS:
        if keyword in text:
            logger.info(f"[音乐模式] 检测到下一首命令: '{text}'")
            return MusicIntent(action="next", message=text)

    # 4. 暂停命令
    for keyword in PAUSE_KEYWORDS:
        if keyword in text:
            logger.info(f"[音乐模式] 检测到暂停命令: '{text}'")
            return MusicIntent(action="pause", message=text)

    # 不是明确的控制命令
    return None


def _contains_any(text: str, keywords: list) -> bool:
    """检查文本是否包含任意关键词"""
    return any(keyword in text for keyword in keywords)


def _extract_keyword(text: str, play_keywords: list) -> Optional[str]:
    """
    从文本中提取搜索关键词

    Args:
        text: 文本
        play_keywords: 播放关键词列表

    Returns:
        str: 提取的关键词，如果没有则返回 None
    """
    # 移除播放关键词
    result = text
    for keyword in play_keywords:
        result = result.replace(keyword, "")

    # 清理空白字符和标点
    result = result.strip()
    result = re.sub(r'[，。！？、\s]+', "", result)

    # 如果清理后为空，说明没有特定关键词
    if not result or result in ["音乐", "歌", "曲"]:
        return None

    return result


def format_music_response(action: str, track_name: Optional[str] = None) -> str:
    """
    格式化音乐操作响应

    Args:
        action: 操作类型
        track_name: 曲目名称

    Returns:
        str: 响应文本
    """
    if action == "play":
        if track_name:
            return f"好的，为您播放《{track_name}》"
        else:
            return "好的，随机播放一首音乐"
    elif action == "pause":
        return "好的，暂停播放"
    elif action == "resume":
        return "好的，继续播放"
    elif action == "stop":
        return "好的，停止播放音乐"
    elif action == "volume_up":
        return "好的，音量已调大"
    elif action == "volume_down":
        return "好的，音量已调小"
    else:
        return "好的"
