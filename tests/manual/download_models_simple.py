#!/usr/bin/env python3
"""
OpenWakeWord 模型下载脚本（简化版）
使用 openwakeword 内置功能下载模型
"""
import sys
from pathlib import Path

def main():
    print("\n" + "=" * 60)
    print("📦 OpenWakeWord 模型下载")
    print("=" * 60)
    print("")

    try:
        # 方法 1: 使用 openwakeword 内置下载
        print("方法 1: 使用 openwakeword 内置功能...")
        print("初始化 Model 类时会自动下载模型...")

        from openwakeword.model import Model
        import openwakeword

        # 创建模型实例（会自动下载）
        model = Model(enable_retrieve_models=True)

        # 获取模型目录
        oww_path = Path(openwakeword.__file__).parent
        models_dir = oww_path / "resources" / "models"

        print("")
        print("=" * 60)
        print("✅ 模型下载完成！")
        print("=" * 60)
        print("")
        print(f"模型目录: {models_dir}")
        print("")
        print("已下载的模型:")
        if models_dir.exists():
            model_files = sorted(models_dir.glob("*"))
            if not model_files:
                print("  ⚠️  模型目录为空")
            else:
                for model_file in model_files:
                    if model_file.is_file():
                        size_kb = model_file.stat().st_size / 1024
                        print(f"  ✅ {model_file.name} ({size_kb:.1f} KB)")
        print("")

        # 测试模型是否可用
        print("测试模型加载...")
        import numpy as np
        audio_data = np.zeros(16000, dtype=np.int16)  # 1秒静音
        predictions = model.predict(audio_data)
        print(f"✅ 模型测试成功！检测到 {len(predictions)} 个唤醒词")
        print("")

        return 0

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(1)
