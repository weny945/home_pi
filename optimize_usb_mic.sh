#!/bin/bash
# ========================================
# ReSpeaker USB Mic Array 优化脚本
# 自动切换到 UAC 2.0 模式
# ========================================

set -e

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
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

echo_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

echo ""
echo "========================================"
echo "ReSpeaker USB Mic Array 优化"
echo "========================================"
echo ""

# 1. 检查设备
echo_step "1. 检查 ReSpeaker 设备"
if lsusb | grep -q "2886:0018"; then
    echo_info "✅ 找到 ReSpeaker USB Mic Array"
    lsusb | grep "2886:0018"
else
    echo_error "❌ 未找到 ReSpeaker 设备"
    echo ""
    echo "请检查："
    echo "  1. USB 线是否插好"
    echo "  2. 设备是否通电"
    echo "  3. 运行 'lsusb' 查看所有 USB 设备"
    exit 1
fi
echo ""

# 2. 检查当前模式
echo_step "2. 检查当前 UAC 模式"
if arecord -l | grep -q "UAC1.0"; then
    echo_warn "⚠️  当前使用 UAC 1.0 模式（功能受限）"
    UAC_MODE="1.0"
elif arecord -l | grep -q "UAC2.0"; then
    echo_info "✅ 当前使用 UAC 2.0 模式"
    UAC_MODE="2.0"
else
    echo_warn "无法确定 UAC 模式"
    UAC_MODE="unknown"
fi
echo ""

# 3. 检查设备信息
echo_step "3. 检查设备详细信息"
arecord -l | grep -i "respeaker\|arrayuac" || echo "未找到 ALSA 设备"
echo ""

# 4. 测试音频通道
echo_step "4. 测试音频通道"
echo_info "运行通道测试（3 秒录音）..."
echo ""

if [ -f "tests/manual/test_usb_channels.py" ]; then
    python tests/manual/test_usb_channels.py
else
    echo_warn "通道测试脚本不存在，跳过"
fi
echo ""

# 5. 询问是否切换到 UAC 2.0
if [ "$UAC_MODE" = "1.0" ]; then
    echo "========================================"
    echo "是否切换到 UAC 2.0 模式？"
    echo "========================================"
    echo ""
    echo "UAC 2.0 的优势："
    echo "  ✅ 支持更高采样率（48kHz）"
    echo "  ✅ 启用板载 AEC（回声消除）"
    echo "  ✅ 启用板载 NS（噪声抑制）"
    echo "  ✅ 启用板载 AGC（自动增益）"
    echo "  ✅ 更好的音频质量和远场性能"
    echo ""
    echo "风险："
    echo "  ⚠️  如果设备不支持 UAC 2.0，可能无法识别"
    echo "  ⚠️  需要重启系统"
    echo ""

    read -p "是否继续？(y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo ""
        echo_info "已取消，保持 UAC 1.0 模式"
        echo ""
        echo "你可以稍后手动切换："
        echo "  sudo nano /etc/modprobe.d/usb-audio.conf"
        echo "  添加: options snd-usb-audio vid=0x2886 pid=0x0018 device_setup=1"
        echo "  sudo reboot"
        exit 0
    fi

    echo ""
    echo_step "5. 配置 UAC 2.0 模式"

    # 创建配置文件
    echo_info "创建配置文件..."
    sudo tee /etc/modprobe.d/usb-audio.conf > /dev/null <<EOF
# ReSpeaker USB Mic Array 配置
# device_setup=0: UAC 1.0 模式
# device_setup=1: UAC 2.0 模式（推荐）
options snd-usb-audio vid=0x2886 pid=0x0018 device_setup=1
EOF

    echo_info "✅ 配置文件已创建: /etc/modprobe.d/usb-audio.conf"
    echo ""

    # 显示配置
    echo "配置内容："
    cat /etc/modprobe.d/usb-audio.conf
    echo ""

    echo_warn "需要重启系统以应用更改"
    echo ""
    read -p "是否现在重启？(y/N): " reboot_confirm
    if [ "$reboot_confirm" = "y" ] || [ "$reboot_confirm" = "Y" ]; then
        echo ""
        echo_info "正在重启..."
        sleep 2
        sudo reboot
    else
        echo ""
        echo_info "请稍后手动重启: sudo reboot"
        echo ""
        echo "重启后验证："
        echo "  arecord -l | grep UAC"
        echo "  # 应该显示 UAC2.0"
    fi
else
    echo_info "✅ 已经使用 UAC 2.0 或更高版本"
fi

echo ""
echo "========================================"
echo "优化完成"
echo "========================================"
echo ""
echo "下一步："
echo "  1. 重启后运行: python tests/manual/test_picovoice_wake_word.py"
echo "  2. 测试远场拾音（3-4 米距离）"
echo "  3. 查看完整指南: docs/RESPEAKER_USB_OPTIMIZATION.md"
echo ""
