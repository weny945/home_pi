"""
夜间免打扰功能演示
Night Mode (Quiet Hours) Feature Demo

运行方式：
    python tests/manual/demo_night_mode.py
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime, time


def demo_quiet_hours():
    """演示静默时段功能"""
    print("=" * 70)
    print("夜间免打扰功能演示")
    print("=" * 70)

    print("\n功能说明：")
    print("  - 静默时段：23:00 - 06:00")
    print("  - 在静默时段内：语音助手不会被唤醒")
    print("  - 但闹钟功能仍然正常工作")

    print("\n" + "=" * 70)
    print("时间状态检查")
    print("=" * 70)

    # 模拟静默时段判断逻辑
    def is_in_quiet_hours(current_time: datetime, start_time: time, end_time: time) -> bool:
        """检查是否在静默时段内"""
        current = current_time.time()

        # 处理跨日情况
        if start_time > end_time:
            # 跨日：当前时间 >= start_time 或 <= end_time
            return current >= start_time or current <= end_time
        else:
            # 同日：start_time <= 当前时间 <= end_time
            return start_time <= current <= end_time

    quiet_start = time(23, 0)
    quiet_end = time(6, 0)

    # 测试不同时间
    test_times = [
        ("晚上10:00", 22, 0),
        ("晚上11:00", 23, 0),
        ("凌晨2:00", 2, 0),
        ("早上6:00", 6, 0),
        ("早上6:01", 6, 1),
        ("早上7:00", 7, 0),
        ("下午2:00", 14, 0),
    ]

    for name, hour, minute in test_times:
        test_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        is_quiet = is_in_quiet_hours(test_time, quiet_start, quiet_end)

        if is_quiet:
            status = "🌙 静默（不会被唤醒，闹钟正常）"
        else:
            status = "🔊 正常（可以被唤醒）"

        print(f"{name:12} - {status}")

    print("\n" + "=" * 70)
    print("\n使用场景：")
    print("  1. 晚上11点后，语音助手进入静默模式")
    print("  2. 夜间环境噪音（如电视、梦话）不会误唤醒")
    print("  3. 早上6点的闹钟仍然会响铃，唤醒你起床")
    print("  4. 早上6点后，可以正常使用语音唤醒功能")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    demo_quiet_hours()
