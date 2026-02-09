# 音频播放故障排除指南

**问题**: `aplay: audio open error: Unknown error 524`

**原因**: 音频输出设备未正确配置

---

## 🔍 快速诊断

### 步骤 1: 运行音频诊断工具

```bash
cd ~/home_pi
python3 tests/manual/diagnose_audio.py
```

这个工具会：
- ✅ 列出所有可用的音频设备
- ✅ 测试每个设备是否可以播放
- ✅ 检查音量设置
- ✅ 提供配置建议

### 步骤 2: 手动检查音频设备

```bash
# 列出所有音频设备
aplay -L

# 测试默认设备
speaker-test -t wav -c 1

# 如果上述命令失败，尝试指定设备
speaker-test -t wav -c 1 -D plughw:0,0
```

### 步骤 3: 检查音量设置

```bash
# 查看当前音量
amixer sget Master

# 设置音量为100%
amixer set Master 100%

# 或使用百分比
amixer set Master 80%
```

---

## ⚙️ 解决方案

### 方案 1: 更新配置文件（推荐）

编辑 `config.yaml`:

```yaml
audio:
  input_device: "seeed-4mic-voicecard"
  output_device: "plughw:0,0"  # 添加这一行
  sample_rate: 16000
  channels: 1
  chunk_size: 512
  format: "int16"
```

### 方案 2: 使用树莓派配置工具

```bash
# 运行配置工具
sudo raspi-config

# 导航到:
# Advanced Options -> Audio
# 选择: 1. Headphones (3.5mm jack)
# 或: 2. HDMI

# 重启生效
sudo reboot
```

### 方案 3: 强制使用 3.5mm 接口

```bash
# 创建或编辑 ALSA 配置
sudo vim /etc/asound.conf

# 添加以下内容:
pcm.!default {
  type hw
  card 0
}

ctl.!default {
  type hw
  card 0
}
```

### 方案 4: 禁用 HDMI 音频

```bash
# 编辑 config.txt
sudo vim /boot/config.txt

# 添加或修改:
hdmi_ignore_hotplug=1
hdmi_drive=0

# 重启
sudo reboot
```

---

## 🎯 常用输出设备

根据 `diagnose_audio.py` 的输出，选择合适的设备：

| 设备名称 | 说明 | 推荐度 |
|---------|------|--------|
| `plughw:0,0` | 3.5mm 接口（自动采样率转换） | ⭐⭐⭐⭐⭐ |
| `hw:0,0` | 3.5mm 接口（直接访问） | ⭐⭐⭐⭐ |
| `default` | 系统默认 | ⭐⭐⭐ |
| `pulse` | PulseAudio（需安装） | ⭐⭐⭐⭐ |

---

## 🧪 测试修复

### 1. 测试音频播放

```bash
# 方法1: 使用诊断工具
python3 tests/manual/diagnose_audio.py

# 方法2: 使用测试脚本
cd ~/home_pi
source .venv/bin/activate
python3 tests/manual/test_software.py
# 选择 [2] 测试 TTS 反馈播放器
```

### 2. 测试完整流程

```bash
python3 tests/manual/test_software.py
# 选择 [3] 测试唤醒词 + TTS 集成
```

### 3. 运行主程序

```bash
python3 main.py
```

说出唤醒词 **"alexa"**，应该能听到 TTS 语音回复。

---

## 📋 故障排除清单

- [ ] 运行 `diagnose_audio.py` 诊断设备
- [ ] 检查 `config.yaml` 中的 `output_device` 设置
- [ ] 使用 `amixer` 检查音量设置
- [ ] 运行 `speaker-test` 测试音频输出
- [ ] 尝试不同的输出设备（`plughw:0,0`, `hw:0,0`, `default`）
- [ ] 检查 3.5mm 接头是否正确连接
- [ ] 使用 `raspi-config` 配置音频输出
- [ ] 重启树莓派

---

## 💡 附加提示

### 查看实时日志

```bash
# 运行主程序并查看详细日志
python3 main.py

# 或查看 systemd 服务日志
sudo journalctl -u voice-assistant.service -f
```

### 切换到 HDMI 音频

如果使用 HDMI 连接显示器和音箱：

```yaml
# config.yaml
audio:
  output_device: "plughw:1,0"  # HDMI 通常使用卡1
```

### 使用 USB 音频设备

如果使用 USB 音频适配器：

```bash
# 查看 USB 设备
lsusb | grep -i audio

# 列出音频设备
aplay -L | grep -i usb

# 配置
audio:
  output_device: "plughw:1,0"  # USB 设备
```

---

## 🔗 相关资源

- [树莓派音频配置](https://www.raspberrypi.com/documentation/computers/configuration.html)
- [ALSA 项目](https://www.alsa-project.org/)
- [aplay 手册](https://linux.die.net/man/1/aplay)

---

**需要帮助?**

如果问题仍然存在，请收集以下信息：

1. `diagnose_audio.py` 的完整输出
2. `aplay -L` 的输出
3. `config.yaml` 的内容
4. `sudo journalctl -u voice-assistant.service -n 50` 的日志

然后提交 Issue 或联系技术支持。
