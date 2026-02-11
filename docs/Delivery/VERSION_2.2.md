# 语音助手 v2.2 - 千问 TTS 集成（智能流式 + 缓存 + Piper 备用）

## 版本信息
- **版本号**: v2.2
- **发布日期**: 2026-02-03
- **基于版本**: v2.1
- **更新类型**: 功能增强（新增千问 TTS + 流式支持 + 缓存）

---

## 更新概览

### 新增功能
1. **千问 TTS 集成**: 集成阿里云千问 TTS Flash 模型（qwen3-tts-flash）
2. **流式 TTS 支持**: 长文本使用 WebSocket 流式 API，首字延迟仅 ~97ms
3. **智能路由**: 自动根据文本长度和场景选择流式/非流式
4. **TTS 缓存系统**: 持久化缓存常用短语，响应速度降至 <1ms
5. **自动预热**: 启动时自动生成常用短语（唤醒回复、系统提示、重试提示等）
6. **新增引擎模式**:
   - **hybrid-qwen**: 优先千问 TTS，失败时降级到 Piper
   - **remote-qwen**: 仅使用千问 TTS
7. **自动降级**: 千问 TTS 失败时自动切换到本地 Piper

### 保留功能
- **原有混合模式**（hybrid）: 本地 Piper + 远程主机 GPT-SoVITS
- **远程模式**（remote）: 仅使用远程主机 GPT-SoVITS
- **本地模式**（piper）: 仅使用本地 Piper

### 改进点
- 提升语音质量（千问 TTS 接近真人）
- 流式优化（长文本首字延迟从 200-500ms 降至 ~97ms）
- 缓存优化（常用短语响应从 5-250ms 降至 <1ms）
- 保持可用性（网络失败时降级到 Piper）
- 降低成本（千问 TTS Flash 模型很便宜）
- 简化配置（所有文本使用千问 TTS，无需区分长短文本）
- 持久化缓存（项目重启后缓存依然有效）

---

## 技术架构

### 千问 TTS 流式/非流式混合架构图

```
┌─────────────────────────────────────────────────────────┐
│                   TTS 引擎选择                            │
│                 (基于 config.tts.engine)                  │
└─────────────────────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
        ▼           ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│  piper   │ │  hybrid  │ │remote-qwen│
│          │ │          │ │          │
│ 仅 Piper │ │ Piper +  │ │ 仅千问  │
│          │ │主机GPT-  │ │  TTS    │
│          │ │ SoVITS   │ │          │
└──────────┘ └──────────┘ └──────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │   hybrid-qwen 优先    │
                │   千问 TTS，失败降级  │
                └───────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
        ┌──────────────────────┐   ┌──────────────┐
        │   千问 TTS 智能选择   │   │  本地 Piper  │
        │                       │   │   (备用)     │
        │ ┌─────────────────┐   │   │              │
        │ │ 文本长度 ≥ 100字│   │   │ - 离线       │
        │ │ 或特定场景      │   │   │ - 降级方案   │
        │ └────────┬────────┘   │   │ - 可靠性     │
        │          ▼             │   │ - 5-50ms    │
        │ │ 流式 WebSocket      │   │              │
        │ │ • 首字 ~97ms       │   └──────────────┘
        │ │ • 实时播放         │
        │ │ • 长文本优化       │
        │ └────────────────────┘
        │
        │ ┌─────────────────┐
        │ │ 文本长度 < 100字│
        │ └────────┬────────┘
        │          ▼
        │ │ 非 流式 HTTP       │
        │ │ • 200-500ms       │
        │ │ • 简单可靠        │
        │ │ • 短文本优化      │
        │ └────────────────────┘
        │
        │ - 高质量     │
        │ - 低成本     │
        │ - 自然度高   │
        └──────────────────────┘
```

### 流式 vs 非流式对比

| 特性 | 非流式 HTTP API | 流式 WebSocket API |
|------|----------------|-------------------|
| **首字延迟 (TTFC)** | 200-500ms | ~97ms |
| **适用场景** | 短文本 (< 100字符) | 长文本 (≥ 100字符) |
| **实现复杂度** | 简单 (单次 HTTP 请求) | 复杂 (WebSocket + 异步) |
| **音频格式** | MP3/WAV | PCM (流式) |
| **播放方式** | 等待完成后播放 | 实时边生成边播放 |
| **网络容错** | 好 (自动重试) | 中 (需处理连接中断) |

### 流式 TTS 优势

**长文本场景优化**：
- 故事朗读（200字以上）→ 首字延迟从 500ms 降至 97ms
- LLM 长回复（100字以上）→ 用户感知响应更快
- 闹钟打气词（150字左右）→ 播放更流畅

**技术优势**：
- WebSocket 双向通信，服务端推送音频块
- 首帧延迟 (Time To First Audio, TTFC) 仅 97ms
- 边生成边播放，无需等待完整音频
- 减少内存占用（流式处理）

### hybrid-qwen 路由决策逻辑

```
输入文本 + 场景
  ↓
┌─────────────────────────────────────────┐
│ 1. 检查流式引擎是否可用                 │
│    - 网络连接                           │
│    - API key 配置                       │
└─────────────────┬───────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
    可用 ◄─────────────► 不可用
        │                   │
        ▼                   ▼
┌───────────────────┐   ┌──────────────────┐
│ 2. 检查场景配置   │   │ 直接使用 Piper   │
│    - llm_reply_long│   │ (本地降级)       │
│    - alarm_cheerword│  └──────────────────┘
│    - story_telling │
└─────────┬─────────┘
          │
    ┌─────┴─────┐
    │           │
流式场景    非流式场景
    │           │
    ▼           ▼
┌──────────┐ ┌──────────┐
│ 3. 检查  │ │ 4. 检查  │
│ 文本长度 │ │ 文本长度 │
└─────┬────┘ └─────┬────┘
      │            │
  ┌───┴───┐    ┌───┴───┐
  │       │    │       │
≥100字 <100字 ≥100字 <100字
  │       │    │       │
  ▼       ▼    ▼       ▼
┌──────┐┌──────┐┌──────┐┌──────┐
│流式  ││非流式││非流式││非流式│
│WebSocket│HTTP││HTTP││HTTP│
└───┬──┘└───┬──┘└───┬──┘└───┬──┘
    │       │    │    │
    └───────┴────┴────┘
            │
    ┌───────┴────────┐
    │                │
成功 ◄──────────► 失败
    │                │
    ▼                ▼
┌──────────┐   ┌──────────┐
│返回音频  │   │降级Piper │
└──────────┘   └──────────┘
```

### 流式场景配置

| 场景 | 流式模式 | 说明 |
|------|---------|------|
| `llm_reply_long` | ✅ 流式 | LLM 长回复（≥100字） |
| `alarm_cheerword` | ✅ 流式 | 闹钟打气词（长文本） |
| `story_telling` | ✅ 流式 | 故事朗读 |
| `article_reading` | ✅ 流式 | 文章阅读 |
| `long_content` | ✅ 流式 | 长内容 |
| `wake_response` | ❌ 非流式 | 唤醒回复（短文本，使用缓存） |
| `system_prompt` | ❌ 非流式 | 系统提示（短文本，使用缓存） |
| `music_control` | ❌ 非流式 | 音乐控制（短文本，使用缓存） |

### TTS 缓存架构 [v2.2 新增]

```
┌─────────────────────────────────────────────────────────┐
│                   TTS 合成请求                            │
│              (text: "我在", scenario: wake)             │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │   检查缓存是否存在     │
        └───────────┬───────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
    命中 ◄─────────────► 未命中
        │                       │
        ▼                       ▼
┌──────────────┐        ┌──────────────┐
│ <1ms 返回音频 │        │ 调用 TTS 引擎│
│ (持久化缓存) │        │ 合成语音     │
└──────────────┘        └──────┬───────┘
                               │
                        ┌──────┴───────┐
                        │ 保存到缓存   │
                        │ (持久化)     │
                        └──────┬───────┘
                               ▼
                        ┌──────────────┐
                        │ 返回音频     │
                        └──────────────┘

缓存目录: ./data/tts_cache/
├── metadata.json          # 元数据（文本、时间戳、访问计数）
├── a1b2c3d4...npy        # 音频文件（MD5 命名）
└── ...

特性：
• 持久化存储（重启后依然有效）
• 自动预热（启动时生成常用短语）
• 智能提取（从 config.yaml 自动提取）
• 空间管理（自动清理过期缓存）
```

### 缓存性能对比

| 短语类型 | 无缓存 | 有缓存 | 提升 |
|---------|--------|--------|------|
| **唤醒回复** (Piper) | 5-50ms | <1ms | 5-50x |
| **唤醒回复** (千问) | 200-500ms | <1ms | 200-500x |
| **系统提示** | 5-500ms | <1ms | 5-500x |
| **重试提示** | 5-500ms | <1ms | 5-500x |

### 自动提取的缓存短语

缓存系统自动从 `config.yaml` 提取以下短语：

1. **唤醒回复** (`feedback.tts.messages`):
   - "我在"、"请吩咐"、"我在听"、"在呢在呢"...

2. **重试提示语** (`audio_quality.retry_prompts`):
   - silence: "抱歉，没听到您的声音，能再说一遍吗？"
   - fragment: "请完整说出您的问题"
   - semantic: "抱歉，不太明白您的意思，能再说一遍吗？"
   - garbage: "抱歉，我没听清，能再说一遍吗？"

3. **自动收尾** (`conversation.auto_farewell.farewell_messages`):
   - "好的，那先这样吧"
   - "嗯，好的"
   - "那下次再聊"

4. **系统提示**:
   - "抱歉，现在胡桃在遨游太空，不在服务区"

---

## 配置文件扩展

### config.yaml 新增配置段

**注意**: v2.2 保留了原有的配置结构，仅添加了千问 TTS 相关配置。

```yaml
# ========================================
# TTS 配置
# ========================================
tts:
  # 引擎类型（5种可选）:
  #   - "hybrid": 本地Piper + 远程主机GPT-SoVITS（原有）
  #   - "remote": 仅远程主机GPT-SoVITS（原有）
  #   - "piper": 仅本地Piper（原有）
  #   - "hybrid-qwen": 本地Piper + 远程千问TTS [v2.2 新增]
  #   - "remote-qwen": 仅远程千问TTS [v2.2 新增]
  engine: "piper"

  # ========================================
  # 原有配置（保留不变）
  # ========================================

  # 混合引擎配置（当 engine="hybrid" 时生效）
  hybrid:
    health_check_interval: 3600        # 健康检查间隔（秒）
    auto_failback: true                # 是否自动切回远程 TTS

  # 远程 TTS 配置（GPT-SoVITS API，当 engine="hybrid" 或 "remote" 时生效）
  remote:
    enabled: true
    server_ip: "192.168.2.141"         # 服务器 IP 地址
    port: 9880
    timeout: 60
    text_lang: "zh"
    speed: 1.0
    max_text_length: 100

  # 本地 TTS 配置（Piper，当 engine="piper", "hybrid", "hybrid-qwen" 时生效）
  local:
    engine: "piper"
    model_path: "./models/piper/zh_CN-huayan-medium.onnx"

    # === 语音合成参数 ===
    length_scale: 1.0                  # 语速缩放 (1.0=正常)
    noise_scale: 0.75                  # 音色随机性/情感波动
    noise_w_scale: 0.8                 # 韵律噪声/语气变化
    sentence_silence: 0.2              # 句间停顿时长（秒）

    # === 文本增强配置 ===
    text_enhancement:
      enabled: true
      pause_marks_enabled: true        # 支持 [PAUSE:0.5] 标记
      pause_to_punctuation:
        enabled: true
        short_pause: "，"
        medium_pause: "，。"
        long_pause: "，。。。"
        commas_per_second: 2
      remove_wavy_tilde: true
      fix_final_particles: true

  # ========================================
  # 千问 TTS 配置 [v2.2 新增]
  # ========================================
  # 当 engine="hybrid-qwen" 或 "remote-qwen" 时生效
  qwen:
    enabled: true                       # 是否启用千问 TTS
    provider: "dashscope"               # "dashscope" | "openai"

    # Dashscope 千问 TTS 配置（非流式 HTTP API）
    dashscope:
      api_key: "${DASHSCOPE_API_KEY}"   # API 密钥（环境变量）
      endpoint: "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/generation"
      model: "qwen3-tts-flash"          # Flash 模型（快速、高质量）

      # 音频参数
      format: "mp3"                     # 音频格式
      sample_rate: 24000                # 采样率
      volume: 50                        # 音量 (0-100)

      # 语音风格（发音人）
      voice: "zhixiaobai"               # 发音人选择:
                                        # • zhixiaobai (小白)：年轻男声，日常对话
                                        # • zhichu (小楚)：温柔女声，陪伴场景
                                        # • zhitian (小天)：活泼男声，儿童场景
                                        # • zhinan (小楠)：成熟女声，助手场景
                                        # • zhiqi (小奇)：可爱女声，娱乐场景

      # 语速和音调
      rate: 1.0                         # 语速 (0.5-2.0)
      pitch: 1.0                        # 音调 (0.5-2.0)

      # 超时配置
      timeout: 30                       # 请求超时（秒）
      retry: 2                          # 失败重试次数

    # OpenAI TTS 配置（备选）
    openai:
      api_key: "${OPENAI_API_KEY}"
      endpoint: "https://api.openai.com/v1/audio/speech"
      model: "tts-1"
      voice: "alloy"
      timeout: 30

  # ========================================
  # 千问流式 TTS 配置 [v2.2 新增]
  # ========================================
  # 当 engine="hybrid-qwen" 时生效（流式引擎）
  qwen_realtime:
    enabled: true                       # 是否启用千问流式 TTS

    # Dashscope 千问流式 TTS 配置
    dashscope:
      api_key: "${DASHSCOPE_API_KEY}"   # API 密钥（环境变量）
      url: "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
      model: "qwen3-tts-flash-realtime" # 流式 Flash 模型

      # 音频参数
      voice: "zhixiaobai"               # 发音人（同 qwen 非流式）
      format: "pcm"                     # 音频格式: pcm（流式推荐）
      sample_rate: 24000                # 采样率: 24000（推荐）

      # 流式模式
      mode: "server_commit"             # server_commit（推荐）| commit
                                        # • server_commit: 服务端自动提交（更简单）
                                        # • commit: 客户端显式提交（更可控）

      # 超时配置
      timeout: 30                       # WebSocket 连接超时（秒）

  # ========================================
  # hybrid-qwen 混合策略配置 [v2.2 新增]
  # ========================================
  # 当 engine="hybrid-qwen" 时生效
  # 逻辑：智能选择流式/非流式，失败时降级到本地 Piper
  hybrid_qwen:
    # 流式切换配置
    streaming_threshold: 100            # 文本长度阈值（字符数）
                                        # • ≥100字符：使用流式 API
                                        # • <100字符：使用非流式 API
    scenario_streaming:                 # 场景级别流式配置
      llm_reply_long: "streaming"       # LLM 长回复 → 流式
      alarm_cheerword: "streaming"      # 闹钟打气词 → 流式
      story_telling: "streaming"        # 讲故事 → 流式
      article_reading: "streaming"      # 文章阅读 → 流式
      long_content: "streaming"         # 长内容 → 流式
      wake_response: "non_streaming"    # 唤醒回复 → 非流式
      system_prompt: "non_streaming"    # 系统提示 → 非流式
      music_control: "non_streaming"    # 音乐控制 → 非流式

    # 降级配置
    fallback_to_piper: true             # 千问失败时降级到 Piper

    # 失败重试配置
    max_retries: 2                      # 千问 TTS 失败重试次数
    retry_delay: 1.0                    # 重试延迟（秒）

    # 性能监控
    enable_monitoring: true             # 是否启用性能监控
    log_decision: true                  # 是否记录引擎切换日志

    # ========================================
    # 缓存配置 [v2.2 新增]
    # ========================================
    cache:
      enabled: true                     # 是否启用缓存
      warmup_on_startup: true           # 启动时预热常用短语
      cache_dir: "./data/tts_cache"     # 缓存目录
      max_cache_age_days: 30            # 缓存最大保留天数（0=永久）

      # 预热短语列表（可选，默认从配置自动提取）
      # 留空则自动从 feedback.tts.messages、retry_prompts 等提取
      warmup_phrases: []                # 自定义预热短语列表
```

---

## 实现架构

### 模块结构

```
src/
└── tts/
    ├── __init__.py
    ├── engine.py                   # TTS 抽象接口
    ├── piper_engine.py             # Piper 本地 TTS（已有）
    ├── qwen_engine.py              # 千问非流式 TTS（新增）
    ├── qwen_realtime_engine.py     # 千问流式 TTS（新增）
    ├── hybrid_qwen_engine.py       # 混合引擎（新增）
    ├── cached_engine.py            # 缓存引擎（新增）
    └── text_preprocessor.py        # 文本预处理（新增）
```

### 核心类设计

#### 1. TTSEngine 基类接口（已有）

```python
from abc import ABC, abstractmethod
from typing import Optional
import numpy as np

class TTSEngine(ABC):
    """TTS 引擎抽象接口"""

    @abstractmethod
    def synthesize(self, text: str) -> np.ndarray:
        """
        合成语音

        Args:
            text: 输入文本

        Returns:
            np.ndarray: 音频数据 (int16, 单声道)
        """
        pass

    @abstractmethod
    def get_sample_rate(self) -> int:
        """获取采样率"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        pass
```

#### 2. 千问 TTS 引擎（新增）

```python
"""
阿里云千问 TTS 引擎（远程）
Qwen TTS Engine (Remote)
"""
import logging
import requests
import numpy as np
import base64
import io
from typing import Optional
from .base import TTSEngine

logger = logging.getLogger(__name__)


class QwenTTSEngine(TTSEngine):
    """阿里云千问 TTS 引擎"""

    def __init__(self, config: dict):
        """
        初始化千问 TTS 引擎

        Args:
            config: 配置字典
        """
        self._config = config
        self._provider = config.get("provider", "dashscope")

        # Dashscope 配置
        if self._provider == "dashscope":
            dashscope_config = config.get("dashscope", {})
            self._api_key = dashscope_config.get("api_key")
            self._endpoint = dashscope_config.get(
                "endpoint",
                "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/generation"
            )
            self._model = dashscope_config.get("model", "qwen3-tts-flash")
            self._format = dashscope_config.get("format", "mp3")
            self._sample_rate = dashscope_config.get("sample_rate", 24000)
            self._volume = dashscope_config.get("volume", 50)
            self._voice = dashscope_config.get("voice", "zhixiaobai")
            self._rate = dashscope_config.get("rate", 1.0)
            self._pitch = dashscope_config.get("pitch", 1.0)
            self._timeout = dashscope_config.get("timeout", 30)
            self._retry = dashscope_config.get("retry", 2)

        # OpenAI 配置（备选）
        elif self._provider == "openai":
            openai_config = config.get("openai", {})
            self._api_key = openai_config.get("api_key")
            self._endpoint = openai_config.get(
                "endpoint",
                "https://api.openai.com/v1/audio/speech"
            )
            self._model = openai_config.get("model", "tts-1")
            self._voice = openai_config.get("voice", "alloy")
            self._timeout = openai_config.get("timeout", 30)

        logger.info(f"千问 TTS 引擎初始化完成: {self._provider}")

    def synthesize(self, text: str) -> np.ndarray:
        """
        合成语音

        Args:
            text: 输入文本

        Returns:
            np.ndarray: 音频数据 (int16, 单声道, 24000Hz)
        """
        if self._provider == "dashscope":
            return self._synthesize_dashscope(text)
        elif self._provider == "openai":
            return self._synthesize_openai(text)
        else:
            raise ValueError(f"不支持的 TTS 提供商: {self._provider}")

    def _synthesize_dashscope(self, text: str) -> np.ndarray:
        """使用 Dashscope API 合成语音"""
        import os

        # 构建请求
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self._model,
            "input": {
                "text": text
            },
            "parameters": {
                "text_type": "PlainText",
                "sample_rate": self._sample_rate,
                "format": self._format,
                "volume": self._volume,
                "rate": self._rate,
                "pitch": self._pitch,
                "voice": self._voice
            }
        }

        # 发送请求（带重试）
        for attempt in range(self._retry + 1):
            try:
                logger.debug(f"千问 TTS 请求 (尝试 {attempt + 1}/{self._retry + 1})")

                response = requests.post(
                    self._endpoint,
                    headers=headers,
                    json=payload,
                    timeout=self._timeout
                )

                response.raise_for_status()
                result = response.json()

                # 检查响应状态
                if result.get("output", {}).get("task_status") == "SUCCESS":
                    # 获取音频数据
                    audio_b64 = result["output"]["audio"]
                    audio_bytes = base64.b64decode(audio_b64)

                    # 转换为 numpy array
                    return self._decode_audio(audio_bytes, self._format)
                else:
                    error_msg = result.get("output", {}).get("message", "未知错误")
                    raise Exception(f"TTS 失败: {error_msg}")

            except requests.exceptions.Timeout:
                logger.warning(f"千问 TTS 请求超时 (尝试 {attempt + 1})")
                if attempt < self._retry:
                    continue
                else:
                    raise Exception(f"千问 TTS 请求超时（{self._timeout}秒）")

            except requests.exceptions.ConnectionError as e:
                logger.warning(f"千问 TTS 网络错误: {e}")
                if attempt < self._retry:
                    continue
                else:
                    raise Exception(f"千问 TTS 网络连接失败: {e}")

            except Exception as e:
                logger.error(f"千问 TTS 请求失败: {e}")
                raise

    def _synthesize_openai(self, text: str) -> np.ndarray:
        """使用 OpenAI API 合成语音"""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self._model,
            "input": text,
            "voice": self._voice,
            "response_format": "mp3"
        }

        response = requests.post(
            self._endpoint,
            headers=headers,
            json=payload,
            timeout=self._timeout
        )

        response.raise_for_status()
        audio_bytes = response.content

        # 转换为 numpy array
        return self._decode_audio(audio_bytes, "mp3")

    def _decode_audio(self, audio_bytes: bytes, format: str) -> np.ndarray:
        """
        解码音频数据

        Args:
            audio_bytes: 音频字节流
            format: 音频格式 (mp3, wav)

        Returns:
            np.ndarray: 音频数据 (int16, 单声道)
        """
        import tempfile
        import os
        from pydub import AudioSegment
        from pydub.utils import make_chunks

        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as f:
            temp_path = f.name
            f.write(audio_bytes)

        try:
            # 使用 pydub 加载音频
            audio = AudioSegment.from_file(temp_path, format=format)

            # 转换为目标格式
            audio = audio.set_frame_rate(self._sample_rate)
            audio = audio.set_channels(1)
            audio = audio.set_sample_width(2)  # 16-bit

            # 转换为 numpy array
            samples = np.array(audio.get_array_of_samples(), dtype=np.int16)

            return samples

        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def get_sample_rate(self) -> int:
        """获取采样率"""
        return self._sample_rate

    def is_available(self) -> bool:
        """
        检查千问 TTS 是否可用

        Returns:
            bool: 是否可用
        """
        if not self._api_key:
            logger.warning("千问 TTS API key 未配置")
            return False

        # 简单检测网络连通性
        try:
            response = requests.get(
                "https://dashscope.aliyuncs.com",
                timeout=5
            )
            return True
        except:
            logger.warning("千问 TTS 网络不可达")
            return False
```

#### 3. 混合 TTS 引擎（新增）

```python
"""
混合 TTS 引擎（本地 Piper + 远程千问 TTS）
Hybrid TTS Engine (Piper + Qwen)
"""
import logging
import time
import numpy as np
from typing import Optional, Literal
from .base import TTSEngine
from .piper_engine import PiperTTSEngine
from .qwen_engine import QwenTTSEngine

logger = logging.getLogger(__name__)


class HybridTTSEngine(TTSEngine):
    """混合 TTS 引擎（智能路由）"""

    def __init__(self, config: dict):
        """
        初始化混合 TTS 引擎

        Args:
            config: 配置字典
        """
        self._config = config
        self._mode = config.get("mode", "hybrid")

        # 初始化 Piper 引擎
        piper_config = config.get("piper", {})
        if piper_config.get("enabled", True):
            try:
                self._piper_engine = PiperTTSEngine(**piper_config)
                self._piper_available = True
                logger.info("✅ Piper TTS 引擎已加载")
            except Exception as e:
                logger.error(f"❌ Piper TTS 加载失败: {e}")
                self._piper_engine = None
                self._piper_available = False
        else:
            self._piper_engine = None
            self._piper_available = False

        # 初始化千问引擎
        qwen_config = config.get("qwen", {})
        if qwen_config.get("enabled", True):
            try:
                self._qwen_engine = QwenTTSEngine(qwen_config)
                self._qwen_available = self._qwen_engine.is_available()
                if self._qwen_available:
                    logger.info("✅ 千问 TTS 引擎已加载")
                else:
                    logger.warning("⚠️ 千问 TTS 不可用（网络/API key 问题）")
            except Exception as e:
                logger.error(f"❌ 千问 TTS 加载失败: {e}")
                self._qwen_engine = None
                self._qwen_available = False
        else:
            self._qwen_engine = None
            self._qwen_available = False

        # 混合策略配置
        hybrid_config = config.get("hybrid", {})
        self._short_text_threshold = hybrid_config.get("short_text_threshold", 50)
        self._scenario_mapping = hybrid_config.get("scenario_mapping", {})
        self._fallback_to_piper = hybrid_config.get("fallback_to_piper", True)
        self._log_decision = hybrid_config.get("log_decision", True)

        # 网络检测
        self._check_network = hybrid_config.get("check_network", True)
        self._last_network_check = 0
        self._network_available = False
        self._network_check_interval = hybrid_config.get("network_check_interval", 60)

        logger.info(f"混合 TTS 引擎初始化完成 (mode={self._mode})")
        logger.info(f"  Piper: {'✅' if self._piper_available else '❌'}")
        logger.info(f"  千问: {'✅' if self._qwen_available else '❌'}")

    def synthesize(
        self,
        text: str,
        scenario: str = "default"
    ) -> np.ndarray:
        """
        合成语音（智能路由）

        Args:
            text: 输入文本
            scenario: 场景类型 (wake_response, system_prompt, llm_reply, etc.)

        Returns:
            np.ndarray: 音频数据 (int16, 单声道, 采样率根据引擎而定)
        """
        # 决策使用哪个引擎
        engine = self._route(text, scenario)

        if engine == "piper":
            return self._synthesize_piper(text, scenario)
        elif engine == "qwen":
            return self._synthesize_qwen(text, scenario)
        else:
            raise Exception(f"没有可用的 TTS 引擎 (route={engine})")

    def _route(
        self,
        text: str,
        scenario: str
    ) -> Literal["piper", "qwen", "none"]:
        """
        路由决策：选择使用哪个 TTS 引擎

        Args:
            text: 输入文本
            scenario: 场景类型

        Returns:
            str: "piper" | "qwen" | "none"
        """
        # 1. 检查是否有可用引擎
        if not self._piper_available and not self._qwen_available:
            logger.error("没有可用的 TTS 引擎")
            return "none"

        # 2. 模式锁定
        if self._mode == "piper":
            return "piper" if self._piper_available else "none"
        elif self._mode == "qwen":
            return "qwen" if self._qwen_available else "none"

        # 3. 混合模式：智能路由
        # 3.1 检查网络状态
        if self._check_network:
            self._update_network_status()
            if not self._network_available:
                if self._log_decision:
                    logger.debug("网络不可用，使用 Piper")
                return "piper" if self._piper_available else "none"

        # 3.2 场景类型映射
        mapped_engine = self._scenario_mapping.get(scenario)
        if mapped_engine:
            if mapped_engine == "piper" and self._piper_available:
                if self._log_decision:
                    logger.debug(f"场景映射: {scenario} → Piper")
                return "piper"
            elif mapped_engine == "qwen" and self._qwen_available:
                if self._log_decision:
                    logger.debug(f"场景映射: {scenario} → 千问")
                return "qwen"

        # 3.3 文本长度判断
        text_length = len(text)
        if text_length <= self._short_text_threshold:
            if self._log_decision:
                logger.debug(f"文本长度 {text_length} <= {self._short_text_threshold}，使用 Piper")
            return "piper" if self._piper_available else "qwen"
        else:
            if self._log_decision:
                logger.debug(f"文本长度 {text_length} > {self._short_text_threshold}，使用千问")
            return "qwen" if self._qwen_available else "piper"

    def _synthesize_piper(self, text: str, scenario: str) -> np.ndarray:
        """使用 Piper 合成语音"""
        if not self._piper_available:
            raise Exception("Piper 引擎不可用")

        if self._log_decision:
            logger.info(f"[Piper TTS] 场景={scenario}, 文本={text[:30]}...")

        try:
            return self._piper_engine.synthesize(text)
        except Exception as e:
            logger.error(f"Piper 合成失败: {e}")
            # 尝试降级到千问
            if self._qwen_available and self._fallback_to_piper:
                logger.info("降级到千问 TTS")
                return self._synthesize_qwen(text, scenario)
            raise

    def _synthesize_qwen(self, text: str, scenario: str) -> np.ndarray:
        """使用千问合成语音"""
        if not self._qwen_available:
            raise Exception("千问引擎不可用")

        if self._log_decision:
            logger.info(f"[千问 TTS] 场景={scenario}, 文本={text[:30]}...")

        try:
            return self._qwen_engine.synthesize(text)
        except Exception as e:
            logger.error(f"千问合成失败: {e}")
            # 尝试降级到 Piper
            if self._piper_available and self._fallback_to_piper:
                logger.info("降级到 Piper TTS")
                return self._synthesize_piper(text, scenario)
            raise

    def _update_network_status(self) -> None:
        """更新网络状态"""
        current_time = time.time()

        # 如果距离上次检查时间不足间隔，跳过
        if current_time - self._last_network_check < self._network_check_interval:
            return

        # 执行网络检查
        self._last_network_check = current_time
        self._network_available = self._qwen_engine.is_available()

        if self._network_available:
            logger.debug("网络可用")
        else:
            logger.warning("网络不可用")

    def get_sample_rate(self) -> int:
        """
        获取采样率

        注意：混合模式下采样率不固定，取决于使用的引擎
        Piper: 22050Hz, 千问: 24000Hz
        """
        # 优先返回 Piper 采样率（更常用）
        if self._piper_available:
            return self._piper_engine.get_sample_rate()
        elif self._qwen_available:
            return self._qwen_engine.get_sample_rate()
        else:
            return 22050  # 默认值

    def is_available(self) -> bool:
        """检查是否有可用的 TTS 引擎"""
        return self._piper_available or self._qwen_available

    def get_engine_status(self) -> dict:
        """
        获取引擎状态

        Returns:
            dict: 引擎状态信息
        """
        return {
            "mode": self._mode,
            "piper_available": self._piper_available,
            "qwen_available": self._qwen_available,
            "network_available": self._network_available,
            "short_text_threshold": self._short_text_threshold
        }
```

#### 4. 文本预处理器（新增）

```python
"""
文本预处理工具
Text Preprocessing Utilities
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)


class TextPreprocessor:
    """文本预处理器"""

    def __init__(self, config: dict):
        """
        初始化预处理器

        Args:
            config: 配置字典
        """
        self._config = config
        self._remove_emoticons = config.get("remove_emoticons", False)
        self._normalize_numbers = config.get("normalize_numbers", True)
        self._split_long_text = config.get("split_long_text", True)
        self._max_segment_length = config.get("max_segment_length", 500)

    def preprocess(self, text: str) -> str:
        """
        预处理文本

        Args:
            text: 原始文本

        Returns:
            str: 处理后的文本
        """
        # 移除表情符号
        if self._remove_emoticons:
            text = self._remove_emoticon(text)

        # 数字转文本
        if self._normalize_numbers:
            text = self._normalize_digit(text)

        # 清理多余空白
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def split(self, text: str) -> List[str]:
        """
        分割长文本

        Args:
            text: 输入文本

        Returns:
            List[str]: 文本段落
        """
        if not self._split_long_text:
            return [text]

        if len(text) <= self._max_segment_length:
            return [text]

        # 按句子分割
        segments = []
        current = ""

        # 按标点符号分割
        for char in text:
            current += char

            if char in ['。', '！', '？', '；', '：']:
                if len(current) >= 10:
                    segments.append(current)
                    current = ""
            elif char in ['，', ',']:
                if len(current) >= self._max_segment_length:
                    segments.append(current)
                    current = ""

        # 添加剩余内容
        if current:
            segments.append(current)

        return segments

    def _remove_emoticon(self, text: str) -> str:
        """移除表情符号"""
        # 简单移除常见表情符号
        emoticon_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        return emoticon_pattern.sub('', text)

    def _normalize_digit(self, text: str) -> str:
        """
        数字转文本

        Args:
            text: 输入文本

        Returns:
            str: 转换后的文本
        """
        # 简单实现：转换常见数字
        digit_map = {
            "0": "零",
            "1": "一",
            "2": "二",
            "3": "三",
            "4": "四",
            "5": "五",
            "6": "六",
            "7": "七",
            "8": "八",
            "9": "九",
            "10": "十"
        }

        # 简单替换单个数字（更复杂的实现需要 CNNUMER 包）
        for digit, chinese in digit_map.items():
            text = text.replace(digit, chinese)

        return text
```

---

## 使用示例

### 引擎模式选择

#### 模式 1：仅使用本地 Piper（原有）
```yaml
tts:
  engine: "piper"
  local:
    model_path: "./models/piper/zh_CN-huayan-medium.onnx"
```

#### 模式 2：混合模式 - 本地主机（原有）
```yaml
tts:
  engine: "hybrid"
  remote:
    server_ip: "192.168.2.141"    # GPT-SoVITS 主机
    port: 9880
  local:
    model_path: "./models/piper/zh_CN-huayan-medium.onnx"
```

#### 模式 3：仅使用千问 TTS [v2.2 新增]
```yaml
tts:
  engine: "remote-qwen"
  qwen:
    enabled: true
    dashscope:
      api_key: "${DASHSCOPE_API_KEY}"
      model: "qwen3-tts-flash"
      voice: "zhixiaobai"
  # remote-qwen 也支持缓存
  hybrid_qwen:
    cache:
      enabled: true               # 启用缓存（推荐）
      cache_dir: "./data/tts_cache"
```

#### 模式 4：混合模式 - Piper + 千问 [v2.2 新增，推荐]
```yaml
tts:
  engine: "hybrid-qwen"
  qwen:
    enabled: true
  hybrid_qwen:
    fallback_to_piper: true       # 千问失败时降级到 Piper
    max_retries: 2                # 失败重试次数
```

**逻辑**：
- 所有文本优先使用千问 TTS（质量好）
- 千问 TTS 失败时（网络/欠费）自动降级到 Piper
- 无需区分长短文本

---

### 状态机集成示例

```python
# 在状态机初始化时（引擎选择由 config 决定）
from src.tts import create_tts_engine

class StateMachine:
    def __init__(self, config):
        # 根据 config.tts.engine 自动创建引擎
        tts_config = config.get("tts", {})
        self._tts_engine = create_tts_engine(tts_config)

        # 反馈播放器
        self._feedback_player = TTSFeedbackPlayer(
            tts_engine=self._tts_engine,
            ...
        )

    def _play_tts(self, text: str, scenario: str = "default") -> None:
        """
        播放 TTS（引擎会根据 scenario 自动选择）

        Args:
            text: 文本内容
            scenario: 场景类型
        """
        audio_data = self._tts_engine.synthesize(text, scenario=scenario)
        self._feedback_player.play_audio(audio_data)

    # 使用示例
    def _process_user_input(self):
        # 唤醒回复（短文本 → Piper）
        self._play_tts("我在这里", scenario="wake_response")

        # LLM 回复（根据长度自动选择）
        llm_reply = self._llm_engine.chat(user_text)
        if len(llm_reply) > 50:
            self._play_tts(llm_reply, scenario="llm_reply_long")  # 千问 TTS
        else:
            self._play_tts(llm_reply, scenario="llm_reply_short")  # Piper

        # 闹钟打气词（长文本 → 千问 TTS）
        cheerword = self._generate_cheerword(theme="运动")
        self._play_tts(cheerword, scenario="alarm_cheerword")
```

---

### 工厂函数示例

```python
# src/tts/__init__.py
def create_tts_engine(config: dict) -> TTSEngine:
    """
    根据配置创建 TTS 引擎

    Args:
        config: TTS 配置字典

    Returns:
        TTSEngine: TTS 引擎实例
    """
    engine_type = config.get("engine", "piper")

    # 模式 1: 仅 Piper
    if engine_type == "piper":
        from .piper_engine import PiperTTSEngine
        local_config = config.get("local", {})
        return PiperTTSEngine(**local_config)

    # 模式 2: 仅远程主机 GPT-SoVITS
    elif engine_type == "remote":
        from .remote_engine import RemoteTTSEngine
        remote_config = config.get("remote", {})
        return RemoteTTSEngine(**remote_config)

    # 模式 3: 混合 - 本地主机
    elif engine_type == "hybrid":
        from .hybrid_engine import HybridTTSEngine
        local_config = config.get("local", {})
        remote_config = config.get("remote", {})

        local_engine = PiperTTSEngine(**local_config)
        remote_engine = RemoteTTSEngine(**remote_config)

        return HybridTTSEngine(
            local_engine=local_engine,
            remote_engine=remote_engine,
            config=config
        )

    # 模式 4: 仅千问 TTS [v2.2 新增]
    elif engine_type == "remote-qwen":
        from .qwen_engine import QwenTTSEngine
        qwen_config = config.get("qwen", {})
        return QwenTTSEngine(qwen_config)

    # 模式 5: 混合 - Piper + 千问（流式/非流式智能选择） [v2.2 新增]
    elif engine_type == "hybrid-qwen":
        from .hybrid_qwen_engine import HybridQwenTTSEngine
        from .qwen_realtime_engine import QwenRealtimeEngine

        local_config = config.get("local", {})
        qwen_config = config.get("qwen", {})
        qwen_realtime_config = config.get("qwen_realtime", {})

        local_engine = PiperTTSEngine(**local_config)
        remote_engine = QwenTTSEngine(qwen_config)
        realtime_engine = QwenRealtimeEngine(qwen_realtime_config)

        return HybridQwenTTSEngine(
            local_engine=local_engine,
            remote_engine=remote_engine,
            realtime_engine=realtime_engine,
            config=config
        )

    else:
        raise ValueError(f"不支持的引擎类型: {engine_type}")
```

---

### 场景类型定义

```python
# 标准场景类型
SCENARIO_WAKE_RESPONSE = "wake_response"        # 唤醒回复
SCENARIO_SYSTEM_PROMPT = "system_prompt"        # 系统提示
SCENARIO_ALARM_RINGTONE = "alarm_ringtone"      # 闹钟铃声
SCENARIO_ALARM_CHEERWORD = "alarm_cheerword"    # 闹钟打气词
SCENARIO_LLM_REPLY_SHORT = "llm_reply_short"    # LLM 短回复
SCENARIO_LLM_REPLY_LONG = "llm_reply_long"      # LLM 长回复
SCENARIO_MUSIC_CONTROL = "music_control"        # 音乐控制反馈
SCENARIO_ERROR_MESSAGE = "error_message"        # 错误提示
SCENARIO_DEFAULT = "default"                    # 默认
```

---

## 性能对比

### Piper vs 千问 TTS Flash (流式/非流式)

| 指标 | Piper (本地) | 千问 TTS Flash (非流式) | 千问 TTS Flash (流式) |
|------|-------------|---------------------|---------------------|
| **首字延迟** | 5-50ms | 200-500ms | ~97ms |
| **质量** | 中等 | 高（接近真人） | 高（接近真人） |
| **成本** | 免费 | ¥0.0006/千字符 | ¥0.0006/千字符 |
| **网络** | 不需要 | 需要 | 需要 |
| **资源占用** | CPU ~10% | 无本地资源 | 无本地资源 |
| **适用场景** | 短文本、快速响应 | 中短文本 | 长文本（≥100字） |

### 混合模式优势

1. **性能优化**:
   - 唤醒回复: 5-50ms → 用户感知更流畅
   - LLM 长回复: ~97ms 首字延迟 → 实时感更强
   - 故事朗读: 流式播放 → 无需等待完整生成

2. **成本控制**:
   - 短文本用千问 TTS（快速、便宜）
   - 长文本用千问流式（体验优先）
   - 失败时降级到 Piper（免费备用）

3. **可靠性**:
   - 网络失败自动降级到 Piper
   - 流式失败重试非流式
   - 多层容错机制

---

## 依赖安装

### 新增依赖

```bash
# 千问 TTS SDK（如果需要）
pip install dashscope

# 音频处理（用于解码 mp3）
pip install pydub

# WebSocket 支持（流式 TTS）
pip install websockets

# 音频编解码器
sudo apt-get install ffmpeg
```

### 完整依赖列表

```txt
# requirements.txt / requirements-arm64.txt

# 已有依赖
numpy>=1.21.0,<2.0.0
onnxruntime>=1.16.0
piper-tts>=1.4.0
pyaudio>=0.2.12

# 新增依赖
dashscope>=1.14.0           # 千问 API
pydub>=0.25.0               # 音频处理
websockets>=12.0            # WebSocket 支持（流式 TTS）
requests>=2.28.0            # HTTP 请求（通常已有）
```

---

## 测试计划

### 单元测试

```bash
# 1. 千问 TTS 引擎测试
pytest tests/unit/test_qwen_tts.py -v

# 2. 混合 TTS 引擎测试
pytest tests/unit/test_hybrid_tts.py -v

# 3. 文本预处理测试
pytest tests/unit/test_text_preprocessor.py -v
```

### 手动测试

```bash
# 1. 千问 TTS 基础测试
python tests/manual/test_qwen_tts.py

# 2. 混合模式路由测试
python tests/manual/test_hybrid_tts_routing.py

# 3. 集成测试（完整流程）
python tests/manual/test_tts_integration.py
```

### 测试用例

```python
# tests/manual/test_qwen_tts.py
import logging
from src.tts.qwen_engine import QwenTTSEngine

logging.basicConfig(level=logging.INFO)

config = {
    "provider": "dashscope",
    "dashscope": {
        "api_key": "your-api-key",
        "model": "qwen3-tts-flash",
        "voice": "zhixiaobai"
    }
}

engine = QwenTTSEngine(config)

# 测试合成
text = "你好，这是千问 TTS 测试"
audio = engine.synthesize(text)

print(f"音频数据: {len(audio)} 采样点")
print(f"采样率: {engine.get_sample_rate()} Hz")
print(f"可用性: {engine.is_available()}")
```

---

## 故障排查

### 千问 TTS 不可用

**问题**: `千问 TTS 不可用（网络/API key 问题）`

**解决方案**:
1. 检查 API key 是否配置:
   ```bash
   echo $DASHSCOPE_API_KEY
   ```
2. 测试网络连通性:
   ```bash
   ping dashscope.aliyuncs.com
   ```
3. 验证 API key 有效性:
   ```python
   import dashscope
   print(dashscope.api_key)
   ```

### mp3 解码失败

**问题**: `pydub 无法解码 mp3`

**解决方案**:
```bash
# 安装 ffmpeg
sudo apt-get update
sudo apt-get install ffmpeg

# 验证安装
ffmpeg -version
```

### 混合模式降级失败

**问题**: 降级到 Piper 时也失败

**解决方案**:
1. 检查 Piper 引擎状态:
   ```python
   status = tts_engine.get_engine_status()
   print(status)
   ```
2. 确保至少有一个引擎可用:
   ```python
   if not status["piper_available"] and not status["qwen_available"]:
       logger.error("没有可用的 TTS 引擎")
   ```

---

## 配置示例

### 场景 1：仅使用本地 Piper

```yaml
tts:
  engine: "piper"
  local:
    model_path: "./models/piper/zh_CN-huayan-medium.onnx"
```

### 场景 2：混合模式 - 本地主机（原有）

```yaml
tts:
  engine: "hybrid"
  remote:
    server_ip: "192.168.2.141"    # GPT-SoVITS 主机 IP
    port: 9880
  local:
    model_path: "./models/piper/zh_CN-huayan-medium.onnx"
```

### 场景 3：仅使用千问 TTS [v2.2 新增]

```yaml
tts:
  engine: "remote-qwen"
  qwen:
    enabled: true
    dashscope:
      api_key: "${DASHSCOPE_API_KEY}"
      model: "qwen3-tts-flash"
      voice: "zhixiaobai"
      rate: 1.0
```

### 场景 4：混合模式 - Piper + 千问 [v2.2 新增，推荐]

**说明**：所有文本优先使用千问 TTS，失败时降级到 Piper

```yaml
tts:
  engine: "hybrid-qwen"
  local:
    model_path: "./models/piper/zh_CN-huayan-medium.onnx"
  qwen:
    enabled: true
    dashscope:
      api_key: "${DASHSCOPE_API_KEY}"
      model: "qwen3-tts-flash"
      voice: "zhixiaobai"
  hybrid_qwen:
    fallback_to_piper: true       # 千问失败时降级到 Piper
    max_retries: 2                # 失败重试次数
    check_network: true           # 定期检测网络状态
```
tts:
  mode: "hybrid"
  piper:
    enabled: true
  qwen:
    enabled: true
  hybrid:
    short_text_threshold: 50
    scenario_mapping:
      wake_response: "piper"
      alarm_cheerword: "qwen"
      llm_reply_long: "qwen"
```

---

## 成本估算

### 千问 TTS Flash 定价

（实际价格以阿里云官方为准）

| 模型 | 计费方式 | 预估成本 |
|------|---------|---------|
| qwen3-tts-flash | 按字符数计费 | ¥0.0006/千字符 |

### 月度成本估算

假设每天使用场景：
- 唤醒回复: 50次 × 5字符 = 250字符（用 Piper）
- LLM 长回复: 20次 × 100字符 = 2000字符（用千问 TTS）
- 闹钟打气词: 2次 × 200字符 = 400字符（用千问 TTS）

**日成本**: (2400字符 / 1000) × ¥0.0006 = ¥0.00144
**月成本**: ¥0.00144 × 30 = **¥0.043**

**结论**: 千问 TTS Flash 成本极低，适合日常使用。

---

## 未来扩展

### 1. 更多 TTS 引擎
- OpenAI TTS (tts-1, tts-1-hd)
- Azure Cognitive Services
- Google Cloud TTS
- 讯飞语音

### 2. 智能路由优化
- 基于用户反馈的 A/B 测试
- 动态调整短文本阈值
- 学习用户偏好

### 3. 语音风格定制
- 根据场景自动选择发音人
- 情感感知 TTS（开心、悲伤、愤怒）
- 多角色语音（对话场景）

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v2.2 | 2026-02-03 | 新增千问 TTS 集成，新增 hybrid-qwen 和 remote-qwen 引擎模式 |
| v2.1 | - | 原有混合模式（本地 Piper + 远程主机 GPT-SoVITS） |
| v2.0 | - | 基础 TTS 功能 |

---

## 参考资源

- **千问 TTS 文档**: https://help.aliyun.com/zh/dashscope/developer-reference/audio-acquisition
- **Piper TTS**: https://github.com/rhasspy/piper
- **Dashscope SDK**: https://github.com/aliyun/dashscope
- **pydub 文档**: https://github.com/jiaaro/pydub

---

## 总结

v2.2 版本引入了**千问 TTS 集成 + 流式支持 + 缓存系统**，通过智能选择流式/非流式 API + 持久化缓存 + Piper 降级方案，实现了：
- ✅ 提升质量（千问 TTS 接近真人，远超 Piper）
- ✅ 快速响应（流式首字延迟 ~97ms，非流式 200-500ms）
- ✅ 缓存加速（常用短语 <1ms，提升 5-500 倍）
- ✅ 降低成本（千问 TTS Flash 极便宜，¥0.0006/千字符）
- ✅ 提高可靠性（失败时自动降级到 Piper）
- ✅ 持久化缓存（项目重启后缓存依然有效）

**向后兼容性**:
- ✅ 完全保留原有配置（hybrid, remote, piper）
- ✅ 原有混合模式（本地主机）继续工作
- ✅ 仅新增配置段，不影响现有功能

**5种引擎模式**:
1. **piper** - 仅本地 Piper（最快，完全离线）
2. **remote** - 仅远程主机 GPT-SoVITS（高质量）
3. **hybrid** - 本地 Piper + 远程主机（原有混合模式）
4. **remote-qwen** - 仅千问 TTS（非流式）+ 缓存 [v2.2 新增]
5. **hybrid-qwen** - 千问流式/非流式智能选择 + 缓存 + Piper 降级 [v2.2 新增，推荐]

**注意**：所有千问相关引擎模式（remote-qwen、hybrid-qwen）都支持缓存功能，通过 `hybrid_qwen.cache.enabled` 配置。

**hybrid-qwen 逻辑**：
- **所有文本优先使用千问 TTS**（无需区分长短文本）
- **短文本（<100字）**：使用非流式 HTTP API（简单可靠）
- **长文本（≥100字）**：使用流式 WebSocket API（首字延迟 ~97ms）
- **常用短语**：自动从缓存读取（<1ms 响应）
- **场景配置**：可指定特定场景强制使用流式/非流式
- **失败降级**：千问 TTS 失败时自动降级到 Piper
- **网络检测**：定期检测网络状态，动态调整

**缓存系统优势**：
- 唤醒回复从 5-250ms 降至 <1ms
- 系统提示即时响应，无需等待 API
- 持久化存储，重启后依然有效
- 自动预热，启动时生成常用短语
- 智能提取，从配置自动获取需缓存的短语

**流式 TTS 优势**：
- 长文本首字延迟从 500ms 降至 97ms
- 实时边生成边播放，无需等待完整音频
- 适合故事朗读、LLM 长回复等场景

**适用场景**:
- 语音助手（体验质量优先 → hybrid-qwen）
- 智能家居（响应速度 + 质量平衡 → hybrid-qwen）
- 教育场景（长朗读内容 → hybrid-qwen 流式）
- 陪伴机器人（情感化语音 → hybrid-qwen）
- 离线环境（仅 Piper → piper）
