#!/bin/bash
# ReSpeaker 4 Mic 增益诊断脚本

echo "=========================================="
echo "ReSpeaker 4 Mic 增益诊断"
echo "=========================================="
echo

echo "【1. 查看声卡列表】"
cat /proc/asound/cards
echo

echo "【2. 查看 ALSA 控制】"
amixer -c 0 scontrols 2>/dev/null || amixer scontrols
echo

echo "【3. 查看当前音量设置】"
echo "--- Capture ---"
amixer -c 0 sget 'Capture' 2>/dev/null || echo "Capture 控制不存在"

echo "--- Mic ---"
amixer -c 0 sget 'Mic' 2>/dev/null || echo "Mic 控制不存在"

echo "--- Digital ---"
amixer -c 0 sget 'Digital' 2>/dev/null || echo "Digital 控制不存在"
echo

echo "【4. 推荐设置】"
echo "如果拾音音量小，请执行以下命令之一："
echo
echo "方案 A - 增加 Capture 音量:"
echo "  amixer -c 0 sset 'Capture' 80%"
echo "  或"
echo "  amixer -c 0 sset 'Capture' 20"
echo
echo "方案 B - 使用 alsamixer 图形界面:"
echo "  alsamixer"
echo "  (按 F6 选择 seeed-4mic-voicecard，调整 Capture 音量)"
echo

echo "【5. 测试录音】"
echo "录制 3 秒测试音频..."
arecord -f cd -D hw:0,0 -d 3 /tmp/test.wav 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ 录制成功: /tmp/test.wav"
    echo "播放测试: aplay /tmp/test.wav"
else
    echo "❌ 录制失败"
fi

echo
echo "=========================================="
echo "诊断完成"
echo "=========================================="
