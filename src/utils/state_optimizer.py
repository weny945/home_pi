"""
状态转换优化器
State Transition Optimizer

P2-5 优化: 优化状态转换逻辑，使用状态转换表
"""
import logging
from typing import Dict, Callable, Optional, Set
from enum import Enum

logger = logging.getLogger(__name__)


class StateTransitionOptimizer:
    """状态转换优化器（P2-5）"""

    def __init__(self):
        """初始化状态转换优化器"""
        # 状态转换表：定义允许的状态转换
        self._allowed_transitions: Dict[str, Set[str]] = {
            'idle': {'wakeup', 'error'},
            'wakeup': {'listening', 'error'},
            'listening': {'processing', 'idle', 'wakeup', 'error'},
            'processing': {'speaking', 'idle', 'listening', 'wakeup', 'error'},
            'speaking': {'idle', 'listening', 'wakeup', 'error'},
            'error': {'idle'},
        }

        # 状态转换钩子：转换前后的回调
        self._before_hooks: Dict[tuple, Callable] = {}
        self._after_hooks: Dict[tuple, Callable] = {}

        # 转换计数统计
        self._transition_counts: Dict[tuple, int] = {}
        self._total_transitions = 0

    def is_allowed(self, from_state: str, to_state: str) -> bool:
        """
        检查状态转换是否允许

        Args:
            from_state: 源状态
            to_state: 目标状态

        Returns:
            bool: 是否允许转换
        """
        from_lower = from_state.lower()
        to_lower = to_state.lower()

        if from_lower not in self._allowed_transitions:
            logger.warning(f"未知的源状态: {from_state}")
            return False

        return to_lower in self._allowed_transitions[from_lower]

    def register_before_hook(
        self,
        from_state: str,
        to_state: str,
        hook: Callable
    ) -> None:
        """
        注册转换前钩子

        Args:
            from_state: 源状态
            to_state: 目标状态
            hook: 钩子函数
        """
        key = (from_state.lower(), to_state.lower())
        self._before_hooks[key] = hook
        logger.debug(f"注册转换前钩子: {from_state} -> {to_state}")

    def register_after_hook(
        self,
        from_state: str,
        to_state: str,
        hook: Callable
    ) -> None:
        """
        注册转换后钩子

        Args:
            from_state: 源状态
            to_state: 目标状态
            hook: 钩子函数
        """
        key = (from_state.lower(), to_state.lower())
        self._after_hooks[key] = hook
        logger.debug(f"注册转换后钩子: {from_state} -> {to_state}")

    def execute_transition(
        self,
        from_state: str,
        to_state: str,
        context: Optional[Dict] = None
    ) -> bool:
        """
        执行状态转换

        P2-5 优化: 统一的状态转换执行逻辑

        Args:
            from_state: 源状态
            to_state: 目标状态
            context: 转换上下文

        Returns:
            bool: 是否成功执行转换
        """
        from_lower = from_state.lower()
        to_lower = to_state.lower()
        key = (from_lower, to_lower)

        # 检查转换是否允许
        if not self.is_allowed(from_state, to_state):
            logger.error(f"❌ 不允许的状态转换: {from_state} -> {to_state}")
            return False

        try:
            # 执行转换前钩子
            if key in self._before_hooks:
                self._before_hooks[key](context)
                logger.debug(f"执行转换前钩子: {from_state} -> {to_state}")

            # 记录转换统计
            self._transition_counts[key] = self._transition_counts.get(key, 0) + 1
            self._total_transitions += 1

            # 记录转换日志
            logger.debug(f"状态转换: {from_state} -> {to_state}")

            # 执行转换后钩子
            if key in self._after_hooks:
                self._after_hooks[key](context)
                logger.debug(f"执行转换后钩子: {from_state} -> {to_state}")

            return True

        except Exception as e:
            logger.error(f"状态转换失败: {from_state} -> {to_state}, 错误: {e}")
            return False

    def get_stats(self) -> Dict[str, any]:
        """
        获取转换统计信息

        Returns:
            统计信息字典
        """
        return {
            'total_transitions': self._total_transitions,
            'transition_counts': dict(self._transition_counts),
            'most_common': sorted(
                self._transition_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5] if self._transition_counts else []
        }


# 全局状态转换优化器实例
_transition_optimizer: Optional[StateTransitionOptimizer] = None


def get_transition_optimizer() -> StateTransitionOptimizer:
    """获取全局状态转换优化器"""
    global _transition_optimizer
    if _transition_optimizer is None:
        _transition_optimizer = StateTransitionOptimizer()
    return _transition_optimizer
