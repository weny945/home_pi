"""
音乐播放模块 - Music Player Module
支持本地音乐播放、音量控制、播放列表管理
Phase 1.8
"""

from .music_player import MusicPlayer
from .music_library import MusicLibrary, Track
from .music_intent_detector import detect_music_intent, MusicIntent

__all__ = [
    'MusicPlayer',
    'MusicLibrary',
    'Track',
    'detect_music_intent',
    'MusicIntent',
]
