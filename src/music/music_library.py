"""
音乐库 - Music Library
扫描和管理本地音乐文件
"""
import logging
import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional
import random

logger = logging.getLogger(__name__)


@dataclass
class Track:
    """音乐曲目"""
    path: str              # 文件路径
    name: str              # 曲目名称
    artist: Optional[str] = None  # 艺术家
    album: Optional[str] = None   # 专辑
    duration: Optional[float] = None  # 时长（秒）

    def __str__(self) -> str:
        """字符串表示"""
        if self.artist:
            return f"{self.artist} - {self.name}"
        return self.name


class MusicLibrary:
    """音乐库管理器"""

    # 支持的音频格式
    SUPPORTED_FORMATS = ['.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac']

    def __init__(self, music_dir: str = "./assets/music"):
        """
        初始化音乐库

        Args:
            music_dir: 音乐文件根目录
        """
        self._music_dir = Path(music_dir)
        self._tracks: List[Track] = []
        self._scanned = False

        logger.info(f"音乐库初始化: {music_dir}")

    def scan(self, recursive: bool = True) -> int:
        """
        扫描音乐文件

        Args:
            recursive: 是否递归扫描子目录

        Returns:
            int: 找到的曲目数量
        """
        if not self._music_dir.exists():
            logger.warning(f"音乐目录不存在: {self._music_dir}")
            logger.info(f"请创建目录并添加音乐文件: {self._music_dir}")
            return 0

        self._tracks = []
        count = 0

        # 获取所有音频文件
        if recursive:
            pattern = '**/*'
        else:
            pattern = '*'

        for file_path in self._music_dir.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_FORMATS:
                track = self._create_track(file_path)
                if track:
                    self._tracks.append(track)
                    count += 1

        self._scanned = True
        logger.info(f"扫描完成，找到 {count} 首曲目")

        return count

    def get_all_tracks(self) -> List[Track]:
        """获取所有曲目"""
        if not self._scanned:
            self.scan()
        return self._tracks

    def get_random_track(self) -> Optional[Track]:
        """获取随机曲目"""
        tracks = self.get_all_tracks()
        if not tracks:
            return None

        # 过滤掉不存在的文件
        valid_tracks = [t for t in tracks if Path(t.path).exists()]

        if not valid_tracks:
            logger.warning("音乐库中没有有效的音乐文件（所有文件都不存在）")
            return None

        return random.choice(valid_tracks)

    def get_track_by_name(self, name: str) -> Optional[Track]:
        """
        根据名称查找曲目

        Args:
            name: 曲目名称（支持模糊匹配）

        Returns:
            Track: 找到的曲目，未找到返回 None
        """
        tracks = self.get_all_tracks()
        name_lower = name.lower()

        # 过滤掉不存在的文件
        valid_tracks = [t for t in tracks if Path(t.path).exists()]

        if not valid_tracks:
            logger.warning("音乐库中没有有效的音乐文件")
            return None

        # 精确匹配
        for track in valid_tracks:
            if name_lower == track.name.lower():
                return track

        # 模糊匹配
        for track in valid_tracks:
            if name_lower in track.name.lower():
                return track

        return None

    def search_tracks(self, keyword: str) -> List[Track]:
        """
        搜索曲目

        Args:
            keyword: 搜索关键词

        Returns:
            List[Track]: 匹配的曲目列表
        """
        tracks = self.get_all_tracks()
        keyword_lower = keyword.lower()

        results = []
        for track in tracks:
            # 搜索曲目名称、艺术家、专辑
            if (keyword_lower in track.name.lower() or
                (track.artist and keyword_lower in track.artist.lower()) or
                (track.album and keyword_lower in track.album.lower())):
                results.append(track)

        return results

    def _create_track(self, file_path: Path) -> Optional[Track]:
        """
        从文件路径创建曲目对象

        Args:
            file_path: 文件路径

        Returns:
            Track: 曲目对象
        """
        try:
            # 使用文件名作为曲目名称（去掉扩展名）
            name = file_path.stem

            # 尝试从路径解析艺术家和专辑
            # 例如：music/艺术家/专辑/曲目.mp3
            parts = file_path.relative_to(self._music_dir).parts

            artist = None
            album = None

            if len(parts) >= 3:
                # 可能的结构：艺术家/专辑/曲目
                artist = parts[0]
                album = parts[1]
            elif len(parts) == 2:
                # 可能的结构：艺术家/曲目 或 专辑/曲目
                # 简化处理：假设第一个是艺术家
                artist = parts[0]

            track = Track(
                path=str(file_path),
                name=name,
                artist=artist,
                album=album
            )

            return track

        except Exception as e:
            logger.warning(f"创建曲目失败 ({file_path}): {e}")
            return None

    def get_library_info(self) -> dict:
        """
        获取音乐库信息

        Returns:
            dict: 音乐库统计信息
        """
        tracks = self.get_all_tracks()

        # 统计艺术家数量
        artists = set()
        albums = set()

        for track in tracks:
            if track.artist:
                artists.add(track.artist)
            if track.album:
                albums.add(track.album)

        return {
            'total_tracks': len(tracks),
            'total_artists': len(artists),
            'total_albums': len(albums),
            'music_dir': str(self._music_dir)
        }
