"""
闹钟功能端到端测试
Alarm End-to-End Tests

运行方式：
    pytest tests/manual/test_alarm_e2e.py -v -s
"""
import pytest
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from src.alarm import AlarmManager, parse_alarm_time


class TestAlarmE2E:
    """闹钟功能端到端测试"""

    @pytest.fixture
    def temp_db(self):
        """临时数据库"""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test_e2e_alarms.db"

        yield str(db_path)

        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def manager(self, temp_db):
        """管理器实例"""
        from src.alarm.alarm_storage import AlarmStorage
        storage = AlarmStorage(temp_db)
        return AlarmManager(storage=storage)

    def test_set_and_list_alarms(self, manager):
        """测试：设置和查询闹钟"""
        print("\n" + "="*60)
        print("测试：设置和查询闹钟")
        print("="*60)

        # 设置闹钟
        print("\n1. 设置闹钟：明天早上7点")
        alarm = manager.add_alarm("明天早上7点", "叫我起床")
        assert alarm is not None
        print(f"   ✓ 闹钟设置成功: {alarm}")

        # 设置第二个闹钟
        print("\n2. 设置闹钟：30分钟后")
        alarm2 = manager.add_alarm("30分钟后", "会议提醒")
        assert alarm2 is not None
        print(f"   ✓ 闹钟设置成功: {alarm2}")

        # 查询闹钟
        print("\n3. 查询所有闹钟")
        alarms = manager.list_alarms()
        assert len(alarms) == 2
        print(f"   ✓ 当前有 {len(alarms)} 个闹钟")

    def test_delete_alarm(self, manager):
        """测试：删除闹钟"""
        print("\n" + "="*60)
        print("测试：删除闹钟")
        print("="*60)

        # 先设置闹钟
        print("\n1. 设置闹钟：明天早上7点")
        alarm = manager.add_alarm("明天早上7点", "测试闹钟")
        assert alarm is not None
        print(f"   ✓ 闹钟设置成功: ID={alarm.id}")

        # 删除闹钟
        print(f"\n2. 删除闹钟：ID={alarm.id}")
        success = manager.delete_alarm(alarm.id)
        assert success is True
        print(f"   ✓ 闹钟删除成功")

        # 验证已删除
        print("\n3. 查询所有闹钟")
        alarms = manager.list_alarms()
        assert len(alarms) == 0
        print(f"   ✓ 闹钟已删除，当前无闹钟")

    def test_snooze_alarm(self, manager):
        """测试：稍后提醒"""
        print("\n" + "="*60)
        print("测试：稍后提醒")
        print("="*60)

        # 先设置闹钟
        print("\n1. 设置闹钟：明天早上7点")
        alarm = manager.add_alarm("明天早上7点", "测试闹钟")
        assert alarm is not None
        print(f"   ✓ 闹钟设置成功: ID={alarm.id}")

        # 稍后提醒
        print("\n2. 稍后提醒：10分钟")
        snoozed_alarm = manager.snooze_alarm(alarm.id, 10)
        assert snoozed_alarm is not None
        print(f"   ✓ 稍后提醒设置成功: {snoozed_alarm.time.strftime('%H:%M')}")

        # 验证原闹钟已禁用
        print("\n3. 验证原闹钟状态")
        storage = manager.get_storage()
        original_alarm = storage.get_alarm(alarm.id)
        assert original_alarm.is_active is False
        print(f"   ✓ 原闹钟已禁用")

    def test_alarm_triggering_simulation(self, manager):
        """测试：闹钟触发模拟（使用未来时间）"""
        print("\n" + "="*60)
        print("测试：闹钟触发模拟")
        print("="*60)

        # 设置一个 2 秒后的闹钟
        print("\n1. 设置闹钟：2秒后")
        alarm_time = datetime.now() + timedelta(seconds=2)
        from src.alarm.alarm_storage import AlarmStorage
        storage = manager.get_storage()
        alarm_id = storage.add_alarm(alarm_time, "测试闹钟")
        print(f"   ✓ 闹钟设置成功: ID={alarm_id}, 时间={alarm_time.strftime('%H:%M:%S')}")

        # 等待触发
        print("\n2. 等待闹钟触发...")
        for i in range(5):
            time.sleep(1)
            manager.check_and_trigger()
            print(f"   检查闹钟... ({i+1}/5)")

            # 检查闹钟是否已触发
            alarm = storage.get_alarm(alarm_id)
            if not alarm.is_active:
                print(f"   ✓ 闹钟已触发！")
                break

    def test_intent_detection(self):
        """测试：意图检测"""
        print("\n" + "="*60)
        print("测试：意图检测")
        print("="*60)

        from src.alarm.intent_detector import detect_alarm_intent

        test_cases = [
            ("明天早上7点叫我起床", "set"),
            ("有哪些闹钟", "list"),
            ("取消1号闹钟", "delete"),
            ("停止", "stop_alarm"),
            ("稍后10分钟", "snooze"),
            ("今天天气怎么样", None),
        ]

        for text, expected_action in test_cases:
            print(f"\n检测: {text}")
            intent = detect_alarm_intent(text)

            if expected_action:
                assert intent is not None
                assert intent.action == expected_action
                print(f"   ✓ 意图识别成功: {intent.action}")
            else:
                assert intent is None
                print(f"   ✓ 正确识别为非闹钟意图")


if __name__ == "__main__":
    # 可以直接运行此文件进行快速测试
    pytest.main([__file__, "-v", "-s"])
