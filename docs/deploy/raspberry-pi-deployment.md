# 树莓派部署指南

**版本**: 1.1
**日期**: 2026-01-22
**硬件平台**: 树莓派 5 (8GB RAM) + ReSpeaker 4 Mic Array
**状态**: ✅ 生产就绪

**v1.1 更新**: 集成 Piper TTS 语音回复功能

---

## 📋 目录

- [硬件准备](#硬件准备)
- [系统安装](#系统安装)
- [软件安装](#软件安装)
- [驱动配置](#驱动配置)
- [项目部署](#项目部署)
- [启动测试](#启动测试)
- [开机自启](#开机自启)
- [故障排除](#故障排除)

---

## 硬件准备

### 必需硬件

| 设备 | 规格 | 用途 |
|------|------|------|
| **树莓派 5** | 8GB RAM | 主控板 |
| **Micro SD 卡** | 32GB+, Class 10 | 系统存储 |
| **电源适配器** | 5V 5A USB-C | 供电 |
| **ReSpeaker 4 Mic Array** | USB | 麦克风阵列 |

### 可选硬件

| 设备 | 规格 | 用途 |
|------|------|------|
| 散热风扇 | 5V | 降温 |
| 外壳 | - | 保护 |
| LED 指示灯 | - | 状态显示 |

---

## 系统安装

### 1. 下载系统镜像

**推荐**: Raspberry Pi OS Lite (64-bit)

下载地址: https://www.raspberrypi.com/software/operating-systems/

选择: `raspios_lite_arm64- bullseye.img.xz`

### 2. 烧录 SD 卡

**使用 Raspberry Pi Imager**:

1. 下载 Raspberry Pi Imager: https://www.raspberrypi.com/software/
2. 插入 SD 卡到电脑
3. 运行 Raspberry Pi Imager
4. 选择 OS: `Raspberry Pi OS Lite (64-bit)`
5. 选择 Storage: 你的 SD 卡
6. 点击设置图标 ⚙️，配置:
   - 设置主机名: `pi-assistant`
   - 启用 SSH: 使用密码认证
   - 设置用户名: `pi`
   - 设置密码: `your_password`
   - 配置 WiFi: SSID 和密码
7. 烧录

### 3. 首次启动

1. 将 SD 卡插入树莓派
2. 连接 ReSpeaker 到 USB 端口
3. 插入电源启动
4. 通过 SSH 连接:
   ```bash
   ssh pi@pi-assistant.local
   ```

---

## 软件安装

### 1. 更新系统

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. 一键安装脚本

```bash
# 克隆项目
git clone https://github.com/your-repo/home_pi.git
cd home_pi

# 运行安装脚本
chmod +x setup.sh
./setup.sh
```

**安装脚本会自动**:
- ✅ 检测 ARM64 架构
- ✅ 创建 Python 虚拟环境
- ✅ 安装系统依赖
- ✅ 安装 Python 依赖
- ✅ 下载唤醒词模型
- ✅ 验证安装

### 3. 手动安装（可选）

如果一键安装失败，请参考 [INSTALL.md](../../INSTALL.md)

---

## 驱动配置

### 安装 ReSpeaker 驱动

```bash
# 1. 克隆驱动仓库
cd ~
git clone https://github.com/seeed-studio/seeed-voicecard.git
cd seeed-voicecard

# 2. 安装驱动
sudo ./install.sh

# 3. 重启系统
sudo reboot
```

### 验证驱动安装

重启后重新连接:

```bash
ssh pi@pi-assistant.local

# 查看音频设备
arecord -L | grep seeed
```

**预期输出**:
```
seeed-4mic-voicecard
    seeed-4mic-voicecard
...
```

---

## 项目部署

### 1. 配置文件

```bash
cd ~/home_pi
cp config.example.yaml config.yaml
vim config.yaml
```

**关键配置**:

```yaml
audio:
  input_device: "seeed-4mic-voicecard"  # ReSpeaker 设备名
  sample_rate: 16000
  channels: 1
  chunk_size: 512

wakeword:
  engine: "openwakeword"
  threshold: 0.5  # 检测阈值 (0-1)

feedback:
  mode: "tts"  # "beep" 蜂鸣声, "audio_file" 音频文件, "tts" 语音回复
  beep_duration_ms: 200
  beep_frequency: 880

  # TTS 语音回复配置（mode: "tts" 时使用）
  tts:
    engine: "piper"
    model_path: "./models/piper/zh_CN-huayan-medium.onnx"
    length_scale: 1.0  # 语速 (1.0=正常, <1.0=更快, >1.0=更慢)
    messages:
      - "我在"
      - "请吩咐"
      - "我在听"
      - "您好"
      - "我在这里"
    random_message: false  # 是否随机选择
    cache_audio: true  # 是否缓存音频

logging:
  level: "INFO"
  file: "./logs/assistant.log"
```

### 2. 创建必要目录

```bash
mkdir -p logs models/piper
```

### 3. 下载 Piper TTS 模型 (v1.1 必需)

```bash
# 进入模型目录
cd ~/home_pi/models/piper

# 下载中文 TTS 模型 (~63MB)
wget https://huggingface.co/rhasspy/piper-voices/v1.0.0/zh_CN/zh_CN-huayan-medium/onnx/zh_CN-huayan-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/v1.0.0/zh_CN/zh_CN-huayan-medium/onnx/zh_CN-huayan-medium.onnx.json

# 验证文件
ls -lh
# 应该看到:
# zh_CN-huayan-medium.onnx    (~63MB)
# zh_CN-huayan-medium.onnx.json  (~5KB)
```

**备用下载方式**:
如果无法访问 HuggingFace，可以从镜像下载：
```bash
# 使用 ModelScope (国内镜像)
# 模型会自动缓存到 ~/.local/share/piper/voices/
```

---

## 启动测试

### 1. 测试硬件

```bash
# 测试麦克风和扬声器
python3 tests/manual/test_hardware.py
```

选择:
- `[1]` 测试麦克风录音
- `[2]` 测试音响播放

### 2. 测试唤醒词

```bash
# 测试唤醒词检测
python3 tests/manual/test_hardware.py
# 选择 [3]
```

对着麦克风说 **"alexa"**，应该能检测到。

### 3. 测试 TTS 语音回复 (v1.1 新增)

```bash
# 测试 Piper TTS 引擎和反馈播放器
python3 tests/manual/test_software.py
```

选择:
- `[1]` 测试 TTS 引擎
- `[2]` 测试 TTS 反馈播放器
- `[3]` 测试唤醒词检测 + TTS 反馈集成

### 4. 测试完整流程

```bash
# 测试第一阶段 1.1 完整流程
python3 tests/manual/test_software.py
# 选择 [3]
```

说出唤醒词 **"alexa"** 后，应该听到 TTS 语音回复（如"我在"、"请吩咐"等）。

### 5. 运行主程序

```bash
# 启动语音助手
python3 main.py
```

**日志输出**:
```
2026-01-22 10:00:00 - root - INFO - ============================================================
2026-01-22 10:00:00 - root - INFO - 语音助手系统启动 v1.1.0 (第一阶段 1.1：唤醒词检测 + TTS语音回复)
2026-01-22 10:00:00 - root - INFO - ============================================================
2026-01-22 10:00:00 - root - INFO - 加载配置文件...
2026-01-22 10:00:00 - root - INFO - 初始化音频输入...
2026-01-22 10:00:00 - root - INFO - 初始化唤醒词检测器...
2026-01-22 10:00:00 - root - INFO - 加载所有 OpenWakeWord 预训练模型...
2026-01-22 10:00:01 - root - INFO - 成功加载 6 个唤醒词模型:
2026-01-22 10:00:01 - root - INFO -   - alexa
2026-01-22 10:00:01 - root - INFO -   - hey_jarvis
...
2026-01-22 10:00:01 - root - INFO - 初始化反馈播放器...
2026-01-22 10:00:02 - root - INFO - 使用 Piper TTS 语音回复模式 (语速: 1.0)
2026-01-22 10:00:02 - root - INFO - 状态机主循环启动...
2026-01-22 10:00:02 - root - INFO - 等待唤醒词...
```

按 `Ctrl+C` 停止程序。

---

## 开机自启

### 使用 systemd 服务

#### 1. 创建服务文件

```bash
sudo vim /etc/systemd/system/voice-assistant.service
```

**内容**:

```ini
[Unit]
Description=Voice Assistant Service
After=network.target sound.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/home_pi
Environment="PATH=/home/pi/home_pi/.venv/bin:/usr/bin"
ExecStart=/home/pi/home_pi/.venv/bin/python /home/pi/home_pi/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 2. 启用并启动服务

```bash
# 重载 systemd 配置
sudo systemctl daemon-reload

# 启用开机自启
sudo systemctl enable voice-assistant.service

# 启动服务
sudo systemctl start voice-assistant.service

# 查看服务状态
sudo systemctl status voice-assistant.service
```

#### 3. 查看日志

```bash
# 实时查看服务日志
sudo journalctl -u voice-assistant.service -f

# 查看最近 100 行
sudo journalctl -u voice-assistant.service -n 100
```

#### 4. 管理服务

```bash
# 停止服务
sudo systemctl stop voice-assistant.service

# 重启服务
sudo systemctl restart voice-assistant.service

# 禁用开机自启
sudo systemctl disable voice-assistant.service
```

---

## 性能优化

### 1. CPU 性能模式

```bash
# 检查当前 CPU 频率
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq

# 设置性能模式
sudo cpufreq-set -g performance

# 查看所有 Governor
cpufreq-info
```

### 2. 内存优化

```bash
# 查看内存使用
free -h

# 监控内存
watch -n 1 free -h
```

### 3. 监控系统资源

```bash
# 安装 htop
sudo apt install htop -y

# 运行 htop
htop
```

---

## 故障排除

### 问题 1: ReSpeaker 未检测到

**症状**:
```
❌ 未找到 ReSpeaker 设备
```

**解决**:
```bash
# 1. 检查 USB 连接
lsusb | grep -i seeed

# 2. 检查驱动
arecord -L | grep seeed

# 3. 重新安装驱动
cd ~/seeed-voicecard
sudo ./install.sh
sudo reboot
```

### 问题 2: 唤醒词检测不工作

**症状**: 说出唤醒词无反应

**解决**:
```bash
# 1. 检查模型文件
ls -lh ~/.venv/lib/python3.10/site-packages/openwakeword/resources/models/

# 2. 测试音频输入
arecord -f S16_LE -r 16000 -c 1 -d 3 test.wav
aplay test.wav

# 3. 降低检测阈值
# 编辑 config.yaml
wakeword:
  threshold: 0.3  # 从 0.5 降低到 0.3
```

### 问题 3: 听不到蜂鸣声/TTS 语音

**症状**: 检测到唤醒词但无声音

**解决**:
```bash
# 1. 检查播放设备
aplay -L

# 2. 测试播放
speaker-test -t wav -c 1

# 3. 检查音量
amixer set Master 100%
```

### 问题 4: TTS 模型加载失败 (v1.1)

**症状**:
```
❌ 模型文件不存在: models/piper/zh_CN-huayan-medium.onnx
```

**解决**:
```bash
# 1. 确认目录存在
mkdir -p models/piper

# 2. 重新下载模型
cd models/piper
wget https://huggingface.co/rhasspy/piper-voices/v1.0.0/zh_CN/zh_CN-huayan-medium/onnx/zh_CN-huayan-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/v1.0.0/zh_CN/zh_CN-huayan-medium/onnx/zh_CN-huayan-medium.onnx.json

# 3. 验证文件完整性
ls -lh
# zh_CN-huayan-medium.onnx    (~63MB)
# zh_CN-huayan-medium.onnx.json  (~5KB)

# 4. 测试 TTS 引擎
cd ~/home_pi
python3 tests/manual/test_software.py
# 选择 [1]
```

### 问题 5: TTS 语音无输出 (v1.1)

**症状**: 检测到唤醒词，但无 TTS 语音回复

**解决**:
```bash
# 1. 检查配置文件
cat config.yaml | grep -A 10 "feedback:"
# 确保 mode: "tts"

# 2. 测试 TTS 反馈播放器
python3 tests/manual/test_software.py
# 选择 [2] 或 [3]

# 3. 检查 Piper TTS 是否安装
source .venv/bin/activate
python -c "from piper import PiperVoice; print('✅ Piper TTS 已安装')"

# 4. 检查音频输出
aplay -L
speaker-test -t wav -c 1
```

### 问题 6: 服务启动失败

**症状**:
```
sudo systemctl status voice-assistant.service
# Status: failed
```

**解决**:
```bash
# 1. 查看详细日志
sudo journalctl -u voice-assistant.service -n 50 --no-pager

# 2. 手动运行测试
cd ~/home_pi
python3 main.py

# 3. 检查权限
ls -la /home/pi/home_pi/
```

### 问题 7: CPU 占用过高

**症状**: CPU 占用 > 50%

**解决**:
```bash
# 1. 检查进程
top

# 2. 检查是否有多个实例
ps aux | grep python

# 3. 降低采样率
# 编辑 config.yaml
audio:
  chunk_size: 1024  # 增加块大小
```

---

## 系统维护

### 更新项目

```bash
cd ~/home_pi
git pull origin main

# 更新依赖
source .venv/bin/activate
pip install -r requirements.txt

# 重启服务
sudo systemctl restart voice-assistant.service
```

### 查看日志

```bash
# 应用日志
tail -f logs/assistant.log

# 系统服务日志
sudo journalctl -u voice-assistant.service -f
```

### 备份配置

```bash
# 备份配置文件
cp config.yaml config.yaml.backup

# 备份整个项目
tar -czf home_pi_backup.tar.gz ~/home_pi
```

---

## 附录

### A. 系统信息查询

```bash
# 查看系统版本
cat /etc/os-release

# 查看 Python 版本
python3 --version

# 查看虚拟环境
which python3

# 查看音频设备
aplay -L
arecord -L
```

### B. 网络配置

```bash
# 查看 IP 地址
hostname -I

# 查看 WiFi 状态
iwconfig

# 测试网络
ping -c 4 baidu.com
```

### C. 存储空间

```bash
# 查看 SD 卡使用情况
df -h

# 查看目录大小
du -sh ~/home_pi
```

---

## 支持与反馈

- **项目地址**: https://github.com/your-repo/home_pi
- **问题反馈**: https://github.com/your-repo/home_pi/issues
- **文档**: https://github.com/your-repo/home_pi/wiki

---

**部署完成！** 🎉

现在你的树莓派语音助手已经可以工作了！
