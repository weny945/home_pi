#!/usr/bin/env python3
"""
检查 ReSpeaker 4 Mic 音频控制
"""
import subprocess
import sys

print("=" * 70)
print("检查 ReSpeaker 4 Mic 音频控制")
print("=" * 70)

# 1. 列出所有声卡
print("\n【1. 列出所有声卡】")
result = subprocess.run(['aplay', '-l'], capture_output=True, text=True)
print(result.stdout)

# 2. 列出所有录音设备
print("\n【2. 列出所有录音设备】")
result = subprocess.run(['arecord', '-l'], capture_output=True, text=True)
print(result.stdout)

# 3. 尝试不同的 mixer 控制名称
print("\n【3. 查找可用的 mixer 控制】")

control_names = [
    'Capture',
    'Mic',
    'Microphone',
    'Input Gain',
    'Gain',
    'ADC Gain',
    'Digital',
]

for control in control_names:
    result = subprocess.run(['amixer', 'sget', control],
                          capture_output=True, text=True)
    if result.returncode == 0:
        print(f"\n✅ 找到控制: {control}")
        print(result.stdout)

# 4. 使用 alsamixer 交互式检查
print("\n【4. 使用 alsamixer 查看】")
print("请运行: alsamixer")
print("然后按 F6 选择声卡，查看可用控制")

# 5. 检查 pulseaudio 控制
print("\n【5. 检查 PulseAudio 控制】")
result = subprocess.run(['pactl', 'list', 'sources'],
                       capture_output=True, text=True)
if result.returncode == 0:
    # 简化输出
    lines = result.stdout.split('\n')
    for i, line in enumerate(lines):
        if 'Name:' in line or 'Description:' in line or 'alsa.' in line:
            print(line)
else:
    print("PulseAudio 未安装或未运行")
