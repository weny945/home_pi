#!/bin/bash
# ========================================
# 生产环境一键部署脚本
# 在树莓派上运行
# 不启动服务，只准备环境
# ========================================

set -e

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 配置
PROJECT_DIR="$HOME/home_pi"
VENV_DIR="$PROJECT_DIR/.venv"

echo "========================================"
echo "🚀 语音助手生产环境部署"
echo "========================================"
echo ""
echo_info "项目目录: $PROJECT_DIR"
echo ""

# 1. 检查项目目录
if [ ! -d "$PROJECT_DIR" ]; then
    echo_error "项目目录不存在: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

# 2. 检查 Python 3.10
echo "========================================"
echo "📋 检查 Python 环境"
echo "========================================"

if command -v python3.10 &> /dev/null; then
    PYTHON_VERSION=$(python3.10 --version)
    echo_info "✅ $PYTHON_VERSION"
else
    echo_error "❌ Python 3.10 未安装"
    echo ""
    echo "安装命令:"
    echo "  sudo add-apt-repository ppa:deadsnakes/ppa -y"
    echo "  sudo apt update"
    echo "  sudo apt install -y python3.10 python3.10-venv python3.10-dev"
    exit 1
fi
echo ""

# 3. 创建虚拟环境
echo "========================================"
echo "📦 创建虚拟环境"
echo "========================================"

if [ -d "$VENV_DIR" ]; then
    echo_warn "虚拟环境已存在"
    read -p "是否删除重建? (y/N): " rebuild
    if [[ "$rebuild" =~ ^[Yy]$ ]]; then
        echo_info "删除旧虚拟环境..."
        rm -rf "$VENV_DIR"
    else
        echo_info "保留现有虚拟环境"
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    echo_info "创建虚拟环境 (Python 3.10)..."
    python3.10 -m venv "$VENV_DIR"
    echo_info "✅ 虚拟环境创建成功"
fi

# 激活虚拟环境
source "$VENV_DIR/bin/activate"
VENV_PYTHON_VERSION=$(python --version)
echo_info "虚拟环境 Python: $VENV_PYTHON_VERSION"
echo ""

# 4. 安装系统依赖
echo "========================================"
echo "🔧 安装系统依赖"
echo "========================================"

echo_info "检查 PortAudio..."
if ! dpkg -l | grep -q portaudio19-dev; then
    echo_info "安装 PortAudio..."
    sudo apt update
    sudo apt install -y portaudio19-dev python3.10-dev
else
    echo_info "✅ PortAudio 已安装"
fi

echo_info "检查 ffmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo_info "安装 ffmpeg..."
    sudo apt update
    sudo apt install -y ffmpeg
else
    echo_info "✅ ffmpeg 已安装"
fi
echo ""

# 5. 安装 Python 依赖
echo "========================================"
echo "📥 安装 Python 依赖"
echo "========================================"

echo_info "升级 pip..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1

echo_info "安装项目依赖..."
if pip install -r requirements.txt; then
    echo_info "✅ 依赖安装成功"
else
    echo_error "❌ 依赖安装失败"
    exit 1
fi
echo ""

# 5.5. 下载 openwakeword 模型文件
echo "========================================"
echo "📥 下载 openwakeword 模型文件"
echo "========================================"

echo_info "检查 openwakeword 模型文件..."

# 创建临时脚本来下载模型
cat > /tmp/download_oww_models.py << 'EOF'
import sys
import os
import openwakeword
from pathlib import Path
import time

def check_models():
    """检查模型是否已存在"""
    venv_path = Path(sys.prefix)
    model_dir = venv_path / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages" / "openwakeword" / "resources" / "models"
    if model_dir.exists():
        tflite_files = list(model_dir.glob("*.tflite"))
        return len(tflite_files) > 0
    return False

def download_with_timeout():
    """下载模型，带超时和进度显示"""
    print("开始下载 openwakeword 模型文件...")
    print("提示：首次下载可能需要 2-5 分钟，请耐心等待...")
    print("")

    start_time = time.time()
    timeout = 600  # 10分钟超时

    # 使用线程运行下载
    import threading

    result = {"success": False, "error": None}
    download_complete = threading.Event()

    def download_thread():
        try:
            openwakeword.utils.download_models()
            result["success"] = True
        except Exception as e:
            result["error"] = str(e)
        finally:
            download_complete.set()

    # 启动下载线程
    thread = threading.Thread(target=download_thread)
    thread.daemon = True
    thread.start()

    # 等待下载完成，显示进度
    dots = 0
    while not download_complete.is_set():
        if time.time() - start_time > timeout:
            print(f"\n⏰ 下载超时（{timeout}秒）")
            return False, "下载超时"

        # 显示进度动画
        dots = (dots + 1) % 4
        elapsed = int(time.time() - start_time)
        print(f"\r下载中{'.' * dots}{' ' * (3 - dots)} (已用时: {elapsed}秒)", end="", flush=True)
        download_complete.wait(timeout=1)

    print("")  # 换行

    elapsed = int(time.time() - start_time)
    print(f"✅ 下载完成！总用时: {elapsed}秒")

    if result["error"]:
        return False, result["error"]

    return result["success"], None

try:
    # 先检查是否已有模型
    if check_models():
        print("✅ 模型文件已存在，跳过下载")
        sys.exit(0)

    # 下载模型
    success, error = download_with_timeout()

    if not success:
        print(f"❌ 模型下载失败: {error}")
        sys.exit(1)

    # 验证模型文件
    venv_path = Path(sys.prefix)
    model_dir = venv_path / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages" / "openwakeword" / "resources" / "models"

    if model_dir.exists():
        print(f"模型目录: {model_dir}")
        tflite_files = list(model_dir.glob("*.tflite"))
        print(f"✅ 已下载 {len(tflite_files)} 个模型文件:")
        for f in sorted(tflite_files):
            size = f.stat().st_size / 1024  # KB
            print(f"  - {f.name} ({size:.1f} KB)")
        sys.exit(0)
    else:
        print(f"❌ 错误：模型目录不存在 {model_dir}")
        sys.exit(1)

except KeyboardInterrupt:
    print("\n⚠️  下载被用户中断")
    sys.exit(1)
except Exception as e:
    print(f"❌ 模型下载失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

# 运行下载脚本
echo_info "运行模型下载脚本..."
if python /tmp/download_oww_models.py; then
    echo_info "✅ openwakeword 模型下载成功"
else
    exit_code=$?
    if [ $exit_code -eq 1 ]; then
        echo_error "❌ openwakeword 模型下载失败"
        echo ""
        echo "可能的解决方案:"
        echo "  1. 检查网络连接"
        echo "  2. 稍后手动运行以下命令下载:"
        echo "     source .venv/bin/activate"
        echo "     python -c 'import openwakeword; openwakeword.utils.download_models()'"
        echo ""
        read -p "是否继续部署（模型可在稍后手动下载）? (y/N): " continue_deploy
        if [[ ! "$continue_deploy" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        exit $exit_code
    fi
fi

# 清理临时脚本
rm -f /tmp/download_oww_models.py
echo ""

# 6. 验证关键包
echo "========================================"
echo "🧪 验证关键组件"
echo "========================================"

check_import() {
    if python -c "import $1" 2>/dev/null; then
        echo_info "✅ $1"
        return 0
    else
        echo_error "❌ $1 导入失败"
        return 1
    fi
}

check_import "openwakeword"
check_import "pyaudio"
check_import "numpy"
check_import "yaml"

# 检查 pygame (v1.8 新增 - 音乐播放功能)
echo_info "检查 pygame (音乐播放)..."
if python -c "import pygame; pygame.mixer.init(); pygame.mixer.quit()" 2>/dev/null; then
    echo_info "✅ pygame 已安装并可用"
    echo_info "  支持格式: mp3, wav, ogg, flac 等"
else
    echo_warn "pygame 未安装或初始化失败"
    echo "  音乐播放功能需要 pygame:"
    echo "  pip install pygame>=2.5.0"
fi

# 检查 ffmpeg (v1.2 新增)
echo_info "检查 ffmpeg..."
if command -v ffmpeg &> /dev/null; then
    echo_info "✅ ffmpeg 系统工具已安装"
else
    echo_error "❌ ffmpeg 系统工具未安装"
    echo "  FunASR 需要 ffmpeg 来处理音频文件:"
    echo "  sudo apt install ffmpeg"
fi

# 检查 Piper TTS (v1.1 新增)
echo_info "检查 Piper TTS..."
if python -c "from piper import PiperVoice" 2>/dev/null; then
    echo_info "✅ Piper TTS 已安装"
    echo_info "  注意: 需要下载 Piper 模型文件 (~63MB)"
    echo_info "  模型应放置在: models/piper/zh_CN-huayan-medium.onnx"
else
    echo_warn "Piper TTS 未安装"
    echo "  TTS 语音回复功能需要 Piper TTS:"
    echo "  pip install piper-tts scipy"
fi

# 检查 FunASR STT/VAD (v1.2 新增)
echo_info "检查 FunASR STT/VAD..."
if python -c "from funasr import AutoModel" 2>/dev/null; then
    echo_info "✅ FunASR 已安装"
    echo_info "  注意: 需要下载 FunASR 模型文件 (~210MB)"
    echo_info "  - SenseVoiceSmall (~200MB): 自动下载到 ~/.cache/modelscope/"
    echo_info "  - fsmn-vad (~10MB): 自动下载到 ~/.cache/modelscope/"
else
    echo_warn "FunASR 未安装"
    echo "  语音识别 (STT) 功能需要 FunASR:"
    echo "  pip install funasr modelscope torchaudio"
fi

# 检查 websockets (v2.2 新增 - 千问流式 TTS)
echo_info "检查 websockets (千问流式 TTS)..."
if python -c "import websockets" 2>/dev/null; then
    echo_info "✅ websockets 已安装"
else
    echo_warn "websockets 未安装"
    echo "  千问流式 TTS 功能需要 websockets:"
    echo "  pip install websockets>=12.0"
fi

# 检查 pydub (v2.2 新增 - 千问 TTS 音频解码)
echo_info "检查 pydub (千问 TTS 音频解码)..."
if python -c "import pydub" 2>/dev/null; then
    echo_info "✅ pydub 已安装"
else
    echo_warn "pydub 未安装"
    echo "  千问 TTS 音频解码需要 pydub:"
    echo "  pip install pydub>=0.25.0"
fi

echo ""

# 7. 配置文件
echo "========================================"
echo "🔧 配置文件"
echo "========================================"

if [ ! -f "$PROJECT_DIR/config.yaml" ]; then
    echo_warn "配置文件不存在，创建默认配置"
    cp "$PROJECT_DIR/config.example.yaml" "$PROJECT_DIR/config.yaml"
    echo_info "✅ 配置文件已创建: config.yaml"
    echo_warn "请根据实际情况编辑配置文件"
else
    echo_info "✅ 配置文件已存在"
fi
echo ""

# 7.5. 检查环境变量文件
echo "========================================"
echo "🔧 环境变量文件"
echo "========================================"

if [ ! -f "$PROJECT_DIR/.env.sh" ]; then
    echo_warn ".env.sh 文件不存在"
    echo ""
    echo "⚠️  警告：未配置环境变量，LLM/TTS 功能将不可用"
    echo ""
    echo "请创建 .env.sh 文件并设置 DASHSCOPE_API_KEY:"
    echo "  获取方式: https://dashscope.console.aliyun.com/"
    echo ""
else
    echo_info "✅ 环境变量文件已找到: .env.sh"

    # 检查 API Key 是否配置
    if grep -q "sk-your-dashscope-api-key-here" "$PROJECT_DIR/.env.sh" 2>/dev/null; then
        echo_warn "  API Key 使用默认值，请编辑 .env.sh 设置正确的密钥"
    else
        echo_info "  API Key 已配置"
    fi
fi
echo ""

# 8. 创建 TTS 缓存目录 (v2.2 新增)
echo "========================================"
echo "📁 创建 TTS 缓存目录"
echo "========================================"

CACHE_DIR="$PROJECT_DIR/data/tts_cache"
if [ ! -d "$CACHE_DIR" ]; then
    echo_info "创建缓存目录: $CACHE_DIR"
    mkdir -p "$CACHE_DIR"
    echo_info "✅ 缓存目录已创建"
else
    echo_info "✅ 缓存目录已存在"
fi
echo ""

# 9. 测试硬件（可选）
echo "========================================"
echo "🧪 硬件测试（可选）"
echo "========================================"

read -p "是否运行硬件测试? (y/N): " run_test
if [[ "$run_test" =~ ^[Yy]$ ]]; then
    echo_info "运行硬件测试..."
    python3 tests/manual/test_hardware.py
else
    echo_info "跳过硬件测试，可以稍后手动运行:"
    echo "  cd ~/home_pi"
    echo "  source .venv/bin/activate"
    echo "  python3 tests/manual/test_hardware.py"
fi
echo ""

# 10. 测试软件（可选）
echo "========================================"
echo "🧪 软件测试（可选）"
echo "========================================"

echo_info "请选择测试版本:"
echo "  [1] v1.1 测试 (TTS 引擎 + TTS 反馈播放器 + 唤醒词集成)"
echo "  [2] v1.2 测试 (STT 引擎 + VAD 检测器 + 完整流程)"
echo "  [3] v1.4 测试 (音频质量检测 + 自适应VAD + 分级重试)"
echo "  [4] v1.5 测试 (智能打断 + 对话优化 + 技能框架)"
echo "  [5] v1.7 测试 (语音定闹钟功能)"
echo "  [6] v1.8 测试 (本地音乐播放功能)"
echo "  [7] v2.2 测试 (千问 TTS + 流式 + 缓存)"
echo "  [a] 全部测试"
echo ""
read -p "请选择: " test_choice

if [[ "$test_choice" == "1" ]]; then
    if [ -f "$PROJECT_DIR/tests/manual/test_software.py" ]; then
        echo_info "运行 v1.1 软件测试..."
        python3 tests/manual/test_software.py
    else
        echo_warn "v1.1 测试文件不存在: tests/manual/test_software.py"
    fi
elif [[ "$test_choice" == "2" ]]; then
    if [ -f "$PROJECT_DIR/tests/manual/test_phase12_stt.py" ]; then
        echo_info "运行 v1.2 STT 测试..."
        python3 tests/manual/test_phase12_stt.py
    else
        echo_warn "v1.2 测试文件不存在: tests/manual/test_phase12_stt.py"
    fi
elif [[ "$test_choice" == "3" ]]; then
    if [ -f "$PROJECT_DIR/tests/manual/test_software.py" ]; then
        echo_info "运行 v1.4 音频质量检测测试..."
        python3 tests/manual/test_software.py
        echo ""
        echo "💡 选择测试 [7] 进行 Phase 1.4 测试"
    else
        echo_warn "v1.4 测试文件不存在: tests/manual/test_software.py"
    fi
elif [[ "$test_choice" == "4" ]]; then
    if [ -f "$PROJECT_DIR/tests/manual/test_software.py" ]; then
        echo_info "运行 v1.5 对话优化测试..."
        python3 tests/manual/test_software.py
        echo ""
        echo "💡 选择测试 [8] 进行 Phase 1.5 测试"
    else
        echo_warn "v1.5 测试文件不存在: tests/manual/test_software.py"
    fi
elif [[ "$test_choice" == "5" ]]; then
    if [ -f "$PROJECT_DIR/tests/manual/test_alarm_e2e.py" ]; then
        echo_info "运行 v1.7 闹钟功能测试..."
        python3 tests/manual/test_alarm_e2e.py
    else
        echo_warn "v1.7 测试文件不存在: tests/manual/test_alarm_e2e.py"
    fi
elif [[ "$test_choice" == "6" ]]; then
    if [ -f "$PROJECT_DIR/tests/manual/test_music_e2e.py" ]; then
        echo_info "运行 v1.8 音乐播放测试..."
        python3 tests/manual/test_music_e2e.py
    else
        echo_warn "v1.8 测试文件不存在: tests/manual/test_music_e2e.py"
    fi
elif [[ "$test_choice" == "7" ]]; then
    if [ -f "$PROJECT_DIR/tests/manual/test_tts_cache.py" ]; then
        echo_info "运行 v2.2 TTS 缓存测试..."
        python3 tests/manual/test_tts_cache.py
    else
        echo_warn "v2.2 测试文件不存在: tests/manual/test_tts_cache.py"
    fi
elif [[ "$test_choice" == "a" ]] || [[ "$test_choice" == "A" ]]; then
    if [ -f "$PROJECT_DIR/tests/manual/test_software.py" ]; then
        echo_info "运行 v1.1-1.5 软件测试..."
        python3 tests/manual/test_software.py
    fi
    if [ -f "$PROJECT_DIR/tests/manual/test_phase12_stt.py" ]; then
        echo_info "运行 v1.2 STT 测试..."
        python3 tests/manual/test_phase12_stt.py
    fi
else
    echo_info "跳过软件测试，可以稍后手动运行:"
    echo "  cd ~/home_pi"
    echo "  source .venv/bin/activate"
    echo "  python3 tests/manual/test_software.py     # v1.1-1.5 综合测试"
    echo "  python3 tests/manual/test_phase12_stt.py # v1.2 STT专项测试"
fi
echo ""

# 10. 配置服务文件
echo "========================================"
echo "🔧 配置服务文件"
echo "========================================"

SERVICE_FILE="/etc/systemd/system/voice-assistant.service"

echo_info "创建 systemd 服务文件..."
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Voice Assistant Service v2.2.0
Documentation=https://github.com/your-repo/home_pi
After=network.target sound.target

[Service]
Type=simple
User=admin
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_DIR/bin:/usr/bin"
ExecStart=$PROJECT_DIR/start-wrapper.sh
Restart=always
RestartSec=10
TimeoutStopSec=5
KillMode=mixed

StandardOutput=journal
StandardError=journal
SyslogIdentifier=voice-assistant

[Install]
WantedBy=multi-user.target
EOF

echo_info "✅ 服务文件已创建: $SERVICE_FILE"
echo_info "重载 systemd..."
sudo systemctl daemon-reload
echo_info "✅ 服务配置完成"
echo ""

# 11. 完成
echo "========================================"
echo "✅ 部署完成！"
echo "========================================"
echo ""
echo "后续步骤:"
echo ""
echo "1. 测试软件功能:"
echo "   source .venv/bin/activate"
echo "   python3 tests/manual/test_software.py       # v1.1-1.5 综合测试"
echo "   python3 tests/manual/test_phase12_stt.py   # v1.2 STT 测试"
echo "   python3 tests/manual/test_alarm_e2e.py     # v1.7 闹钟测试"
echo "   python3 tests/manual/test_music_e2e.py     # v1.8 音乐测试"
echo "   python3 tests/manual/test_tts_cache.py     # v2.2 TTS 缓存测试"
echo ""
echo "2. 查看服务状态:"
echo "   sudo systemctl status voice-assistant.service"
echo ""
echo "3. 启动服务:"
echo "   ./start-service.sh"
echo ""
echo "4. 或手动启动:"
echo "   source .venv/bin/activate"
echo "   python3 main.py"
echo ""
echo "5. 查看日志:"
echo "   sudo journalctl -u voice-assistant.service -f"
echo "   tail -f logs/assistant.log"
echo ""
echo "========================================"
echo "📋 测试指南"
echo "========================================"
echo ""
echo "硬件测试:"
echo "  python3 tests/manual/test_hardware.py"
echo "  - [1] 测试麦克风"
echo "  - [2] 测试扬声器"
echo "  - [3] 测试唤醒词检测"
echo ""
echo "软件测试 v1.1-1.5 (综合测试):"
echo "  python3 tests/manual/test_software.py"
echo "  - [1] 测试 TTS 引擎"
echo "  - [2] 测试 TTS 反馈播放器"
echo "  - [3] 测试唤醒词 + TTS 集成"
echo "  - [4] 测试 STT 模块"
echo "  - [5] 测试 LLM 模块"
echo "  - [6] 测试完整流程"
echo "  - [7] 测试 Phase 1.4 音频质量检测"
echo "  - [8] 测试 Phase 1.5 对话优化"
echo "  - [a] 运行所有测试"
echo ""
echo "软件测试 v1.7 (闹钟功能):"
echo "  python3 tests/manual/test_alarm_e2e.py"
echo "  - 测试设置、查询、删除闹钟"
echo "  - 测试闹钟响铃与语音控制"
echo ""
echo "软件测试 v1.8 (音乐播放):"
echo "  python3 tests/manual/test_music_e2e.py"
echo "  - 测试本地音乐播放"
echo "  - 测试语音控制（播放、暂停、音量）"
echo ""
echo "软件测试 v2.2 (千问 TTS + 缓存):"
echo "  python3 tests/manual/test_tts_cache.py"
echo "  - 测试缓存功能"
echo "  - 测试预热常用短语"
echo "  - 测试缓存持久化"
echo ""
echo "软件测试 v1.2 (STT专项):"
echo "  python3 tests/manual/test_phase12_stt.py"
echo "  - [1] 测试 STT 引擎"
echo "  - [2] 测试 VAD 检测器"
echo "  - [3] 测试完整交互流程"
echo "  - [a] 运行所有测试"
echo ""
