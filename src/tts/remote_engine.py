"""
远程 TTS 引擎（GPT-SoVITS API）
Remote TTS Engine using GPT-SoVITS API
"""
import logging
import numpy as np
import requests
from typing import Optional
import io
import wave

from .engine import TTSEngine

logger = logging.getLogger(__name__)


class RemoteTTSEngine(TTSEngine):
    """
    远程 TTS 引擎

    通过 HTTP API 调用 GPT-SoVITS 服务生成语音
    """

    def __init__(
        self,
        server_ip: str,
        port: int = 9880,
        timeout: int = 60,
        text_lang: str = "zh",
        speed: float = 1.0,
        max_text_length: int = 100
    ):
        """
        初始化远程 TTS 引擎

        Args:
            server_ip: TTS 服务器 IP 地址
            port: 端口号，默认 9880
            timeout: 请求超时时间（秒）
            text_lang: 文本语言 (zh/en/ja/zh_en/ja_en/auto)
            speed: 语速 (0.6-1.65)
            max_text_length: 单次请求最大文本长度（超过则分段）
        """
        self._server_ip = server_ip
        self._port = port
        self._timeout = timeout
        self._text_lang = text_lang
        self._speed = speed
        self._max_text_length = max_text_length

        # 构建API URL
        self._tts_url = f"http://{server_ip}:{port}/tts"
        self._status_url = f"http://{server_ip}:{port}/status"

        logger.info(f"远程 TTS 引擎初始化: {self._tts_url}")
        logger.info(f"  语言: {text_lang}, 语速: {speed}")
        logger.info(f"  最大文本长度: {max_text_length} 字（超过则自动分段）")

        # 启动时检查服务器状态
        self._is_available = self._check_server()
        if self._is_available:
            logger.info("✅ 远程 TTS 服务器连接成功")
        else:
            logger.warning("⚠️  远程 TTS 服务器连接失败，将使用本地 TTS")

    def _check_server(self) -> bool:
        """
        检查服务器是否可用

        Returns:
            bool: 服务器是否可用
        """
        try:
            response = requests.get(self._status_url, timeout=5)
            if response.status_code == 200:
                logger.debug("远程 TTS 服务器状态检查: OK")
                return True
            else:
                logger.warning(f"远程 TTS 服务器响应异常: HTTP {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            logger.warning("远程 TTS 服务器连接失败（ConnectionError）")
            return False
        except requests.exceptions.Timeout:
            logger.warning("远程 TTS 服务器连接超时")
            return False
        except Exception as e:
            logger.warning(f"远程 TTS 服务器检查失败: {e}")
            return False

    def check_health(self) -> bool:
        """
        健康检查（供外部调用）

        Returns:
            bool: 服务器是否可用
        """
        is_available = self._check_server()

        # 更新状态
        if is_available != self._is_available:
            if is_available:
                logger.info("✅ 远程 TTS 服务器已恢复在线")
            else:
                logger.warning("⚠️  远程 TTS 服务器已离线")
            self._is_available = is_available

        return is_available

    def synthesize(
        self,
        text: str,
        speaker_id: Optional[int] = None
    ) -> np.ndarray:
        """
        合成语音（支持长文本自动分段）

        Args:
            text: 要合成的文本
            speaker_id: 说话人ID（远程引擎不支持此参数）

        Returns:
            np.ndarray: 音频数据 (16kHz, 16bit, 单声道)

        Raises:
            Exception: 合成失败时抛出异常
        """
        if not text or text.strip() == "":
            raise ValueError("文本不能为空")

        if not self._is_available:
            raise ConnectionError("远程 TTS 服务器不可用")

        text_length = len(text)
        logger.debug(f"远程 TTS 合成文本长度: {text_length} 字")

        # 如果文本长度超过阈值，分段处理
        if text_length > self._max_text_length:
            logger.info(f"📝 文本过长 ({text_length} 字)，自动分段处理")
            return self._synthesize_segmented(text)

        # 单次请求
        return self._synthesize_single(text)

    def _split_text(self, text: str) -> list:
        """
        智能分段文本

        策略：
        1. 按标点符号分段（句号、问号、感叹号）
        2. 控制每段长度（不超过 max_text_length）
        3. 避免在单词或句子中间断开

        Args:
            text: 要分段的文本

        Returns:
            list: 文本段列表
        """
        import re

        segments = []
        current_segment = ""

        # 按句子分割（保留分隔符）
        sentences = re.split(r'([。！？\.\!\?])', text)

        # 重新组合句子和分隔符
        i = 0
        while i < len(sentences):
            sentence = sentences[i]
            # 如果当前句子是分隔符，加上前一个句子
            if i > 0 and sentences[i] in '。！？.!?':
                sentence = sentences[i-1] + sentences[i]
                i += 1
            elif i < len(sentences) - 1 and sentences[i+1] in '。！？.!?':
                sentence = sentences[i] + sentences[i+1]
                i += 2
                if not sentence.strip():
                    continue
            else:
                i += 1

            if not sentence or not sentence.strip():
                continue

            # 检查是否可以添加到当前段
            if len(current_segment) + len(sentence) <= self._max_text_length:
                current_segment += sentence
            else:
                # 当前段已满，保存并开始新段
                if current_segment:
                    segments.append(current_segment.strip())
                current_segment = sentence

        # 添加最后一段
        if current_segment:
            segments.append(current_segment.strip())

        # 如果分段后仍有超长段（可能是因为没有标点），强制按长度切分
        final_segments = []
        for segment in segments:
            if len(segment) > self._max_text_length:
                # 强制按长度切分
                for i in range(0, len(segment), self._max_text_length):
                    final_segments.append(segment[i:i+self._max_text_length])
            else:
                final_segments.append(segment)

        logger.info(f"  文本分段: {len(final_segments)} 段")
        for i, seg in enumerate(final_segments):
            logger.debug(f"    段 {i+1}: {len(seg)} 字 - {seg[:30]}{'...' if len(seg) > 30 else ''}")

        return final_segments

    def _synthesize_single(self, text: str) -> np.ndarray:
        """
        单次请求合成

        Args:
            text: 要合成的文本

        Returns:
            np.ndarray: 音频数据
        """
        params = {
            "text": text,
            "text_lang": self._text_lang,
            "speed": self._speed,
        }

        try:
            logger.debug(f"请求远程 TTS: {text[:50]}{'...' if len(text) > 50 else ''}")

            response = requests.get(
                self._tts_url,
                params=params,
                timeout=self._timeout
            )

            if response.status_code != 200:
                error_msg = f"远程 TTS 请求失败: HTTP {response.status_code}"
                logger.error(error_msg)
                raise ConnectionError(error_msg)

            audio_data = self._parse_wav(response.content)
            logger.debug(f"✅ 远程 TTS 合成成功: {len(audio_data)} 采样点")
            return audio_data

        except requests.exceptions.Timeout:
            error_msg = "远程 TTS 请求超时"
            logger.error(error_msg)
            self._is_available = False
            raise ConnectionError(error_msg)

        except requests.exceptions.ConnectionError:
            error_msg = "远程 TTS 连接失败"
            logger.error(error_msg)
            self._is_available = False
            raise ConnectionError(error_msg)

        except Exception as e:
            logger.error(f"远程 TTS 合成失败: {e}")
            self._is_available = False
            raise

    def _synthesize_segmented(self, text: str) -> np.ndarray:
        """
        分段合成长文本

        Args:
            text: 要合成的长文本

        Returns:
            np.ndarray: 合并后的音频数据
        """
        # 分段
        segments = self._split_text(text)

        # 逐段合成
        all_audio = []
        total_samples = 0

        for i, segment in enumerate(segments, 1):
            logger.info(f"  合成第 {i}/{len(segments)} 段...")

            try:
                audio = self._synthesize_single(segment)
                all_audio.append(audio)
                total_samples += len(audio)

                logger.info(f"    ✅ 第 {i} 段完成: {len(audio)} 采样点")

            except Exception as e:
                logger.error(f"    ❌ 第 {i} 段失败: {e}")
                # 可以选择：继续合成下一段，或者抛出异常
                # 这里选择抛出异常，保证完整性
                raise RuntimeError(f"长文本合成失败（第 {i}/{len(segments)} 段）: {e}")

        # 合并所有音频段
        logger.info(f"  合并 {len(all_audio)} 段音频...")
        merged_audio = np.concatenate(all_audio)

        logger.info(f"✅ 长文本合成完成: {total_samples} 采样点 ({len(segments)} 段)")
        return merged_audio

    def _parse_wav(self, wav_bytes: bytes) -> np.ndarray:
        """
        解析 WAV 字节数据

        Args:
            wav_bytes: WAV 文件的字节数据

        Returns:
            np.ndarray: 音频数据 (16bit PCM)
        """
        try:
            # 使用 io.BytesIO 包装字节数据
            with wave.open(io.BytesIO(wav_bytes), 'rb') as wav_file:
                # 读取音频参数
                frames = wav_file.getnframes()
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                sampwidth = wav_file.getsampwidth()

                # 读取音频数据
                audio_bytes = wav_file.readframes(frames)

                # 转换为 numpy 数组
                if sampwidth == 2:  # 16-bit
                    dtype = np.int16
                elif sampwidth == 4:  # 32-bit
                    dtype = np.int32
                else:
                    raise ValueError(f"不支持的采样位宽: {sampwidth}")

                audio_data = np.frombuffer(audio_bytes, dtype=dtype)

                # 如果是立体声，转换为单声道
                if channels == 2:
                    audio_data = audio_data.reshape(-1, 2).mean(axis=1).astype(dtype)

                # 重采样到 16kHz（如果需要）
                if sample_rate != 16000:
                    logger.info(f"远程 TTS 返回采样率 {sample_rate}Hz，重采样到 16kHz")
                    # 使用 resample_poly 获得更好的音质
                    from scipy import signal
                    from fractions import Fraction

                    # 计算重采样比例（约分后更精确）
                    ratio = Fraction(16000, sample_rate)
                    up = ratio.numerator
                    down = ratio.denominator

                    # 使用多项式重采样（质量更好）
                    audio_data = signal.resample_poly(
                        audio_data,
                        up,
                        down,
                        window=('kaiser', 5.0)  # Kaiser 窗提供更好的抗混叠
                    ).astype(dtype)

                    logger.debug(f"  重采样比例: {up}/{down} (原始 {sample_rate}Hz → 16kHz)")

                return audio_data

        except Exception as e:
            logger.error(f"解析 WAV 数据失败: {e}")
            raise ValueError(f"无效的 WAV 数据: {e}")

    def get_sample_rate(self) -> int:
        """获取采样率"""
        return 16000

    def is_ready(self) -> bool:
        """
        是否已就绪

        Returns:
            bool: 远程服务器是否可用
        """
        return self._is_available

    def get_model_info(self) -> dict:
        """
        获取模型信息

        Returns:
            dict: 模型信息
        """
        return {
            "name": "GPT-SoVITS Remote API",
            "server": f"{self._server_ip}:{self._port}",
            "language": self._text_lang,
            "speed": self._speed,
            "available": self._is_available
        }

    def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        speaker_id: Optional[int] = None
    ) -> None:
        """
        合成语音并保存到文件

        Args:
            text: 要合成的文本
            output_path: 输出文件路径
            speaker_id: 说话人ID（不支持）
        """
        audio_data = self.synthesize(text, speaker_id)

        # 保存为 WAV 文件
        import wave
        with wave.open(output_path, 'wb') as wav_file:
            wav_file.setnchannels(1)  # 单声道
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(16000)  # 16kHz
            wav_file.writeframes(audio_data.tobytes())

        logger.info(f"音频已保存到: {output_path}")
