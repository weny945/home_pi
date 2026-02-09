"""
闹钟意图检测器 - 识别用户是否要设置/查询/删除闹钟
Alarm Intent Detector for Natural Language Understanding
"""
import logging
import re
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime, timedelta

from .time_parser import parse_alarm_time, format_alarm_time

logger = logging.getLogger(__name__)


@dataclass
class AlarmIntent:
    """闹钟意图数据类"""
    action: str  # "set", "delete", "list", "snooze", "stop_alarm", "set_theme"
    time: Optional[datetime] = None  # 解析出的时间
    time_str: Optional[str] = None  # 格式化的时间字符串（用于确认）
    message: str = ""  # 原始用户输入
    alarm_id: Optional[int] = None  # 闹钟 ID（用于删除操作）
    minutes: Optional[int] = None  # 分钟数（用于稍后提醒）
    theme: Optional[str] = None  # 打气词主题（用于设置闹钟主题）
    target_alarm_id: Optional[int] = None  # 目标闹钟 ID（用于修改主题）


# 闹钟关键词
ALARM_KEYWORDS = [
    "闹钟", "提醒", "叫", "定", "设置", "添加"
]

# 删除关键词
DELETE_KEYWORDS = [
    "取消", "删除", "关掉", "不要", "去掉"
]

# 查询关键词（必须明确提到"闹钟"相关查询）
LIST_KEYWORDS = [
    "有哪些闹钟", "闹钟有哪些", "查看闹钟", "列出闹钟",
    "看看闹钟", "查询闹钟", "所有闹钟", "闹钟列表",
    "闹钟查询", "查看所有闹钟"
]

# 停止闹钟关键词
STOP_ALARM_KEYWORDS = [
    "停止", "停下", "别响了", "够了", "关掉"
]

# 稍后提醒关键词
SNOOZE_KEYWORDS = [
    "稍后", "过会", "等会", "推迟", "延迟", "一会"
]

# 修改主题关键词
UPDATE_THEME_KEYWORDS = [
    "修改主题", "改成", "更换主题", "换个主题"
]

# 打气词主题
THEME_KEYWORDS = {
    "起床": ["起床", "早安", "叫醒", "起床了"],
    "工作": ["工作", "上班", "努力", "奋斗"],
    "运动": ["运动", "锻炼", "健身", "跑步"],
    "学习": ["学习", "读书", "阅读", "自习"],
    "睡觉": ["睡觉", "晚安", "休息", "睡眠"],
}

# 时间模式（正则表达式）
TIME_PATTERNS = [
    r'\d+点\d*分?',  # "7点"、"7点30"、"7点30分"
    r'[一二三四五六七八九十百零]+点\d*分?',  # "七点"、"七点三十"、"七点三十分"
    r'\d+点',  # "7点"、"8点"（单独匹配）
    r'[一二三四五六七八九十百零]+点',  # "七点"、"八点"
    r'明天',  # "明天"
    r'今天',  # "今天"
    r'后天',  # "后天"
    r'早上',  # "早上"
    r'上午',  # "上午"
    r'中午',  # "中午"
    r'下午',  # "下午"
    r'晚上',  # "晚上"
    r'半夜',  # "半夜"
    r'凌晨',  # "凌晨"
    r'[\d一二三四五六七八九十百零]+\s*分钟\s*(?:之)?[后后以]+',  # "30分钟后"、"两分钟以后"、"五分钟之后"
    r'[\d一二三四五六七八九十百零]+\s*小时\s*(?:之)?[后后以]+',  # "2小时后"、"两小时以后"、"五小时之后"
]


def detect_alarm_intent(text: str, llm_engine=None) -> Optional[AlarmIntent]:
    """
    检测闹钟意图（关键词快筛 + 时间解析）

    Args:
        text: 用户输入文本
        llm_engine: LLM 引擎（可选，用于复杂时间表达解析）

    Returns:
        AlarmIntent: 闹钟意图对象，如果不是闹钟相关则返回 None
    """
    if not text:
        return None

    text = text.strip()

    # 1. 检测停止闹钟意图（优先级最高，闹钟正在响铃时使用）
    if _contains_any(text, STOP_ALARM_KEYWORDS):
        logger.info("检测到停止闹钟意图")
        return AlarmIntent(
            action="stop_alarm",
            message=text
        )

    # 2. 检测稍后提醒意图
    snooze_minutes = _extract_snooze_minutes(text)
    if snooze_minutes and _contains_any(text, SNOOZE_KEYWORDS):
        logger.info(f"检测到稍后提醒意图: {snooze_minutes}分钟")
        return AlarmIntent(
            action="snooze",
            minutes=snooze_minutes,
            message=text
        )

    # 3. 检测查询闹钟意图（但不包含时间模式，避免与设置闹钟冲突）
    if _contains_any(text, LIST_KEYWORDS) and not _contains_time_pattern(text):
        logger.info("检测到查询闹钟意图")
        return AlarmIntent(
            action="list",
            message=text
        )

    # 4. 检测删除闹钟意图
    if _contains_any(text, DELETE_KEYWORDS) and _contains_any(text, ALARM_KEYWORDS):
        alarm_id = _extract_alarm_id(text)
        logger.info(f"检测到删除闹钟意图: ID={alarm_id}")
        return AlarmIntent(
            action="delete",
            alarm_id=alarm_id,
            message=text
        )

    # 5. 检测设置闹钟意图
    if _contains_any(text, ALARM_KEYWORDS):
        # 检查是否包含时间信息
        if _contains_time_pattern(text):
            alarm_time = parse_alarm_time(text, llm_engine)

            if alarm_time:
                time_str = format_alarm_time(alarm_time)
                logger.info(f"检测到设置闹钟意图: {time_str}")

                # 提取备注（去掉时间相关词汇）
                message = _extract_alarm_message(text)

                return AlarmIntent(
                    action="set",
                    time=alarm_time,
                    time_str=time_str,
                    message=message
                )
            else:
                logger.warning(f"包含闹钟关键词但无法解析时间: {text}")

    # 5.5. 新增：支持"仅时间"的简洁表达（如"12点20"、"7点30"）
    # 检查文本是否主要是时间表达（短文本 + 时间模式）
    if _is_simple_time_expression(text):
        alarm_time = parse_alarm_time(text)

        if alarm_time:
            time_str = format_alarm_time(alarm_time)
            logger.info(f"检测到简洁时间表达（无闹钟关键词）: {time_str}")

            return AlarmIntent(
                action="set",
                time=alarm_time,
                time_str=time_str,
                message="闹钟"
            )

    # 6. 不是闹钟相关意图
    return None


def _contains_any(text: str, keywords: List[str]) -> bool:
    """
    检查文本是否包含任意关键词

    Args:
        text: 文本
        keywords: 关键词列表

    Returns:
        bool: 是否包含
    """
    return any(keyword in text for keyword in keywords)


def _contains_time_pattern(text: str) -> bool:
    """
    检查文本是否包含时间模式

    Args:
        text: 文本

    Returns:
        bool: 是否包含时间模式
    """
    for pattern in TIME_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def _is_simple_time_expression(text: str) -> bool:
    """
    检查文本是否为简洁的时间表达（如"12点20"、"7点30"）

    用于支持用户直接说时间来设置闹钟，无需关键词

    Args:
        text: 文本

    Returns:
        bool: 是否为简洁时间表达
    """
    # 清理文本
    cleaned = text.strip()
    # 移除多余的标点符号
    cleaned = re.sub(r'[。！？、，]+', '', cleaned)

    # 检查是否为短文本（≤ 10个字符）
    if len(cleaned) > 10:
        return False

    # 必须包含时间模式
    if not _contains_time_pattern(cleaned):
        return False

    # 排除包含其他意图关键词的情况（避免误判）
    exclude_keywords = [
        "查询", "查看", "删除", "取消", "去掉", "停止",
        "稍后", "推迟", "延迟", "播放音乐", "唱歌", "讲故事"
    ]

    for keyword in exclude_keywords:
        if keyword in cleaned:
            return False

    # 检查文本是否主要由时间表达组成
    # 提取所有时间相关的词
    time_related_chars = 0
    for char in cleaned:
        if char in "0123456789点分秒早晚上午下午半夜凌晨今天明天后天小时":
            time_related_chars += 1

    # 如果80%以上是时间相关字符，认为是简洁时间表达
    time_ratio = time_related_chars / len(cleaned) if cleaned else 0
    return time_ratio >= 0.7


def _extract_alarm_id(text: str) -> Optional[int]:
    """
    从文本中提取闹钟 ID

    Args:
        text: 文本

    Returns:
        int: 闹钟 ID，无法提取返回 None
    """
    # 匹配 "ID 1"、"第1个"、"1号" 等模式
    patterns = [
        r'ID\s*(\d+)',
        r'第\s*(\d+)\s*个',
        r'(\d+)\s*号',
        r'编号\s*(\d+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                continue

    return None


def _extract_snooze_minutes(text: str) -> Optional[int]:
    """
    从文本中提取稍后提醒的分钟数

    Args:
        text: 文本

    Returns:
        int: 分钟数，无法提取返回 None
    """
    # 匹配 "10分钟"、"5分钟" 等模式
    match = re.search(r'(\d+)\s*分钟', text)
    if match:
        try:
            minutes = int(match.group(1))
            # 限制范围：1-120 分钟
            if 1 <= minutes <= 120:
                return minutes
        except (ValueError, IndexError):
            pass

    return None


def _extract_alarm_message(text: str) -> str:
    """
    从文本中提取闹钟备注（去掉时间相关词汇）

    Args:
        text: 文本

    Returns:
        str: 备注消息
    """
    # 移除闹钟关键词
    for keyword in ALARM_KEYWORDS + DELETE_KEYWORDS + LIST_KEYWORDS:
        text = text.replace(keyword, "")

    # 移除时间模式
    for pattern in TIME_PATTERNS:
        text = re.sub(pattern, "", text)

    # 清理多余空格和标点
    message = text.strip()
    message = re.sub(r'[，。！？、]', "", message)
    message = re.sub(r'\s+', "", message)

    # 如果为空，使用默认备注
    if not message:
        message = "闹钟"

    return message


def format_alarm_confirm(alarm_time: datetime, message: str) -> str:
    """
    格式化闹钟设置确认消息（口语化格式）

    Args:
        alarm_time: 闹钟时间
        message: 备注消息

    Returns:
        str: 确认消息
    """
    now = datetime.now()
    today = now.date()
    tomorrow = today + timedelta(days=1)
    alarm_date = alarm_time.date()

    # 判断是今天、明天还是其他日期
    if alarm_date == today:
        date_str = "今天"
    elif alarm_date == tomorrow:
        date_str = "明天"
    else:
        # 其他日期，显示月日
        date_str = f"{alarm_time.month}月{alarm_time.day}日"

    # 口语化时间格式：16点32分
    hour = alarm_time.hour
    minute = alarm_time.minute

    if minute == 0:
        time_str = f"{hour}点"
    else:
        time_str = f"{hour}点{minute}分"

    # 组合回复
    if message == "闹钟":
        return f"好的，{date_str}{time_str}提醒您"
    else:
        return f"好的，{date_str}{time_str}的{message}"
