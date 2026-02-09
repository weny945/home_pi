# Ubuntu 24 / 树莓派5 Python 环境配置指南

**适用系统**: Ubuntu 24.04 LTS on Raspberry Pi 5
**推荐 Python 版本**: 3.10.x
**原因**: openwakeword 的 tflite-runtime 依赖支持最佳

---

## ⚠️ 重要说明

### Python 版本兼容性

| Python 版本 | openwakeword | 推荐度 | 说明 |
|------------|-------------|--------|------|
| **3.10** | ✅ 完全支持 | ⭐⭐⭐⭐⭐ | **推荐**，LTS 版本 |
| 3.11 | ✅ 支持 | ⭐⭐⭐⭐ | 可用，但非首选 |
| 3.12 | ❌ 不支持 | ⭐ | tflite-runtime 不兼容 |

### 为什么选择 Python 3.10？

- ✅ Python 3.10 是 LTS 长期支持版本
- ✅ openwakeword 官方主要在 3.10 上测试
- ✅ 树莓派 OS 默认使用 3.10
- ✅ 兼容性和稳定性最好

### Ubuntu 可以安装多个 Python 版本吗？

**✅ 完全可以！** Ubuntu 支持同时安装多个 Python 版本：

```bash
# 系统可以同时有：
/usr/bin/python3.10  ← 项目使用这个
/usr/bin/python3.11  ← 可选
/usr/bin/python3.12  ← 系统默认（不用于此项目）

# 每个版本互不干扰，独立使用
python3.10 --version
python3.11 --version
python3.12 --version
```

### 项目的 Python 在哪里？

**✅ 在虚拟环境中！** 这是 Python 最佳实践：

```
~/home_pi/                  ← 项目目录
├── .venv/                   ← 虚拟环境（项目专用，独立隔离）
│   ├── bin/
│   │   ├── python           → Python 3.10 副本
│   │   ├── pip
│   │   └── activate
│   └── lib/
│       └── python3.10/
│           └── site-packages/
│               ├── numpy/   ← 项目依赖
│               ├── openwakeword/
│               └── ...
├── src/                     ← 源代码
├── tests/                   ← 测试
└── requirements.txt         ← 依赖列表
```

**虚拟环境优势**：
- ✅ **隔离**: 完全独立，不影响系统，也不受系统影响
- ✅ **便携**: 整个项目依赖都在 .venv 目录
- ✅ **灵活**: 不同项目可以使用不同 Python 版本
- ✅ **易管**: 删除项目只需删除目录，无需清理

---

## 安装 Python 3.10

### 方法 1: 使用 deadsnakes PPA（推荐）

**最简单的方法**，适合大多数用户：

```bash
# 1. 添加 deadsnakes PPA
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# 2. 安装 Python 3.10
sudo apt install -y python3.10 python3.10-venv python3.10-dev

# 3. 验证安装
python3.10 --version
# 预期输出: Python 3.10.x
```

### 方法 2: 从源码编译

如果 PPA 不可用或需要特定版本：

```bash
# 1. 安装编译依赖
sudo apt update
sudo apt install -y build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev curl \
    libncursesw5-dev xz-utils tk-dev libxml2-dev \
    libxmlsec1-dev libffi-dev liblzma-dev

# 2. 下载 Python 3.10 源码
cd /tmp
wget https://www.python.org/ftp/python/3.10.13/Python-3.10.13.tgz
tar -xzf Python-3.10.13.tgz
cd Python-3.10.13

# 3. 编译安装（树莓派需要 30-60 分钟）
./configure --enable-optimizations --with-lto
make -j$(nproc)
sudo make altinstall

# 4. 验证安装
python3.10 --version
```

### 方法 3: 使用 pyenv（多版本管理）

**适合需要管理多个 Python 版本的开发者**：

```bash
# 1. 安装 pyenv 依赖
sudo apt update
sudo apt install -y make build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev curl \
    libncursesw5-dev xz-utils tk-dev libxml2-dev \
    libxmlsec1-dev libffi-dev liblzma-dev git

# 2. 安装 pyenv
curl https://pyenv.run | bash

# 3. 配置环境变量
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc

# 4. 安装 Python 3.10
pyenv install 3.10.13

# 5. 设置全局或局部版本
# 全局版本（影响所有目录）
pyenv global 3.10.13

# 或局部版本（仅当前项目）
cd ~/home_pi
pyenv local 3.10.13

# 6. 验证
python --version
# 应该显示: Python 3.10.13
```

---

## 创建虚拟环境

### 使用 Python 3.10 创建

```bash
# 进入项目目录
cd ~/home_pi

# ⚠️ 关键：使用 Python 3.10 创建虚拟环境
python3.10 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 验证 Python 版本（重要！）
python --version
# ✅ 必须显示: Python 3.10.x
# ❌ 如果是 3.12.x，说明创建错误！
```

### 验证虚拟环境

```bash
# 1. 查看版本
python --version

# 2. 查看 Python 路径
which python
# 应该显示: /home/pi/home_pi/.venv/bin/python
# 而不是: /usr/bin/python3

# 3. 查看 Python 的实际链接
ls -l .venv/bin/python
# python -> python3.10

# 4. 查看已安装的包
pip list
```

---

## 安装项目依赖

### 基础依赖

```bash
# 激活虚拟环境
source ~/home_pi/.venv/bin/activate

# 升级 pip
pip install --upgrade pip setuptools wheel

# 安装项目依赖
pip install -r requirements.txt

# 验证关键包
python -c "import openwakeword; print('✅ openwakeword OK')"
python -c "import pyaudio; print('✅ pyaudio OK')"
python -c "import numpy; print('✅ numpy OK')"
```

### 系统依赖

```bash
# 安装 PortAudio（PyAudio 依赖）
sudo apt install -y portaudio19-dev python3.10-dev

# 验证 PyAudio
python -c "import pyaudio; p = pyaudio.PyAudio(); print(f'✅ PyAudio {p.get_version()}')"
```

---

## 安装 ReSpeaker 驱动

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

重启后验证：
```bash
# 查看音频设备
arecord -L | grep seeed
# 应该看到 seeed-4mic-voicecard
```

---

## 运行测试

```bash
# 激活虚拟环境
cd ~/home_pi
source .venv/bin/activate

# 1. 硬件测试
python3 tests/manual/test_hardware.py

# 2. 流程测试
python3 tests/manual/test_phase1_flow.py

# 3. 主程序
python3 main.py
```

---

## 故障排除

### 问题 1: Python 3.10 未找到

**错误**: `bash: python3.10: command not found`

**解决**:
```bash
# 检查已安装的 Python 版本
ls -l /usr/bin/python3*

# 如果没有 3.10，重新安装
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev
```

### 问题 2: 虚拟环境使用了错误的 Python 版本

**症状**: 虚拟环境中 `python --version` 显示 3.12

**解决**:
```bash
# 退出虚拟环境
deactivate

# 删除旧虚拟环境
rm -rf ~/home_pi/.venv

# 使用 Python 3.10 重新创建
cd ~/home_pi
python3.10 -m venv .venv
source .venv/bin/activate

# 验证版本
python --version
# 应该显示: Python 3.10.x

# 重新安装依赖
pip install -r requirements.txt
```

### 问题 3: openwakeword 安装失败

**错误**: `No matching distribution found for tflite-runtime`

**原因**: 虚拟环境使用了 Python 3.12

**解决**: 参考问题 2，重新创建虚拟环境

### 问题 4: numpy 版本冲突

**错误**: `numpy version mismatch` 或安装失败

**解决**:
```bash
# 卸载旧版本
pip uninstall numpy -y

# 安装兼容版本
pip install "numpy>=1.21.0,<2.0.0"
```

### 问题 5: PyAudio 安装失败

**错误**: `PortAudio not found`

**解决**:
```bash
# 安装系统依赖
sudo apt install -y portaudio19-dev python3.10-dev

# 重新安装 PyAudio
pip install pyaudio
```

### 问题 6: 虚拟环境无法激活

**错误**: `source: .venv/bin/activate: No such file or directory`

**原因**: 虚拟环境创建失败

**解决**:
```bash
# 删除损坏的虚拟环境
rm -rf ~/home_pi/.venv

# 确保 Python 3.10 已安装
python3.10 --version

# 重新创建
python3.10 -m venv .venv
source .venv/bin/activate
```

---

## 配置开机自启服务

如果使用 systemd 服务，需要确保服务使用虚拟环境中的 Python 3.10：

```bash
# 编辑服务文件
sudo vim /etc/systemd/system/voice-assistant.service
```

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

**关键点**: `ExecStart` 使用虚拟环境中的 Python：`/home/pi/home_pi/.venv/bin/python`

---

## 验证安装

### 完整检查清单

```bash
# 1. 系统 Python 3.10 已安装
python3.10 --version
# ✅ 输出: Python 3.10.x

# 2. 虚拟环境使用 Python 3.10
source ~/home_pi/.venv/bin/activate
python --version
# ✅ 输出: Python 3.10.x

# 3. Python 在虚拟环境中
which python
# ✅ 输出: /home/pi/home_pi/.venv/bin/python

# 4. 关键包已安装
python -c "import openwakeword; print('✅ openwakeword')"
python -c "import pyaudio; print('✅ pyaudio')"
python -c "import numpy; print('✅ numpy')"
# ✅ 所有检查通过

# 5. ReSpeaker 驱动已安装
arecord -L | grep seeed
# ✅ 输出包含 seeed-4mic-voicecard

# 6. 硬件测试通过
python3 tests/manual/test_hardware.py
# ✅ 所有测试通过

# 7. 流程测试通过
python3 tests/manual/test_phase1_flow.py
# ✅ 检测到唤醒词并播放反馈
```

---

## 常用命令参考

```bash
# === Python 版本管理 ===
# 查看所有已安装的 Python 版本
ls /usr/bin/python3*

# 查看特定版本
python3.10 --version

# === 虚拟环境 ===
# 创建虚拟环境（使用 Python 3.10）
python3.10 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 退出虚拟环境
deactivate

# 查看虚拟环境中的 Python 版本
python --version

# 查看 Python 路径
which python

# === 依赖管理 ===
# 安装依赖
pip install -r requirements.txt

# 查看已安装的包
pip list

# 升级 pip
pip install --upgrade pip

# === 测试 ===
# 运行硬件测试
python3 tests/manual/test_hardware.py

# 运行流程测试
python3 tests/manual/test_phase1_flow.py

# === 服务管理 ===
# 启动服务
sudo systemctl start voice-assistant.service

# 查看服务状态
sudo systemctl status voice-assistant.service

# 查看服务日志
sudo journalctl -u voice-assistant.service -f
```

---

## 总结

### 推荐配置

| 项目 | 推荐 | 说明 |
|------|------|------|
| **Python 版本** | 3.10.x | LTS 版本，兼容性最好 |
| **虚拟环境** | venv | 标准库内置，无需额外安装 |
| **包管理** | pip + requirements.txt | 简单可靠 |

### 安装顺序

1. ✅ 安装 Python 3.10（`python3.10`）
2. ✅ 创建虚拟环境（`python3.10 -m venv .venv`）
3. ✅ 安装 PortAudio（`sudo apt install portaudio19-dev`）
4. ✅ 安装 Python 依赖（`pip install -r requirements.txt`）
5. ✅ 安装 ReSpeaker 驱动
6. ✅ 配置并测试

### 关键要点

1. **Ubuntu 支持多个 Python 版本共存**，互不干扰
2. **项目的 Python 在虚拟环境中**，与系统完全隔离
3. **创建虚拟环境时必须指定版本**：`python3.10 -m venv .venv`
4. **验证虚拟环境中的 Python 版本**：`source .venv/bin/activate && python --version`
5. **不要使用系统默认的 Python 3.12**，会导致依赖安装失败

---

**配置完成！** 🎉

现在你的 Ubuntu 24 / 树莓派5 环境已经配置好了，可以开始使用语音助手了。

Sources:
- [openwakeword PyPI](https://pypi.org/project/openwakeword/)
- [Python venv 官方文档](https://docs.python.org/3/library/venv.html)
- [deadsnakes PPA](https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa)
