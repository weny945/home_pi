# ReSpeaker 4-Mic Array GPIO 模式安装指南

## 为什么需要 GPIO 模式？

### USB 模式 vs GPIO 模式对比

| 特性 | USB 模式（UAC） | GPIO 模式（I2S） |
|------|----------------|-----------------|
| 连接方式 | USB 线 | 40-pin GPIO 排针 |
| 驱动安装 | 即插即用 | 需要安装 seeed-voicecard |
| 波束成形 | ❌ 不支持 | ✅ XMOS 硬件处理 |
| 回声消除 | ❌ 无 | ✅ 支持 AEC |
| 噪声抑制 | ❌ 无 | ✅ 支持 NS |
| 自动增益 | ❌ 无 | ✅ 支持 AGC |
| 音频质量 | 差（多通道原始） | 优（单通道处理后） |
| 远场拾音 | 1-2 米 | 3-5 米 |
| 灵敏度需求 | 0.75-0.85 | 0.5-0.6 |
| 适用场景 | 简单测试 | **生产环境** |

**结论**：USB 模式**无法发挥 ReSpeaker 的真正实力**！

---

## 硬件安装

### 1. 检查硬件

**所需硬件**：
- ✅ 树莓派 5（或 4B/3B+）
- ✅ ReSpeaker 4-Mic Array v2.0
- ✅ 40-pin GPIO 连接器（板子自带）

**不需要**：
- ❌ USB 线（拔掉！GPIO 模式不需要 USB）

### 2. 物理连接

**步骤**：
1. **关闭树莓派电源**
2. 将 ReSpeaker 对准树莓派的 40-pin GPIO 接口
3. 轻轻按下，确保完全插入
4. 检查所有引脚对齐

**接口图示**：
```
ReSpeaker 4-Mic Array
        |
        | (40-pin GPIO)
        ↓
   Raspberry Pi 5

[Pin 1]  3.3V    ●●  5V      [Pin 2]
[Pin 3]  GPIO2   ●●  5V      [Pin 4]
[Pin 5]  GPIO3   ●●  GND     [Pin 6]
[Pin 7]  GPIO4   ●●  GPIO14  [Pin 8]
[Pin 9]  GND     ●●  GPIO15  [Pin 10]
...
```

**重要引脚**：
- Pin 12 (GPIO18): I2S CLK
- Pin 35 (GPIO19): I2S FS
- Pin 38 (GPIO20): I2S DIN
- Pin 40 (GPIO21): I2S DOUT

### 3. 重启树莓派

```bash
sudo reboot
```

---

## 驱动安装

### 方法1：自动安装脚本（推荐）

```bash
# 1. 克隆驱动仓库
cd ~
git clone https://github.com/seeed-studio/seeed-voicecard.git
cd seeed-voicecard

# 2. 运行安装脚本
sudo ./install.sh

# 3. 重启
sudo reboot
```

**安装时间**：约 5-10 分钟

### 方法2：手动安装

如果自动脚本失败，可以手动安装：

```bash
# 1. 编辑 boot 配置
sudo nano /boot/firmware/config.txt

# 2. 添加以下内容到文件末尾
dtoverlay=i2s-mmap
dtoverlay=seeed-4mic-voicecard

# 3. 保存退出（Ctrl+X, Y, Enter）

# 4. 重启
sudo reboot
```

---

## 验证安装

### 1. 检查声卡

```bash
arecord -l
```

**预期输出**（GPIO 模式）：
```
**** List of CAPTURE Hardware Devices ****
card 0: seeed4micvoicec [seeed-4mic-voicecard], device 0: bcm2835-i2s-ac108-pcm0 ac108-pcm0-0 [bcm2835-i2s-ac108-pcm0 ac108-pcm0-0]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
```

**对比 USB 模式**：
```
card 0: ArrayUAC10 [ReSpeaker 4 Mic Array (UAC1.0)]  # USB 模式（旧）
```

### 2. 测试录音

```bash
# 录音 3 秒（使用波束成形后的音频）
arecord -D plughw:seeed4micvoicec -f cd -d 3 test_gpio.wav

# 播放测试
aplay test_gpio.wav
```

**对比测试**：
- GPIO 模式的录音应该明显更清晰
- 远场拾音效果更好
- 背景噪音更少

### 3. 检查 LED 状态

GPIO 模式下，ReSpeaker 上的 12 个 LED 应该可以控制：

```bash
# 安装 Python 库
pip install rpi_ws281x

# 测试 LED
python -c "from rpi_ws281x import *; print('LED support available')"
```

---

## 配置修改

### 更新 config.yaml

GPIO 模式安装完成后，修改配置文件：

```yaml
audio:
  # GPIO 模式设备名称
  input_device: "plughw:seeed4micvoicec"  # 或 "seeed-4mic-voicecard"

  # 或使用更简单的名称
  # input_device: "seeed4micvoicec"

  output_device: "default"
  sample_rate: 16000
  channels: 1  # GPIO 模式输出已经是波束成形后的单通道
  chunk_size: 512

  # 软件增益可以降低（XMOS 已经做了增益处理）
  input_gain: 1.5  # 从 4.0 降低到 1.5-2.0

wakeword:
  engine: "picovoice"
  model: "models/picovoice/胡桃_zh_raspberry-pi_v4_0_0.ppn"

  # 灵敏度可以降低（音频质量更好）
  sensitivity: 0.6  # 从 0.85 降低到 0.5-0.6

  access_key: "${PICOVOICE_ACCESS_KEY}"
  porcupine_model: "models/picovoice/porcupine_params_zh.pv"
```

**关键变化**：
- ✅ `input_device` 改为 seeed-4mic-voicecard
- ✅ `input_gain` 从 4.0 降低到 1.5-2.0
- ✅ `sensitivity` 从 0.85 降低到 0.5-0.6

---

## 性能对比测试

### USB 模式（当前）

```bash
# 测试唤醒词
python tests/manual/test_picovoice_wake_word.py

# 预期：
# - 灵敏度需要 0.85
# - 需要多次尝试
# - 距离 < 2 米
# - 需要高软件增益（4.0）
```

### GPIO 模式（安装后）

```bash
# 测试唤醒词
python tests/manual/test_picovoice_wake_word.py

# 预期：
# - 灵敏度 0.5-0.6 即可
# - 第一次就能触发
# - 距离 3-5 米
# - 低软件增益（1.5-2.0）
```

---

## 故障排查

### 问题1：驱动安装失败

**症状**：
```
arecord -l
# 没有 seeed-4mic-voicecard 设备
```

**解决**：
```bash
# 检查 I2S 是否启用
sudo raspi-config
# Interface Options -> I2S -> Enable

# 检查内核模块
lsmod | grep snd_soc_ac108
# 应该有输出

# 重新安装驱动
cd ~/seeed-voicecard
sudo ./uninstall.sh
sudo ./install.sh
sudo reboot
```

### 问题2：只有 USB 设备，没有 GPIO 设备

**原因**：
- USB 线仍然插着
- 驱动未正确安装

**解决**：
```bash
# 1. 拔掉 USB 线（GPIO 模式不需要）
# 2. 重新安装驱动
# 3. 重启
```

### 问题3：录音无声音

**检查混音器设置**：
```bash
alsamixer
# 按 F6 选择 seeed-4mic-voicecard
# 检查 ADC Capture Volume 是否为 0（静音）
# 用方向键调整音量
```

### 问题4：树莓派 5 兼容性问题

树莓派 5 使用新的设备树，可能需要额外配置：

```bash
# 编辑 config.txt
sudo nano /boot/firmware/config.txt

# 确保有以下内容
dtparam=i2s=on
dtoverlay=i2s-mmap
dtoverlay=seeed-4mic-voicecard

# 保存重启
sudo reboot
```

---

## GPIO 模式的额外功能

### 1. LED 控制

GPIO 模式可以控制板载的 12 个 APA102 LED：

```python
# 示例：唤醒时 LED 闪烁
from rpi_ws281x import *

# 初始化 LED
strip = Adafruit_NeoPixel(12, 18, 800000, 10, False)
strip.begin()

# 设置颜色（唤醒时变绿）
for i in range(12):
    strip.setPixelColor(i, Color(0, 255, 0))  # 绿色
strip.show()
```

### 2. 回声消除（AEC）

GPIO 模式支持回声消除，播放音乐时也能唤醒：

```bash
# 测试回声消除
# 1. 播放音乐
aplay music.wav &

# 2. 同时测试唤醒词
python tests/manual/test_picovoice_wake_word.py
# GPIO 模式下应该仍能检测到唤醒词
```

### 3. 方向检测（DOA）

可以检测声音来源方向（需要额外配置）：

```python
# 读取 DOA 数据
# /sys/class/sound/cardX/doa
```

---

## 推荐配置（GPIO 模式）

### 安静环境

```yaml
audio:
  input_device: "plughw:seeed4micvoicec"
  input_gain: 1.5

wakeword:
  sensitivity: 0.5
```

### 一般家庭环境

```yaml
audio:
  input_device: "plughw:seeed4micvoicec"
  input_gain: 2.0

wakeword:
  sensitivity: 0.6
```

### 嘈杂环境

```yaml
audio:
  input_device: "plughw:seeed4micvoicec"
  input_gain: 2.5

wakeword:
  sensitivity: 0.7
```

---

## 性能预期

### USB 模式（当前）

- 📏 有效距离：1-2 米
- 🎤 灵敏度需求：0.75-0.85
- 🔊 增益需求：3.0-5.0
- ⚠️ 误报风险：高
- 🎯 唤醒成功率：60-70%

### GPIO 模式（推荐）

- 📏 有效距离：**3-5 米**
- 🎤 灵敏度需求：**0.5-0.6**
- 🔊 增益需求：**1.5-2.0**
- ⚠️ 误报风险：低
- 🎯 唤醒成功率：**90-95%**

---

## 总结

**当前问题**：
- ❌ USB 模式无法发挥 ReSpeaker 的远场拾音能力
- ❌ 无波束成形、回声消除、噪声抑制
- ❌ 需要很高的灵敏度（0.85）才能勉强工作

**解决方案**：
1. ✅ 拔掉 USB 线
2. ✅ 通过 GPIO 连接 ReSpeaker
3. ✅ 安装 seeed-voicecard 驱动
4. ✅ 更新 config.yaml 配置

**预期改善**：
- ✅ 远场拾音距离提升到 3-5 米
- ✅ 灵敏度降低到 0.5-0.6
- ✅ 音频质量显著提升
- ✅ 误报率大幅降低

**下一步**：
1. 关机断电
2. 移除 USB 线，安装到 GPIO
3. 安装驱动
4. 重启测试

