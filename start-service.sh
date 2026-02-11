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

# 3.5. 检查并加载环境变量文件
echo_info "检查环境变量文件..."
if [ ! -f "$PROJECT_DIR/.env.sh" ]; then
    echo_warn "环境变量文件 .env.sh 不存在"
    echo_warn "⚠️  LLM/TTS/Picovoice 功能将不可用"
    echo ""
    echo "创建方法："
    echo "  1. 编辑 .env.sh 文件，设置 DASHSCOPE_API_KEY, PICOVOICE_ACCESS_KEY 等"
    echo "  2. 获取方式: https://dashscope.console.aliyun.com/"
    echo "  3. 获取方式: https://console.picovoice.ai/"
    echo ""
else
    # 加载环境变量
    echo_info "正在加载环境变量..."
    set +e  # 临时关闭 errexit，避免 .env.sh 中的 source 命令失败导致脚本退出
    source "$PROJECT_DIR/.env.sh" > /dev/null 2>&1
    set -e  # 恢复 errexit

    # 检查关键环境变量是否加载成功
    if [ -n "$PICOVOICE_ACCESS_KEY" ] && [ "$PICOVOICE_ACCESS_KEY" != "your_picovoice_access_key_here" ]; then
        echo_info "✅ Picovoice Access Key 已加载"
    else
        echo_warn "⚠️  Picovoice Access Key 未配置或使用默认值"
        echo_warn "唤醒词检测可能无法工作"
    fi

    if [ -n "$DASHSCOPE_API_KEY" ] && [ "$DASHSCOPE_API_KEY" != "sk-your-dashscope-api-key-here" ]; then
        echo_info "✅ DashScope API Key 已加载"
    else
        echo_warn "⚠️  DashScope API Key 未配置"
    fi

    echo_info "✅ 环境变量已加载"
fi
echo ""

# 4. 启用服务（开机自启）
echo_info "启用开机自启..."
sudo systemctl enable "$SERVICE_NAME" 2>/dev/null
echo_info "✅ 已启用开机自启"
echo ""

# 5. 重启服务
echo_info "重启服务..."
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo_info "服务正在运行，执行重启..."
    sudo systemctl restart "$SERVICE_NAME"
else
    echo_info "服务未运行，执行启动..."
    sudo systemctl start "$SERVICE_NAME"
fi
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
