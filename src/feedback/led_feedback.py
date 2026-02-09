"""
LED 反馈控制器 (Phase 1.4 可选功能)
LED Feedback Controller for Voice Assistant

利用 ReSpeaker 的环形 LED 灯带显示系统状态
"""
import logging
import time
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class LEDFeedback:
    """LED 反馈控制器"""

    def __init__(self, config: dict):
        """
        初始化 LED 反馈控制器

        Args:
            config: 配置字典
        """
        self._enabled = config.get("enabled", False)
        self._pin = config.get("pin", 12)
        self._led_count = config.get("led_count", 12)
        self._brightness = config.get("brightness", 0.5)

        self._available = False
        self._pixels = None
        self._animation_thread: Optional[threading.Thread] = None
        self._stop_animation = False

        if self._enabled:
            self._initialize_led()
        else:
            logger.info("LED 反馈已禁用")

    def _initialize_led(self) -> None:
        """初始化 LED 硬件"""
        try:
            # 尝试导入 LED 控制库
            import board
            import neopixel

            # 初始化 NeoPixel
            self._pixels = neopixel.NeoPixel(
                getattr(board, f"D{self._pin}"),
                self._led_count,
                brightness=self._brightness,
                auto_write=False
            )

            self._available = True
            logger.info(f"✓ LED 反馈已启用 (pin={self._pin}, count={self._led_count})")

            # 启动时显示一个测试效果
            self._test_animation()

        except ImportError as e:
            logger.warning(f"LED 控制库未安装: {e}")
            logger.info("提示: 安装 adafruit-circuitpython-neopixel 和 rpi_ws281x 以启用 LED 反馈")
            self._available = False
        except Exception as e:
            logger.error(f"LED 初始化失败: {e}")
            self._available = False

    def _test_animation(self) -> None:
        """测试动画：依次点亮所有 LED"""
        if not self._available:
            return

        try:
            for i in range(self._led_count):
                self._pixels[i] = (50, 50, 50)  # 灰色
                self._pixels.show()
                time.sleep(0.05)

            time.sleep(0.2)

            for i in range(self._led_count):
                self._pixels[i] = (0, 0, 0)
                self._pixels.show()
                time.sleep(0.05)

        except Exception as e:
            logger.error(f"LED 测试动画失败: {e}")

    def set_state(self, state: str) -> None:
        """
        设置 LED 状态

        Args:
            state: 状态名称
                - "idle": 待机（蓝色呼吸）
                - "wakeup": 唤醒成功（绿色快闪）
                - "listening": 录音中（青色流动）
                - "processing": 处理中（黄色常亮）
                - "speaking": 播放中（绿色脉冲）
                - "error": 错误（红色快闪）
                - "retry_1": 第1次重试（橙色闪烁1次）
                - "retry_2": 第2次重试（橙色闪烁2次）
                - "off": 关闭所有 LED
        """
        if not self._available or not self._pixels:
            return

        # 停止当前动画
        self._stop_current_animation()

        # 根据状态设置 LED 效果
        if state == "idle":
            self._start_animation(self._breathe_animation, (0, 0, 255))  # 蓝色呼吸
        elif state == "wakeup":
            self._start_animation(self._blink_animation, (0, 255, 0), 0.2)  # 绿色快闪
        elif state == "listening":
            self._start_animation(self._flow_animation, (0, 255, 255))  # 青色流动
        elif state == "processing":
            self._solid_color((255, 255, 0))  # 黄色常亮
        elif state == "speaking":
            self._start_animation(self._pulse_animation, (0, 255, 0))  # 绿色脉冲
        elif state == "error":
            self._start_animation(self._blink_animation, (255, 0, 0), 0.1)  # 红色快闪
        elif state == "retry_1":
            self._blink_count((255, 165, 0), 1)  # 橙色闪烁1次
        elif state == "retry_2":
            self._blink_count((255, 165, 0), 2)  # 橙色闪烁2次
        elif state == "off":
            self._solid_color((0, 0, 0))

    def _stop_current_animation(self) -> None:
        """停止当前动画"""
        self._stop_animation = True
        if self._animation_thread:
            self._animation_thread.join(timeout=1.0)
            self._animation_thread = None

    def _start_animation(self, animation_func, *args) -> None:
        """启动动画线程"""
        self._stop_animation = False
        self._animation_thread = threading.Thread(
            target=animation_func,
            args=args,
            daemon=True
        )
        self._animation_thread.start()

    # ============================================================
    # LED 动画效果
    # ============================================================

    def _solid_color(self, color: tuple) -> None:
        """设置常亮颜色"""
        if self._available and self._pixels:
            self._pixels.fill(color)
            self._pixels.show()

    def _breathe_animation(self, color: tuple) -> None:
        """呼吸动画"""
        if not self._available or not self._pixels:
            return

        min_brightness = 0.1
        max_brightness = self._brightness
        step = 0.05
        delay = 0.05

        brightness = min_brightness
        direction = 1

        while not self._stop_animation:
            # 调整亮度
            r, g, b = color
            self._pixels.fill((int(r * brightness), int(g * brightness), int(b * brightness)))
            self._pixels.show()

            brightness += step * direction

            if brightness >= max_brightness:
                direction = -1
            elif brightness <= min_brightness:
                direction = 1

            time.sleep(delay)

    def _blink_animation(self, color: tuple, speed: float) -> None:
        """闪烁动画"""
        if not self._available or not self._pixels:
            return

        while not self._stop_animation:
            self._pixels.fill(color)
            self._pixels.show()
            time.sleep(speed)
            self._pixels.fill((0, 0, 0))
            self._pixels.show()
            time.sleep(speed)

    def _flow_animation(self, color: tuple) -> None:
        """流动动画（LED 依次点亮）"""
        if not self._available or not self._pixels:
            return

        delay = 0.1
        offset = 0

        while not self._stop_animation:
            for i in range(self._led_count):
                # 计算每个 LED 的亮度（基于位置和偏移）
                pos = (i + offset) % self._led_count
                brightness = 1.0 - (pos / self._led_count)

                r, g, b = color
                self._pixels[i] = (int(r * brightness * self._brightness),
                                    int(g * brightness * self._brightness),
                                    int(b * brightness * self._brightness))

            self._pixels.show()
            time.sleep(delay)
            offset = (offset + 1) % self._led_count

    def _pulse_animation(self, color: tuple) -> None:
        """脉冲动画（快速闪烁几次）"""
        if not self._available or not self._pixels:
            return

        r, g, b = color

        while not self._stop_animation:
            # 快速脉冲
            for _ in range(3):
                if self._stop_animation:
                    break
                self._pixels.fill((int(r * 0.3 * self._brightness),
                                    int(g * 0.3 * self._brightness),
                                    int(b * 0.3 * self._brightness)))
                self._pixels.show()
                time.sleep(0.1)

                self._pixels.fill((int(r * self._brightness),
                                    int(g * self._brightness),
                                    int(b * self._brightness)))
                self._pixels.show()
                time.sleep(0.1)

            time.sleep(0.5)

    def _blink_count(self, color: tuple, count: int) -> None:
        """闪烁指定次数"""
        if not self._available or not self._pixels:
            return

        for _ in range(count):
            if self._stop_animation:
                break
            self._pixels.fill(color)
            self._pixels.show()
            time.sleep(0.2)
            self._pixels.fill((0, 0, 0))
            self._pixels.show()
            time.sleep(0.2)

    # ============================================================
    # 状态判断方法
    # ============================================================

    def is_available(self) -> bool:
        """LED 是否可用"""
        return self._available

    def cleanup(self) -> None:
        """清理资源"""
        self._stop_animation = True
        if self._animation_thread:
            self._animation_thread.join(timeout=1.0)

        if self._available and self._pixels:
            self._pixels.fill((0, 0, 0))
            self._pixels.show()

        logger.info("LED 反馈已清理")
