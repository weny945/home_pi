# 第一阶段 1.2 开发文档：唤醒词检测 + TTS 回复 + 语音识别

**版本**: 1.2
**日期**: 2026-01-22
**状态**: 🚧 开发中

---

## 📋 阶段目标

在第一阶段 1.1（唤醒词检测 + Piper TTS 语音回复）的基础上，添加**语音识别**功能：

```
ReSpeaker 4-Mic → OpenWakeWord → 唤醒成功 → Piper TTS 语音回复
                                              ↓
                                    录音 + VAD 检测
                                              ↓
                                    FunASR 语音识别
                                              ↓
                                    输出识别文本
```

### 核心功能

1. ✅ **ReSpeaker 音频输入** - 从麦克风阵列获取波束成形音频流（继承自 1.1）
2. ✅ **唤醒词检测** - 使用 OpenWakeWord 实时检测唤醒词（继承自 1.1）
3. ✅ **Piper TTS 语音回复** - 播放高质量中文语音回复（继承自 1.1）
4. 🆕 **语音活动检测 (VAD)** - 使用 FunASR 内置 VAD 检测语音段
5. 🆕 **语音识别 (STT)** - 使用 FunASR SenseVoiceSmall 离线识别

### 与 1.1 的区别

| 特性 | v1.1 | v1.2 |
|------|------|------|
| **唤醒反馈** | Piper TTS 语音 | Piper TTS 语音 |
| **语音录制** | ❌ 无 | ✅ VAD 检测自动录音 |
| **语音识别** | ❌ 无 | ✅ FunASR 离线识别 |
| **输出** | 无文本输出 | 识别文本输出 |
| **离线支持** | ✅ | ✅ |
| **模型大小** | ~63MB (Piper) | ~63MB + ~200MB (FunASR) |
| **响应流程** | 唤醒 → 回复 → 结束 | 唤醒 → 回复 → 录音 → 识别 → 输出文本 |

---

## 🎯 状态机设计（v1.2）

### 状态转换图

```
┌──────────┐
│  IDLE    │ ◄──────────────────────────────────┐
└────┬─────┘                                    │
     │ 检测到唤醒词                              │
     ▼                                           │
┌──────────┐                                    │
│ WAKEUP   │                                    │
│ (播放    │                                    │
│  Piper   │                                    │
│  TTS)    │                                    │
└────┬─────┘                                    │
     │ 播放完成                                  │
     ▼                                          │
┌──────────┐  录音超时/静音                      │
│LISTENING │─────────────────────────────────────┘
│ (VAD     │  ↓ 检测到语音结束
│ 录音)    │
└────┬─────┘
     │ VAD 检测到语音结束
     ▼
┌──────────┐
│PROCESSING│
│ (STT     │
│ 识别)   │
└────┬─────┘
     │ 识别完成
     ▼
┌──────────┐
│  IDLE    │  (返回待机，输出文本)
└──────────┘
```

### 状态定义

| 状态 | 描述 | 超时 | 转换条件 |
|------|------|------|----------|
| **IDLE** | 监听唤醒词，持续采集音频 | 无 | 检测到唤醒词 → WAKEUP |
| **WAKEUP** | 播放 Piper TTS 语音回复 | 5秒 | 播放完成 → LISTENING |
| **LISTENING** | VAD 检测录音，监听用户语音 | 10秒 | 语音结束/VAD超时 → PROCESSING |
| **PROCESSING** | FunASR 语音识别 | 5秒 | 识别完成 → IDLE |
| **ERROR** | 错误状态 | - | 返回 IDLE |

---

## 📁 模块结构

### 新增模块

```
src/
├── stt/                           # STT 模块（新增）
│   ├── __init__.py
│   ├── engine.py                  # STT 引擎抽象层
│   └── funasr_engine.py          # FunASR STT 实现
│
└── vad/                          # VAD 模块（新增）
    ├── __init__.py
    ├── detector.py                # VAD 检测器抽象层
    └── funasr_vad.py             # FunASR VAD 实现

src/state_machine/
├── states.py                     # 状态定义（扩展 LISTENING, PROCESSING）
└── machine.py                    # 状态机（扩展新状态处理）
```

### 测试文件

```
tests/
├── unit/                         # 单元测试（新增）
│   ├── test_stt.py              # FunASR STT 引擎测试
│   └── test_vad.py              # FunASR VAD 检测器测试
│
└── manual/                       # 集成测试（新增）
    └── test_phase12_stt.py      # Phase 1.2 完整流程测试
```

---

## 🔧 技术实现

### 1. STT 引擎（新增）

**职责**: 提供离线中文语音识别功能

**技术选型**:
- **引擎**: FunASR
- **模型**: SenseVoiceSmall
- **离线能力**: ✅ 完全离线
- **模型大小**: ~200MB
- **支持语言**: 中英文混合
- **采样率**: 16000 Hz

**接口设计**:
```python
class STTEngine(ABC):
    @abstractmethod
    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """转录音频为文本"""
        pass

    @abstractmethod
    def transcribe_file(self, audio_file: str) -> str:
        """转录音频文件为文本"""
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """引擎是否已就绪"""
        pass
```

**FunASR 实现** (`funasr_engine.py`):
- 使用 `AutoModel` 加载模型
- 支持中英文混合识别
- 自动语言检测
- 支持标点符号恢复

**依赖**:
```python
funasr>=1.0.0          # FunASR 核心库
modelscope>=0.0.0     # 模型下载
```

### 2. VAD 检测器（新增）

**职责**: 检测语音活动，判断用户何时开始和结束说话

**技术选型**:
- **引擎**: FunASR 内置 VAD
- **模型**: fsmn-vad
- **用途**: 自动切分语音段

**接口设计**:
```python
class VADDetector(ABC):
    @abstractmethod
    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        """检测音频块是否包含语音"""
        pass

    @abstractmethod
    def detect_speech_segments(self, audio_data: np.ndarray) -> List[tuple]:
        """检测音频中的语音段"""
            pass
```

**FunASR VAD 实现** (`funasr_vad.py`):
- 使用 FunASR 的 VAD 模型
- 支持流式检测
- 返回语音段时间戳

---

## ⚙️ 配置管理

**config.yaml 新增配置**:
```yaml
stt:
  engine: "funasr"
  model: "iic/SenseVoiceSmall"
  device: "cpu"

vad:
  enabled: true
  model: "fsmn-vad"
  device: "cpu"

listening:
  max_duration: 10      # 最大录音时长（秒）
  silence_threshold: 1.5 # 静音阈值（秒），超过则认为说话结束

processing:
  timeout: 5            # STT 识别超时（秒）
```

---

## 📊 性能指标

| 指标 | 目标 | 说明 |
|------|------|------|
| **STT 准确率** | > 90% | 中文常用语句 |
| **STT 延迟** | < 2s | 从录音结束到输出文本 |
| **VAD 响应** | < 100ms | 语音检测延迟 |
| **模型加载** | < 5s | 首次加载时间 |
| **内存占用** | < 500MB | 包含 STT + VAD |
| **CPU 占用** | < 70% | 识别期间 |

---

## 🧪 测试

### 单元测试

**文件**: `tests/unit/test_stt.py`

```bash
pytest tests/unit/test_stt.py -v
```

**测试覆盖**:
- ✅ STT 引擎初始化
- ✅ 模型加载
- ✅ 音频转录
- ✅ 文件转录
- ✅ 错误处理

**文件**: `tests/unit/test_vad.py`

```bash
pytest tests/unit/test_vad.py -v
```

**测试覆盖**:
- ✅ VAD 检测器初始化
- ✅ 语音检测
- ✅ 语音段检测
- ✅ 流式处理

### 集成测试

**文件**: `tests/manual/test_phase12_stt.py`

```bash
python tests/manual/test_phase12_stt.py
```

**测试项目**:
1. ✅ 唤醒词检测
2. ✅ TTS 语音回复
3. ✅ VAD 录音
4. ✅ STT 语音识别
5. ✅ 完整流程测试

---

## 🚀 实现步骤

### 第 1 步：安装依赖

```bash
# 安装 FunASR
pip install funasr

# 安装 ModelScope
pip install modelscope
```

### 第 2 步：下载模型

```bash
# FunASR 会在首次运行时自动下载模型
# SenseVoiceSmall: ~200MB
# fsmn-vad: ~10MB
```

### 第 3 步：更新配置

```yaml
# config.yaml
stt:
  engine: "funasr"
  model: "iic/SenseVoiceSmall"

vad:
  enabled: true
  model: "fsmn-vad"
```

### 第 4 步：运行测试

```bash
# 测试 STT
python tests/manual/test_phase12_stt.py
```

---

## 📝 API 参考

### FunASRSTTEngine

```python
from src.stt import FunASRSTTEngine

# 初始化
engine = FunASRSTTEngine(
    model_name="iic/SenseVoiceSmall",
    device="cpu",
    load_model=True
)

# 转录音频
text = engine.transcribe(audio_data)

# 转录文件
text = engine.transcribe_file("/path/to/audio.wav")
```

### FunASRVADDetector

```python
from src.vad import FunASRVADDetector

# 初始化
vad = FunASRVADDetector(
    vad_model="fsmn-vad",
    device="cpu",
    load_model=True
)

# 检测语音
is_speech = vad.is_speech(audio_chunk)

# 检测语音段
segments = vad.detect_speech_segments(audio_data)
```

---

## 🔗 后续阶段

### Phase 1.3 计划

- [ ] 添加 LLM 对话生成（千问 API）
- [ ] 完整对话流程：唤醒 → 录音 → STT → LLM → TTS
- [ ] 多轮对话支持
- [ ] 上下文记忆

---

## 📚 参考资源

- [FunASR GitHub](https://github.com/alibaba-damo-academy/FunASR)
- [SenseVoiceSmall 模型](https://github.com/alibaba-damo-academy/SenseVoice)
- [FunASR 文档](https://funasr.readthedocs.io/)

---

## ✅ 完成清单

### 代码实现
- [x] STTEngine 抽象接口
- [x] FunASRSTTEngine 实现
- [x] VADDetector 抽象接口
- [x] FunASRVADDetector 实现
- [ ] 状态机 LISTENING 状态处理
- [ ] 状态机 PROCESSING 状态处理
- [ ] 配置文件更新

### 测试
- [ ] 单元测试 (STT)
- [ ] 单元测试 (VAD)
- [ ] 集成测试
- [ ] 完整流程测试

### 文档
- [ ] 开发文档
- [ ] API 参考
- [ ] 部署指南

---

**Phase 1.2 开发中...** 🚧

此文档将随着开发进度持续更新。
