#!/usr/bin/env python3
"""
音频增益测试
测试不同软件增益对唤醒识别的影响
"""
import sys
import os
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, project_root)

from src.config import get_config
from src.audio import create_audio_input
import pyaudio
import time

config = get_config()
audio_config = config.get_audio_config()

print("=" * 70)
print("音频增益测试")
print("=" * 70)
print()

# 创建 PyAudio 实例
p = pyaudio.PyAudio()

# 获取设备索引
device_name = audio_config.get('input_device')
device_index = None

for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if device_name in info['name']:
        device_index = i
        break

if device_index is None:
    print(f"❌ 找不到设备: {device_name}")
    exit(1)

print(f"✅ 找到设备: {device_name} (索引: {device_index})")

# 查看硬件音量
try:
    import subprocess
    result = subprocess.run(['amixer', 'sget', 'Capture'], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"\n当前麦克风增益:")
        print(result.stdout)
    else:
        print(f"\n⚠️  无法获取增益信息")
        print(f"尝试: amixer scontrols")
except:
    pass

# 测试音频录制
print(f"\n开始录制 3 秒音频...")
print(f"请说话（距离 1 米）...")

stream = p.open(
    input_device_index=device_index,
    format=pyaudio.paInt16,
    channels=1,
    rate=16000,
    input=True,
    frames_per_buffer=512
)

frames = []
for _ in range(int(16000 / 512 * 3)):
    data = stream.read(512, exception_on_overflow=False)
    frames.append(data)

stream.stop_stream()
stream.close()

# 计算音频能量
audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
energy = np.mean(np.abs(audio_data))
max_amplitude = np.max(np.abs(audio_data))

print(f"\n音频分析:")
print(f"  平均能量: {energy:.2f}")
print(f"  最大振幅: {max_amplitude}")

if energy < 500:
    print(f"  ⚠️  能量较低，建议增加麦克风增益")
elif energy > 5000:
    print(f"  ⚠️  能量较高，可能有失真")
else:
    print(f"  ✅ 能量正常")

print(f"\n建议:")
if max_amplitude < 10000:
    print(f"  - 增加麦克风增益: amixer sset 'Capture' 80%")
    print(f"  - 或在配置中增加软件增益")
else:
    print(f"  - 当前增益设置合理")

p.terminate()
