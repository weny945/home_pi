"""
字符串常量缓存
String Constants Cache

P2-3 优化: 缓存常用字符串，避免重复创建
"""

# 状态名称常量
STATE_NAMES = {
    'IDLE': 'idle',
    'WAKEUP': 'wakeup',
    'LISTENING': 'listening',
    'PROCESSING': 'processing',
    'SPEAKING': 'speaking',
    'ERROR': 'error'
}

# 常用日志消息模板
LOG_TEMPLATES = {
    'state_transition': "状态转换: {} → {}",
    'cooldown_remaining': "冷却期中，剩余 {:.1f}s",
    'noise_floor': "环境底噪: {:.4f}, 阈值: {:.4f}",
    'detection_confidence': "检测到唤醒词: {} (置信度: {:.3f})",
}

# 常用提示语
PROMPT_MESSAGES = {
    'wake_detected': "🎤 检测到唤醒词！",
    'listening_start': "🎧 开始监听用户语音...",
    'processing_start': "🔄 开始处理用户输入...",
    'error_occurred': "❌ 发生错误",
}

# 音频质量检查消息
QUALITY_MESSAGES = {
    'too_short': "音频太短 ({:.2f}s < {:.2f}s)",
    'low_energy': "音频能量太低 ({:.4f} < {:.4f})",
    'short_speech': "有效语音时长太短 ({:.2f}s < {:.2f}s)",
}

# 格式化辅助函数
def format_log(template_key: str, *args) -> str:
    """
    使用缓存的模板格式化日志消息

    P2-3 优化: 避免重复创建字符串

    Args:
        template_key: 模板键名
        *args: 格式化参数

    Returns:
        str: 格式化后的字符串
    """
    template = LOG_TEMPLATES.get(template_key, template_key)
    return template.format(*args)


def get_state_name(state) -> str:
    """
    获取状态名称

    P2-3 优化: 使用预定义的常量

    Args:
        state: 状态对象

    Returns:
        str: 状态名称
    """
    return STATE_NAMES.get(state.name.upper(), state.name.lower())
