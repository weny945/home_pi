#!/bin/bash
# ========================================
# 创建 Swap 文件（通用方法）
# 不依赖 dphys-swapfile
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

echo_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

echo "========================================"
echo "📦 创建 Swap 文件（通用方法）"
echo "========================================"
echo ""

# 配置
SWAP_FILE="/swapfile"
SWAP_SIZE_MB=${1:-2048}  # 默认 2GB

echo_step "1. 检查当前状态"
echo ""
free -h
echo ""

if [ -f "$SWAP_FILE" ]; then
    echo_warn "Swap 文件已存在: $SWAP_FILE"
    echo ""
    read -p "是否删除重建? (y/N): " rebuild
    if [[ "$rebuild" =~ ^[Yy]$ ]]; then
        echo_info "停止并删除旧 swap..."
        sudo swapoff "$SWAP_FILE" 2>/dev/null || true
        sudo rm -f "$SWAP_FILE"
        echo_info "✅ 旧 swap 已删除"
    else
        echo_info "保留现有 swap"
        exit 0
    fi
fi

echo_step "2. 创建 ${SWAP_SIZE_MB}MB swap 文件"
echo ""
echo_info "这可能需要几分钟，请耐心等待..."
echo ""

# 创建 swap 文件
sudo dd if=/dev/zero of="$SWAP_FILE" bs=1M count="$SWAP_SIZE_MB" status=progress

echo ""
echo_info "设置权限..."
sudo chmod 600 "$SWAP_FILE"

echo_info "格式化为 swap..."
sudo mkswap "$SWAP_FILE"

echo_info "启用 swap..."
sudo swapon "$SWAP_FILE"

echo ""
echo_step "3. 验证新 Swap"
echo ""

# 显示新的 swap 信息
free -h
echo ""

echo_info "Swap 详情:"
swapon --show
echo ""

# 添加到 /etc/fstab 实现永久挂载
echo_step "4. 配置永久挂载"
echo ""

if grep -q "$SWAP_FILE" /etc/fstab; then
    echo_info "✅ /etc/fstab 中已存在配置"
else
    echo_info "添加到 /etc/fstab..."
    echo "$SWAP_FILE none swap sw 0 0" | sudo tee -a /etc/fstab
    echo_info "✅ 已添加到 /etc/fstab"
fi

echo ""
echo "========================================"
echo "✅ Swap 创建完成！"
echo "========================================"
echo ""
echo_info "配置信息："
echo_info "  Swap 文件: $SWAP_FILE"
echo_info "  大小: ${SWAP_SIZE_MB}MB"
echo_info "  永久挂载: 已配置"
echo ""
echo_warn "注意事项："
echo_warn "  1. Swap 使用磁盘空间，速度比物理内存慢"
echo_warn "  2. 推荐使用 2048MB (2GB) 以应对大模型加载"
echo_warn "  3. 如需调整大小，重新运行此脚本即可"
echo ""
echo "后续步骤:"
echo "  1. 重启语音助手服务:"
echo "     sudo systemctl restart voice-assistant.service"
echo ""
echo "  2. 查看内存使用:"
echo "     free -h"
echo ""
echo "  3. 查看 swap 使用情况:"
echo "     swapon --show"
echo "     cat /proc/swaps"
echo ""
