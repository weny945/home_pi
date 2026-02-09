#!/usr/bin/env python3
"""
OpenWakeWord 模型下载脚本
Download OpenWakeWord Models

用途: 下载 openwakeword 所需的所有模型文件
模型文件会被下载到虚拟环境中 openwakeword 的 resources/models 目录

用法:
    python3 tests/manual/download_www_models.py
"""
import sys
import os
from pathlib import Path
import urllib.request
import hashlib

# 添加项目路径
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))

# 颜色输出
class Colors:
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'

def print_info(msg):
    print(f"{Colors.GREEN}[INFO]{Colors.NC} {msg}")

def print_warn(msg):
    print(f"{Colors.YELLOW}[WARN]{Colors.NC} {msg}")

def print_error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}")

def print_step(msg):
    print(f"{Colors.BLUE}[STEP]{Colors.NC} {msg}")


# 模型文件列表
MODELS = {
    # 唤醒词模型
    "alexa_v0.1.tflite": {
        "url": "https://github.com/dscripka/openWakeWord/releases/download/v0.5.0/alexa_v0.1.tflite",
        "size": 422000  # 约 422 KB
    },
    "hey_jarvis_v0.1.tflite": {
        "url": "https://github.com/dscripka/openWakeWord/releases/download/v0.5.0/hey_jarvis_v0.1.tflite",
        "size": 422000
    },
    "hey_mycroft_v0.1.tflite": {
        "url": "https://github.com/dscripka/openWakeWord/releases/download/v0.5.0/hey_mycroft_v0.1.tflite",
        "size": 422000
    },
    "hey_rhasspy_v0.1.tflite": {
        "url": "https://github.com/dscripka/openWakeWord/releases/download/v0.5.0/hey_rhasspy_v0.1.tflite",
        "size": 422000
    },
    "timer_v0.1.tflite": {
        "url": "https://github.com/dscripka/openWakeWord/releases/download/v0.5.0/timer_v0.1.tflite",
        "size": 422000
    },
    "weather_v0.1.tflite": {
        "url": "https://github.com/dscripka/openWakeWord/releases/download/v0.5.0/weather_v0.1.tflite",
        "size": 422000
    },

    # 特征提取模型
    "embedding_model_v1.tflite": {
        "url": "https://github.com/dscripka/openWakeWord/releases/download/v0.5.0/embedding_model_v1.tflite",
        "size": 14000000  # 约 14 MB
    },
    "melspectrogram_model_v1.tflite": {
        "url": "https://github.com/dscripka/openWakeWord/releases/download/v0.5.0/melspectrogram_model_v1.tflite",
        "size": 100000  # 约 100 KB
    },

    # VAD 模型
    "silero_vad.onnx": {
        "url": "https://github.com/dscripka/openWakeWord/releases/download/v0.5.0/silero_vad.onnx",
        "size": 66000000  # 约 66 MB
    }
}


def get_models_dir():
    """获取模型目录"""
    # 方法 1: 使用 import 直接获取包路径（最可靠）
    try:
        import openwakeword
        oww_path = Path(openwakeword.__file__).parent
        models_dir = oww_path / "resources" / "models"
        if models_dir.exists():
            return models_dir
        else:
            print_warn(f"  找到 openwakeword 包: {oww_path}")
            print_warn(f"  但模型目录不存在: {models_dir}")
            # 尝试创建目录
            try:
                models_dir.mkdir(parents=True, exist_ok=True)
                print_info(f"  已创建模型目录: {models_dir}")
                return models_dir
            except Exception as e:
                print_error(f"  无法创建模型目录: {e}")
    except ImportError:
        print_error("  无法导入 openwakeword 模块")

    # 方法 2: 尝试从虚拟环境获取
    venv_packages = Path(".venv/lib/python3.10/site-packages")
    if venv_packages.exists():
        models_dir = venv_packages / "openwakeword/resources/models"
        if models_dir.exists():
            return models_dir
        else:
            print_warn(f"  虚拟环境存在但模型目录不存在: {models_dir}")
            try:
                models_dir.mkdir(parents=True, exist_ok=True)
                print_info(f"  已创建模型目录: {models_dir}")
                return models_dir
            except Exception as e:
                print_error(f"  无法创建模型目录: {e}")

    # 方法 3: 尝试系统包
    import site
    for site_dir in site.getsitepackages():
        models_dir = Path(site_dir) / "openwakeword/resources/models"
        if models_dir.exists():
            return models_dir

    return None


def download_file(url, dest_path, expected_size=None):
    """
    下载文件并显示进度

    Args:
        url: 下载 URL
        dest_path: 目标路径
        expected_size: 预期文件大小（字节）

    Returns:
        bool: 是否成功
    """
    try:
        print(f"  下载: {Path(dest_path).name}")

        def report_progress(block_num, block_size, total_size):
            """显示下载进度"""
            if total_size > 0:
                downloaded = block_num * block_size
                percent = min(downloaded * 100 / total_size, 100)
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                print(f"\r    进度: {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end='')
            else:
                mb_downloaded = block_num * block_size / (1024 * 1024)
                print(f"\r    已下载: {mb_downloaded:.1f} MB", end='')

        urllib.request.urlretrieve(url, dest_path, reporthook=report_progress)
        print()  # 换行

        # 验证文件大小
        actual_size = os.path.getsize(dest_path)
        if expected_size and abs(actual_size - expected_size) > expected_size * 0.1:
            print_warn(f"    警告: 文件大小异常 (预期: {expected_size}, 实际: {actual_size})")
            return False

        print(f"  ✅ 下载成功 ({actual_size / 1024:.1f} KB)")
        return True

    except Exception as e:
        print_error(f"  ❌ 下载失败: {e}")
        return False


def check_model(models_dir, model_name):
    """
    检查模型文件是否存在

    Args:
        models_dir: 模型目录
        model_name: 模型文件名

    Returns:
        bool: 是否存在且有效
    """
    model_path = models_dir / model_name
    if not model_path.exists():
        return False

    # 检查文件大小
    size = model_path.stat().st_size
    expected_size = MODELS[model_name]['size']

    # 允许 10% 的误差
    if abs(size - expected_size) > expected_size * 0.1:
        print_warn(f"  {model_name}: 文件存在但大小异常 ({size} vs {expected_size})")
        return False

    return True


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("📦 OpenWakeWord 模型下载工具")
    print("=" * 60)
    print("")

    # 1. 获取模型目录
    print_step("1. 查找模型目录...")
    models_dir = get_models_dir()

    if not models_dir:
        print_error("❌ 未找到 openwakeword 安装目录")
        print("")
        print("请确保已安装 openwakeword:")
        print("  pip install openwakeword")
        return 1

    print_info(f"✅ 模型目录: {models_dir}")
    print("")

    # 2. 检查现有模型
    print_step("2. 检查现有模型...")
    existing_models = []
    missing_models = []

    for model_name in MODELS.keys():
        if check_model(models_dir, model_name):
            existing_models.append(model_name)
            print_info(f"  ✅ {model_name}")
        else:
            missing_models.append(model_name)
            print_warn(f"  ❌ {model_name} (缺失)")

    print("")
    print(f"现有模型: {len(existing_models)}/{len(MODELS)}")
    print(f"缺失模型: {len(missing_models)}/{len(MODELS)}")
    print("")

    # 3. 下载缺失的模型
    if missing_models:
        print_step("3. 下载缺失的模型...")
        print("")

        success_count = 0
        fail_count = 0

        for model_name in missing_models:
            model_info = MODELS[model_name]
            dest_path = models_dir / model_name

            print(f"📥 {model_name}")
            print(f"  URL: {model_info['url']}")

            if download_file(model_info['url'], dest_path, model_info['size']):
                success_count += 1
            else:
                fail_count += 1

                # 清理失败的文件
                if dest_path.exists():
                    dest_path.unlink()

            print("")

        print("=" * 60)
        print(f"下载完成: {success_count} 成功, {fail_count} 失败")
        print("=" * 60)

        if fail_count > 0:
            print_error("部分模型下载失败，请重试")
            return 1
    else:
        print_step("3. 所有模型已存在，无需下载")
        print("")

    # 4. 验证所有模型
    print_step("4. 验证所有模型...")
    print("")

    all_valid = True
    for model_name in MODELS.keys():
        if check_model(models_dir, model_name):
            size_kb = (models_dir / model_name).stat().st_size / 1024
            print_info(f"  ✅ {model_name} ({size_kb:.1f} KB)")
        else:
            print_error(f"  ❌ {model_name} 验证失败")
            all_valid = False

    print("")

    if all_valid:
        print("=" * 60)
        print_info("✅ 所有模型已就绪！")
        print("=" * 60)
        print("")
        print("模型列表:")
        print("  唤醒词模型:")
        print("    - alexa (亚马逊 Alexa)")
        print("    - hey_jarvis (贾维斯)")
        print("    - hey_mycroft (迈克洛夫特)")
        print("    - hey_rhasspy (Rhasspy)")
        print("    - timer (定时器)")
        print("    - weather (天气)")
        print("  特征提取模型:")
        print("    - embedding_model")
        print("    - melspectrogram_model")
        print("  VAD 模型:")
        print("    - silero_vad")
        print("")
        print("现在可以运行语音助手:")
        print("  python3 main.py")
        print("")
        return 0
    else:
        print_error("模型验证失败")
        return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(1)
    except Exception as e:
        print_error(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
