#!/bin/bash
# ========================================
# 内存优化脚本
# 清理缓存并设置系统参数
# ========================================

set -e

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

echo "========================================"
echo "🧹 内存优化"
echo "========================================"
echo ""

# 1. 清理 punc_ct-transformer 缓存（节省 1.1 GB 磁盘）
echo_step "1/3 清理 FunASR punc 模型缓存..."
PUNC_CACHE_DIR="$HOME/.cache/modelscope/hub/damo/speech_paraformer-lm-punc_ct-transformer_zh-cn-common-vocab2726270"

if [ -d "$PUNC_CACHE_DIR" ]; then
    CACHE_SIZE=$(du -sh "$PUNC_CACHE_DIR" | cut -f1)
    echo_warn "找到 punc 模型缓存: $PUNC_CACHE_DIR ($CACHE_SIZE)"
    echo_warn "该模型已在 config.yaml 中禁用 (punc_model: null)"
    read -p "是否删除? (y/N): " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        rm -rf "$PUNC_CACHE_DIR"
        echo_info "✅ 已删除 punc 模型缓存，节省 $CACHE_SIZE"
    else
        echo_info "跳过删除"
    fi
else
    echo_info "punc 模型缓存不存在，无需清理"
fi
echo ""

# 2. 设置透明大页优化
echo_step "2/3 配置透明大页（THP）..."
if [ -w /sys/kernel/mm/transparent_hugepage/enabled ]; then
    CURRENT_THP=$(cat /sys/kernel/mm/transparent_hugepage/enabled)
    echo_info "当前 THP 设置: $CURRENT_THP"

    # 设置为 madvise（减少内存碎片）
    echo madvise | sudo tee /sys/kernel/mm/transparent_hugepage/enabled > /dev/null
    echo_info "✅ 已设置 THP= madvise（减少内存碎片浪费）"

    # 检查是否持久化
    if ! grep -q "transparent_hugepage" /etc/rc.local 2>/dev/null; then
        echo ""
        echo_warn "提示：要使 THP 设置在重启后生效，可以添加到 /etc/rc.local:"
        echo "  echo 'echo madvise > /sys/kernel/mm/transparent_hugepage/enabled' | sudo tee -a /etc/rc.local"
    fi
else
    echo_warn "无法设置 THP（权限不足或系统不支持）"
fi
echo ""

# 3. 清理 jieba 缓存（可选）
echo_step "3/3 清理 jieba 缓存..."
JIEBA_CACHE_DIR="./models/jieba_cache"

if [ -d "$JIEBA_CACHE_DIR" ]; then
    JIEBA_SIZE=$(du -sh "$JIEBA_CACHE_DIR" | cut -f1)
    echo_info "jieba 缓存大小: $JIEBA_SIZE"
    echo_info "jieba 缓存用于加速分词，建议保留"
    read -p "是否清理 jieba 缓存? (y/N): " confirm_jieba
    if [[ "$confirm_jieba" =~ ^[Yy]$ ]]; then
        rm -rf "$JIEBA_CACHE_DIR"
        echo_info "✅ 已删除 jieba 缓存，节省 $JIEBA_SIZE"
        echo_warn "下次启动时会重新构建 jieba 缓存（首次使用 STT 时会稍慢）"
    else
        echo_info "保留 jieba 缓存"
    fi
else
    echo_info "jieba 缓存不存在"
fi
echo ""

echo "========================================"
echo "✅ 优化完成"
echo "========================================"
echo ""
echo "建议：重启服务以应用更改"
echo "  sudo systemctl restart voice-assistant.service"
echo ""
