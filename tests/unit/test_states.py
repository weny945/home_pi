"""
状态枚举测试
Tests for State Enum
"""
import pytest
from enum import Enum
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.state_machine.states import State


@pytest.mark.unit
class TestState:
    """状态枚举测试类"""

    def test_state_values(self):
        """测试状态值"""
        assert State.IDLE.value == "idle"
        assert State.WAKEUP.value == "wakeup"
        assert State.LISTENING.value == "listening"
        assert State.PROCESSING.value == "processing"
        assert State.SPEAKING.value == "speaking"
        assert State.ERROR.value == "error"

    def test_state_string_representation(self):
        """测试状态字符串表示"""
        assert str(State.IDLE) == "idle"
        assert str(State.WAKEUP) == "wakeup"

    def test_state_repr(self):
        """测试状态 repr"""
        assert repr(State.IDLE) == "State.IDLE"
        assert repr(State.WAKEUP) == "State.WAKEUP"

    def test_state_equality(self):
        """测试状态相等性"""
        assert State.IDLE == State.IDLE
        assert State.IDLE != State.WAKEUP

    def test_state_in_collection(self):
        """测试状态在集合中"""
        states = [State.IDLE, State.WAKEUP, State.LISTENING]
        assert State.IDLE in states
        assert State.ERROR not in states
