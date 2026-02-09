#!/bin/bash
# ========================================
# 自动安装脚本
# 自动检测并安装项目依赖
# 支持 AMD64 和 ARM64 架构
# ========================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检测系统架构
detect_architecture() {
    ARCH=$(uname -m)
    echo_info "检测到系统架构: $ARCH"

    if [[ "$ARCH" == "x86_64" ]]; then
        ARCH_TYPE="amd64"
        echo_info "这是开发环境 (AMD64)"
    elif [[ "$ARCH" == "aarch64" ]]; then
        ARCH_TYPE="arm64"
        echo_info "这是生产环境 (ARM64 - 树莓派)"
    else
        echo_error "未知架构: $ARCH"
        exit 1
    fi
}

# 检查 Python 版本
check_python() {
    # 检查系统是否有任何 Python 3
    if ! command -v python3 &> /dev/null; then
        echo_error "未找到 Python 3"
        echo_info "请先安装 Python 3.10+"
        exit 1
    fi

    # 优先检查 Python 3.10
    if command -v python3.10 &> /dev/null; then
        PYTHON_CMD="python3.10"
        echo_info "✅ 找到 Python 3.10"
    elif command -v python3.11 &> /dev/null; then
        PYTHON_CMD="python3.11"
        echo_info "✅ 找到 Python 3.11"
    else
        # 使用系统默认 python3
        PYTHON_CMD="python3"
    fi

    PYTHON_VERSION=$($PYTHON_CMD --version | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    echo_info "Python 版本: $PYTHON_VERSION"

    # 检查是否为 Python 3.12（不兼容 openwakeword）
    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -eq 12 ]; then
        echo ""
        echo_warn "⚠️  Python 3.12 与 openwakeword 不兼容！"
        echo ""
        echo_error "❌ 问题: tflite-runtime 依赖仅支持 Python 3.11 及以下"
        echo ""
        echo_info "💡 推荐解决方案: 安装 Python 3.10"
        echo_info ""
        echo_info "   # Ubuntu 22.04/24.04 / 树莓派5:"
        echo_info "   $ sudo add-apt-repository ppa:deadsnakes/ppa -y"
        echo_info "   $ sudo apt update"
        echo_info "   $ sudo apt install -y python3.10 python3.10-venv python3.10-dev"
        echo ""
        echo_info "   # 然后创建虚拟环境:"
        echo_info "   $ python3.10 -m venv .venv"
        echo_info "   $ source .venv/bin/activate"
        echo ""
        echo_info "   📚 详细指南: docs/deploy/python-version-quickref.md"
        echo ""

        # 如果没有找到 Python 3.10 或 3.11，退出
        if ! command -v python3.10 &> /dev/null && ! command -v python3.11 &> /dev/null; then
            read -p "是否继续安装（可能会失败）? (y/N): " continue_install
            if [[ ! "$continue_install" =~ ^[Yy]$ ]]; then
                echo_info "安装已取消，请先安装 Python 3.10 或 3.11"
                exit 1
            fi
        fi
    fi

    # 检查最低版本要求
    if [[ $PYTHON_MAJOR -lt 3 ]] || [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 10 ]]; then
        echo_error "Python 版本过低 (需要 >= 3.10)"
        exit 1
    fi

    # 推荐使用 Python 3.10
    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -eq 10 ]; then
        echo_info "✅ Python 3.10 - 完美兼容，推荐版本"
    elif [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -eq 11 ]; then
        echo_info "✅ Python 3.11 - 完全兼容"
    fi
}

# 检查虚拟环境
check_venv() {
    if [[ -z "$VIRTUAL_ENV" ]]; then
        echo_warn "未检测到虚拟环境"
        echo_info "项目使用虚拟环境隔离 Python 依赖"

        if [[ ! -d ".venv" ]]; then
            echo_info "创建虚拟环境（使用 Python 3.10）..."

            # 优先使用 python3.10
            if command -v python3.10 &> /dev/null; then
                python3.10 -m venv .venv
                echo_info "✅ 使用 Python 3.10 创建虚拟环境"
            elif command -v python3.11 &> /dev/null; then
                python3.11 -m venv .venv
                echo_info "✅ 使用 Python 3.11 创建虚拟环境"
            else
                python3 -m venv .venv
                echo_warn "⚠️  使用系统默认 Python 创建虚拟环境"
            fi

            echo_info "虚拟环境创建成功"
        fi

        echo_info "激活虚拟环境..."
        source .venv/bin/activate

        # 显示虚拟环境中的 Python 版本
        VENV_PYTHON_VERSION=$(python --version 2>&1)
        echo_info "虚拟环境 Python: $VENV_PYTHON_VERSION"
    else
        echo_info "✅ 虚拟环境已激活: $VIRTUAL_ENV"
        VENV_PYTHON_VERSION=$(python --version 2>&1)
        echo_info "虚拟环境 Python: $VENV_PYTHON_VERSION"
    fi
}

# AMD64 环境安装
install_amd64() {
    echo_info "安装 AMD64 (开发环境) 依赖..."

    # 更新 pip
    echo_info "更新 pip..."
    pip install --upgrade pip setuptools wheel

    # 安装系统依赖
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo_info "安装系统依赖 (PortAudio)..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y portaudio19-dev python3-dev
        elif command -v yum &> /dev/null; then
            sudo yum install -y portaudio-devel python3-devel
        else
            echo_warn "无法自动安装 PortAudio，请手动安装"
        fi
    fi

    # 安装 Python 依赖
    echo_info "安装 Python 依赖..."
    pip install -r requirements.txt
}

# ARM64 环境安装 (树莓派)
install_arm64() {
    echo_info "安装 ARM64 (树莓派) 依赖..."

    # 更新 pip
    echo_info "更新 pip..."
    pip install --upgrade pip setuptools wheel

    # 安装系统依赖
    echo_info "安装系统依赖..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y portaudio19-dev python3-dev
    else
        echo_error "未找到 apt-get，无法安装依赖"
        exit 1
    fi

    # 安装 Python 依赖
    echo_info "安装 Python 依赖..."
    pip install -r requirements-arm64.txt
}

# 安装 ReSpeaker 驱动 (仅 ARM64)
install_respeaker_driver() {
    if [[ "$ARCH_TYPE" == "arm64" ]]; then
        echo_info "检查 ReSpeaker 驱动..."

        if ! arecord -L | grep -q "seeed-4mic-voicecard"; then
            echo_warn "未检测到 ReSpeaker 驱动"
            echo_info "是否安装 ReSpeaker 驱动? (y/N)"
            read -r answer

            if [[ "$answer" == "y" || "$answer" == "Y" ]]; then
                echo_info "克隆 ReSpeaker 驱动仓库..."
                git clone https://github.com/seeed-studio/seeed-voicecard.git

                echo_info "安装驱动..."
                cd seeed-voicecard
                sudo ./install.sh

                echo_info "驱动安装完成，需要重启系统"
                echo_warn "重启后运行: sudo reboot"
            fi
        else
            echo_info "ReSpeaker 驱动已安装"
        fi
    else
        echo_info "AMD64 环境跳过 ReSpeaker 驱动安装"
    fi
}

# 验证安装
verify_installation() {
    echo_info "验证安装..."

    # 检查 Python 包
    python3 -c "
import yaml
import numpy
import pyaudio
import openwakeword
print('✅ 所有依赖安装成功')
    "

    if [[ $? -eq 0 ]]; then
        echo_info "✅ 所有依赖安装成功"
    else
        echo_error "依赖安装失败"
        exit 1
    fi
}

# 主安装流程
main() {
    echo "============================================================"
    echo "        语音助手系统 - 自动安装脚本"
    echo "============================================================"
    echo ""

    # 检测架构
    detect_architecture

    # 检查 Python
    check_python

    # 检查虚拟环境
    check_venv

    # 根据架构安装依赖
    if [[ "$ARCH_TYPE" == "amd64" ]]; then
        install_amd64
    elif [[ "$ARCH_TYPE" == "arm64" ]]; then
        install_arm64
    fi

    # 可选：安装 ReSpeaker 驱动
    echo ""
    echo_info "是否安装 ReSpeaker 驱动? (仅树莓派需要)"
    echo_info "输入 'y' 安装，其他键跳过"
    read -r answer

    if [[ "$answer" == "y" || "$answer" == "Y" ]]; then
        install_respeaker_driver
    fi

    # 验证安装
    echo ""
    verify_installation

    echo ""
    echo "============================================================"
    echo "                   安装完成！"
    echo "============================================================"
    echo ""
    echo_info "下一步操作:"
    echo "  1. 配置系统: cp config.example.yaml config.yaml"
    echo "  2. 运行测试: python tests/manual/test_hardware.py"
    echo "  3. 运行主程序: python main.py"
    echo ""
}

# 运行主函数
main "$@"
