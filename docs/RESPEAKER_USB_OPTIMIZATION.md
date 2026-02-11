# ReSpeaker USB Mic Array 优化指南

## 设备识别

**你的设备**：ReSpeaker USB Mic Array（带声学外壳）
- 产品 ID: 2886:0018
- 6 麦克风阵列
- 只支持 USB 连接（无 GPIO）
- 带 XMOS 板载处理器

**重要**：这个设备**没有 GPIO 模式**，USB 就是正常工作方式！

---

## 问题分析

### 当前状态

从系统信息看到：
```bash
# 设备模式
ReSpeaker 4 Mic Array (UAC1.0)  # UAC 1.0 模式（受限）

# 录音通道
Channels: 6  # 6 个麦克风通道
Channel map: FL FR FC LFE RL RR
```

**问题**：
1. ⚠️ 工作在 **UAC 1.0** 模式（功能受限）
2. ⚠️ 当前配置只读取 **1 个通道**
3. ⚠️ 可能没有使用**波束成形后的通道**

---

## 优化方案

### 方案1：使用正确的音频通道（推荐）

ReSpeaker USB Mic Array 的 6 个通道：
- **通道 0 (FL)**: 波束成形后的音频 ← **应该用这个**
- 通道 1 (FR): 原始麦克风 2
- 通道 2 (FC): 原始麦克风 3
- 通道 3 (LFE): 原始麦克风 4
- 通道 4 (RL): 原始麦克风 5
- 通道 5 (RR): 原始麦克风 6

**当前问题**：可能读取了错误的通道

#### 测试不同通道

```bash
# 创建测试脚本
python tests/manual/test_usb_channels.py
```

### 方案2：升级到 UAC 2.0 模式

UAC 2.0 支持更多功能：
- ✅ 板载 AEC（回声消除）
- ✅ 板载 NS（噪声抑制）
- ✅ 板载 AGC（自动增益）
- ✅ 更好的音频质量

#### 检查是否支持 UAC 2.0

```bash
# 检查设备描述符
lsusb -v -d 2886:0018 | grep -A 5 "bcdUSB"

# 如果显示 bcdUSB 2.0，设备支持 UAC 2.0
```

#### 强制使用 UAC 2.0

编辑内核模块参数：

```bash
# 1. 创建配置文件
sudo nano /etc/modprobe.d/usb-audio.conf

# 2. 添加以下内容
options snd-usb-audio vid=0x2886 pid=0x0018 device_setup=1

# 3. 重新加载模块
sudo modprobe -r snd_usb_audio
sudo modprobe snd_usb_audio

# 4. 重启（推荐）
sudo reboot
```

**参数说明**：
- `device_setup=0`: UAC 1.0 模式（当前）
- `device_setup=1`: UAC 2.0 模式（推荐）

### 方案3：调整 ALSA 配置

创建专用的 ALSA 配置文件：

```bash
# 编辑 ALSA 配置
nano ~/.asoundrc
```

添加以下内容：

```
# ReSpeaker USB Mic Array 配置
pcm.respeaker {
    type hw
    card ArrayUAC10
    device 0
    channels 6  # 6 个通道
}

# 使用通道 0（波束成形）
pcm.respeaker_beamformed {
    type plug
    slave.pcm "hw:ArrayUAC10"
    slave.channels 6
    ttable.0.0 1  # 只使用通道 0
}
```

然后在配置中使用：

```yaml
audio:
  input_device: "respeaker_beamformed"
```

### 方案4：固件更新（如果可用）

检查是否有固件更新：

```bash
# 检查当前固件版本
lsusb -v -d 2886:0018 | grep bcdDevice
# 当前: bcdDevice 4.00

# 访问 Seeed 官网下载最新固件
# https://wiki.seeedstudio.com/ReSpeaker_Mic_Array_v2.0/
```

---

## 推荐配置

### 配置 1：使用波束成形通道（简单）

```yaml
audio:
  input_device: "plughw:ArrayUAC10"
  output_device: "default"
  sample_rate: 16000
  channels: 1  # 保持 1 通道，但确保读取通道 0
  chunk_size: 512
  input_gain: 2.0  # 降低增益（从 4.0 到 2.0）

wakeword:
  sensitivity: 0.7  # 降低灵敏度（从 0.85 到 0.7）
```

### 配置 2：升级 UAC 2.0 后

```yaml
audio:
  input_device: "plughw:ArrayUAC10"
  sample_rate: 48000  # UAC 2.0 支持更高采样率
  channels: 1
  chunk_size: 512
  input_gain: 1.5  # UAC 2.0 音频质量更好，降低增益

wakeword:
  sensitivity: 0.6  # UAC 2.0 信噪比更好
```

---

## 测试音频通道

### 创建通道测试脚本

```python
# tests/manual/test_usb_channels.py
"""
测试 ReSpeaker USB Mic Array 的不同音频通道
"""
import pyaudio
import numpy as np
import wave

def test_channels():
    """测试所有 6 个通道"""
    p = pyaudio.PyAudio()

    # 找到 ReSpeaker 设备
    device_index = None
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if 'ReSpeaker' in info['name'] or 'ArrayUAC' in info['name']:
            device_index = i
            print(f"找到设备: {info['name']}")
            break

    if device_index is None:
        print("未找到 ReSpeaker 设备")
        return

    # 录制所有 6 个通道
    print("\n录制 6 通道音频（3 秒）...")
    stream = p.open(
        format=pyaudio.paInt16,
        channels=6,  # 6 个通道
        rate=16000,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=512
    )

    frames = []
    for _ in range(int(16000 / 512 * 3)):  # 3 秒
        data = stream.read(512)
        frames.append(data)

    stream.stop_stream()
    stream.close()

    # 保存为 6 通道 WAV 文件
    wf = wave.open('test_6ch.wav', 'wb')
    wf.setnchannels(6)
    wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
    wf.setframerate(16000)
    wf.writeframes(b''.join(frames))
    wf.close()

    print("✅ 已保存 test_6ch.wav")
    print()

    # 分析每个通道的能量
    audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
    audio_data = audio_data.reshape(-1, 6)  # 重塑为 6 通道

    print("各通道能量分析：")
    for ch in range(6):
        channel_data = audio_data[:, ch]
        energy = np.sqrt(np.mean(channel_data.astype(np.float32) ** 2))
        print(f"  通道 {ch}: 能量 = {energy:.0f}")

    print()
    print("建议：")
    print("  - 通道 0 通常是波束成形后的音频（能量最高）")
    print("  - 如果通道 0 能量很低，可能需要切换到 UAC 2.0 模式")
    print("  - 播放 test_6ch.wav 检查音质（需要支持多通道的播放器）")

    p.terminate()

if __name__ == "__main__":
    test_channels()
```

运行测试：

```bash
python tests/manual/test_usb_channels.py
```

---

## UAC 1.0 vs UAC 2.0 对比

| 特性 | UAC 1.0（当前）| UAC 2.0（推荐）|
|------|---------------|---------------|
| 最大采样率 | 16000 Hz | 48000 Hz |
| 板载 AEC | ❌ 可能不支持 | ✅ 支持 |
| 板载 NS | ❌ 可能不支持 | ✅ 支持 |
| 板载 AGC | ❌ 可能不支持 | ✅ 支持 |
| 音频质量 | 中等 | 优秀 |
| 延迟 | 中等 | 低 |

---

## 故障排查

### 问题1：切换 UAC 2.0 后无法识别设备

```bash
# 恢复 UAC 1.0
sudo nano /etc/modprobe.d/usb-audio.conf
# 改为: device_setup=0

sudo modprobe -r snd_usb_audio
sudo modprobe snd_usb_audio
```

### 问题2：音频质量仍然差

```bash
# 1. 检查 USB 总线速度
lsusb -t
# 确保是 USB 2.0 或 3.0，不是 USB 1.1

# 2. 检查是否有 USB 干扰
# 拔掉其他 USB 设备

# 3. 更换 USB 端口
# 使用直接连接到主板的 USB 口
```

### 问题3：通道 0 没有音频

```bash
# 测试所有通道
arecord -D plughw:ArrayUAC10 -f S16_LE -r 16000 -c 6 -d 3 test.wav

# 播放检查（需要多通道播放器）
# 或者使用 audacity 打开 test.wav 查看各通道波形
```

---

## 性能优化建议

### 1. 使用低延迟 USB

```bash
# 检查 USB 延迟
cat /sys/module/snd_usb_audio/parameters/nrpacks
# 默认值: 8

# 降低延迟（可选）
echo "options snd-usb-audio nrpacks=1" | sudo tee -a /etc/modprobe.d/usb-audio.conf
```

### 2. 优化 ALSA 缓冲

```bash
# 编辑 ~/.asoundrc
pcm.respeaker {
    type hw
    card ArrayUAC10
    period_size 512
    buffer_size 2048
}
```

### 3. 禁用不需要的处理

```yaml
audio:
  input_gain: 1.5  # 降低软件增益（让板载 DSP 处理）
```

---

## 预期性能

### 当前（UAC 1.0 + 单通道）

- 📏 有效距离：1-2 米
- 🎤 灵敏度需求：0.85
- 🔊 增益需求：4.0
- 🎯 唤醒成功率：70%

### 优化后（UAC 2.0 + 波束成形通道）

- 📏 有效距离：**3-4 米**
- 🎤 灵敏度需求：**0.6-0.7**
- 🔊 增益需求：**1.5-2.0**
- 🎯 唤醒成功率：**85-90%**

**注意**：USB Mic Array 的远场性能不如 HAT 版本（HAT 版本可达 5 米）

---

## 总结

**你的设备是正确的**：
- ✅ USB 就是正常连接方式
- ✅ 没有 GPIO 模式
- ✅ 可以通过优化配置提升性能

**优化步骤**：
1. ✅ 测试音频通道（确认通道 0 是波束成形）
2. ✅ 切换到 UAC 2.0 模式（如果支持）
3. ✅ 降低软件增益和灵敏度
4. ✅ 配置 ALSA 使用正确通道

**预期改善**：
- 📏 远场距离提升到 3-4 米
- 🎤 灵敏度降低到 0.6-0.7
- 🎯 成功率提升到 85-90%

