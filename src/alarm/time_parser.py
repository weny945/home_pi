"""
时间解析器 - 解析自然语言时间表达
Time Parser for Natural Language Time Expressions

Phase 1.7: 新增 LLM 辅助解析功能
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# 尝试导入 dateparser
try:
    import dateparser
    DATEPARSER_AVAILABLE = True
except ImportError:
    DATEPARSER_AVAILABLE = False
    logger.warning("dateparser 未安装，时间解析功能将受限")


# 模糊时段映射
TIME_MAPPING = {
    "早上": "07:00",
    "上午": "09:00",
    "中午": "12:00",
    "下午": "14:00",
    "晚上": "18:00",
    "半夜": "00:00",
    "凌晨": "02:00",
}

# 时间单位映射（用于相对时间）
TIME_UNITS = {
    "秒": 1,
    "分钟": 60,
    "小时": 3600,
    "天": 86400,
}

# 中文数字映射（用于相对时间解析）
CHINESE_NUMBERS = {
    "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
    "半": 0.5
}


def parse_alarm_time(text: str, llm_engine=None) -> Optional[datetime]:
    """
    解析闹钟时间（支持自然语言）

    Args:
        text: 用户输入的时间文本，如 "明天早上7点"、"半小时后"
        llm_engine: LLM 引擎（可选，用于复杂表达解析）

    Returns:
        datetime: 解析后的时间，失败返回 None

    Examples:
        >>> parse_alarm_time("明天早上7点")
        datetime.datetime(2026, 1, 27, 7, 0)
        >>> parse_alarm_time("半小时后")
        datetime.datetime(2026, 1, 26, 12, 30)
        >>> parse_alarm_time("定下午3点的闹钟", llm_engine)
        datetime.datetime(2026, 1, 27, 15, 0)
    """
    if not text:
        return None

    text = text.strip()

    # 方法1：使用 dateparser（推荐）
    if DATEPARSER_AVAILABLE:
        result = _parse_with_dateparser(text)
        if result:
            return result

    # 方法2：使用内置解析器（相对时间）
    result = _parse_relative_time(text)
    if result:
        return result

    # 方法3：使用内置解析器（模糊时段）
    result = _parse_fuzzy_time(text)
    if result:
        return result

    # 方法4：使用 LLM 辅助解析（Phase 1.7 新增）
    if llm_engine:
        logger.info(f"传统方法无法解析，尝试使用 LLM 解析: {text}")
        result = _parse_with_llm(text, llm_engine)
        if result:
            return result

    logger.warning(f"无法解析时间: {text}")
    return None


def _parse_with_dateparser(text: str) -> Optional[datetime]:
    """
    使用 dateparser 解析时间

    Args:
        text: 时间文本

    Returns:
        datetime: 解析后的时间
    """
    try:
        # 预处理：替换模糊时段
        processed_text = text
        for keyword, default_time in TIME_MAPPING.items():
            if keyword in processed_text:
                processed_text = processed_text.replace(keyword, default_time)
                logger.debug(f"时间映射: {keyword} → {default_time}")

        # 使用 dateparser 解析
        settings = {
            'PREFER_DATES_FROM': 'future',  # 优先选择未来的日期
            'TIMEZONE': 'local',  # 使用本地时区
        }

        result = dateparser.parse(
            processed_text,
            languages=['zh'],
            settings=settings
        )

        if result:
            logger.info(f"dateparser 解析成功: {text} → {result}")
            return result

    except Exception as e:
        logger.warning(f"dateparser 解析失败: {e}")

    return None


def _parse_relative_time(text: str) -> Optional[datetime]:
    """
    解析相对时间（如"半小时后"、"10分钟后"、"两分钟之后"）

    Args:
        text: 时间文本

    Returns:
        datetime: 解析后的时间
    """
    import re

    # 匹配模式: "数字+单位+(之)?(以)?后?"
    # 支持阿拉伯数字和中文数字
    # 例如: "30分钟后", "2小时后", "1天后", "2分钟以后", "两分钟之后", "半小时后"
    pattern = r'([一二三四五六七八九十百零半\d\.]+)\s*(秒|分钟|小时|天)\s*(?:之)?(?:以)?后?'
    match = re.search(pattern, text)

    if match:
        try:
            number_str = match.group(1)
            unit = match.group(2)

            # 转换中文数字为阿拉伯数字
            value = _chinese_number_to_number(number_str)

            # 计算秒数
            if unit in TIME_UNITS:
                seconds = value * TIME_UNITS[unit]
                result = datetime.now() + timedelta(seconds=seconds)

                logger.info(f"相对时间解析成功: {text} → {result}")
                return result

        except Exception as e:
            logger.warning(f"相对时间解析失败: {e}")

    return None


def _chinese_number_to_number(text: str) -> int:
    """
    将中文数字转换为阿拉伯数字

    Args:
        text: 中文数字（如"两"、"三十"、"半"）

    Returns:
        int: 阿拉伯数字
    """
    # 直接查找映射
    if text in CHINESE_NUMBERS:
        return CHINESE_NUMBERS[text]

    # 处理"几十"的情况（如"三十"）
    import re
    if text.endswith("十"):
        if text == "十":
            return 10
        else:
            # "三十" -> "三" + "十"
            prefix = text[:-1]
            if prefix in CHINESE_NUMBERS:
                return CHINESE_NUMBERS[prefix] * 10

    # 尝试直接转换为 float（支持"0.5"这样的输入）
    try:
        return int(float(text))
    except (ValueError, TypeError):
        pass

    logger.warning(f"无法解析中文数字: {text}")
    return 0


def _parse_fuzzy_time(text: str) -> Optional[datetime]:
    """
    解析模糊时段（如"明天"、"早上"）

    Args:
        text: 时间文本

    Returns:
        datetime: 解析后的时间
    """
    import re

    now = datetime.now()

    # 检查是否包含"明天"
    if "明天" in text:
        target_date = now + timedelta(days=1)

        # 查找小时
        hour_match = re.search(r'(\d+)点', text)
        if hour_match:
            hour = int(hour_match.group(1))
            # 限制小时范围 0-23
            hour = min(23, max(0, hour))
        else:
            # 如果没有指定小时，使用默认时间（早上7点）
            hour = 7

        # 查找分钟
        minute_match = re.search(r'(\d+)分', text)
        if minute_match:
            minute = int(minute_match.group(1))
        else:
            minute = 0

        result = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

        logger.info(f"模糊时间解析成功: {text} → {result}")
        return result

    # 检查"今天"
    if "今天" in text:
        hour_match = re.search(r'(\d+)点', text)
        if hour_match:
            hour = int(hour_match.group(1))
            hour = min(23, max(0, hour))

            minute_match = re.search(r'(\d+)分', text)
            minute = int(minute_match.group(1)) if minute_match else 0

            result = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # 如果时间已过，则设为明天
            if result < now:
                result += timedelta(days=1)

            logger.info(f"模糊时间解析成功: {text} → {result}")
            return result

    return None


def format_alarm_time(alarm_time: datetime) -> str:
    """
    格式化闹钟时间为自然语言

    Args:
        alarm_time: 闹钟时间

    Returns:
        str: 格式化的时间字符串
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

    # 格式化时间
    time_str = alarm_time.strftime("%H:%M")

    return f"{date_str} {time_str}"


def _parse_with_llm(text: str, llm_engine) -> Optional[datetime]:
    """
    使用 LLM 解析复杂的时间表达

    Args:
        text: 用户输入的时间文本
        llm_engine: LLM 引擎

    Returns:
        datetime: 解析后的时间，失败返回 None
    """
    if not llm_engine:
        logger.warning("LLM 引擎未配置，无法使用 LLM 解析时间")
        return None

    try:
        now = datetime.now()
        current_time_str = now.strftime("%Y年%m月%d日 %H:%M:%S")

        # 构建提示词
        prompt = f"""你是一个时间解析助手。请从用户的输入中提取闹钟时间。

当前时间：{current_time_str}

用户输入：{text}

请严格按照以下 JSON 格式返回时间信息：
{{
    "has_time": true,
    "year": 2026,
    "month": 1,
    "day": 27,
    "hour": 15,
    "minute": 30,
    "reason": "解析说明"
}}

注意：
1. 只返回 JSON，不要有其他内容
2. 如果用户输入没有明确的时间，设置 has_time 为 false
3. year/month/day 使用数字，不要有前导零
4. hour 使用 24 小时制（0-23）
5. minute 使用 0-59
6. 相对时间（如"半小时后"）请基于当前时间计算
7. 如果日期没有明确指定，优先选择未来的日期

请返回 JSON："""

        # 调用 LLM
        logger.info(f"调用 LLM 解析时间: {text}")
        result = llm_engine.chat(prompt, system_prompt="你是一个精确的时间解析助手。")

        # 提取 LLM 返回的内容
        llm_reply = result.get("reply", "")

        logger.debug(f"LLM 原始返回: {llm_reply}")

        # 解析 JSON
        # 尝试提取 JSON（可能包含其他文本）
        import re
        json_match = re.search(r'\{[^{}]*\}', llm_reply)
        if json_match:
            json_str = json_match.group(0)
            time_info = json.loads(json_str)

            if time_info.get("has_time"):
                # 构建 datetime 对象
                try:
                    parsed_time = datetime(
                        year=time_info["year"],
                        month=time_info["month"],
                        day=time_info["day"],
                        hour=time_info["hour"],
                        minute=time_info["minute"],
                        second=0
                    )

                    logger.info(f"✅ LLM 时间解析成功: {text} → {parsed_time}")
                    logger.info(f"   解析说明: {time_info.get('reason', '')}")
                    return parsed_time

                except (KeyError, ValueError) as e:
                    logger.error(f"LLM 返回的 JSON 格式不正确: {e}")
                    logger.error(f"   JSON: {time_info}")
            else:
                logger.info(f"LLM 判断输入中没有明确的时间")
        else:
            logger.warning(f"LLM 返回的内容中未找到有效的 JSON: {llm_reply}")

    except Exception as e:
        logger.error(f"LLM 时间解析失败: {e}")
        import traceback
        logger.error(traceback.format_exc())

    return None


def is_time_in_past(alarm_time: datetime) -> bool:
    """
    检查时间是否已过

    Args:
        alarm_time: 闹钟时间

    Returns:
        bool: 是否已过
    """
    return alarm_time < datetime.now()
