# Python 版本选择快速指南

**问题**: Ubuntu 24 / 树莓派5 默认使用 Python 3.12，但不兼容 openwakeword

**解决**: 使用 Python 3.10（推荐）

---

## ⚡ 快速解决方案（3分钟）

### 推荐配置

| 项目 | 版本 | 说明 |
|------|------|------|
| **Python** | **3.10.x** | ✅ 稳定兼容，推荐 |
| Python | 3.11.x | ✅ 可用 |
| Python | 3.12.x | ❌ 不兼容 |

### 核心概念

```
系统 Python（多个版本共存）:
├── /usr/bin/python3.10  ← 项目使用这个
├── /usr/bin/python3.11  ← 可选
└── /usr/bin/python3.12  ← 系统默认（不用）

项目虚拟环境（隔离）:
└── ~/home_pi/.venv/     ← 使用 Python 3.10 创建
    └── lib/python3.10/site-packages/  ← 项目依赖
```

---

## 🚀 Ubuntu 24 / 树莓派5 快速安装

### 步骤 1: 安装 Python 3.10（2分钟）

```bash
# 添加 deadsnakes PPA
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# 安装 Python 3.10 及相关工具
sudo apt install -y python3.10 python3.10-venv python3.10-dev

# 验证安装
python3.10 --version
# 输出: Python 3.10.x
```

### 步骤 2: 创建虚拟环境（30秒）

```bash
# 进入项目目录
cd ~/home_pi

# ⚠️ 关键：使用 Python 3.10 创建虚拟环境
python3.10 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate
```

### 步骤 3: 验证版本（10秒）

```bash
# 查看虚拟环境中的 Python 版本
python --version
# ✅ 必须显示: Python 3.10.x
# ❌ 如果是 3.12.x，说明创建错误！
```

### 步骤 4: 安装依赖（1分钟）

```bash
# 升级 pip
pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt
```

---

## ❓ 常见问题

### Q1: Ubuntu 可以安装多个 Python 版本吗？

**✅ 可以！** 完全支持，它们互不干扰：

```bash
# 查看所有已安装的 Python 版本
ls /usr/bin/python3*

# 示例输出：
# /usr/bin/python3.10
# /usr/bin/python3.11
# /usr/bin/python3.12

# 每个版本独立使用：
python3.10 --version  # Python 3.10.x
python3.11 --version  # Python 3.11.x
python3.12 --version  # Python 3.12.x
```

### Q2: 项目的 Python 安装在哪里？

**✅ 在虚拟环境中！** 这是最佳实践：

```
~/home_pi/
├── .venv/                    ← 虚拟环境（项目专用）
│   ├── bin/
│   │   ├── python            → 指向 Python 3.10
│   │   ├── pip
│   │   └── activate
│   └── lib/
│       └── python3.10/       ← 使用 Python 3.10
│           └── site-packages/
│               ├── numpy/
│               ├── openwakeword/
│               └── ...       ← 所有项目依赖
├── src/                      ← 源代码
├── tests/                    ← 测试
└── requirements.txt          ← 依赖列表
```

**优势**：
- ✅ **隔离**: 不影响系统 Python，也不受系统影响
- ✅ **独立**: 每个项目可以有不同版本
- ✅ **易管理**: 删除项目只需删除 .venv 目录
- ✅ **无权限**: 不需要 sudo 安装依赖

### Q3: 如何指定使用哪个 Python 版本？

**创建虚拟环境时指定**：

```bash
# 使用 Python 3.10 创建
python3.10 -m venv .venv

# 使用 Python 3.11 创建
python3.11 -m venv .venv

# 使用系统默认（可能是 3.12，不推荐）
python3 -m venv .venv
```

### Q4: 虚拟环境已经用 Python 3.12 创建了怎么办？

**删除并重新创建**：

```bash
# 1. 退出当前虚拟环境（如果在其中）
deactivate

# 2. 删除旧虚拟环境
rm -rf ~/home_pi/.venv

# 3. 使用 Python 3.10 重新创建
cd ~/home_pi
python3.10 -m venv .venv

# 4. 激活新虚拟环境
source .venv/bin/activate

# 5. 重新安装依赖
pip install -r requirements.txt
```

### Q5: 如何验证虚拟环境使用的 Python 版本？

```bash
# 激活虚拟环境
source ~/home_pi/.venv/bin/activate

# 查看版本
python --version

# 查看完整路径
which python
# 应该显示: /home/pi/home_pi/.venv/bin/python
# 而不是: /usr/bin/python3

# 查看 Python 的实际链接
ls -l ~/home_pi/.venv/bin/python
# python -> python3.10
```

### Q6: 为什么要用 Python 3.10 而不是 3.11？

**原因**：
- ✅ Python 3.10 是 LTS 版本，更稳定
- ✅ openwakeword 官方测试主要在 3.10 上
- ✅ 树莓派 OS 默认使用 3.10
- ✅ 兼容性最好

**Python 3.11 也可以用**，但 3.10 是我们的标准选择。

### Q7: 系统的 Python 和虚拟环境的 Python 有什么区别？

```
系统 Python（全局）:
/usr/bin/python3.10       ← 系统级，所有用户共享
/usr/lib/python3.10/      ← 系统包

虚拟环境 Python（项目）:
~/home_pi/.venv/bin/python3.10  ← 项目级，仅此项目
~/home_pi/.venv/lib/python3.10/ ← 项目包
```

**结论**：虚拟环境中的 Python 是**独立的副本**，完全隔离。

---

## 📋 部署检查清单

在 Ubuntu 24 / 树莓派5 上部署前，请确认：

- [ ] 系统已安装 Python 3.10: `python3.10 --version`
- [ ] 使用 Python 3.10 创建虚拟环境: `python3.10 -m venv .venv`
- [ ] 虚拟环境中 Python 版本是 3.10.x:
      ```bash
      source .venv/bin/activate
      python --version
      ```
- [ ] 已安装所有依赖: `pip install -r requirements.txt`
- [ ] openwakeword 导入成功: `python -c "import openwakeword"`
- [ ] 测试通过: `python3 tests/manual/test_phase1_flow.py`

---

## 🔧 常用命令

```bash
# 查看系统所有 Python 版本
ls /usr/bin/python3*

# 查看 Python 3.10 是否安装
python3.10 --version

# 创建虚拟环境（使用 Python 3.10）
python3.10 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 查看当前 Python 版本
python --version

# 查看 Python 路径
which python

# 退出虚拟环境
deactivate

# 删除虚拟环境
rm -rf .venv

# 重新创建（如果出错了）
rm -rf .venv && python3.10 -m venv .venv
```

---

## 🎯 完整安装流程（Ubuntu 24 / 树莓派5）

```bash
# 1. 安装 Python 3.10
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev

# 2. 安装 PortAudio（PyAudio 依赖）
sudo apt install -y portaudio19-dev python3.10-dev

# 3. 克隆项目（如果还没有）
git clone https://github.com/your-repo/home_pi.git
cd home_pi

# 4. 创建虚拟环境（关键：使用 Python 3.10）
python3.10 -m venv .venv

# 5. 激活虚拟环境
source .venv/bin/activate

# 6. 验证 Python 版本
python --version
# ✅ 必须是: Python 3.10.x

# 7. 安装项目依赖
pip install --upgrade pip
pip install -r requirements.txt

# 8. 安装 ReSpeaker 驱动
cd ~
git clone https://github.com/seeed-studio/seeed-voicecard.git
cd seeed-voicecard
sudo ./install.sh
sudo reboot

# 9. 重启后测试
cd ~/home_pi
source .venv/bin/activate
python3 tests/manual/test_phase1_flow.py
```

---

## 📚 相关文档

- **完整配置指南**: [ubuntu24-python-setup.md](./ubuntu24-python-setup.md)
- **树莓派部署指南**: [raspberry-pi-deployment.md](./raspberry-pi-deployment.md)
- **项目安装指南**: [INSTALL.md](../../INSTALL.md)
- **安装脚本**: `setup.sh` (自动检测和创建)

---

## 💡 总结

1. ✅ **Ubuntu 可以安装多个 Python 版本**，它们互不干扰
2. ✅ **项目的 Python 在虚拟环境中**，与系统隔离
3. ✅ **使用 Python 3.10 创建虚拟环境**：`python3.10 -m venv .venv`
4. ✅ **验证虚拟环境版本**：`source .venv/bin/activate && python --version`
5. ❌ **不要使用系统默认的 Python 3.12**，会安装失败

---

**核心要点**: 使用 `python3.10 -m venv .venv` 创建虚拟环境，确保项目使用 Python 3.10！

Sources:
- [openwakeword PyPI](https://pypi.org/project/openwakeword/)
- [Python venv 文档](https://docs.python.org/3/library/venv.html)
- [deadsnakes PPA](https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa)
