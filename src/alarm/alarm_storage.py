"""
闹钟存储 - SQLite 持久化
Alarm Storage with SQLite
"""
import logging
import sqlite3
import threading
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Alarm:
    """闹钟数据类"""
    id: int
    time: datetime
    message: str
    is_active: bool = True
    theme: str = "铃声"  # "铃声" = 播放普通铃声，其他 = 播放打气词
    cheerword: Optional[str] = None  # 预生成的打气词

    def __str__(self) -> str:
        """字符串表示"""
        status = "启用" if self.is_active else "禁用"
        if self.theme == "铃声":
            return f"[{self.id}] {self.time.strftime('%Y-%m-%d %H:%M')} - {self.message} ({status})"
        else:
            theme_str = f" [{self.theme}主题]" if self.theme else ""
            return f"[{self.id}] {self.time.strftime('%Y-%m-%d %H:%M')} - {self.message}{theme_str} ({status})"

    def use_cheerword(self) -> bool:
        """检查是否使用打气词（而不是铃声）"""
        return self.theme not in [None, "", "铃声"]


class AlarmStorage:
    """闹钟存储管理器（线程安全）"""

    def __init__(self, db_path: str = "./data/alarms.db"):
        """
        初始化闹钟存储

        Args:
            db_path: 数据库文件路径
        """
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        # 线程锁（确保线程安全）
        self._lock = threading.Lock()

        # 初始化数据库
        self._init_db()

        logger.info(f"闹钟存储初始化完成: {self._db_path}")

    def _init_db(self) -> None:
        """初始化数据库表"""
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                cursor = conn.cursor()

                # 创建闹钟表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS alarms (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        time TEXT NOT NULL,
                        message TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        theme TEXT DEFAULT '铃声',
                        cheerword TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # 尝试添加 theme 列（兼容已存在的数据库）
                try:
                    cursor.execute('''
                        ALTER TABLE alarms ADD COLUMN theme TEXT DEFAULT '铃声'
                    ''')
                    logger.info("已添加 theme 列")
                except sqlite3.OperationalError:
                    pass  # 列已存在

                # 尝试添加 cheerword 列
                try:
                    cursor.execute('''
                        ALTER TABLE alarms ADD COLUMN cheerword TEXT
                    ''')
                    logger.info("已添加 cheerword 列")
                except sqlite3.OperationalError:
                    pass  # 列已存在

                conn.commit()
                logger.info("数据库表初始化完成")

            except Exception as e:
                logger.error(f"数据库初始化失败: {e}")
                raise
            finally:
                conn.close()

    def add_alarm(self, alarm_time: datetime, message: str = "闹钟", theme: str = "铃声") -> int:
        """
        添加闹钟

        Args:
            alarm_time: 闹钟时间
            message: 闹钟备注
            theme: 主题（"铃声" = 播放铃声，其他 = 播放打气词）

        Returns:
            int: 闹钟 ID
        """
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                cursor = conn.cursor()

                # 插入闹钟
                time_str = alarm_time.strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute('''
                    INSERT INTO alarms (time, message, is_active, theme)
                    VALUES (?, ?, 1, ?)
                ''', (time_str, message, theme))

                conn.commit()
                alarm_id = cursor.lastrowid

                logger.info(f"添加闹钟: ID={alarm_id}, 时间={time_str}, 备注={message}, 主题={theme}")
                return alarm_id

            except Exception as e:
                logger.error(f"添加闹钟失败: {e}")
                conn.rollback()
                raise
            finally:
                conn.close()

    def delete_alarm(self, alarm_id: int) -> bool:
        """
        删除闹钟

        Args:
            alarm_id: 闹钟 ID

        Returns:
            bool: 是否删除成功
        """
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                cursor = conn.cursor()

                # 删除闹钟
                cursor.execute('DELETE FROM alarms WHERE id = ?', (alarm_id,))
                conn.commit()

                deleted = cursor.rowcount > 0
                if deleted:
                    logger.info(f"删除闹钟: ID={alarm_id}")
                else:
                    logger.warning(f"闹钟不存在: ID={alarm_id}")

                return deleted

            except Exception as e:
                logger.error(f"删除闹钟失败: {e}")
                conn.rollback()
                return False
            finally:
                conn.close()

    def get_alarm(self, alarm_id: int) -> Optional[Alarm]:
        """
        获取单个闹钟

        Args:
            alarm_id: 闹钟 ID

        Returns:
            Alarm: 闹钟对象，不存在返回 None
        """
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                cursor = conn.cursor()

                # 尝试获取完整字段（包括 theme 和 cheerword）
                try:
                    cursor.execute('''
                        SELECT id, time, message, is_active, theme, cheerword
                        FROM alarms WHERE id = ?
                    ''', (alarm_id,))
                    row = cursor.fetchone()
                except sqlite3.OperationalError:
                    # 回退到旧字段（兼容已存在的数据库）
                    cursor.execute('''
                        SELECT id, time, message, is_active
                        FROM alarms WHERE id = ?
                    ''', (alarm_id,))
                    row = cursor.fetchone()

                if row:
                    return self._row_to_alarm(row)
                else:
                    return None

            except Exception as e:
                logger.error(f"获取闹钟失败: {e}")
                return None
            finally:
                conn.close()

    def get_all_alarms(self) -> List[Alarm]:
        """
        获取所有闹钟

        Returns:
            List[Alarm]: 闹钟列表
        """
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                cursor = conn.cursor()

                # 尝试获取完整字段
                try:
                    cursor.execute('''
                        SELECT id, time, message, is_active, theme, cheerword
                        FROM alarms ORDER BY time
                    ''')
                    rows = cursor.fetchall()
                except sqlite3.OperationalError:
                    # 回退到旧字段
                    cursor.execute('''
                        SELECT id, time, message, is_active
                        FROM alarms ORDER BY time
                    ''')
                    rows = cursor.fetchall()

                alarms = [self._row_to_alarm(row) for row in rows]
                return alarms

            except Exception as e:
                logger.error(f"获取闹钟列表失败: {e}")
                return []
            finally:
                conn.close()

    def get_active_alarms(self) -> List[Alarm]:
        """
        获取所有启用的闹钟

        Returns:
            List[Alarm]: 启用的闹钟列表
        """
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                cursor = conn.cursor()

                # 尝试获取完整字段
                try:
                    cursor.execute('''
                        SELECT id, time, message, is_active, theme, cheerword
                        FROM alarms
                        WHERE is_active = 1
                        ORDER BY time
                    ''')
                    rows = cursor.fetchall()
                except sqlite3.OperationalError:
                    # 回退到旧字段
                    cursor.execute('''
                        SELECT id, time, message, is_active
                        FROM alarms
                        WHERE is_active = 1
                        ORDER BY time
                    ''')
                    rows = cursor.fetchall()

                alarms = [self._row_to_alarm(row) for row in rows]
                return alarms

            except Exception as e:
                logger.error(f"获取启用闹钟列表失败: {e}")
                return []
            finally:
                conn.close()

    def update_alarm(self, alarm_id: int, **kwargs) -> bool:
        """
        更新闹钟

        Args:
            alarm_id: 闹钟 ID
            **kwargs: 要更新的字段（time, message, is_active）

        Returns:
            bool: 是否更新成功
        """
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                cursor = conn.cursor()

                # 构建更新语句
                updates = []
                values = []

                if 'time' in kwargs:
                    updates.append('time = ?')
                    values.append(kwargs['time'].strftime('%Y-%m-%d %H:%M:%S'))

                if 'message' in kwargs:
                    updates.append('message = ?')
                    values.append(kwargs['message'])

                if 'is_active' in kwargs:
                    updates.append('is_active = ?')
                    values.append(1 if kwargs['is_active'] else 0)

                if not updates:
                    return False

                values.append(alarm_id)
                query = f"UPDATE alarms SET {', '.join(updates)} WHERE id = ?"

                cursor.execute(query, values)
                conn.commit()

                updated = cursor.rowcount > 0
                if updated:
                    logger.info(f"更新闹钟: ID={alarm_id}, 字段={list(kwargs.keys())}")

                return updated

            except Exception as e:
                logger.error(f"更新闹钟失败: {e}")
                conn.rollback()
                return False
            finally:
                conn.close()

    def disable_alarm(self, alarm_id: int) -> bool:
        """
        禁用闹钟

        Args:
            alarm_id: 闹钟 ID

        Returns:
            bool: 是否禁用成功
        """
        return self.update_alarm(alarm_id, is_active=False)

    def clear_past_alarms(self) -> int:
        """
        清除已过的闹钟

        Returns:
            int: 清除的闹钟数量
        """
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                cursor = conn.cursor()

                now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                cursor.execute('DELETE FROM alarms WHERE time < ?', (now_str,))
                conn.commit()

                deleted_count = cursor.rowcount
                if deleted_count > 0:
                    logger.info(f"清除 {deleted_count} 个已过闹钟")

                return deleted_count

            except Exception as e:
                logger.error(f"清除已过闹钟失败: {e}")
                conn.rollback()
                return 0
            finally:
                conn.close()

    def update_theme(self, alarm_id: int, theme: str, cheerword: str = None) -> bool:
        """
        更新闹钟主题

        Args:
            alarm_id: 闹钟 ID
            theme: 主题（"铃声" 或其他主题）
            cheerword: 预生成的打气词（可选）

        Returns:
            bool: 是否更新成功
        """
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                cursor = conn.cursor()

                # 检查列是否存在
                cursor.execute("PRAGMA table_info(alarms)")
                columns = [row[1] for row in cursor.fetchall()]

                if 'theme' in columns:
                    # 更新主题
                    if cheerword:
                        cursor.execute('''
                            UPDATE alarms SET theme = ?, cheerword = ?
                            WHERE id = ?
                        ''', (theme, cheerword, alarm_id))
                    else:
                        cursor.execute('''
                            UPDATE alarms SET theme = ?
                            WHERE id = ?
                        ''', (theme, alarm_id))

                    conn.commit()
                    logger.info(f"更新闹钟主题: ID={alarm_id}, 主题={theme}")
                    return True
                else:
                    logger.warning("数据库不支持 theme 列，无法更新主题")
                    return False

            except Exception as e:
                logger.error(f"更新闹钟主题失败: {e}")
                conn.rollback()
                return False
            finally:
                conn.close()

    @staticmethod
    def _row_to_alarm(row) -> Alarm:
        """将数据库行转换为 Alarm 对象（兼容新旧数据库）"""
        # 检查行数（3列或6列）
        if len(row) == 3:
            # 旧数据库（没有 theme 和 cheerword）
            alarm_id, time_str, message = row
            is_active = True
            theme = "铃声"
            cheerword = None
        elif len(row) == 4:
            alarm_id, time_str, message, is_active = row
            theme = "铃声"
            cheerword = None
        elif len(row) == 6:
            # 新数据库（有 theme 和 cheerword）
            alarm_id, time_str, message, is_active, theme, cheerword = row
        else:
            logger.error(f"数据库行格式错误: 列数={len(row)}")
            # 尝试提取最少需要的字段
            alarm_id, time_str, message = row[:3]
            is_active = True
            theme = "铃声"
            cheerword = None

        # 解析时间
        alarm_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')

        return Alarm(
            id=alarm_id,
            time=alarm_time,
            message=message,
            is_active=bool(is_active),
            theme=theme or "铃声",
            cheerword=cheerword
        )
