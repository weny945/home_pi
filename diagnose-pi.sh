#!/bin/bash
# ========================================
# 树莓派问题诊断脚本
# 检查语音助手服务被杀死的真实原因
# ========================================

echo "========================================"
echo "🔍 树莓派问题诊断"
echo "========================================"
echo ""

# 1. 检查内存情况
echo "=== 1. 内存使用情况 ==="
free -h
echo ""
echo "内存详情:"
cat /proc/meminfo | grep -E "MemTotal|MemFree|MemAvailable|Cached|SwapTotal|SwapFree"
echo ""

# 2. 检查 OOM Killer 日志
echo "=== 2. OOM Killer 日志 ==="
if sudo dmesg | grep -i "out of memory" | tail -20; then
    echo ""
    echo "⚠️  发现 OOM 记录！"
else
    echo "✅ 未发现 OOM 记录"
fi
echo ""

# 3. 检查 systemd 服务的资源限制
echo "=== 3. systemd 服务资源限制 ==="
if [ -f /etc/systemd/system/voice-assistant.service ]; then
    echo "服务文件内容:"
    sudo cat /etc/systemd/system/voice-assistant.service
    echo ""

    echo "资源限制:"
    systemctl show voice-assistant.service | grep -E "MemoryLimit|LimitNOFILE|LimitNPROC" || echo "未设置特殊限制"
else
    echo "❌ 服务文件不存在"
fi
echo ""

# 4. 检查最近的 kill 事件
echo "=== 4. 系统日志中的 KILL 事件 ==="
sudo journalctl -k --since "10 minutes ago" | grep -i "killed process" | tail -10
echo ""

# 5. 检查语音助手服务日志
echo "=== 5. 语音助手服务日志（最近 50 行）==="
sudo journalctl -u voice-assistant.service -n 50 --no-pager
echo ""

# 6. 检查 FunASR 模型缓存大小
echo "=== 6. FunASR 模型缓存 ==="
if [ -d ~/.cache/modelscope ]; then
    echo "模型目录: ~/.cache/modelscope"
    du -sh ~/.cache/modelscope/*
    echo ""
    echo "模型文件列表:"
    find ~/.cache/modelscope -name "*.pt" -o -name "*.onnx" -o -name "*.tflite" 2>/dev/null | head -20
else
    echo "模型缓存目录不存在"
fi
echo ""

# 7. 检查进程内存使用（如果服务正在运行）
echo "=== 7. 当前进程内存使用 ==="
if pgrep -f "main.py" > /dev/null; then
    PID=$(pgrep -f "main.py" | head -1)
    echo "主进程 PID: $PID"
    ps -p $PID -o pid,vsz,rss,%mem,cmd
    echo ""
    echo "详细内存使用:"
    sudo cat /proc/$PID/status | grep -E "VmPeak|VmSize|VmRSS|VmData|VmStk|VmExe|VmLib"
else
    echo "服务未运行"
fi
echo ""

# 8. 检查 swap 使用情况
echo "=== 8. Swap 使用情况 ==="
swapon --show
echo ""
cat /proc/swaps
echo ""

# 9. 检查系统负载
echo "=== 9. 系统负载 ==="
uptime
echo ""
echo "CPU 使用率:"
top -bn1 | grep "Cpu(s)"
echo ""

# 10. 建议和总结
echo "========================================"
echo "📋 诊断总结"
echo "========================================"
echo ""

# 检查是否是 OOM
if sudo dmesg | grep -qi "out of memory.*voice-assistant\|out of memory.*main.py"; then
    echo "❌ 问题确认：内存不足（OOM）"
    echo ""
    echo "解决方案："
    echo "  1. 增加 swap 大小"
    echo "  2. 或者禁用一些不需要的模块"
else
    echo "✅ 排除 OOM 问题"
fi

# 检查是否设置了内存限制
if systemctl show voice-assistant.service 2>/dev/null | grep -q "MemoryLimit=[0-9]"; then
    MEMORY_LIMIT=$(systemctl show voice-assistant.service | grep MemoryLimit | cut -d= -f2)
    echo "⚠️  发现内存限制：$MEMORY_LIMIT"
    echo ""
    echo "解决方案：修改服务配置，移除或增加内存限制"
fi

echo ""
echo "请将以上诊断结果发送给开发者进行分析"
