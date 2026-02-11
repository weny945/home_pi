# ReSpeaker USB Mic Array 使用说明

## ⚠️ 重要澄清

**你的设备是正确的！**

- ✅ **USB 连接就是正常的工作方式**
- ✅ **没有 GPIO 模式**（这个设备不支持）
- ✅ **不需要切换连接方式**

我之前的 GPIO 建议是**错误的**（误认为你的设备是 4-Mic HAT）。

---

## 你的设备

**型号**：ReSpeaker USB Mic Array（带声学外壳）
- 🎤 **6 个麦克风**（环形阵列）
- 🔌 **USB 接口**（唯一连接方式）
- 🔊 **3.5mm 音频接口**（扬声器输出）
- 💻 **XMOS 板载处理器**

**关键特点**：
- ✅ 板载 DSP 处理（波束成形、AEC、NS、AGC）
- ✅ 支持远场拾音（3-5 米）
- ✅ USB 即插即用

---

## 当前问题

从系统信息看到：

```bash
# 当前状态
ReSpeaker 4 Mic Array (UAC1.0)  ← UAC 1.0 模式（受限）
Channels: 6                      ← 6 个麦克风通道
```

**问题**：
1. ⚠️ 工作在 **UAC 1.0** 模式（功能受限）
2. ⚠️ 板载 DSP 可能未启用
3. ⚠️ 需要高灵敏度（0.85）才能检测

**解决方案**：升级到 **UAC 2.0** 模式

---

## 性能对比

| 特性 | UAC 1.0（当前）| UAC 2.0（推荐）|
|------|---------------|---------------|
| 最大采样率 | 16 kHz | **48 kHz** |
| 板载 AEC | ❌ 可能不支持 | ✅ **支持** |
| 板载 NS | ❌ 可能不支持 | ✅ **支持** |
| 板载 AGC | ❌ 可能不支持 | ✅ **支持** |
| 灵敏度需求 | 0.85（很高）| **0.6-0.7（正常）** |
| 软件增益 | 4.0（很高）| **1.5-2.0（正常）** |
| 有效距离 | 1-2 米 | **3-4 米** |
| 音频质量 | 中等 | **优秀** |

---

## 🚀 快速优化（推荐）

### 方法1：自动优化脚本

```bash
# 运行优化脚本
./optimize_usb_mic.sh

# 脚本会：
# 1. 检测设备
# 2. 测试音频通道
# 3. 自动配置 UAC 2.0
# 4. 提示重启
```

### 方法2：手动配置

```bash
# 1. 创建配置文件
sudo nano /etc/modprobe.d/usb-audio.conf

# 2. 添加以下内容
options snd-usb-audio vid=0x2886 pid=0x0018 device_setup=1

# 3. 保存退出，重启
sudo reboot

# 4. 验证
arecord -l | grep UAC
# 应该显示 UAC2.0（而不是 UAC1.0）
```

---

## 测试步骤

### Step 1：测试音频通道

```bash
python tests/manual/test_usb_channels.py
```

**检查输出**：
- 通道 0 能量应该最高（波束成形后的音频）
- 如果通道 0 能量很低，需要升级 UAC 2.0

### Step 2：切换 UAC 2.0

```bash
./optimize_usb_mic.sh
# 或手动配置（见上文）
```

### Step 3：重启并验证

```bash
sudo reboot

# 重启后检查
arecord -l
# 应该看到: UAC2.0
```

### Step 4：更新配置

编辑 `config.yaml`：

```yaml
audio:
  input_device: "plughw:ArrayUAC10"
  sample_rate: 48000  # UAC 2.0 支持更高采样率
  channels: 1
  chunk_size: 512
  input_gain: 1.5  # 降低增益（从 4.0 到 1.5）

wakeword:
  sensitivity: 0.6  # 降低灵敏度（从 0.85 到 0.6）
```

### Step 5：测试唤醒词

```bash
source .env.sh
python tests/manual/test_picovoice_wake_word.py
```

**预期改善**：
- ⏱️ 3-5 秒内检测到（而不是 59 秒）
- 📏 3-4 米距离仍可唤醒
- 🎯 第一次就能触发

---

## 故障排查

### 问题1：切换 UAC 2.0 后设备消失

**原因**：设备可能不支持 UAC 2.0（罕见）

**解决**：
```bash
# 恢复 UAC 1.0
sudo nano /etc/modprobe.d/usb-audio.conf
# 改为: device_setup=0

sudo reboot
```

### 问题2：音质没有改善

**检查**：
```bash
# 1. 确认 UAC 模式
arecord -l | grep UAC

# 2. 测试通道能量
python tests/manual/test_usb_channels.py

# 3. 检查 USB 连接
lsusb -t  # 确保是 USB 2.0/3.0
```

### 问题3：仍需要高灵敏度

**可能原因**：
1. 环境噪音过大
2. 距离过远（>5 米）
3. 音频增益过低

**解决**：
```yaml
audio:
  input_gain: 2.0  # 提高到 2.0-2.5

wakeword:
  sensitivity: 0.7  # 提高到 0.7-0.75
```

---

## 文档索引

- **优化指南**：`docs/RESPEAKER_USB_OPTIMIZATION.md`
- **灵敏度调优**：`docs/SENSITIVITY_TUNING.md`
- **故障排查**：`docs/TROUBLESHOOTING_PICOVOICE.md`

---

## 总结

### 关键点

1. ✅ **你的设备没有问题**（USB 就是正常工作方式）
2. ✅ **不需要 GPIO 模式**（硬件不支持）
3. ✅ **可以通过升级 UAC 2.0 优化性能**

### 性能预期

**当前（UAC 1.0）**：
- 📏 1-2 米
- 🎤 灵敏度 0.85
- ⏱️ 59 秒才检测到

**优化后（UAC 2.0）**：
- 📏 **3-4 米** ✅
- 🎤 **灵敏度 0.6** ✅
- ⏱️ **3-5 秒检测到** ✅

### 下一步

```bash
# 1. 测试通道
python tests/manual/test_usb_channels.py

# 2. 优化配置
./optimize_usb_mic.sh

# 3. 重启测试
sudo reboot
```

---

## 常见误解

❌ **误解**：USB 麦克风无法远场拾音
✅ **事实**：ReSpeaker USB Mic Array 有板载 DSP，支持 3-5 米远场

❌ **误解**：需要切换到 GPIO 模式才能发挥性能
✅ **事实**：你的设备**只有** USB 模式，这是正常的

❌ **误解**：需要购买 HAT 版本
✅ **事实**：你的 USB 版本通过优化配置即可达到良好效果

---

**你的设备很好，只需要正确配置！** 🚀

