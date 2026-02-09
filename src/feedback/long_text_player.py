"""
TTS 打气词播放器（支持分段播放）
TTS Cheerword Player with Chunked Playback
"""
import logging
import re
import threading
import time
import queue
from typing import List, Optional
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class AudioChunk:
    """音频块"""
    audio: np.ndarray
    text: str  # 原始文本
    index: int  # 播放顺序


class ChunkedTTSPlayer:
    """
    分段 TTS 播放器

    功能：
    1. 将长文本分段生成
    2. 队列播放（支持打断）
    3. 支持暂停/恢复
    """

    def __init__(self, tts_engine, stop_event: threading.Event):
        """
        初始化播放器

        Args:
            tts_engine: TTS 引擎（有 synthesize 方法）
            stop_event: 停止事件（用于外部控制停止）
        """
        self._tts_engine = tts_engine
        self._stop_event = stop_event

        # 播放队列
        self._play_queue: queue.Queue = queue.Queue()

        # 播放线程
        self._play_thread: Optional[threading.Thread] = None
        self._is_playing = False

    def play_long_text(
        self,
        text: str,
        chunk_by_sentence: bool = True,
        target_duration: int = 30
    ) -> None:
        """
        播放长文本（分段生成 + 队列播放）

        Args:
            text: 要播放的文本
            chunk_by_sentence: 是否按句子分段（否则一次性生成）
            target_duration: 目标时长（秒）
        """
        logger.info(f"开始播放长文本（目标时长: {target_duration}秒）")

        if chunk_by_sentence:
            # 分段生成和播放
            chunks = self._split_text_by_sentences(text)
            logger.info(f"文本已分为 {len(chunks)} 个片段")

            # 启动播放线程
            self._start_play_thread()

            # 逐个生成并入队
            for i, chunk_text in enumerate(chunks):
                if self._stop_event.is_set():
                    logger.info("收到停止信号，停止生成")
                    break

                try:
                    logger.info(f"正在生成第 {i+1}/{len(chunks)} 段音频...")
                    audio_data = self._tts_engine.synthesize(chunk_text)

                    chunk = AudioChunk(
                        audio=audio_data,
                        text=chunk_text,
                        index=i
                    )

                    # 入队
                    self._play_queue.put(chunk)
                    logger.info(f"第 {i+1}/{len(chunks)} 段已生成并入队")

                    # 短暂延迟，让播放线程先播放当前段
                    time.sleep(0.1)

                except Exception as e:
                    logger.error(f"生成第 {i+1} 段失败: {e}")
                    break

            # 播放结束标记
            self._play_queue.put(None)

        else:
            # 一次性生成全部
            logger.info("一次性生成全部音频...")
            audio_data = self._tts_engine.synthesize(text)
            chunk = AudioChunk(audio=audio_data, text=text, index=0)
            self._play_queue.put(chunk)
            self._play_queue.put(None)

            # 启动播放线程
            self._start_play_thread()

        # 等待播放完成
        self._wait_for_play_complete()

    def _start_play_thread(self) -> None:
        """启动播放线程"""
        if self._play_thread and self._play_thread.is_alive():
            return

        self._is_playing = True
        self._play_thread = threading.Thread(
            target=self._play_loop,
            daemon=True
        )
        self._play_thread.start()
        logger.info("播放线程已启动")

    def _play_loop(self) -> None:
        """播放循环（在独立线程中运行）"""
        logger.info("播放循环开始")

        while True:
            try:
                # 从队列获取音频块（超时 1 秒）
                chunk = self._play_queue.get(timeout=1.0)

                if chunk is None:
                    # 播放结束标记
                    logger.info("收到播放结束标记")
                    break

                if self._stop_event.is_set():
                    logger.info("收到停止信号")
                    break

                # 播放音频
                logger.debug(f"播放片段 {chunk.index + 1}: {chunk.text[:20]}...")
                self._play_audio_chunk(chunk.audio)

            except queue.Empty:
                # 队列暂时为空，继续等待
                continue
            except Exception as e:
                logger.error(f"播放出错: {e}")
                break

        self._is_playing = False
        logger.info("播放循环结束")

    def _play_audio_chunk(self, audio_data: np.ndarray) -> None:
        """
        播放单个音频块

        Args:
            audio_data: 音频数据
        """
        import subprocess
        import tempfile
        import struct
        import os

        sample_rate = self._tts_engine.get_sample_rate()

        temp_path = None
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                temp_path = f.name

                # 写入 WAV 文件
                f.write(b'RIFF')
                f.write(struct.pack('<I', 36 + len(audio_data) * 2))
                f.write(b'WAVE')
                f.write(b'fmt ')
                f.write(struct.pack('<I', 16))
                f.write(struct.pack('<H', 1))
                f.write(struct.pack('<H', 1))
                f.write(struct.pack('<I', sample_rate))
                f.write(struct.pack('<I', sample_rate * 2))
                f.write(struct.pack('<H', 2))
                f.write(struct.pack('<H', 16))
                f.write(b'data')
                f.write(struct.pack('<I', len(audio_data) * 2))
                f.write(audio_data.astype(np.int16).tobytes())

            # 使用 aplay 播放
            cmd = ['aplay', '-q', temp_path]
            result = subprocess.run(cmd, check=True, capture_output=True)

        except Exception as e:
            logger.error(f"播放音频块失败: {e}")
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

    def _wait_for_play_complete(self) -> None:
        """等待播放完成"""
        if self._play_thread and self._play_thread.is_alive():
            self._play_thread.join()
        logger.info("播放已完成")

    def _split_text_by_sentences(self, text: str) -> List[str]:
        """
        将文本按句子分段

        Args:
            text: 输入文本

        Returns:
            List[str]: 分段后的文本列表
        """
        # 使用正则表达式按标点符号分段
        # 优先分段：。！？；：
        # 每段控制在 30-50 字左右（约 5-8 秒语音）

        sentences = []
        current = ""

        for char in text:
            current += char

            # 遇到句子结束符
            if char in ['。', '！', '？', '；', '：']:
                # 检查当前句子长度
                if len(current) >= 10:  # 至少 10 个字符
                    sentences.append(current)
                    current = ""
                else:
                    # 太短，继续累积
                    pass
            elif char in ['，', ',', '、']:
                # 逗号分段（如果句子较长）
                if len(current) >= 30:  # 30 字以上分段
                    sentences.append(current)
                    current = ""

        # 添加剩余内容
        if current:
            sentences.append(current)

        logger.debug(f"文本分段: {len(sentences)} 段")
        for i, s in enumerate(sentences):
            logger.debug(f"  段 {i+1}: {s[:30]}...")

        return sentences

    def is_playing(self) -> bool:
        """是否正在播放"""
        return self._is_playing

    def stop(self) -> None:
        """停止播放"""
        logger.info("停止播放")
        self._stop_event.set()
        self._is_playing = False
