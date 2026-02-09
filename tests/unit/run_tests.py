#!/usr/bin/env python3
"""
快速验证脚本
Quick validation script to check project setup
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def check_imports():
    """检查关键模块是否可以导入"""
    print("检查模块导入...")

    try:
        import yaml
        print("  ✓ yaml")
    except ImportError:
        print("  ✗ yaml (请运行: pip install pyyaml)")
        return False

    try:
        import numpy
        print("  ✓ numpy")
    except ImportError:
        print("  ✗ numpy (请运行: pip install numpy)")
        return False

    # PyAudio 和 openwakeword 可选（需要硬件或特定环境）
    try:
        import pyaudio
        print("  ✓ pyaudio")
    except ImportError:
        print("  ⚠ pyaudio (可选, 需要 PortAudio)")

    try:
        import openwakeword
        print("  ✓ openwakeword")
    except ImportError:
        print("  ⚠ openwakeword (可选)")

    return True


def check_project_structure():
    """检查项目结构"""
    print("\n检查项目结构...")

    required_dirs = [
        "src/config",
        "src/audio",
        "src/wake_word",
        "src/feedback",
        "src/state_machine",
        "tests/unit",
        "docs/demand",
        "docs/development",
        "assets",
        "logs",
        "models"
    ]

    all_exist = True
    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            print(f"  ✓ {dir_path}")
        else:
            print(f"  ✗ {dir_path} (不存在)")
            all_exist = False

    return all_exist


def check_config_file():
    """检查配置文件"""
    print("\n检查配置文件...")

    config_path = Path("config.yaml")
    if not config_path.exists():
        print("  ✗ config.yaml 不存在")
        return False

    try:
        from src.config import get_config
        config = get_config()
        config.validate()
        print("  ✓ config.yaml (有效)")
        return True
    except Exception as e:
        print(f"  ✗ config.yaml (错误: {e})")
        return False


def check_source_files():
    """检查源代码文件"""
    print("\n检查源代码文件...")

    required_files = [
        "src/__init__.py",
        "src/config/config_loader.py",
        "src/audio/microphone.py",
        "src/audio/respeaker_input.py",
        "src/wake_word/detector.py",
        "src/wake_word/openwakeword_detector.py",
        "src/feedback/player.py",
        "src/feedback/audio_feedback.py",
        "src/state_machine/states.py",
        "src/state_machine/machine.py",
        "main.py"
    ]

    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path} (不存在)")
            all_exist = False

    return all_exist


def main():
    """主函数"""
    print("=" * 60)
    print("项目验证脚本")
    print("=" * 60)

    results = {
        "模块导入": check_imports(),
        "项目结构": check_project_structure(),
        "配置文件": check_config_file(),
        "源代码": check_source_files()
    }

    print("\n" + "=" * 60)
    print("验证结果")
    print("=" * 60)

    all_passed = all(results.values())

    for check, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{check}: {status}")

    print("=" * 60)

    if all_passed:
        print("\n✓ 项目验证通过! 可以开始开发了。")
        print("\n下一步:")
        print("  1. 运行测试: pytest")
        print("  2. 运行主程序: python main.py")
        return 0
    else:
        print("\n✗ 项目验证失败，请修复上述问题。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
