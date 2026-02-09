"""
资源管理器
Resource Manager for Voice Assistant System

P2-2 优化: 实现资源自动清理和引用计数
"""
import logging
import gc
import threading
import time
from typing import Dict, Any, Optional, Callable
from weakref import WeakSet

logger = logging.getLogger(__name__)

# 尝试导入 psutil（可选依赖）
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None


class Resource:
    """资源基类"""

    def __init__(self, name: str, cleanup_callback: Optional[Callable] = None):
        self.name = name
        self.cleanup_callback = cleanup_callback
        self.ref_count = 0
        self.last_used = time.time()

    def acquire(self) -> None:
        """增加引用计数"""
        self.ref_count += 1
        self.last_used = time.time()
        logger.debug(f"资源 {self.name} 引用计数: {self.ref_count}")

    def release(self) -> None:
        """减少引用计数"""
        if self.ref_count > 0:
            self.ref_count -= 1
            self.last_used = time.time()
            logger.debug(f"资源 {self.name} 引用计数: {self.ref_count}")

    def cleanup(self) -> None:
        """清理资源"""
        if self.cleanup_callback:
            try:
                self.cleanup_callback()
                logger.info(f"✅ 资源 {self.name} 已清理")
            except Exception as e:
                logger.error(f"清理资源 {self.name} 失败: {e}")


class ResourceManager:
    """资源管理器（P2-2 优化）"""

    def __init__(self, cleanup_interval: float = 60.0, resource_timeout: float = 300.0):
        """
        初始化资源管理器

        Args:
            cleanup_interval: 自动清理间隔（秒）
            resource_timeout: 资源超时时间（秒），超过此时间未使用的资源将被清理
        """
        self._resources: Dict[str, Resource] = {}
        self._cleanup_interval = cleanup_interval
        self._resource_timeout = resource_timeout
        self._running = False
        self._cleanup_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # 使用弱集合跟踪资源，避免循环引用
        self._tracked_resources = WeakSet()

    def register_resource(
        self,
        name: str,
        cleanup_callback: Optional[Callable] = None
    ) -> Resource:
        """
        注册资源

        Args:
            name: 资源名称
            cleanup_callback: 清理回调函数

        Returns:
            Resource: 资源对象
        """
        with self._lock:
            if name not in self._resources:
                resource = Resource(name, cleanup_callback)
                self._resources[name] = resource
                logger.info(f"📝 注册资源: {name}")
            else:
                resource = self._resources[name]

            self._tracked_resources.add(resource)
            return resource

    def acquire(self, name: str) -> Optional[Resource]:
        """
        获取资源（增加引用计数）

        Args:
            name: 资源名称

        Returns:
            Resource: 资源对象，如果不存在返回 None
        """
        with self._lock:
            resource = self._resources.get(name)
            if resource:
                resource.acquire()
            return resource

    def release(self, name: str) -> None:
        """
        释放资源（减少引用计数）

        Args:
            name: 资源名称
        """
        with self._lock:
            resource = self._resources.get(name)
            if resource:
                resource.release()

    def cleanup_resource(self, name: str) -> None:
        """
        手动清理指定资源

        Args:
            name: 资源名称
        """
        with self._lock:
            resource = self._resources.pop(name, None)
            if resource:
                resource.cleanup()

    def cleanup_all(self) -> None:
        """清理所有资源"""
        with self._lock:
            for name, resource in list(self._resources.items()):
                if resource.ref_count == 0:
                    resource.cleanup()
                    del self._resources[name]

        logger.info("🧹 已清理所有未使用的资源")

    def start_auto_cleanup(self) -> None:
        """启动自动清理线程"""
        if self._running:
            logger.warning("自动清理已在运行")
            return

        self._running = True
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_worker,
            daemon=True,
            name="ResourceCleaner"
        )
        self._cleanup_thread.start()
        logger.info(f"🔄 启动自动清理（间隔: {self._cleanup_interval}s, 超时: {self._resource_timeout}s）")

    def stop_auto_cleanup(self) -> None:
        """停止自动清理线程"""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5.0)
            logger.info("⏹️ 自动清理已停止")

    def _cleanup_worker(self) -> None:
        """自动清理工作线程"""
        while self._running:
            try:
                time.sleep(self._cleanup_interval)

                # 清理超时的未使用资源
                current_time = time.time()
                with self._lock:
                    for name, resource in list(self._resources.items()):
                        if (resource.ref_count == 0 and
                            current_time - resource.last_used > self._resource_timeout):
                            logger.info(f"⏰ 资源 {name} 超时，自动清理")
                            resource.cleanup()
                            del self._resources[name]

                # 手动触发 Python 垃圾回收
                gc.collect()

            except Exception as e:
                logger.error(f"自动清理出错: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        获取资源统计信息

        Returns:
            资源统计字典
        """
        with self._lock:
            return {
                'total_resources': len(self._resources),
                'resources': {
                    name: {
                        'ref_count': resource.ref_count,
                        'last_used': resource.last_used,
                        'idle_time': time.time() - resource.last_used
                    }
                    for name, resource in self._resources.items()
                }
            }


# 全局资源管理器实例
_resource_manager: Optional[ResourceManager] = None


def get_resource_manager() -> ResourceManager:
    """获取全局资源管理器实例"""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
        _resource_manager.start_auto_cleanup()
    return _resource_manager
