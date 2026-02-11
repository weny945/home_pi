#!/bin/bash
# ========================================
# 语音助手服务启动包装脚本
# 用于 systemd 服务启动
# ========================================
#
# 作用：
# 1. 加载 .env.sh 中的环境变量
# 2. 启动 Python 应用
# ========================================

set -e

# 项目目录（使用绝对路径，避免依赖 $HOME）
PROJECT_DIR="/home/admin/home_pi"
ENV_FILE="$PROJECT_DIR/.env.sh"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
MAIN_PY="$PROJECT_DIR/main.py"

# 加载环境变量
if [ -f "$ENV_FILE" ]; then
    # 加载环境变量（显示输出到 journal，便于调试）
    echo "正在加载环境变量: $ENV_FILE"
    source "$ENV_FILE"
    echo "环境变量加载完成"
else
    echo "警告: .env.sh 文件不存在: $ENV_FILE" >&2
    echo "LLM/TTS 功能将不可用" >&2
fi

# 显示调试信息
echo "启动应用: $MAIN_PY"
echo "API Key 前缀: ${DASHSCOPE_API_KEY:0:10}..."

# 启动应用（使用 exec 替换当前进程）
exec "$VENV_PYTHON" "$MAIN_PY"
