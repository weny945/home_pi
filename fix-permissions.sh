#!/bin/bash
# ========================================
# 修复权限脚本
# 在树莓派上运行
# ========================================

echo "========================================"
echo "🔧 修复 home_pi 目录权限"
echo "========================================"
echo ""

PROJECT_DIR="$HOME/home_pi"

# 检查目录是否存在
if [ ! -d "$PROJECT_DIR" ]; then
    echo "目录不存在: $PROJECT_DIR"
    echo "请先创建目录:"
    echo "  mkdir -p ~/home_pi"
    exit 1
fi

echo "当前目录状态:"
ls -la "$PROJECT_DIR" | head -10
echo ""

# 显示当前用户
echo "当前用户: $USER"
echo ""

# 询问修复方式
echo "选择修复方式:"
echo "  1) 修改目录所有者为当前用户 (推荐)"
echo "  2) 添加写权限 (不修改所有者)"
echo "  3) 使用 sudo 删除重建"
echo ""
read -p "请选择 (1-3): " choice

case $choice in
    1)
        echo "修改目录所有者为 $USER..."
        sudo chown -R $USER:$USER "$PROJECT_DIR"
        echo "✅ 完成"
        ;;
    2)
        echo "添加写权限..."
        sudo chmod -R u+rw "$PROJECT_DIR"
        echo "✅ 完成"
        ;;
    3)
        echo "⚠️  将删除整个目录重建"
        read -p "确认? (y/N): " confirm
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            sudo rm -rf "$PROJECT_DIR"
            mkdir -p "$PROJECT_DIR"
            echo "✅ 目录已重建"
        else
            echo "已取消"
            exit 0
        fi
        ;;
    *)
        echo "无效选择"
        exit 1
        ;;
esac

echo ""
echo "修复后的权限:"
ls -la "$PROJECT_DIR" | head -10
