"""
音乐播放功能演示
Music Player Feature Demo

运行方式：
    python tests/manual/demo_music_player.py
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime, time


def demo_music_intent_detection():
    """演示音乐意图检测"""
    print("=" * 70)
    print("音乐播放功能演示 - 意图检测")
    print("=" * 70)

    from src.music.music_intent_detector import detect_music_intent

    test_cases = [
        # 播放类
        ("播放音乐", "play"),
        ("来点小曲", "play"),
        ("烘托氛围", "play"),
        ("听歌", "play"),
        ("背景音乐", "play"),
        ("播放《夜曲》", "play"),

        # 控制类
        ("暂停", "pause"),
        ("继续", "resume"),
        ("停止", "stop"),

        # 音量类
        ("大声点", "volume_up"),
        ("声音大点", "volume_up"),
        ("放大音量", "volume_up"),
        ("小声点", "volume_down"),
        ("声音小点", "volume_down"),
        ("减小音量", "volume_down"),

        # 非音乐类
        ("今天天气怎么样", None),
        ("设置闹钟", None),
    ]

    print("\n意图识别测试：\n")

    for text, expected_action in test_cases:
        intent = detect_music_intent(text)

        if expected_action:
            if intent and intent.action == expected_action:
                keyword = f" (关键词: '{intent.keyword}')" if intent.keyword else ""
                print(f"✓ '{text}' → {intent.action}{keyword}")
            else:
                print(f"✗ '{text}' → 期望 {expected_action}, 实际 {intent.action if intent else 'None'}")
        else:
            if intent is None:
                print(f"✓ '{text}' → 未识别（符合预期）")
            else:
                print(f"✗ '{text}' → {intent.action} (不应该被识别)")

    print("\n" + "=" * 70)


def demo_music_features():
    """演示音乐功能特性"""
    print("\n" + "=" * 70)
    print("音乐播放功能特性")
    print("=" * 70)

    features = [
        "✅ 本地音乐播放（支持 mp3, wav, ogg, flac 等）",
        "✅ 多级目录扫描（自动扫描 assets/music/）",
        "✅ 语音控制播放、暂停、停止",
        "✅ 音量调节（语音控制放大/缩小）",
        "✅ 背景播放（不阻塞其他功能）",
        "✅ 指定歌曲播放（支持模糊搜索）",
        "✅ 随机播放",
        "⏳ 在线音乐（预留，未实现）",
    ]

    print("\n功能列表：\n")
    for feature in features:
        print(f"  {feature}")

    print("\n" + "=" * 70)
    print("\n语音命令示例：\n")

    commands = [
        ("播放", "播放随机音乐"),
        ("播放《夜曲》", "播放指定歌曲"),
        ("暂停", "暂停当前播放"),
        ("继续", "恢复播放"),
        ("停止", "停止播放"),
        ("大声点", "音量增大 10%"),
        ("小声点", "音量减小 10%"),
    ]

    for cmd, desc in commands:
        print(f"  \"{cmd}\" → {desc}")

    print("\n" + "=" * 70)
    print("\n音乐目录结构示例：\n")

    structure = """
assets/music/
├── song1.mp3                    # 根目录文件
├── Artist1/                     # 按艺术家分类
│   ├── Album1/
│   │   ├── track1.flac
│   │   └── track2.flac
│   └── Album2/
│       └── track3.mp3
└── Artist2/
    └── track4.ogg
"""

    print(structure)

    print("\n" + "=" * 70)
    print("\n使用说明：\n")
    print("1. 将音乐文件放入 assets/music/ 目录")
    print("2. 支持多级子目录分类（艺术家/专辑/曲目）")
    print("3. 对语音助手说：\"派蒙，播放音乐\"")
    print("4. 播放中可以控制：\"派蒙，暂停\"、\"派蒙，大声点\"")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    demo_music_intent_detection()
    demo_music_features()
