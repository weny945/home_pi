#!/usr/bin/env python3
"""
快速配置 ReSpeaker 音频输出
Quick Configuration for ReSpeaker Audio Output
"""
import sys
import subprocess
from pathlib import Path

# 添加项目根目录
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))


def run_command(cmd, description):
    """运行命令"""
    print(f"\n{'='*60}")
    print(f"🔍 {description}")
    print(f"命令: {' '.join(cmd)}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 失败: {e}")
        return False


def main():
    print("\n" + "="*60)
    print("🎧 ReSpeaker 音频配置工具")
    print("="*60)

    # 1. 查找 ReSpeaker 设备
    print("\n步骤 1: 查找 ReSpeaker 设备")
    print("-"*60)

    try:
        result = subprocess.run(
            ['aplay', '-l'],
            capture_output=True,
            text=True,
            check=True
        )

        # 解析输出，找到 ReSpeaker
        lines = result.stdout.split('\n')
        respeaker_card = None

        for i, line in enumerate(lines):
            if 'ReSpeaker' in line or 'ArrayUAC10' in line:
                # 解析 card 编号
                # 格式: card 2: ArrayUAC10 [ReSpeaker 4 Mic Array (UAC1.0)]
                if 'card' in line:
                    parts = line.split('card')[1].split(':')[0].strip()
                    respeaker_card = int(parts)
                    print(f"✅ 找到 ReSpeaker: card {respeaker_card}")
                    break

        if respeaker_card is None:
            print("❌ 未找到 ReSpeaker 设备")
            print("\n可用设备:")
            print(result.stdout)
            return

    except Exception as e:
        print(f"❌ 错误: {e}")
        return

    # 2. 推荐配置
    recommended_device = f"plughw:{respeaker_card},0"
    print(f"\n推荐配置:")
    print(f"  output_device: \"{recommended_device}\"")

    # 3. 询问是否更新配置文件
    print(f"\n步骤 2: 更新配置文件")
    print("-"*60)

    config_path = project_root / "config.yaml"

    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return

    print(f"配置文件: {config_path}")
    print(f"\n建议修改:")
    print(f"  audio:")
    print(f"    output_device: \"{recommended_device}\"")

    choice = input(f"\n是否自动更新配置文件? (y/N): ").strip().lower()

    if choice == 'y':
        # 读取配置文件
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否已有 output_device
        if 'output_device:' in content:
            # 替换现有的 output_device
            import re
            content = re.sub(
                r'output_device:\s*[\'"]?[^\'"\n]*[\'"]?',
                f'output_device: "{recommended_device}"',
                content
            )
            print(f"✅ 已更新现有的 output_device 配置")
        else:
            # 在 audio 部分添加 output_device
            # 找到 audio: 部分，在第一个配置项后添加
            lines = content.split('\n')
            new_lines = []
            audio_section_found = False
            first_item_added = False

            for i, line in enumerate(lines):
                new_lines.append(line)

                if not audio_section_found:
                    if line.strip().startswith('audio:'):
                        audio_section_found = True
                elif audio_section_found and not first_item_added:
                    if line.strip().startswith('input_device:') or line.strip().startswith('sample_rate:'):
                        # 在这行后添加 output_device
                        indent = len(line) - len(line.lstrip())
                        new_lines.append(' ' * indent + f'output_device: "{recommended_device}"')
                        first_item_added = True

            content = '\n'.join(new_lines)
            print(f"✅ 已添加 output_device 配置")

        # 写回文件
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ 配置文件已更新")

    else:
        print("⏭️  跳过自动更新")
        print(f"\n请手动编辑 {config_path}")
        print(f"添加或修改:")
        print(f"  audio:")
        print(f"    output_device: \"{recommended_device}\"")

    # 4. 测试音频输出
    print(f"\n步骤 3: 测试音频输出")
    print("-"*60)

    test_choice = input(f"\n是否测试音频播放? (y/N): ").strip().lower()

    if test_choice == 'y':
        print(f"\n正在测试设备: {recommended_device}")

        # 生成测试音频
        import numpy as np
        import wave
        import tempfile

        sample_rate = 44100
        duration = 1
        frequency = 440  # A4 音

        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = (np.sin(2 * np.pi * frequency * t) * 32767).astype(np.int16)

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', mode='wb', delete=False) as f:
                temp_path = f.name
                with wave.open(f, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(audio_data.tobytes())

            # 播放测试音频
            result = subprocess.run(
                ['aplay', '-q', '-D', recommended_device, temp_path],
                capture_output=True,
                timeout=3
            )

            if result.returncode == 0:
                print(f"✅ 音频播放测试成功！")
            else:
                print(f"❌ 音频播放测试失败")
                if result.stderr:
                    print(f"错误: {result.stderr.decode('utf-8', errors='ignore')}")

        except subprocess.TimeoutExpired:
            print(f"⚠️  播放超时")
        except Exception as e:
            print(f"❌ 测试失败: {e}")
        finally:
            if temp_path and Path(temp_path).exists():
                Path(temp_path).unlink()

    # 5. 完成
    print(f"\n{'='*60}")
    print("✅ 配置完成")
    print("="*60)
    print(f"\n后续步骤:")
    print(f"1. 运行 TTS 测试:")
    print(f"   python3 tests/manual/test_software.py")
    print(f"   选择 [2] 测试 TTS 反馈播放器")
    print(f"\n2. 运行完整测试:")
    print(f"   python3 tests/manual/test_software.py")
    print(f"   选择 [3] 测试唤醒词 + TTS 集成")
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
