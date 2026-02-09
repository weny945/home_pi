"""
智能开关意图检测器
Smart Switch Intent Detector

从用户语音中识别开关控制意图
"""
import logging
import re
from dataclasses import dataclass
from typing import Optional, List

logger = logging.getLogger(__name__)


@dataclass
class SwitchIntent:
    """开关意图"""
    action: str           # 动作: on/off/toggle/query
    device: str           # 设备名称（如"客厅灯"）
    location: str = ""    # 位置（如"客厅"）
    all: bool = False     # 是否控制所有设备

    def __str__(self):
        return f"SwitchIntent(action={self.action}, device={self.device}, all={self.all})"


# 设备类型关键词映射
DEVICE_TYPE_KEYWORDS = {
    "light": ["灯", "照明", "电灯", "灯具"],
    "fan": ["风扇", "吊扇", "排气扇"],
    "socket": ["插座", "插排", "电源"],
    "ac": ["空调", "冷气"],
    "heater": ["暖气", "加热器"],
    "curtain": ["窗帘", "卷帘"],
}

# 位置关键词
LOCATION_KEYWORDS = {
    "客厅": ["客厅", "大厅"],
    "卧室": ["卧室", "睡房"],
    "厨房": ["厨房"],
    "卫生间": ["卫生间", "洗手间", "厕所", "浴室"],
    "阳台": ["阳台"],
    "书房": ["书房", "工作室"],
}

# 动作关键词
ACTION_KEYWORDS = {
    "on": ["打开", "开", "开启", "启动", "亮", "点亮"],
    "off": ["关闭", "关", "熄灭", "关掉", "停"],
    "toggle": ["切换", "反转"],
    "query": ["怎么样", "状态", "是否", "开了没", "关了没"],
}


def detect_switch_intent(
    user_text: str,
    known_devices: List[str] = None
) -> Optional[SwitchIntent]:
    """
    检测开关控制意图

    支持的指令示例：
    - "打开客厅灯" -> action=on, device=客厅灯
    - "关灯" -> action=off, device=灯（默认设备）
    - "打开所有灯" -> action=on, all=True
    - "卧室的灯打开" -> action=on, device=卧室灯

    Args:
        user_text: 用户输入文本
        known_devices: 已知设备名称列表

    Returns:
        SwitchIntent: 开关意图，如果不是开关相关返回 None
    """
    if not user_text:
        return None

    text = user_text.strip()

    # 1. 检测是否为开关控制指令
    has_device_keyword = any(
        keyword in text
        for keywords in DEVICE_TYPE_KEYWORDS.values()
        for keyword in keywords
    )

    # 检查是否包含已知设备名称
    has_known_device = False
    matched_device = ""
    if known_devices:
        for device in known_devices:
            if device in text:
                has_known_device = True
                matched_device = device
                break

    if not has_device_keyword and not has_known_device:
        return None  # 不是开关相关指令

    # 2. 检测动作
    action = None
    for act, keywords in ACTION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                action = act
                break
        if action:
            break

    if not action:
        # 如果没有明确动作，默认为查询
        if any(kw in text for kw in ["怎么样", "状态", "是否", "吗", "呢"]):
            action = "query"
        else:
            return None

    # 3. 检测是否控制所有设备
    is_all = any(keyword in text for keyword in ["所有", "全部", "都", "一切"])

    # 4. 提取设备名称和位置
    location = ""
    device = ""

    # 匹配位置
    for loc_name, loc_keywords in LOCATION_KEYWORDS.items():
        for keyword in loc_keywords:
            if keyword in text:
                location = loc_name
                break
        if location:
            break

    # 如果有已知设备，优先使用
    if matched_device:
        device = matched_device
    elif is_all:
        device = "所有设备"
    else:
        # 尝试从文本中提取设备名称
        device = _extract_device_name(text, location)

        if not device:
            # 使用默认设备名
            device_type = _detect_device_type(text)
            device = f"{location}{device_type}" if location else device_type

    # 5. 创建意图
    intent = SwitchIntent(
        action=action,
        device=device,
        location=location,
        all=is_all
    )

    logger.info(f"✓ 识别到开关意图: {intent}")
    return intent


def _extract_device_name(text: str, location: str) -> str:
    """
    从文本中提取设备名称

    Args:
        text: 输入文本
        location: 已识别的位置

    Returns:
        str: 设备名称
    """
    # 尝试匹配 "位置+设备类型" 模式
    for device_type, keywords in DEVICE_TYPE_KEYWORDS.items():
        for keyword in keywords:
            pattern = f"{location}{keyword}" if location else keyword
            if pattern in text:
                return pattern

    # 如果没有匹配，尝试提取 "的" 字后面的内容
    # 例如："卧室的灯打开" -> "卧室灯"
    if location and "的" in text:
        match = re.search(rf"{location}的(.+?)(?:打开|关闭|切换)", text)
        if match:
            return f"{location}{match.group(1)}"

    return ""


def _detect_device_type(text: str) -> str:
    """
    检测设备类型

    Args:
        text: 输入文本

    Returns:
        str: 设备类型名称
    """
    for device_type, keywords in DEVICE_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                return keyword

    return "设备"


def is_switch_control_text(user_text: str) -> bool:
    """
    快速检查是否为开关控制文本

    Args:
        user_text: 用户输入

    Returns:
        bool: 是否可能包含开关控制意图
    """
    # 检查动作关键词
    has_action = any(
        keyword in user_text
        for keywords in ACTION_KEYWORDS.values()
        for keyword in keywords
    )

    # 检查设备关键词
    has_device = any(
        keyword in user_text
        for keywords in DEVICE_TYPE_KEYWORDS.values()
        for keyword in keywords
    )

    return has_action and has_device


# ============================================================
# 便捷函数
# ============================================================

def format_switch_confirm(intent: SwitchIntent, success: bool = True) -> str:
    """
    格式化开关控制确认回复

    Args:
        intent: 开关意图
        success: 是否成功

    Returns:
        str: 自然语言回复
    """
    if not success:
        return f"抱歉，{intent.device}控制失败"

    action_map = {
        "on": "打开",
        "off": "关闭",
        "toggle": "切换",
        "query": "查询",
    }

    action_text = action_map.get(intent.action, intent.action)

    if intent.all:
        return f"好的，已{action_text}所有设备"
    else:
        return f"好的，已{action_text}{intent.device}"
