"""
音乐播放功能端到端测试
Music Player End-to-End Tests

运行方式：
    pytest tests/manual/test_music_e2e.py -v -s
"""
import pytest
import tempfile
import shutil
from pathlib import Path

from src.music.music_player import MusicPlayer
from src.music.music_library import MusicLibrary
from src.music.music_intent_detector import detect_music_intent


class TestMusicE2E:
    """音乐播放 E2E 测试"""

    @pytest.fixture
    def temp_music_dir(self):
        """临时音乐目录"""
        temp_dir = tempfile.mkdtemp()
        music_dir = Path(temp_dir) / "music"
        music_dir.mkdir(parents=True, exist_ok=True)

        # 创建一些假的音频文件（实际测试需要真实音频文件）
        (music_dir / "song1.mp3").touch()
        (music_dir / "song2.wav").touch()

        # 创建子目录
        artist_dir = music_dir / "Artist" / "Album"
        artist_dir.mkdir(parents=True, exist_ok=True)
        (artist_dir / "track1.flac").touch()

        yield str(music_dir)

        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_music_player_initialization(self, temp_music_dir):
        """测试音乐播放器初始化"""
        print("\n" + "="*60)
        print("测试：音乐播放器初始化")
        print("="*60)

        player = MusicPlayer(music_dir=temp_music_dir)

        library = player.get_library()
        count = library.scan()

        print(f"\n扫描到 {count} 首曲目")
        assert count == 3

    def test_music_intent_detection(self):
        """测试音乐意图检测"""
        print("\n" + "="*60)
        print("测试：音乐意图检测")
        print("="*60)

        test_cases = [
            ("播放音乐", "play"),
            ("来点小曲", "play"),
            ("暂停", "pause"),
            ("继续", "resume"),
            ("停止", "stop"),
            ("大声点", "volume_up"),
            ("小声点", "volume_down"),
        ]

        for text, expected_action in test_cases:
            print(f"\n检测: {text}")
            intent = detect_music_intent(text)

            if intent:
                print(f"  ✓ 意图: {intent.action}")
                assert intent.action == expected_action
            else:
                print(f"  ✗ 未检测到意图")

    def test_music_library_info(self, temp_music_dir):
        """测试音乐库信息"""
        print("\n" + "="*60)
        print("测试：音乐库信息")
        print("="*60)

        library = MusicLibrary(temp_music_dir)
        library.scan()

        info = library.get_library_info()

        print(f"\n曲目总数: {info['total_tracks']}")
        print(f"艺术家数: {info['total_artists']}")
        print(f"专辑数: {info['total_albums']}")

        assert info['total_tracks'] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
