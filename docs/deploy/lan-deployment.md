# 局域网部署指南

**用途**: 从测试环境（开发机）部署到生产环境（树莓派5）
**支持方式**: SCP、rsync、Git、Samba
**文档版本**: 1.0.0

---

## 📋 目录

- [部署流程概览](#部署流程概览)
- [方式一：SCP 直接传输](#方式一scp-直接传输)
- [方式二：rsync 同步](#方式二rsync-同步)
- [方式三：Git 仓库](#方式三git-仓库)
- [方式四：Samba 共享文件夹](#方式四samba-共享文件夹)
- [生产环境部署步骤](#生产环境部署步骤)
- [常见问题](#常见问题)

---

## 部署流程概览

```
┌─────────────────┐              ┌─────────────────┐
│  开发机 (测试)   │              │  树莓派 (生产)   │
│  AMD64 / Ubuntu │              │  ARM64 / Ubuntu │
├─────────────────┤              ├─────────────────┤
│                 │   传输项目    │                 │
│  ~/dev/home_pi/ │ ────────────→ │ ~/home_pi/      │
│                 │              │                 │
│  - 开发测试     │              │  - 生产运行     │
│  - 代码修改     │              │  - 开机自启     │
└─────────────────┘              └─────────────────┘
```

### 部署前检查

**开发机（测试环境）**:
```bash
# 1. 确认项目路径
cd ~/dev/home_pi  # 或你的项目路径
pwd

# 2. 确认代码已提交
git status
# 或确认已测试完成

# 3. 排除不必要的文件
ls -la .venv/
# 虚拟环境不需要传输
```

**树莓派（生产环境）**:
```bash
# 1. 检查网络连接
hostname -I
# 记录 IP 地址，例如: 192.168.1.100

# 2. 检查 SSH 服务
sudo systemctl status ssh
# 应该是 active (running)

# 3. 检查磁盘空间
df -h
# 确保有足够空间
```

---

## 方式一：SCP 直接传输

**适合**: 单次传输、文件较小（< 100MB）

### 开发机操作

```bash
# 1. 打包项目（排除虚拟环境）
cd ~/dev/home_pi
tar -czf home_pi.tar.gz \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='logs/*' \
    --exclude='*.log' \
    .

# 2. 传输到树莓派
# 替换 192.168.1.100 为你的树莓派 IP
scp home_pi.tar.gz pi@192.168.1.100:~/

# 3. 传输配置文件（如果有）
scp config.yaml pi@192.168.1.100:~/home_pi/

# 4. 清理临时文件
rm home_pi.tar.gz
```

### 树莓派操作

```bash
# 1. 解压项目
cd ~
tar -xzf home_pi.tar.gz -C home_pi/
rm home_pi.tar.gz

# 2. 进入项目目录
cd ~/home_pi

# 3. 检查文件
ls -la

# 4. 继续部署步骤（见下方）
```

---

## 方式二：rsync 同步

**适合**: 频繁更新、增量同步、保留文件权限

### 开发机操作

```bash
# 1. 使用 rsync 同步（排除虚拟环境）
rsync -avz --progress \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='logs/*' \
    --exclude='*.log' \
    ~/dev/home_pi/ \
    pi@192.168.1.100:~/home_pi/

# 参数说明:
# -a: 归档模式，保留权限、时间等
# -v: 详细输出
# -z: 压缩传输
# --progress: 显示进度
```

### 同步特定文件

```bash
# 只同步源代码
rsync -avz ~/dev/home_pi/src/ pi@192.168.1.100:~/home_pi/src/

# 只同步配置文件
rsync -avz ~/dev/home_pi/*.yaml pi@192.168.1.100:~/home_pi/

# 只同步测试文件
rsync -avz ~/dev/home_pi/tests/ pi@192.168.1.100:~/home_pi/tests/
```

### 创建同步脚本

**开发机** `~/dev/sync-to-pi.sh`:

```bash
#!/bin/bash
# 同步项目到树莓派

PROJECT_DIR="$HOME/dev/home_pi"
PI_USER="pi"
PI_HOST="192.168.1.100"  # 修改为你的树莓派 IP
PI_DIR="~/home_pi"

echo "正在同步到 $PI_USER@$PI_HOST:$PI_DIR ..."

rsync -avz --progress \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='logs/*' \
    --exclude='*.log' \
    --exclude='.pytest_cache' \
    --exclude='htmlcov' \
    --exclude='.coverage' \
    "$PROJECT_DIR/" \
    "$PI_USER@$PI_HOST:$PI_DIR/"

echo "同步完成！"
echo ""
echo "在树莓派上运行以下命令部署："
echo "  cd ~/home_pi"
echo "  source .venv/bin/activate"
echo "  sudo systemctl restart voice-assistant.service"
```

使用：

```bash
chmod +x ~/dev/sync-to-pi.sh
~/dev/sync-to-pi.sh
```

---

## 方式三：Git 仓库

**适合**: 版本控制、多人协作、有 Git 服务器

### 方案 A: 使用 GitHub/GitLab

```bash
# 开发机 - 提交代码
cd ~/dev/home_pi
git add .
git commit -m "发布 v1.0.0 到生产环境"
git push origin main

# 树莓派 - 拉取代码
cd ~/home_pi
git fetch origin
git reset --hard origin/main  # 强制更新
```

### 方案 B: 局域网 Git 服务器

#### 在开发机上设置 Git 服务器

```bash
# 1. 安装 Git
sudo apt install git

# 2. 创建裸仓库
sudo mkdir -p /srv/git/home_pi.git
sudo cd /srv/git/home_pi.git
sudo git init --bare

# 3. 设置权限
sudo chown -R $USER:$USER /srv/git/home_pi.git

# 4. 在项目目录添加远程
cd ~/dev/home_pi
git remote add pi /srv/git/home_pi.git

# 5. 推送到本地仓库
git push pi main
```

#### 在树莓派上克隆

```bash
# 通过 SSH 克隆
git clone ssh://admin@开发机IP/srv/git/home_pi.git ~/home_pi

# 或者使用 SCP 传输仓库
# 开发机:
cd ~
tar -czf home_pi.git.tar.gz /srv/git/home_pi.git
scp home_pi.git.tar.gz admin@192.168.1.200:~/

# 树莓派:
mkdir -p ~/repos
tar -xzf ~/home_pi.git.tar.gz -C ~/repos/
git clone ~/repos/home_pi.git ~/home_pi
```

---

## 方式四：Samba 共享文件夹

**适合**: Windows 环境、图形界面操作

### 在树莓派上安装 Samba

```bash
# 1. 安装 Samba
sudo apt update
sudo apt install -y samba

# 2. 配置 Samba
sudo vim /etc/samba/smb.conf
```

添加以下内容：

```ini
[home_pi]
   path = /home/pi/home_pi
   browseable = yes
   writable = yes
   create mask = 0775
   directory mask = 0775
   force user = pi
```

```bash
# 3. 设置 Samba 密码
sudo smbpasswd -a pi

# 4. 重启 Samba
sudo systemctl restart smbd
```

### 在开发机上访问

```bash
# Linux 开发机
sudo apt install smbclient
# 查看共享文件夹
smbclient -L 192.168.1.100 -U pi

# 挂载到本地
sudo mkdir /mnt/pi
sudo mount -t cifs //192.168.1.100/home_pi /mnt/pi -o user=pi

# 复制文件
cp -r ~/dev/home_pi/* /mnt/pi/

# 卸载
sudo umount /mnt/pi
```

**Windows 开发机**:
```
# 在文件管理器中输入
\\192.168.1.100\home_pi

# 或映射网络驱动器
```

---

## 生产环境部署步骤

**在树莓派上执行**:

### 1. 准备环境

```bash
# 确认 Python 3.10 已安装
python3.10 --version

# 如果没有，安装它
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev

# 安装系统依赖
sudo apt install -y portaudio19-dev python3.10-dev
```

### 2. 创建虚拟环境

```bash
cd ~/home_pi

# 删除旧的虚拟环境（如果有）
rm -rf .venv

# 使用 Python 3.10 创建
python3.10 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 验证版本
python --version
# 必须是 Python 3.10.x
```

### 3. 安装依赖

```bash
# 升级 pip
pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt

# 验证关键包
python -c "import openwakeword; print('✅ openwakeword')"
python -c "import pyaudio; print('✅ pyaudio')"
python -c "import numpy; print('✅ numpy')"
```

### 4. 配置项目

```bash
# 如果没有配置文件
cp config.example.yaml config.yaml
vim config.yaml

# 根据实际环境修改配置
# 主要检查音频设备名称
```

### 5. 安装 ReSpeaker 驱动（如果未安装）

```bash
# 克隆驱动
cd ~
git clone https://github.com/seeed-studio/seeed-voicecard.git
cd seeed-voicecard

# 安装驱动
sudo ./install.sh

# 重启
sudo reboot
```

### 6. 测试硬件

```bash
# 重启后重新连接
cd ~/home_pi
source .venv/bin/activate

# 测试硬件
python3 tests/manual/test_hardware.py
```

### 7. 测试完整流程

```bash
# 测试唤醒词检测
python3 tests/manual/test_phase1_flow.py
```

### 8. 配置开机自启

```bash
# 创建 systemd 服务文件
sudo vim /etc/systemd/system/voice-assistant.service
```

内容：

```ini
[Unit]
Description=Voice Assistant Service
Documentation=https://github.com/your-repo/home_pi
After=network.target sound.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/home_pi
Environment="PATH=/home/pi/home_pi/.venv/bin:/usr/bin"
ExecStart=/home/pi/home_pi/.venv/bin/python /home/pi/home_pi/main.py
Restart=always
RestartSec=10

# 日志
StandardOutput=journal
StandardError=journal
SyslogIdentifier=voice-assistant

[Install]
WantedBy=multi-user.target
```

```bash
# 重载 systemd
sudo systemctl daemon-reload

# 启用开机自启
sudo systemctl enable voice-assistant.service

# 启动服务
sudo systemctl start voice-assistant.service

# 查看状态
sudo systemctl status voice-assistant.service

# 查看日志
sudo journalctl -u voice-assistant.service -f
```

### 9. 验证部署

```bash
# 1. 检查服务状态
sudo systemctl status voice-assistant.service
# 应该是 active (running)

# 2. 查看日志
sudo journalctl -u voice-assistant.service -n 50

# 3. 检查进程
ps aux | grep python
# 应该看到 main.py 在运行

# 4. 测试唤醒词
# 对着麦克风说 "alexa"
# 应该听到蜂鸣声回复

# 5. 检查日志
tail -f logs/assistant.log
```

---

## 一键部署脚本

**树莓派** `~/home_pi/deploy.sh`:

```bash
#!/bin/bash
# 生产环境一键部署脚本

set -e

PROJECT_DIR="$HOME/home_pi"
VENV_DIR="$PROJECT_DIR/.venv"
SERVICE_FILE="/etc/systemd/system/voice-assistant.service"

echo "========================================"
echo "🚀 语音助手生产环境部署"
echo "========================================"
echo ""

# 1. 检查 Python 3.10
echo "📋 检查 Python 3.10..."
if ! command -v python3.10 &> /dev/null; then
    echo "❌ Python 3.10 未安装"
    echo "请先安装: sudo apt install python3.10 python3.10-venv"
    exit 1
fi
echo "✅ Python 3.10 已安装"
echo ""

# 2. 创建虚拟环境
echo "📦 创建虚拟环境..."
if [ -d "$VENV_DIR" ]; then
    echo "⚠️  虚拟环境已存在，删除重建"
    rm -rf "$VENV_DIR"
fi

python3.10 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
python_version=$(python --version)
echo "✅ 虚拟环境创建成功 ($python_version)"
echo ""

# 3. 安装依赖
echo "📥 安装项目依赖..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r "$PROJECT_DIR/requirements.txt"
echo "✅ 依赖安装完成"
echo ""

# 4. 验证配置
echo "🔧 检查配置文件..."
if [ ! -f "$PROJECT_DIR/config.yaml" ]; then
    echo "⚠️  配置文件不存在，创建默认配置"
    cp "$PROJECT_DIR/config.example.yaml" "$PROJECT_DIR/config.yaml"
fi
echo "✅ 配置文件就绪"
echo ""

# 5. 配置服务
echo "🔧 配置 systemd 服务..."
if [ -f "$SERVICE_FILE" ]; then
    echo "⚠️  服务文件已存在，跳过"
else
    echo "请创建服务文件:"
    echo "  sudo vim /etc/systemd/system/voice-assistant.service"
    echo ""
    exit 0
fi
echo ""

# 6. 测试
echo "🧪 运行测试..."
cd "$PROJECT_DIR"
source "$VENV_DIR/bin/activate"
python3 -c "import openwakeword; print('✅ openwakeword 导入成功')"
python3 -c "import pyaudio; print('✅ pyaudio 导入成功')"
echo ""

# 7. 启动服务
echo "🚀 启动服务..."
sudo systemctl daemon-reload
sudo systemctl enable voice-assistant.service
sudo systemctl restart voice-assistant.service
sleep 2
sudo systemctl status voice-assistant.service --no-pager
echo ""

echo "========================================"
echo "✅ 部署完成！"
echo "========================================"
echo ""
echo "查看日志:"
echo "  sudo journalctl -u voice-assistant.service -f"
echo ""
echo "查看服务状态:"
echo "  sudo systemctl status voice-assistant.service"
echo ""
echo "停止/重启服务:"
echo "  sudo systemctl stop voice-assistant.service"
echo "  sudo systemctl restart voice-assistant.service"
echo ""
```

使用：

```bash
chmod +x ~/home_pi/deploy.sh
~/home_pi/deploy.sh
```

---

## 快速部署流程总结

### 开发机（准备）

```bash
# 1. 确认代码已测试
cd ~/dev/home_pi

# 2. 提交代码（如果使用 Git）
git add .
git commit -m "发布到生产环境"

# 3. 同步到树莓派（选择一种方式）
# 方式 A: rsync
rsync -avz --progress \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    ~/dev/home_pi/ \
    pi@192.168.1.100:~/home_pi/

# 方式 B: Git
git push origin main

# 方式 C: SCP
tar -czf home_pi.tar.gz --exclude='.venv' .
scp home_pi.tar.gz pi@192.168.1.100:~/
```

### 树莓派（部署）

```bash
# 1. 进入项目目录
cd ~/home_pi

# 2. 如果使用 Git
git pull origin main

# 3. 运行部署脚本
./deploy.sh

# 4. 测试
source .venv/bin/activate
python3 tests/manual/test_phase1_flow.py

# 5. 启动服务
sudo systemctl start voice-assistant.service
```

---

## 常见问题

### Q1: rsync 传输很慢

**解决**: 使用压缩和排除更多文件

```bash
rsync -avzz --progress \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='logs/*' \
    --exclude='*.log' \
    --exclude='models/*' \
    --exclude='tests/manual/*.wav' \
    ~/dev/home_pi/ \
    pi@192.168.1.100:~/home_pi/
```

### Q2: SSH 连接被拒绝

**解决**: 检查 SSH 服务

```bash
# 树莓派上
sudo systemctl status ssh
sudo systemctl start ssh
sudo systemctl enable ssh

# 查看IP
hostname -I
```

### Q3: 权限问题

**解决**: 使用正确的用户和权限

```bash
# 树莓派上
sudo chown -R pi:pi ~/home_pi
chmod +x ~/home_pi/*.sh
```

### Q4: 虚拟环境在不同架构间不兼容

**解决**: 虚拟环境不能跨架构传输，必须重建

```bash
# 开发机 (AMD64) 的 .venv 不要传输
# 在树莓派 (ARM64) 上重新创建
python3.10 -m venv .venv
```

### Q5: 服务启动失败

**解决**: 查看详细日志

```bash
# 查看服务日志
sudo journalctl -u voice-assistant.service -n 100 --no-pager

# 手动运行测试
cd ~/home_pi
source .venv/bin/activate
python3 main.py
```

---

## 推荐部署方式

| 场景 | 推荐方式 | 原因 |
|------|---------|------|
| **首次部署** | rsync | 保留权限、增量传输 |
| **频繁更新** | Git | 版本管理、回滚方便 |
| **单次传输** | SCP | 简单直接 |
| **图形界面** | Samba | Windows 友好 |
| **自动化** | rsync + 脚本 | 可编写脚本自动化 |

**最佳实践**:
- 开发时使用 Git 管理代码
- 部署时使用 rsync 同步
- 虚拟环境在生产环境重建

---

**部署准备就绪！** 🚀

选择适合你的方式，将项目从开发机传输到树莓派生产环境。

