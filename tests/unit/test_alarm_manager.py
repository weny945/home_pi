"""
闹钟管理器单元测试
Alarm Manager Unit Tests
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from src.alarm.alarm_storage import AlarmStorage, Alarm
from src.alarm.alarm_manager import AlarmManager


class TestAlarmStorage:
    """闹钟存储测试"""

    @pytest.fixture
    def temp_db(self):
        """临时数据库"""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test_alarms.db"

        yield str(db_path)

        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def storage(self, temp_db):
        """存储实例"""
        return AlarmStorage(temp_db)

    def test_add_alarm(self, storage):
        """测试添加闹钟"""
        alarm_time = datetime.now() + timedelta(hours=1)
        alarm_id = storage.add_alarm(alarm_time, "测试闹钟")

        assert alarm_id > 0

    def test_get_alarm(self, storage):
        """测试获取单个闹钟"""
        alarm_time = datetime.now() + timedelta(hours=1)
        alarm_id = storage.add_alarm(alarm_time, "测试闹钟")

        alarm = storage.get_alarm(alarm_id)
        assert alarm is not None
        assert alarm.id == alarm_id
        assert alarm.message == "测试闹钟"

    def test_get_all_alarms(self, storage):
        """测试获取所有闹钟"""
        # 添加多个闹钟
        now = datetime.now()
        storage.add_alarm(now + timedelta(hours=1), "闹钟1")
        storage.add_alarm(now + timedelta(hours=2), "闹钟2")
        storage.add_alarm(now + timedelta(hours=3), "闹钟3")

        alarms = storage.get_all_alarms()
        assert len(alarms) == 3

    def test_delete_alarm(self, storage):
        """测试删除闹钟"""
        alarm_time = datetime.now() + timedelta(hours=1)
        alarm_id = storage.add_alarm(alarm_time, "测试闹钟")

        # 删除闹钟
        success = storage.delete_alarm(alarm_id)
        assert success is True

        # 验证已删除
        alarm = storage.get_alarm(alarm_id)
        assert alarm is None

    def test_update_alarm(self, storage):
        """测试更新闹钟"""
        alarm_time = datetime.now() + timedelta(hours=1)
        alarm_id = storage.add_alarm(alarm_time, "原备注")

        # 更新备注
        success = storage.update_alarm(alarm_id, message="新备注")
        assert success is True

        # 验证已更新
        alarm = storage.get_alarm(alarm_id)
        assert alarm.message == "新备注"

    def test_disable_alarm(self, storage):
        """测试禁用闹钟"""
        alarm_time = datetime.now() + timedelta(hours=1)
        alarm_id = storage.add_alarm(alarm_time, "测试闹钟")

        # 禁用闹钟
        success = storage.disable_alarm(alarm_id)
        assert success is True

        # 验证已禁用
        alarm = storage.get_alarm(alarm_id)
        assert alarm.is_active is False

    def test_get_active_alarms(self, storage):
        """测试获取启用的闹钟"""
        now = datetime.now()
        storage.add_alarm(now + timedelta(hours=1), "闹钟1")
        alarm_id2 = storage.add_alarm(now + timedelta(hours=2), "闹钟2")

        # 禁用第二个闹钟
        storage.disable_alarm(alarm_id2)

        # 获取启用的闹钟
        active_alarms = storage.get_active_alarms()
        assert len(active_alarms) == 1
        assert active_alarms[0].message == "闹钟1"

    def test_clear_past_alarms(self, storage):
        """测试清除已过的闹钟"""
        now = datetime.now()

        # 添加一个已过的闹钟
        storage.add_alarm(now - timedelta(hours=1), "已过闹钟")

        # 添加一个未来的闹钟
        storage.add_alarm(now + timedelta(hours=1), "未来闹钟")

        # 清除已过的闹钟
        deleted_count = storage.clear_past_alarms()
        assert deleted_count == 1

        # 验证只剩一个
        alarms = storage.get_all_alarms()
        assert len(alarms) == 1


class TestAlarmManager:
    """闹钟管理器测试"""

    @pytest.fixture
    def temp_db(self):
        """临时数据库"""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test_alarms.db"

        yield str(db_path)

        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def manager(self, temp_db):
        """管理器实例"""
        storage = AlarmStorage(temp_db)
        return AlarmManager(storage=storage)

    def test_add_alarm_with_natural_language(self, manager):
        """测试使用自然语言添加闹钟"""
        alarm = manager.add_alarm("明天早上7点", "叫我起床")

        assert alarm is not None
        assert alarm.message == "叫我起床"

    def test_add_alarm_with_invalid_time(self, manager):
        """测试使用无效时间添加闹钟"""
        alarm = manager.add_alarm("无效的时间", "测试")
        assert alarm is None

    def test_add_alarm_with_past_time(self, manager):
        """测试使用过去时间添加闹钟"""
        # 昨天的时间
        alarm = manager.add_alarm("昨天早上7点", "测试")
        assert alarm is None

    def test_delete_alarm(self, manager):
        """测试删除闹钟"""
        # 先添加一个闹钟
        alarm = manager.add_alarm("明天早上7点", "测试")
        assert alarm is not None

        # 删除闹钟
        success = manager.delete_alarm(alarm.id)
        assert success is True

    def test_list_alarms(self, manager):
        """测试列出闹钟"""
        # 添加多个闹钟
        manager.add_alarm("明天早上7点", "闹钟1")
        manager.add_alarm("明天晚上8点", "闹钟2")

        # 列出闹钟
        alarms = manager.list_alarms()
        assert len(alarms) == 2

    def test_snooze_alarm(self, manager):
        """测试稍后提醒"""
        # 先添加一个闹钟
        alarm = manager.add_alarm("明天早上7点", "测试")
        assert alarm is not None

        # 稍后提醒 10 分钟
        snoozed_alarm = manager.snooze_alarm(alarm.id, 10)
        assert snoozed_alarm is not None

        # 验证新闹钟时间大约在 10 分钟后
        expected_time = datetime.now() + timedelta(minutes=10)
        diff = abs((snoozed_alarm.time - expected_time).total_seconds())
        assert diff < 60.0  # 允许 1 分钟误差

    def test_check_and_trigger_no_alarms(self, manager):
        """测试检查闹钟（无闹钟）"""
        # 不应该抛出异常
        manager.check_and_trigger()
