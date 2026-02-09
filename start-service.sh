#!/bin/bash
# ========================================
# 启动服务脚本
# 在树莓派上运行
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

SERVICE_NAME="voice-assistant.service"
PROJECT_DIR="$HOME/home_pi"

echo "========================================"
echo "🚀 启动语音助手服务"
echo "========================================"
echo ""

# 1. 检查服务文件
if [ ! -f "/etc/systemd/system/$SERVICE_NAME" ]; then
    echo_error "服务文件不存在"
    echo ""
    echo "请先运行部署脚本创建服务文件:"
    echo "  cd ~/home_pi"
    echo "  ./deploy.sh"
    exit 1
fi
echo_info "✅ 服务文件已找到"
echo ""

# 2. 检查虚拟环境
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo_error "虚拟环境不存在"
    echo ""
    echo "请先运行部署脚本创建虚拟环境:"
    echo "  cd ~/home_pi"
    echo "  ./deploy.sh"
    exit 1
fi
echo_info "✅ 虚拟环境已找到"
echo ""

# 3. 检查配置文件
if [ ! -f "$PROJECT_DIR/config.yaml" ]; then
    echo_warn "配置文件不存在，使用默认配置"
    if [ -f "$PROJECT_DIR/config.example.yaml" ]; then
        cp "$PROJECT_DIR/config.example.yaml" "$PROJECT_DIR/config.yaml"
        echo_info "✅ 已创建默认配置文件"
    fi
else
    echo_info "✅ 配置文件已找到"
fi
echo ""

# 4. 停止旧服务（如果运行中）
echo_info "检查服务状态..."
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo_warn "服务正在运行，先停止..."
    sudo systemctl stop "$SERVICE_NAME"
    sleep 1
    echo_info "✅ 旧服务已停止"
else
    echo_info "服务未运行"
fi
echo ""

# 5. 启用服务（开机自启）
echo_info "启用开机自启..."
sudo systemctl enable "$SERVICE_NAME" 2>/dev/null
echo_info "✅ 已启用开机自启"
echo ""

# 6. 启动服务
echo_info "启动服务..."
sudo systemctl start "$SERVICE_NAME"
sleep 2

# 7. 显示服务状态
echo ""
echo "========================================"
echo "📊 服务状态"
echo "========================================"
sudo systemctl status "$SERVICE_NAME" --no-pager
echo ""

# 8. 检查服务是否启动成功
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo_info "✅ 服务启动成功！"
    echo ""
    echo "查看日志:"
    echo "  sudo journalctl -u $SERVICE_NAME -f"
    echo ""
    echo "查看应用日志:"
    echo "  tail -f $PROJECT_DIR/logs/assistant.log"
    echo ""
else
    echo_error "❌ 服务启动失败！"
    echo ""
    echo "查看错误日志:"
    echo "  sudo journalctl -u $SERVICE_NAME -n 50 --no-pager"
    echo ""
    echo "常见问题:"
    echo "  1. 检查虚拟环境: source $PROJECT_DIR/.venv/bin/activate"
    echo "  2. 检查配置文件: cat $PROJECT_DIR/config.yaml"
    echo "  3. 手动运行测试: cd $PROJECT_DIR && source .venv/bin/activate && python3 main.py"
    echo ""
    exit 1
fi
