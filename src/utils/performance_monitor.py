"""
性能监控器
Performance Monitor for Voice Assistant System

P2-4 优化: 实现性能指标采集和报告
"""
import logging
import time
import threading
from typing import Dict, Any, List, Optional
from collections import defaultdict
import os

logger = logging.getLogger(__name__)

# 尝试导入 psutil（可选依赖）
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None


class PerformanceMonitor:
    """性能监控器（P2-4 优化）"""

    def __init__(self, enabled: bool = True, sample_interval: float = 1.0):
        """
        初始化性能监控器

        Args:
            enabled: 是否启用监控
            sample_interval: 采样间隔（秒）
        """
        self._enabled = enabled
        self._sample_interval = sample_interval
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None

        # 性能指标存储
        self._metrics = defaultdict(list)
        self._timers = {}
        self._counters = defaultdict(int)

        # 进程信息（如果 psutil 可用）
        self._process = psutil.Process(os.getpid()) if PSUTIL_AVAILABLE else None

    def start(self) -> None:
        """启动性能监控"""
        if not self._enabled:
            return

        if self._running:
            logger.warning("性能监控已在运行")
            return

        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_worker,
            daemon=True,
            name="PerformanceMonitor"
        )
        self._monitor_thread.start()
        logger.info(f"📊 启动性能监控（采样间隔: {self._sample_interval}s）")

    def stop(self) -> None:
        """停止性能监控"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        logger.info("⏹️ 性能监控已停止")

    def record_latency(self, operation: str, duration: float) -> None:
        """
        记录操作延迟

        Args:
            operation: 操作名称
            duration: 延迟（秒）
        """
        if not self._enabled:
            return

        self._metrics[operation].append(duration)
        # 只保留最近1000个样本
        if len(self._metrics[operation]) > 1000:
            self._metrics[operation] = self._metrics[operation][-1000:]

    def start_timer(self, operation: str) -> None:
        """
        开始计时

        Args:
            operation: 操作名称
        """
        if not self._enabled:
            return

        self._timers[operation] = time.time()

    def end_timer(self, operation: str) -> float:
        """
        结束计时并记录

        Args:
            operation: 操作名称

        Returns:
            float: 延迟（秒）
        """
        if not self._enabled or operation not in self._timers:
            return 0.0

        duration = time.time() - self._timers[operation]
        del self._timers[operation]
        self.record_latency(operation, duration)
        return duration

    def increment_counter(self, counter: str, value: int = 1) -> None:
        """
        增加计数器

        Args:
            counter: 计数器名称
            value: 增加值（默认1）
        """
        if not self._enabled:
            return

        self._counters[counter] += value

    def get_stats(self, operation: str) -> Dict[str, float]:
        """
        获取操作统计数据

        Args:
            operation: 操作名称

        Returns:
            统计数据字典
        """
        if operation not in self._metrics or not self._metrics[operation]:
            return {}

        durations = self._metrics[operation]
        return {
            'count': len(durations),
            'avg': sum(durations) / len(durations),
            'min': min(durations),
            'max': max(durations),
            'p50': sorted(durations)[len(durations) // 2],
            'p95': sorted(durations)[int(len(durations) * 0.95)] if len(durations) > 20 else max(durations),
            'p99': sorted(durations)[int(len(durations) * 0.99)] if len(durations) > 100 else max(durations),
        }

    def get_all_stats(self) -> Dict[str, Any]:
        """
        获取所有统计数据

        Returns:
            所有统计数据
        """
        stats = {
            'operations': {op: self.get_stats(op) for op in self._metrics},
            'counters': dict(self._counters),
        }

        # 添加系统资源使用
        try:
            stats['system'] = self._get_system_stats()
        except Exception as e:
            logger.error(f"获取系统统计失败: {e}")

        return stats

    def _get_system_stats(self) -> Dict[str, float]:
        """获取系统资源使用统计"""
        if not PSUTIL_AVAILABLE or self._process is None:
            return {}

        try:
            # CPU 使用率
            cpu_percent = self._process.cpu_percent(interval=0.1)

            # 内存使用
            memory_info = self._process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            # 线程数
            num_threads = self._process.num_threads()

            # 打开文件数
            try:
                num_files = len(self._process.open_files())
            except:
                num_files = 0

            return {
                'cpu_percent': cpu_percent,
                'memory_mb': memory_mb,
                'num_threads': num_threads,
                'num_files': num_files,
            }
        except Exception as e:
            logger.error(f"获取系统统计失败: {e}")
            return {}

    def print_report(self) -> None:
        """打印性能报告"""
        if not self._enabled:
            return

        stats = self.get_all_stats()

        print("\n" + "=" * 60)
        print("📊 性能监控报告")
        print("=" * 60)

        # 操作统计
        if stats['operations']:
            print("\n操作延迟统计:")
            for op, op_stats in stats['operations'].items():
                if op_stats:
                    print(f"\n  {op}:")
                    print(f"    次数: {op_stats['count']}")
                    print(f"    平均: {op_stats['avg']*1000:.2f}ms")
                    print(f"    最小: {op_stats['min']*1000:.2f}ms")
                    print(f"    最大: {op_stats['max']*1000:.2f}ms")
                    print(f"    P95: {op_stats['p95']*1000:.2f}ms")
                    print(f"    P99: {op_stats['p99']*1000:.2f}ms")

        # 计数器
        if stats['counters']:
            print("\n计数器统计:")
            for counter, value in stats['counters'].items():
                print(f"  {counter}: {value}")

        # 系统资源
        if 'system' in stats:
            sys_stats = stats['system']
            print("\n系统资源:")
            print(f"  CPU: {sys_stats['cpu_percent']:.1f}%")
            print(f"  内存: {sys_stats['memory_mb']:.1f}MB")
            print(f"  线程数: {sys_stats['num_threads']}")
            print(f"  打开文件数: {sys_stats['num_files']}")

        print("=" * 60 + "\n")

    def _monitor_worker(self) -> None:
        """监控工作线程"""
        while self._running:
            try:
                time.sleep(self._sample_interval)

                # 记录系统资源使用
                sys_stats = self._get_system_stats()
                self.record_latency('system.cpu', sys_stats['cpu_percent'] / 100.0)
                self.record_latency('system.memory', sys_stats['memory_mb'])

            except Exception as e:
                logger.error(f"监控工作线程出错: {e}")


# 全局性能监控器实例
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor(enabled: bool = True) -> PerformanceMonitor:
    """获取全局性能监控器实例"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor(enabled=enabled)
        _performance_monitor.start()
    return _performance_monitor


# 上下文管理器，用于自动计时
class Timer:
    """性能计时器上下文管理器"""

    def __init__(self, operation: str, monitor: Optional[PerformanceMonitor] = None):
        self.operation = operation
        self.monitor = monitor or get_performance_monitor()

    def __enter__(self):
        self.monitor.start_timer(self.operation)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.monitor.end_timer(self.operation)
        return False
