#!/usr/bin/env python3
"""
音频设备诊断脚本
Audio Device Diagnostic Script for Raspberry Pi

用于检测和配置音频输出设备
"""
import subprocess
import sys
from pathlib import Path

# 添加项目根目录
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))


def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n{'='*60}")
    print(f"🔍 {description}")
    print(f"{'='*60}")
    print(f"命令: {' '.join(cmd)}")
    print()

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令执行失败: {e}")
        if e.stderr:
            print(f"错误: {e.stderr}")
        return None


def main():
    print("\n" + "="*60)
    print("🎧 音频设备诊断工具")
    print("="*60)

    # 1. 列出所有播放设备
    print("\n" + "="*60)
    print("步骤 1: 列出所有 ALSA 音频设备")
    print("="*60)

    output = run_command(['aplay', '-L'], '列出所有音频设备')

    if output:
        # 解析设备列表
        devices = []
        for line in output.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                if ':' in line or line.startswith('plughw:') or line.startswith('hw:'):
                    devices.append(line)

        print("\n" + "-"*60)
        print(f"找到 {len(devices)} 个音频设备")
        print("-"*60)

        # 显示常用设备
        common_devices = ['plughw:0,0', 'hw:0,0', 'default', 'pulse']
        print("\n推荐的设备（按优先级）:")
        for device in common_devices:
            if device in devices or device == 'default':
                print(f"  ✅ {device}")

        print("\n所有可用设备:")
        for device in devices[:10]:  # 只显示前10个
            print(f"  - {device}")

    # 2. 检查 PulseAudio（如果安装）
    print("\n" + "="*60)
    print("步骤 2: 检查 PulseAudio")
    print("="*60)

    try:
        result = subprocess.run(
            ['pactl', 'info'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            print("✅ PulseAudio 正在运行")
            print("💡 建议: 可以使用 'pulse' 作为输出设备")
        else:
            print("⚠️  PulseAudio 未运行或未安装")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("⚠️  PulseAudio 未安装")

    # 3. 测试音频播放
    print("\n" + "="*60)
    print("步骤 3: 测试音频播放")
    print("="*60)

    test_devices = ['plughw:0,0', 'hw:0,0', 'default']

    # 创建测试音频（1秒的440Hz正弦波）
    print("\n生成测试音频...")
    import numpy as np
    import wave
    import tempfile

    sample_rate = 44100
    duration = 1  # 秒
    frequency = 440  # A4音

    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio_data = (np.sin(2 * np.pi * frequency * t) * 32767).astype(np.int16)

    temp_path = None
    try:
        # 创建临时WAV文件
        with tempfile.NamedTemporaryFile(suffix='.wav', mode='wb', delete=False) as f:
            temp_path = f.name
            with wave.open(f, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data.tobytes())

        print(f"测试音频已生成: {temp_path}")
        print("\n测试不同设备...")

        for device in test_devices:
            print(f"\n  测试设备: {device}")
            try:
                cmd = ['aplay', '-q', '-D', device, temp_path]
                result = subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    timeout=3
                )
                print(f"  ✅ {device} 可以正常播放")
            except subprocess.CalledProcessError as e:
                print(f"  ❌ {device} 播放失败")
                if e.stderr:
                    error_msg = e.stderr.decode('utf-8', errors='ignore')
                    if 'Unknown error' in error_msg:
                        print(f"     错误: 设备不可用或未配置")
                    else:
                        print(f"     错误: {error_msg}")
            except subprocess.TimeoutExpired:
                print(f"  ⚠️  {device} 播放超时")
            except Exception as e:
                print(f"  ❌ {device} 测试失败: {e}")

    finally:
        # 清理临时文件
        if temp_path and Path(temp_path).exists():
            Path(temp_path).unlink()

    # 4. 检查音量设置
    print("\n" + "="*60)
    print("步骤 4: 检查音量设置")
    print("="*60)

    try:
        result = subprocess.run(
            ['amixer', 'sget', 'Master'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("⚠️  无法获取主音量设置")
            print("💡 尝试: sudo amixer set Master 100%")
    except Exception as e:
        print(f"⚠️  无法检查音量: {e}")

    # 5. 配置建议
    print("\n" + "="*60)
    print("📋 配置建议")
    print("="*60)

    print("\n1. 编辑配置文件:")
    print("   vim config.yaml")
    print("\n2. 修改音频输出设备:")
    print("   audio:")
    print("     output_device: \"plughw:0,0\"  # 或其他可用设备")
    print("\n3. 常用设备选项:")
    print("   - plughw:0,0  # 推荐，自动采样率转换")
    print("   - hw:0,0      # 直接硬件访问")
    print("   - default     # 系统默认设备")
    print("   - pulse       # PulseAudio (如果安装)")
    print("\n4. 如果仍然无法播放，尝试:")
    print("   - 检查 3.5mm 接口是否连接")
    print("   - 运行: sudo raspi-config")
    print("   - 选择: Advanced Options -> Audio")
    print("   - 确保选择了正确的输出设备")

    print("\n" + "="*60)
    print("✅ 诊断完成")
    print("="*60)
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
