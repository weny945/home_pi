# Picovoice 唤醒词修复总结

## 已完成的修复（2026-02-11）

### 1. ✅ 环境变量检查 - main.py

**修改内容**：
- 在 `main.py` 的 `main()` 函数开头添加环境变量检查
- 如果 Picovoice Access Key 未加载，立即中断执行并提示错误

**效果**：
```bash
# 未加载环境变量时运行
python main.py
# 输出：
# ❌ 错误：Picovoice Access Key 未配置！
#    请先加载环境变量: source .env.sh
#    获取方式: https://console.picovoice.ai/
```

### 2. ✅ 自动加载环境变量 - start-service.sh

**修改内容**：
- 在启动服务前自动加载 `.env.sh`
- 检查关键环境变量是否加载成功
- 显示加载状态

**效果**：
```bash
./start-service.sh
# 输出：
# [INFO] 正在加载环境变量...
# [INFO] ✅ Picovoice Access Key 已加载
# [INFO] ✅ DashScope API Key 已加载
```

### 3. ✅ 音频设备配置修复 - config.yaml

**修改内容**：
- 将 `input_device` 从 `"ReSpeaker 4 Mic Array"` 改为 `"plughw:0,0"`
- 使用 ALSA 直接访问硬件设备

**原因**：
- PyAudio 枚举无法正确识别 ReSpeaker 的输入通道数
- 直接使用 ALSA 设备名称可以绕过枚举问题

**配置**：
```yaml
audio:
  input_device: "plughw:0,0"  # Card 0, Device 0
  sample_rate: 16000
  channels: 1
  chunk_size: 512
  input_gain: 3.0
```

### 4. ✅ 音频输入代码增强 - respeaker_input.py

**修改内容**：
- 支持 ALSA 设备名称格式（`plughw:0,0`, `hw:0,0`, `default`）
- 自动查找 ReSpeaker 设备
- 提供详细的错误诊断信息

**特性**：
- 智能设备匹配（名称或索引）
- 降级策略（找不到设备时使用默认设备）
- 增强的错误提示

---

## 测试步骤

### 1. 停止占用音频设备的进程（已完成）

```bash
sudo systemctl stop voice-assistant.service
# 或
kill -9 $(pgrep -f "main.py")
```

### 2. 测试音频设备（已验证 ✅）

```bash
# ALSA 录音测试
arecord -D plughw:0,0 -f cd -d 3 /tmp/test.wav
# 结果：✅ 录音成功，生成 345KB 文件
```

### 3. 测试 Picovoice 唤醒词（需要手动测试）

```bash
# 加载环境变量
source .env.sh

# 运行测试（需要说"胡桃"）
python tests/manual/test_picovoice_wake_word.py
```

**预期输出**：
```
============================================================
Picovoice 唤醒词测试
============================================================
Access Key (from env): vqmLo4yqTyp4PPASkhnu...

初始化 Picovoice 检测器...
✅ 检测器就绪
  帧大小: 512
  采样率: 16000

初始化音频输入...
找到候选设备: sysdefault (索引: 0)
  音频设备: plughw:0,0
  块大小: 512

============================================================
开始监听唤醒词（说'胡桃'）...
按 Ctrl+C 退出
============================================================

运行中... 已处理 100 帧 (31.2 fps)
运行中... 已处理 200 帧 (31.5 fps)
```

**测试唤醒**：
- 对着麦克风清晰地说"胡桃"
- 距离 1-3 米
- 环境相对安静
- 使用标准普通话发音

**成功标志**：
```
✅✅✅ 检测到唤醒词！（第 XXX 帧）
============================================================
```

---

## 启动服务（生产环境）

修复完成后，启动服务：

```bash
# 方法1：使用启动脚本（推荐）
./start-service.sh

# 方法2：手动启动
source .env.sh
python main.py

# 方法3：systemd 服务
sudo systemctl start voice-assistant.service
```

---

## 问题根因分析

### 问题1：环境变量未加载 ⚠️ **致命**

**症状**：
- Picovoice 初始化成功但无法检测唤醒词
- 日志显示 "⚠️  未提供 Access Key"

**根本原因**：
- Picovoice 官网训练的唤醒词（`.ppn` 文件）**必须**使用 Access Key 验证
- 未执行 `source .env.sh` 导致环境变量未加载

**修复**：
- 在 main.py 中添加检查，未加载时中断执行
- 在 start-service.sh 中自动加载环境变量

### 问题2：音频设备被占用

**症状**：
```
OSError: [Errno -9996] Invalid input device
arecord: audio open error: Device or resource busy
```

**根本原因**：
- 后台有 `main.py` 进程正在运行
- 音频设备同一时间只能被一个进程访问

**解决**：
- 停止旧进程后再启动新测试

### 问题3：PyAudio 无法枚举输入设备

**症状**：
```bash
# PyAudio 枚举结果
设备 0: sysdefault (输入通道: 0)  # 报告为 0 通道！
设备 1: default (输入通道: 0)
设备 2: dmix (输入通道: 0)

# 但 ALSA 能看到设备
arecord -l
card 0: ArrayUAC10 [ReSpeaker 4 Mic Array (UAC1.0)], device 0
```

**根本原因**：
- PyAudio 的 ALSA 后端在某些情况下无法正确查询输入通道数
- 这是 PyAudio/ALSA 交互的已知问题

**解决方案**：
1. **直接使用 ALSA 设备名称**：`plughw:0,0`（已采用）
2. 代码增强：智能查找设备，不依赖通道数判断
3. 提供降级策略：找不到设备时使用默认设备

---

## 配置文件说明

### .env.sh（环境变量）

**必需配置**：
```bash
export PICOVOICE_ACCESS_KEY="vqmLo4yqTyp4PPASkhnuYhLDLpxaPdHi9+jej0STKVMvYoEzoyJcgg=="
export DASHSCOPE_API_KEY="sk-7198c03ff1c54b1ba4f5942ef834d681"
```

**获取方式**：
- Picovoice: https://console.picovoice.ai/
- DashScope: https://dashscope.console.aliyun.com/

### config.yaml（系统配置）

**关键配置**：
```yaml
audio:
  input_device: "plughw:0,0"  # ALSA 直接访问
  sample_rate: 16000
  channels: 1
  chunk_size: 512
  input_gain: 3.0

wakeword:
  engine: "picovoice"
  model: "models/picovoice/胡桃_zh_raspberry-pi_v4_0_0.ppn"
  sensitivity: 0.5  # 0.0-1.0，越高越灵敏
  access_key: "${PICOVOICE_ACCESS_KEY}"
  porcupine_model: "models/picovoice/porcupine_params_zh.pv"
```

---

## 诊断工具

### 1. 音频设备诊断

```bash
python tests/manual/diagnose_audio_devices.py
```

### 2. 环境检查

```bash
# 检查环境变量
echo $PICOVOICE_ACCESS_KEY
echo $DASHSCOPE_API_KEY

# 检查设备
lsusb | grep -i respeaker
arecord -l

# 检查进程
ps aux | grep main.py
lsof /dev/snd/*
```

### 3. 录音测试

```bash
# ALSA 录音测试
arecord -D plughw:0,0 -f cd -d 3 test.wav

# 播放测试
aplay test.wav
```

---

## 文件修改清单

| 文件 | 修改内容 | 状态 |
|------|----------|------|
| `main.py` | 添加环境变量检查 | ✅ |
| `start-service.sh` | 自动加载 .env.sh | ✅ |
| `config.yaml` | 修改 input_device | ✅ |
| `src/audio/respeaker_input.py` | 支持 ALSA 设备名称 | ✅ |
| `tests/manual/diagnose_audio_devices.py` | 新增诊断工具 | ✅ |
| `docs/TROUBLESHOOTING_PICOVOICE.md` | 新增故障排查文档 | ✅ |

---

## 下一步操作

### 1. 手动测试唤醒词（重要！）

```bash
source .env.sh
python tests/manual/test_picovoice_wake_word.py
# 说"胡桃"测试
```

### 2. 启动服务

```bash
./start-service.sh
```

### 3. 查看日志

```bash
# 实时查看系统日志
sudo journalctl -u voice-assistant.service -f

# 实时查看应用日志
tail -f logs/phase1.log
```

### 4. 测试完整流程

- 说"胡桃"唤醒
- 听到唤醒回复（TTS）
- 说出指令
- 收到回复

---

## 常见问题快速参考

| 问题 | 解决方法 |
|------|----------|
| "环境变量未配置" | `source .env.sh` |
| "Invalid input device" | 停止旧进程 `kill -9 $(pgrep -f main.py)` |
| "Device or resource busy" | 同上 |
| 无法唤醒 | 检查环境变量、提高 sensitivity |
| 音频质量差 | 调整 input_gain、检查麦克风距离 |

---

## 总结

**已修复的核心问题**：
1. ✅ 环境变量未加载（已添加自动检查和加载）
2. ✅ 音频设备配置错误（已改用 ALSA 直接访问）
3. ✅ PyAudio 枚举问题（已实现智能设备查找）

**当前状态**：
- ✅ 代码修改完成
- ✅ 配置文件更新
- ✅ ALSA 录音测试通过
- ⏳ Picovoice 唤醒词测试（需要人工验证）

**建议**：
1. 先手动测试唤醒词功能
2. 确认能正常唤醒后再启动服务
3. 如有问题，查看 `docs/TROUBLESHOOTING_PICOVOICE.md`

