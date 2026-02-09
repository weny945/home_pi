# 第一阶段 1.1 开发文档：唤醒词检测 + Piper TTS 语音回复

**版本**: 1.1
**日期**: 2026-01-22
**状态**: ✅ 完成

---

## 📋 阶段目标

在第一阶段 1.0（唤醒词检测 + 蜂鸣声反馈）的基础上，升级为**Piper TTS 语音回复**功能：

```
ReSpeaker 4-Mic → OpenWakeWord → 唤醒成功 → Piper TTS 语音回复
```

### 核心功能
1. ✅ **ReSpeaker 音频输入** - 从麦克风阵列获取波束成形音频流（继承自 1.0）
2. ✅ **唤醒词检测** - 使用 OpenWakeWord 实时检测唤醒词（继承自 1.0）
3. ✅ **Piper TTS 语音回复** - 使用 Piper TTS 播放高质量中文语音（新增）

### 与 1.0 的区别

| 特性 | v1.0 | v1.1 |
|------|------|------|
| **唤醒反馈** | 蜂鸣声 / 音频文件 | Piper TTS 语音 |
| **反馈质量** | 简单蜂鸣声 | 高质量中文语音 |
| **离线支持** | ✅ | ✅ |
| **模型大小** | - | ~63MB (onnx) |
| **合成延迟** | < 0.2s | < 0.5s (≤5字) |
| **音色** | 单一 | 多种中文音色（取决于模型）|

---

## 🎯 状态机设计（v1.1）

```
┌─────────┐
│  IDLE   │ ◄────────────────┐
└────┬────┘                  │
     │ 检测到唤醒词          │
     ▼                       │
┌─────────┐                  │
│ WAKEUP  │                  │
│ (播放   │                  │
│  Piper  │                  │
│  TTS)   │                  │
└────┬────┘                  │
     │ 播放完成              │
     └──────────────────────┘
```

### 状态定义（与 1.0 相同）

| 状态 | 描述 | 超时 | 转换条件 |
|------|------|------|----------|
| **IDLE** | 监听唤醒词，持续采集音频 | 无 | 检测到唤醒词 → WAKEUP |
| **WAKEUP** | 播放 Piper TTS 语音回复 | 5秒 | 播放完成 → IDLE |

---

## 📁 模块结构

### 新增模块

```
src/
├── tts/                       # TTS 模块（新增）
│   ├── __init__.py
│   ├── engine.py              # TTS 引擎抽象层
│   └── piper_engine.py        # Piper TTS 实现
│
└── feedback/                  # 反馈模块（扩展）
    ├── __init__.py            # 新增导出 TTSFeedbackPlayer
    ├── player.py              # 抽象层（不变）
    ├── audio_feedback.py      # 蜂鸣声反馈（不变）
    └── tts_feedback.py        # Piper TTS 反馈（新增）
```

### 测试文件

```
tests/
├── unit/                      # 单元测试（新增）
│   ├── test_tts.py            # Piper TTS 引擎测试
│   └── test_tts_feedback.py   # TTS 反馈播放器测试
│
└── manual/                    # 集成测试（新增）
    └── test_piper_tts.py      # Piper TTS 集成测试
```

---

## 🔧 技术实现

### 1. Piper TTS 引擎（新增）

**职责**: 提供高质量中文文本转语音功能

**技术选型**:
- **引擎**: Piper TTS
- **模型**: zh_CN-huayan-medium.onnx
- **离线能力**: ✅ 完全离线
- **模型大小**: ~63MB
- **音色**: 中文女声（花燕 medium）
- **采样率**: 22050 Hz

**接口设计**:
```python
class TTSEngine(ABC):
    @abstractmethod
    def synthesize(self, text: str, speaker_id: Optional[int] = None) -> np.ndarray:
        """合成语音，返回 numpy array (22050Hz, 16bit)"""
        pass

    @abstractmethod
    def get_sample_rate(self) -> int:
        """获取采样率 (22050 Hz)"""
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """是否已就绪"""
        pass

    @abstractmethod
    def get_model_info(self) -> dict:
        """获取模型信息"""
        pass
```

**Piper TTS 实现** (`piper_engine.py`):
- 使用 `PiperVoice.load()` 加载 ONNX 模型
- 支持 `SynthesisConfig` 参数调整（语速、噪声等）
- 自动处理配置文件路径（`.onnx.json` 或 `.json`）
- 支持多说话人（通过 `speaker_id` 参数）

**关键方法**:
```python
# 初始化引擎
engine = PiperTTSEngine(
    model_path="./models/piper/zh_CN-huayan-medium.onnx",
    length_scale=1.0,  # 语速
    load_model=True
)

# 合成语音
audio_data = engine.synthesize("你好")

# 调整语速
engine.set_synthesis_config(length_scale=0.8)  # 更快
```

**依赖**:
```python
piper-tts>=1.3.0      # Piper TTS 核心库
onnxruntime>=1.23.0    # ONNX 模型推理
numpy>=1.21.0,<2.0.0   # 音频数据处理
scipy>=1.10.0          # 音频文件保存
```

---

### 2. Piper TTS 反馈播放器（新增）

**职责**: 使用 Piper TTS 播放唤醒回复

**接口设计**:
```python
class TTSFeedbackPlayer(FeedbackPlayer):
    def __init__(
        self,
        messages: List[str],           # 回复消息列表
        model_path: str,                # 模型路径
        length_scale: float = 1.0,      # 语速
        random_message: bool = False,   # 随机选择
        cache_audio: bool = True        # 缓存音频
    ):
        """初始化播放器"""

    def play_wake_feedback(self) -> None:
        """播放唤醒反馈（从消息列表中选择并合成）"""
```

**功能特性**:
- 顺序或随机选择回复消息
- 音频缓存机制（加快响应）
- 支持动态调整语速
- 支持自定义消息列表

**缓存机制**:
- 首次初始化时预加载所有消息音频
- 缓存目录: `./cache/tts_audio/`
- 缓存格式: WAV (16-bit, 22050Hz)
- 缓存命中时直接播放，避免重复合成

---

### 3. 配置管理（更新）

**config.yaml 新增配置**:
```yaml
feedback:
  mode: "tts"  # 新增 TTS 模式

  tts:
    engine: "piper"
    model_path: "./models/piper/zh_CN-huayan-medium.onnx"
    length_scale: 1.0  # 语速控制
    messages:
      - "我在"
      - "请吩咐"
      - "我在听"
      - "您好"
      - "我在这里"
    random_message: false
    cache_audio: true
```

---

## 📊 性能指标

| 指标 | 目标 | 实测 | 状态 |
|------|------|------|------|
| **合成延迟** | < 0.5s | ~0.3s | ✅ |
| **模型加载** | < 3s | ~1.5s | ✅ |
| **内存占用** | < 200MB | ~180MB | ✅ |
| **CPU 占用** | < 50% | ~30% | ✅ |
| **音频质量** | 自然清晰 | 良好 | ✅ |

**测试环境**:
- 硬件: AMD64 (开发机)
- 操作系统: Linux 6.8.0-90-generic
- Python: 3.10.12

---

## 🧪 测试

### 单元测试

**文件**: `tests/unit/test_tts.py`

```bash
pytest tests/unit/test_tts.py -v
```

**测试覆盖**:
- ✅ 引擎初始化
- ✅ 模型加载
- ✅ 语音合成
- ✅ 多文本合成
- ✅ 保存到文件
- ✅ 语速调整
- ✅ 错误处理

**文件**: `tests/unit/test_tts_feedback.py`

```bash
pytest tests/unit/test_tts_feedback.py -v
```

**测试覆盖**:
- ✅ 播放器初始化
- ✅ 消息顺序选择
- ✅ 消息随机选择
- ✅ 消息列表更新
- ✅ 语速调整
- ✅ 播放状态

**测试结果**: ✅ 23 passed

### 集成测试

**文件**: `tests/manual/test_piper_tts.py`

```bash
python tests/manual/test_piper_tts.py
```

**测试项目**:
1. ✅ Piper TTS 引擎测试
2. ✅ TTS 反馈播放器测试
3. ✅ 完整配置集成测试

**测试结果**: ✅ 全部通过

---

## 📦 部署指南

### 开发环境 (AMD64)

```bash
# 1. 安装依赖
pip install piper-tts

# 2. 验证安装
python -c "from piper import PiperVoice; print('✅ Piper TTS 安装成功')"

# 3. 运行测试
python tests/manual/test_piper_tts.py
```

### 生产环境 (ARM64 / 树莓派)

```bash
# 1. 安装依赖
source .venv/bin/activate
pip install piper-tts

# 2. 更新配置
vim config.yaml
# 设置 feedback.mode: "tts"

# 3. 测试
python tests/manual/test_piper_tts.py

# 4. 启动服务
sudo systemctl restart voice-assistant.service
```

---

## 🔧 开发注意事项

### 模型文件位置

模型文件应放置在 `models/piper/` 目录：
```
models/piper/
├── zh_CN-huayan-medium.onnx       # 模型文件 (~63MB)
└── zh_CN-huayan-medium.onnx.json  # 配置文件 (~5KB)
```

### 配置文件路径检测

PiperTTSEngine 会自动检测配置文件：
1. 优先查找 `<model>.onnx.json`
2. 回退到 `<model>.json`

### 语速控制

- `length_scale = 1.0`: 正常语速
- `length_scale < 1.0`: 更快语速（如 0.8）
- `length_scale > 1.0`: 更慢语速（如 1.2）

### 缓存策略

- ✅ 启用缓存: 首次启动慢，后续响应快
- ❌ 禁用缓存: 启动快，每次合成需等待

建议生产环境启用缓存。

### PyTorch 兼容性

Piper TTS 使用 ONNX Runtime，不依赖 PyTorch，更加轻量。

---

## 📝 API 参考

### PiperTTSEngine

```python
from src.tts import PiperTTSEngine

# 初始化
engine = PiperTTSEngine(
    model_path="./models/piper/zh_CN-huayan-medium.onnx",
    length_scale=1.0,
    load_model=True
)

# 合成语音
audio_data = engine.synthesize("你好")

# 保存到文件
engine.synthesize_to_file("你好", "./output.wav")

# 获取模型信息
info = engine.get_model_info()

# 调整语速
engine.set_synthesis_config(length_scale=0.8)
```

### TTSFeedbackPlayer

```python
from src.feedback import TTSFeedbackPlayer

# 初始化
player = TTSFeedbackPlayer(
    messages=["我在", "请吩咐", "我在听"],
    model_path="./models/piper/zh_CN-huayan-medium.onnx",
    cache_audio=True
)

# 播放反馈
player.play_wake_feedback()

# 设置自定义消息
player.set_messages(["你好主人", "有什么可以帮您"])

# 调整语速
player.set_speed(0.9)
```

---

## 🚀 后续优化方向

### v1.2 改进计划

- [ ] 支持更多中文音色模型
- [ ] 支持多说话人（通过 `speaker_id`）
- [ ] 异步音频合成（非阻塞）
- [ ] 流式音频输出（边合成边播放）
- [ ] 音频效果处理（音量、淡入淡出）

### 性能优化

- [ ] 模型量化（减少模型大小）
- [ ] 批量合成（减少重复加载）
- [ ] 音频流式传输

---

## 📚 参考资源

- [Piper TTS GitHub](https://github.com/rhasspy/piper)
- [Piper TTS 文档](https://rhasspy.github.io/piper/)
- [中文 TTS 模型](https://github.com/rhasspy/piper/releases/tag/v1.0.0)

---

## ✅ 完成清单

### 代码实现
- ✅ TTSEngine 抽象接口
- ✅ PiperTTSEngine 实现
- ✅ TTSFeedbackPlayer 实现
- ✅ 配置文件更新
- ✅ main.py 集成

### 测试
- ✅ 单元测试 (11 个)
- ✅ 单元测试 (12 个)
- ✅ 集成测试工具

### 文档
- ✅ 开发文档
- ✅ API 参考
- ✅ 部署指南

### 验证
- ✅ 功能测试通过
- ✅ 性能指标达标
- ✅ 代码质量良好

---

**v1.1 开发完成！** 🎉

版本 1.1.0 已完成开发、测试和文档，可以投入生产使用。
