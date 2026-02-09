"""
音乐库单元测试
Music Library Unit Tests
"""
import pytest
import tempfile
import shutil
from pathlib import Path

from src.music.music_library import MusicLibrary, Track


class TestMusicLibrary:
    """音乐库测试"""

    @pytest.fixture
    def temp_music_dir(self):
        """临时音乐目录"""
        temp_dir = tempfile.mkdtemp()
        music_dir = Path(temp_dir) / "music"
        music_dir.mkdir(parents=True, exist_ok=True)

        yield str(music_dir)

        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def library(self, temp_music_dir):
        """音乐库实例"""
        return MusicLibrary(temp_music_dir)

    def test_scan_empty_directory(self, library):
        """测试扫描空目录"""
        count = library.scan()
        assert count == 0

    def test_create_track(self, library):
        """测试创建曲目"""
        from src.music.music_library import Track

        track = Track(
            path="/path/to/song.mp3",
            name="song",
            artist="Artist",
            album="Album"
        )

        assert track.name == "song"
        assert str(track) == "Artist - song"

    def test_get_random_track_empty(self, library):
        """测试从空库获取随机曲目"""
        track = library.get_random_track()
        assert track is None


class TestMusicIntentDetector:
    """音乐意图检测器测试"""

    def test_detect_play_intent(self):
        """测试检测播放意图"""
        from src.music.music_intent_detector import detect_music_intent

        test_cases = [
            ("播放音乐", "play"),
            ("来点小曲", "play"),
            ("烘托氛围", "play"),
            ("听歌", "play"),
        ]

        for text, expected_action in test_cases:
            intent = detect_music_intent(text)
            assert intent is not None
            assert intent.action == expected_action

    def test_detect_pause_intent(self):
        """测试检测暂停意图"""
        from src.music.music_intent_detector import detect_music_intent

        intent = detect_music_intent("暂停")
        assert intent is not None
        assert intent.action == "pause"

    def test_detect_volume_up_intent(self):
        """测试检测音量增大意图"""
        from src.music.music_intent_detector import detect_music_intent

        test_cases = [
            "大声点",
            "声音大点",
            "放大音量"
        ]

        for text in test_cases:
            intent = detect_music_intent(text)
            assert intent is not None
            assert intent.action == "volume_up"

    def test_detect_volume_down_intent(self):
        """测试检测音量减小意图"""
        from src.music.music_intent_detector import detect_music_intent

        test_cases = [
            "小声点",
            "声音小点",
            "减小音量"
        ]

        for text in test_cases:
            intent = detect_music_intent(text)
            assert intent is not None
            assert intent.action == "volume_down"

    def test_non_music_intent(self):
        """测试非音乐意图"""
        from src.music.music_intent_detector import detect_music_intent

        intent = detect_music_intent("今天天气怎么样")
        assert intent is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
