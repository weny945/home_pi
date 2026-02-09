"""
闹钟管理器 - 调度和触发闹钟
Alarm Manager for Scheduling and Triggering Alarms
"""
import logging
import threading
import time
from datetime import datetime
from typing import Optional, List, Callable

from .alarm_storage import AlarmStorage, Alarm
from .time_parser import parse_alarm_time, format_alarm_time, is_time_in_past

logger = logging.getLogger(__name__)


class AlarmManager:
    """闹钟管理器"""

    def __init__(
        self,
        storage: Optional[AlarmStorage] = None,
        ringtone_callback: Optional[Callable] = None,
        check_interval: float = 1.0
    ):
        """
        初始化闹钟管理器

        Args:
            storage: 闹钟存储（默认创建新实例）
            ringtone_callback: 响铃回调函数（在独立线程中调用）
            check_interval: 检查间隔（秒）
        """
        self._storage = storage or AlarmStorage()
        self._ringtone_callback = ringtone_callback
        self._check_interval = check_interval

        # 闹钟检查线程
        self._check_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # 记录已触发的闹钟（避免重复触发）
        self._triggered_alarms = set()

        logger.info(f"闹钟管理器初始化完成 (检查间隔: {check_interval}s)")

    def add_alarm(self, time_text, message: str = "闹钟", alarm_time=None, theme: str = "铃声") -> Optional[Alarm]:
        """
        添加闹钟（自然语言时间或 datetime 对象）

        Args:
            time_text: 时间文本（如"明天早上7点"、"半小时后"）或 datetime 对象
            message: 闹钟备注
            alarm_time: 已解析的 datetime 对象（可选，如果提供则跳过解析）
            theme: 主题（"铃声" = 播放铃声，其他 = 播放打气词）

        Returns:
            Alarm: 闹钟对象，失败返回 None
        """
        # 如果已经提供了 datetime 对象，直接使用
        if alarm_time is None:
            # 解析时间
            alarm_time = parse_alarm_time(time_text)

            if not alarm_time:
                logger.error(f"无法解析时间: {time_text}")
                return None

        # 检查时间是否已过
        if is_time_in_past(alarm_time):
            logger.warning(f"闹钟时间已过: {alarm_time}")
            return None

        # 添加到数据库
        alarm_id = self._storage.add_alarm(alarm_time, message, theme)

        # 创建闹钟对象
        alarm = Alarm(
            id=alarm_id,
            time=alarm_time,
            message=message,
            is_active=True,
            theme=theme
        )

        logger.info(f"✓ 闹钟设置成功: {alarm}")
        return alarm

    def delete_alarm(self, alarm_id: int) -> bool:
        """
        删除闹钟

        Args:
            alarm_id: 闹钟 ID

        Returns:
            bool: 是否删除成功
        """
        success = self._storage.delete_alarm(alarm_id)

        if success:
            logger.info(f"✓ 闹钟删除成功: ID={alarm_id}")
        else:
            logger.warning(f"闹钟删除失败: ID={alarm_id}")

        return success

    def list_alarms(self) -> List[Alarm]:
        """
        列出所有闹钟

        Returns:
            List[Alarm]: 闹钟列表
        """
        alarms = self._storage.get_all_alarms()

        if not alarms:
            logger.info("当前没有闹钟")
        else:
            logger.info(f"当前有 {len(alarms)} 个闹钟")
            for alarm in alarms:
                logger.info(f"  - {alarm}")

        return alarms

    def snooze_alarm(self, alarm_id: int, minutes: int = 10) -> Optional[Alarm]:
        """
        稍后提醒（推迟闹钟）

        Args:
            alarm_id: 闹钟 ID
            minutes: 推迟分钟数

        Returns:
            Alarm: 新闹钟对象，失败返回 None
        """
        from datetime import timedelta

        # 获取原闹钟
        original_alarm = self._storage.get_alarm(alarm_id)
        if not original_alarm:
            logger.warning(f"闹钟不存在: ID={alarm_id}")
            return None

        # 计算新时间
        new_time = datetime.now() + timedelta(minutes=minutes)

        # 禁用原闹钟
        self._storage.disable_alarm(alarm_id)

        # 创建新闹钟
        new_message = f"{original_alarm.message} (稍后提醒)"
        new_alarm_id = self._storage.add_alarm(new_time, new_message)

        # 创建闹钟对象
        new_alarm = Alarm(
            id=new_alarm_id,
            time=new_time,
            message=new_message,
            is_active=True
        )

        logger.info(f"✓ 稍后提醒: {minutes}分钟后 ({new_time.strftime('%H:%M')})")
        return new_alarm

    def check_and_trigger(self) -> None:
        """
        检查并触发闹钟（在状态机主循环中调用）

        注意：此方法应该频繁调用（如每秒一次）
        """
        now = datetime.now()

        # 获取所有启用的闹钟
        active_alarms = self._storage.get_active_alarms()

        for alarm in active_alarms:
            # 检查是否应该触发
            if alarm.time <= now:
                # 避免重复触发
                if alarm.id not in self._triggered_alarms:
                    self._trigger_alarm(alarm)
                    self._triggered_alarms.add(alarm.id)

                    # 禁用已触发的闹钟
                    self._storage.disable_alarm(alarm.id)

        # 清理旧的触发记录（每天清理一次）
        if int(time.time()) % 86400 == 0:
            self._triggered_alarms.clear()

    def _trigger_alarm(self, alarm: Alarm) -> None:
        """
        触发闹钟

        Args:
            alarm: 闹钟对象
        """
        logger.info("=" * 60)
        logger.info(f"⏰ 闹钟触发: {alarm}")
        logger.info("=" * 60)

        # 如果有响铃回调，在独立线程中调用
        if self._ringtone_callback:
            logger.info("播放闹钟铃声...")

            # 在独立线程中播放铃声（避免阻塞主循环）
            ringtone_thread = threading.Thread(
                target=self._ringtone_callback,
                kwargs={"alarm": alarm},
                daemon=True
            )
            ringtone_thread.start()

        else:
            logger.warning("响铃回调未设置，闹钟静默触发")

    def start_background_check(self) -> None:
        """启动后台检查线程（可选）"""
        if self._check_thread is not None:
            logger.warning("后台检查线程已在运行")
            return

        self._stop_event.clear()
        self._check_thread = threading.Thread(
            target=self._background_check_loop,
            daemon=True
        )
        self._check_thread.start()

        logger.info("后台检查线程已启动")

    def stop_background_check(self) -> None:
        """停止后台检查线程"""
        if self._check_thread is None:
            return

        self._stop_event.set()
        self._check_thread.join(timeout=2.0)
        self._check_thread = None

        logger.info("后台检查线程已停止")

    def _background_check_loop(self) -> None:
        """后台检查循环"""
        while not self._stop_event.is_set():
            try:
                self.check_and_trigger()
            except Exception as e:
                logger.error(f"后台检查失败: {e}")

            # 等待下一次检查
            self._stop_event.wait(self._check_interval)

    def get_storage(self) -> AlarmStorage:
        """获取存储对象"""
        return self._storage
