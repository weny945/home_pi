# Picovoice 唤醒词故障排查指南

## 问题总结

Picovoice 唤醒词无法工作的原因分析（已完成诊断）：

### ✅ 已修复的问题

1. **环境变量未加载** ⚠️ **致命问题**
   - **症状**：Picovoice Access Key 未加载到运行环境
   - **原因**：启动前未执行 `source .env.sh`
   - **修复**：
     - 已在 `main.py` 中添加环境变量检查（未加载会中断执行）
     - 已在 `start-service.sh` 中添加自动加载 `.env.sh`

2. **音频设备配置不匹配**
   - **症状**：PyAudio 无法通过设备名称找到 ReSpeaker
   - **原因**：PyAudio 枚举问题，无法正确识别 ALSA 输入设备
   - **修复**：已修改 `src/audio/respeaker_input.py` 支持 ALSA 设备名称

### 🔥 当前关键问题

**音频设备被占用** ⚠️ **需要立即解决**

**症状**：
```
arecord: audio open error: Device or resource busy
OSError: [Errno -9996] Invalid input device
```

**原因**：
- 后台有 `main.py` 进程（PID 5887）正在运行
- 该进程已占用音频设备，导致新进程无法访问

**解决方法**：

#### 方法1：停止服务（推荐）
```bash
sudo systemctl stop voice-assistant.service
```

#### 方法2：手动杀进程
```bash
# 查看进程
ps aux | grep main.py

# 停止进程（替换 PID）
kill 5887
# 或强制停止
kill -9 5887
```

#### 方法3：重启系统（最彻底）
```bash
sudo reboot
```

---

## 完整修复步骤

### 第一步：停止占用音频设备的进程

```bash
# 停止服务
sudo systemctl stop voice-assistant.service

# 确认没有进程占用
ps aux | grep main.py
# 应该没有输出（除了 grep 自身）
```

### 第二步：加载环境变量

```bash
cd ~/home_pi
source .env.sh
```

**验证环境变量**：
```bash
echo $PICOVOICE_ACCESS_KEY
# 应该输出：vqmLo4yqTyp4PPASkhnu...（不是空或 ${...}）
```

### 第三步：修改配置文件（可选，推荐）

编辑 `config.yaml`，修改音频设备配置：

```yaml
audio:
  # 方法1：使用 ALSA 设备名称（推荐，直接访问硬件）
  input_device: "plughw:0,0"  # Card 0, Device 0

  # 方法2：使用默认设备
  # input_device: "default"

  # 其他配置保持不变
  sample_rate: 16000
  channels: 1
  chunk_size: 512
  input_gain: 3.0
```

### 第四步：测试音频设备

```bash
# 测试 ALSA 录音（应该成功）
arecord -D plughw:0,0 -f cd -d 3 /tmp/test.wav
# 按 Ctrl+C 停止

# 测试 PyAudio 设备诊断
python tests/manual/diagnose_audio_devices.py
```

### 第五步：测试 Picovoice 唤醒词

```bash
# 确保环境变量已加载
source .env.sh

# 运行测试
python tests/manual/test_picovoice_wake_word.py
```

**预期输出**：
```
✅ 检测器就绪
  帧大小: 512
  采样率: 16000

初始化音频输入...
  音频设备: plughw:0,0
  块大小: 512

============================================================
开始监听唤醒词（说'胡桃'）...
按 Ctrl+C 退出
============================================================

运行中... 已处理 100 帧 (31.2 fps)
```

**测试唤醒**：
- 对着麦克风说"胡桃"（清晰、标准普通话）
- 距离 1-3 米
- 环境相对安静

### 第六步：启动服务（生产环境）

```bash
# start-service.sh 已修改，会自动加载环境变量
./start-service.sh
```

---

## 配置说明

### 1. 环境变量配置 (`.env.sh`)

**必需的环境变量**：
```bash
# Picovoice Access Key（唤醒词检测必需）
export PICOVOICE_ACCESS_KEY="vqmLo4yqTyp4PPASkhnuYhLDLpxaPdHi9+jej0STKVMvYoEzoyJcgg=="

# 千问 API Key（对话生成必需）
export DASHSCOPE_API_KEY="sk-your-key-here"

# 豆包 TTS（可选）
export DOUBAO_ACCESS_KEY="your-key-here"
export DOUBAO_APP_ID="your-app-id"
```

**获取方式**：
- Picovoice: https://console.picovoice.ai/
- DashScope: https://dashscope.console.aliyun.com/

### 2. 音频设备配置 (`config.yaml`)

**推荐配置**（树莓派 + ReSpeaker）：
```yaml
audio:
  input_device: "plughw:0,0"  # 直接使用 ALSA 设备
  output_device: "default"
  sample_rate: 16000
  channels: 1
  chunk_size: 512
  input_gain: 3.0  # USB 模式需要高增益
```

**备选配置**：
```yaml
audio:
  input_device: "ReSpeaker 4 Mic Array"  # 通过名称查找（可能失败）
  # 或
  input_device: "default"  # 使用系统默认设备
```

### 3. 唤醒词配置 (`config.yaml`)

```yaml
wakeword:
  engine: "picovoice"
  model: "models/picovoice/胡桃_zh_raspberry-pi_v4_0_0.ppn"
  sensitivity: 0.5  # 0.0-1.0，越高越灵敏（但误报也越多）
  access_key: "${PICOVOICE_ACCESS_KEY}"  # 从环境变量读取
  porcupine_model: "models/picovoice/porcupine_params_zh.pv"  # 中文模型
```

---

## 常见问题

### Q1: 运行测试时提示 "环境变量未加载"

**原因**：未执行 `source .env.sh`

**解决**：
```bash
source .env.sh
python tests/manual/test_picovoice_wake_word.py
```

### Q2: 提示 "Invalid input device"

**原因**：音频设备被其他进程占用

**解决**：
```bash
# 检查占用进程
lsof /dev/snd/* | grep python

# 停止服务
sudo systemctl stop voice-assistant.service

# 或杀进程
kill -9 $(pgrep -f "main.py")
```

### Q3: 唤醒词无法识别

**可能原因**：
1. ✅ **环境变量未加载**（最常见）
2. ✅ **音频设备配置错误**
3. 灵敏度过低
4. 环境噪音过大
5. 发音不标准

**解决方法**：
1. 确认环境变量：`echo $PICOVOICE_ACCESS_KEY`
2. 修改灵敏度：`sensitivity: 0.7`（提高到 0.7）
3. 降低环境噪音
4. 使用标准普通话发音
5. 距离麦克风 1-2 米测试

### Q4: 检测器就绪但运行报错

**症状**：
```
✅ 检测器就绪
启动音频流失败: [Errno -9996] Invalid input device
```

**原因**：PyAudio 无法访问音频设备

**解决**：
1. 修改 `config.yaml` 使用 `plughw:0,0`
2. 测试 ALSA 录音：`arecord -D plughw:0,0 -d 3 test.wav`
3. 检查设备权限：`groups | grep audio`
4. 重启系统：`sudo reboot`

---

## 验证清单

完成修复后，请依次验证：

- [ ] 环境变量已加载：`echo $PICOVOICE_ACCESS_KEY`
- [ ] 没有进程占用音频设备：`lsof /dev/snd/* | grep python`
- [ ] ALSA 录音正常：`arecord -D plughw:0,0 -d 3 test.wav`
- [ ] Picovoice 测试成功：`python tests/manual/test_picovoice_wake_word.py`
- [ ] 能检测到唤醒词（说"胡桃"）

---

## 技术细节

### 为什么 PyAudio 看不到输入设备？

**诊断结果**：
```bash
# PyAudio 枚举结果
设备 0: sysdefault (输入通道: 0, 输出通道: 128)
设备 1: default (输入通道: 0, 输出通道: 128)
设备 2: dmix (输入通道: 0, 输出通道: 2)

# 但 ALSA 能看到设备
arecord -l
card 0: ArrayUAC10 [ReSpeaker 4 Mic Array (UAC1.0)], device 0
```

**原因分析**：
- PyAudio 的默认枚举方式无法正确识别某些 ALSA 设备的输入通道数
- 这是 PyAudio/ALSA 交互的已知问题
- 直接使用 ALSA 设备名称（`plughw:0,0`）可以绕过枚举问题

### 代码修改说明

1. **`main.py`**：添加了环境变量检查，未加载时中断执行
2. **`start-service.sh`**：自动加载 `.env.sh`
3. **`src/audio/respeaker_input.py`**：支持 ALSA 设备名称格式

---

## 总结

**问题根源**：
1. ✅ 环境变量未加载（已修复）
2. ✅ 音频设备被占用（需要手动停止进程）
3. ✅ PyAudio 枚举问题（已通过使用 ALSA 设备名称绕过）

**修复后的工作流程**：
```bash
# 1. 停止旧进程
sudo systemctl stop voice-assistant.service

# 2. 加载环境变量
source .env.sh

# 3. 测试
python tests/manual/test_picovoice_wake_word.py

# 4. 生产部署
./start-service.sh  # 会自动加载环境变量
```

