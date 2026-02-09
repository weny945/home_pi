"""
最小化 STT 测试 - 避免内存问题
"""
import sys
import os
from pathlib import Path

# 获取项目根目录并切换工作目录
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

print("=" * 50)
print("最小化 STT 测试")
print("=" * 50)

print("\n[1/3] 导入模块...")
try:
    from src.stt import FunASRSTTEngine
    print("✅ 模块导入成功")
except Exception as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)

print("\n[2/3] 加载模型（禁用 VAD 和标点模型）...")
try:
    import time
    start = time.time()
    engine = FunASRSTTEngine(
        model_name='iic/SenseVoiceSmall',
        device='cpu',
        punc_model=None,  # 禁用标点
        vad_model=None,   # 禁用 VAD
        load_model=True
    )
    print(f"✅ 模型加载成功 (耗时: {time.time()-start:.1f}s)")
except Exception as e:
    print(f"❌ 模型加载失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[3/3] 转录音频文件...")
audio_file = "./test_recording.wav"
if not Path(audio_file).exists():
    print(f"❌ 音频文件不存在: {audio_file}")
    sys.exit(1)

try:
    start = time.time()
    result = engine.transcribe_file(audio_file)
    elapsed = time.time() - start

    print(f"\n✅ 转录完成!")
    print(f"识别结果: {result}")
    print(f"耗时: {elapsed:.1f}s")
except Exception as e:
    print(f"❌ 转录失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 50)
print("✅ 测试通过")
print("=" * 50)
