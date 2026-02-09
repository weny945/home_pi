# 安装指南

**版本**: 1.0
**日期**: 2026-01-21

---

## 快速安装

### Linux / macOS

```bash
# 1. 克隆或下载项目
cd /path/to/home_pi

# 2. 运行安装脚本
chmod +x setup.sh
./setup.sh
```

**安装脚本会自动**:
- ✅ 检测系统架构 (AMD64/ARM64)
- ✅ 检查 Python 版本
- ✅ 创建虚拟环境
- ✅ 安装所有依赖
- ✅ 验证安装成功

### Windows

```cmd
# 1. 进入项目目录
cd C:\path\to\home_pi

# 2. 运行安装脚本
setup.bat
```

---

## 手动安装

### 1. Python 环境

**要求**: Python 3.10+

```bash
python3 --version  # 检查版本
```

### 2. 创建虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/mac
# 或
.venv\Scripts\activate  # Windows
```

### 3. 安装系统依赖

**Linux (AMD64)**:
```bash
sudo apt update
sudo apt install -y portaudio19-dev python3-dev
```

**Linux (ARM64 / 树莓派)**:
```bash
sudo apt update
sudo apt install -y portaudio19-dev python3-dev
```

**Windows**:
- 下载并安装 PortAudio: http://www.portaudio.com/
- 或使用 `pip install pyaudio` (可能需要编译器)

### 4. 安装 Python 依赖

**AMD64 (开发环境)**:
```bash
pip install -r requirements.txt
```

**ARM64 (树莓派)**:
```bash
pip install -r requirements-arm64.txt
```

---

## 依赖说明

### 核心依赖

| 包 | 版本 | 说明 |
|---|------|------|
| numpy | >=1.21.0,<2.0.0 | 数值计算 |
| pyyaml | >=6.0 | YAML 配置文件解析 |
| pyaudio | >=0.2.12 | 音频 I/O |

### 唤醒词检测

| 包 | 版本 | 说明 |
|---|------|------|
| openwakeword | >=0.5.0 | 离线唤醒词检测 |

### 测试依赖

| 包 | 版本 | 说明 |
|---|------|------|
| pytest | >=7.0.0 | 测试框架 |
| pytest-mock | >=3.10.0 | Mock 支持 |
| pytest-cov | >=4.0.0 | 覆盖率 |

### 可选依赖

| 包 | 说明 |
|---|------|
| psutil | 性能监控 (硬件测试) |

---

## 架构兼容性

### AMD64 (开发环境)

- ✅ 开发机
- ✅ 单元测试
- ✅ Mock 硬件测试

### ARM64 (树莓派 5)

- ✅ 生产环境
- ✅ 真实硬件测试
- ✅ ReSpeaker 驱动支持

---

## 安装 ReSpeaker 驱动 (仅树莓派)

### 自动安装

```bash
# 在安装脚本中选择 "y" 安装驱动
./setup.sh
```

### 手动安装

```bash
# 1. 克隆驱动仓库
git clone https://github.com/seeed-studio/seeed-voicecard.git
cd seeed-voicecard

# 2. 安装驱动
sudo ./install.sh

# 3. 重启系统
sudo reboot
```

### 验证驱动

```bash
# 查看设备列表
arecord -L | grep seeed

# 应该看到 seeed-4mic-voicecard
```

---

## 配置系统

### 1. 复制配置文件

```bash
cp config.example.yaml config.yaml
```

### 2. 编辑配置

```bash
vim config.yaml  # 或使用其他编辑器
```

### 3. 配置音频设备

**查看可用设备**:
```bash
# 录音设备
arecord -L

# 播放设备
aplay -L
```

**更新配置**:
```yaml
audio:
  input_device: "seeed-4mic-voicecard"  # 修改为你的设备名
```

---

## 验证安装

### 1. 运行单元测试

```bash
pytest tests/unit/ -v
```

**预期结果**: 22 passed

### 2. 运行硬件测试

```bash
python tests/manual/test_hardware.py
```

选择 `[l]` 查看设备列表

---

## 故障排除

### Python 版本过低

**错误**: `Python 3.10+ required`

**解决**:
```bash
# 安装 Python 3.10+
# Ubuntu/Debian
sudo apt install python3.10

# macOS
brew install python@3.10
```

### PyAudio 安装失败

**错误**: `PortAudio not found`

**解决**:
```bash
# Linux
sudo apt install portaudio19-dev python3-dev

# macOS
brew install portaudio

# Windows
# 下载并安装 PortAudio
# http://www.portaudio.com/download.html
```

### openwakeword 安装失败

**错误**: `Failed building wheel`

**解决**:
```bash
# 使用预编译版本
pip install --no-binary :all: openwakeword
```

### 虚拟环境问题

**错误**: `Command 'venv' not found`

**解决**:
```bash
# Ubuntu/Debian
sudo apt install python3-venv

# macOS
# Python 3 自带 venv 模块

# Windows
# Python 安装程序自带 venv
```

---

## 下载唤醒词模型

### 官方预训练模型

```bash
# 创建模型目录
mkdir -p models/openwakeword

# 下载模型 (选择一个)
cd models/openwakeword
wget https://github.com/dscripka/openWakeWord/raw/main/data/models/hey_jarvis_v0.1.ppn
# 或
wget https://github.com/dscripka/openWakeWord/raw/main/data/models/alexa_v0.1.ppn
```

### 训练自定义唤醒词

参考: [OpenWakeWord Wiki](https://github.com/dscripka/openWakeWord/wiki)

---

**安装完成！** 🎉

下一步:
1. 配置: `cp config.example.yaml config.yaml`
2. 测试: `python tests/manual/test_hardware.py`
3. 运行: `python main.py`
