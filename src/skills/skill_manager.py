"""
技能管理器
Skill Manager for Voice Assistant

Phase 1.5: 为未来功能扩展（智能家居控制、音乐播放等）预留接口
"""
import logging
from typing import Callable, Dict, Any, Optional

logger = logging.getLogger(__name__)


class SkillManager:
    """技能管理器 (Phase 1.5 框架)"""

    def __init__(self, config: dict):
        """
        初始化技能管理器

        Args:
            config: 配置字典
        """
        self._enabled = config.get("enabled", False)
        self._skills: Dict[str, Callable] = {}
        self._skill_metadata: Dict[str, Dict[str, Any]] = {}

        if self._enabled:
            logger.info("✓ 技能管理器已启用")
        else:
            logger.info("技能管理器已禁用（Phase 1.5 默认禁用）")

    def register_skill(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        parameters: Dict[str, Any] = None
    ) -> None:
        """
        注册技能

        Args:
            name: 技能名称
            handler: 技能处理函数
            description: 技能描述
            parameters: 参数配置
        """
        self._skills[name] = handler
        self._skill_metadata[name] = {
            "description": description,
            "parameters": parameters or {}
        }
        logger.info(f"注册技能: {name} - {description}")

    def unregister_skill(self, name: str) -> None:
        """
        注销技能

        Args:
            name: 技能名称
        """
        if name in self._skills:
            del self._skills[name]
            del self._skill_metadata[name]
            logger.info(f"注销技能: {name}")

    def has_skill(self, name: str) -> bool:
        """
        检查技能是否存在

        Args:
            name: 技能名称

        Returns:
            bool: 是否存在
        """
        return name in self._skills

    def execute_skill(self, skill_name: str, **kwargs) -> Any:
        """
        执行技能

        Args:
            skill_name: 技能名称
            **kwargs: 技能参数

        Returns:
            Any: 技能执行结果
        """
        if not self._enabled:
            logger.warning("技能管理器未启用")
            return None

        if skill_name not in self._skills:
            logger.warning(f"技能不存在: {skill_name}")
            return None

        try:
            logger.info(f"执行技能: {skill_name} (参数: {kwargs})")
            handler = self._skills[skill_name]
            result = handler(**kwargs)
            logger.info(f"技能执行完成: {skill_name}")
            return result
        except Exception as e:
            logger.error(f"技能执行失败 ({skill_name}): {e}")
            return None

    def list_skills(self) -> Dict[str, Dict[str, Any]]:
        """
        列出所有已注册的技能

        Returns:
            dict: 技能元数据
        """
        return self._skill_metadata.copy()

    def get_skill_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取技能信息

        Args:
            name: 技能名称

        Returns:
            dict: 技能元数据
        """
        return self._skill_metadata.get(name)

    def is_enabled(self) -> bool:
        """
        检查技能管理器是否启用

        Returns:
            bool: 是否启用
        """
        return self._enabled

    def clear_all_skills(self) -> None:
        """清空所有技能"""
        self._skills.clear()
        self._skill_metadata.clear()
        logger.info("已清空所有技能")


# ============================================================
# 示例技能（Phase 1.5 演示）
# ============================================================

def example_control_light(action: str, device_id: str = None) -> str:
    """
    示例技能：控制灯光

    Args:
        action: 动作 (on/off)
        device_id: 设备ID

    Returns:
        str: 执行结果
    """
    logger.info(f"[示例技能] 控制灯光: {action} (设备: {device_id or '默认'})")
    return f"已{'打开' if action == 'on' else '关闭'}灯光"

def example_play_music(song: str = None) -> str:
    """
    示例技能：播放音乐

    Args:
        song: 歌曲名称

    Returns:
        str: 执行结果
    """
    logger.info(f"[示例技能] 播放音乐: {song or '随机播放'}")
    return f"正在播放: {song or '随机音乐'}"

def example_get_weather(location: str = "北京") -> str:
    """
    示例技能：查询天气

    Args:
        location: 地点

    Returns:
        str: 天气信息
    """
    logger.info(f"[示例技能] 查询天气: {location}")
    return f"{location}今天天气晴朗，温度 25°C"
