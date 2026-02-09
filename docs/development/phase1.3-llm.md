# 第一阶段 1.3 开发文档：对话生成 (千问 API)

**版本**: 1.3
**日期**: 2026-01-22
**状态**: 🚧 开发中

---

## 📋 阶段目标

在 Phase 1.2 的基础上，添加**对话生成功能**，实现完整的语音交互闭环：

- **语音识别** (STT) - FunASR SenseVoiceSmall (离线)
- **对话生成** (LLM) - 阿里云千问 API (需联网)
- **语音合成** (TTS) - Piper TTS (离线)

### 核心功能

1. ✅ **语音识别** - FunASR 离线识别 (Phase 1.2 已实现)
2. 🆕 **对话生成** - 千问 API 在线对话
3. ✅ **语音合成** - Piper TTS 离线合成 (Phase 1.1 已实现)
4. 🆕 **完整交互流程** - 唤醒→TTS回复→录音→STT识别→LLM生成→TTS播报

### 版本对比

| 模块 | v1.2 | v1.3 | 变化 |
|------|------|------|------|
| **唤醒检测** | OpenWakeWord | OpenWakeWord | 无变化 |
| **语音回复** | Piper TTS | Piper TTS | 无变化 |
| **语音录制** | VAD 自动 | VAD 自动 | 无变化 |
| **语音识别** | FunASR 离线 | FunASR 离线 | 无变化 |
| **对话生成** | ❌ 无 | ✅ 千问 API | **新增** |
| **文本输出** | ✅ 控制台输出 | ❌ 无 | 移除 (改为语音播报) |
| **状态机** | IDLE→WAKEUP→LISTENING→PROCESSING→IDLE | IDLE→WAKEUP→LISTENING→PROCESSING→SPEAKING→IDLE | **新增 SPEAKING 状态** |

---

## 🎯 状态机设计

### 状态转换图

```
IDLE (监听唤醒词)
  ↓ 检测到唤醒词
WAKEUP (播放唤醒反馈)
  ↓ 播放完成
LISTENING (VAD 录音)
  ↓ 检测到语音结束
PROCESSING (STT 识别 + LLM 生成 + TTS 合成)
  ↓ 合成完成
SPEAKING (播放 TTS 回复)
  ↓ 播放完成
IDLE
```

### 状态定义

| 状态 | 描述 | 超时 | 转换条件 |
|------|------|------|----------|
| **IDLE** | 监听唤醒词 | 无 | 检测到唤醒词 → WAKEUP |
| **WAKEUP** | 播放唤醒反馈 | 无 | 播放完成 → LISTENING |
| **LISTENING** | VAD 录音 | 10s | 静音1.5s / 超时 → PROCESSING |
| **PROCESSING** | STT识别 + LLM生成 + TTS合成 | 5s | 合成完成 → SPEAKING |
| **SPEAKING** | 播放 TTS 回复 | 无 | 播放完成 → IDLE |
| **ERROR** | 错误状态 | 1s | 超时 → IDLE |

---

## 📁 模块结构

### 新增模块

```
src/
└── llm/                      # LLM 对话生成模块
    ├── __init__.py           # 模块初始化
    ├── engine.py             # LLM 引擎抽象接口
    └── qwen_engine.py        # 千问 API 实现
```

### 修改模块

```
src/
└── state_machine/
    └── machine.py            # 添加 SPEAKING 状态处理

main.py                       # 添加 LLM 和 TTS 引擎初始化
config.yaml                   # 添加 llm 和 tts 配置段
requirements.txt              # 添加 dashscope 依赖
requirements-arm64.txt        # 添加 dashscope 依赖
```

### 测试文件

```
tests/
├── unit/
│   └── test_llm.py           # LLM 模块单元测试
└── manual/
    └── test_phase13_llm.py   # Phase 1.3 集成测试工具
```

---

## 🔧 技术实现

### 技术选型

| 组件 | 技术方案 | 原因 |
|------|----------|------|
| **LLM 引擎** | 千问 API (DashScope SDK) | 中文支持好、响应快、价格合理 |
| **模型选择** | qwen-turbo | 速度快、适合实时对话 |
| **网络依赖** | 需要 API 请求 | 云端推理、无需本地 GPU |
| **TTS 播放** | 复用 Piper TTS | 与唤醒反馈使用同一引擎 |

### LLM 引擎接口设计

#### 抽象基类 (`src/llm/engine.py`)

```python
class LLMEngine(ABC):
    """LLM 引擎抽象基类"""

    @abstractmethod
    def generate(self, prompt: str, conversation_history: Optional[List] = None) -> str:
        """生成回复"""

    @abstractmethod
    def chat(self, message: str, conversation_history: Optional[List] = None) -> Dict:
        """对话接口（带完整返回信息）"""

    @abstractmethod
    def is_ready(self) -> bool:
        """检查引擎是否就绪"""

    @abstractmethod
    def get_model_info(self) -> Dict:
        """获取模型信息"""

    @abstractmethod
    def reset_conversation(self) -> None:
        """重置对话上下文"""

    @abstractmethod
    def get_conversation_history(self) -> List:
        """获取当前对话历史"""
```

#### 千问实现 (`src/llm/qwen_engine.py`)

**关键特性**:
- 支持 `qwen-turbo` / `qwen-plus` / `qwen-max` 模型
- 支持对话历史上下文
- 支持 API Key 环境变量配置
- 完整的错误处理

**初始化参数**:
```python
QwenLLMEngine(
    api_key: str,                    # DashScope API Key
    model: str = "qwen-turbo",       # 模型选择
    temperature: float = 0.7,        # 温度参数 (0-1)
    max_tokens: int = 1500,          # 最大 token 数
    enable_history: bool = True,     # 是否启用对话历史
    max_history: int = 10            # 最大历史轮数
)
```

**使用示例**:
```python
from src.llm import QwenLLMEngine

# 初始化引擎
llm = QwenLLMEngine(
    api_key="your-api-key",
    model="qwen-turbo",
    enable_history=True
)

# 生成回复
result = llm.chat("今天天气怎么样")
print(result["reply"])
print(result["usage"])  # Token 使用情况
```

### 状态机更新

#### 新增参数

```python
StateMachine(
    ...
    llm_engine: Optional['LLMEngine'] = None,  # LLM 引擎
    tts_engine: Optional['TTSEngine'] = None,  # TTS 引擎
    ...
)
```

#### PROCESSING 状态流程

```python
def _process_user_input(self) -> None:
    """处理用户输入：STT + LLM + TTS"""

    # Step 1: STT 语音识别
    user_text = self._stt_engine.transcribe(audio_data)

    # Step 2: LLM 对话生成
    result = self._llm_engine.chat(user_text)
    llm_reply = result["reply"]

    # Step 3: TTS 语音合成
    audio_data = self._tts_engine.synthesize(llm_reply)

    # 播放 TTS
    self._feedback_player.play_audio(audio_data)

    # 转换到 SPEAKING 状态
    self.transition_to(State.SPEAKING)
```

#### SPEAKING 状态

```python
def _update_speaking(self) -> None:
    """SPEAKING 状态更新：等待 TTS 播放完成"""
    if not self._feedback_player.is_playing():
        self.transition_to(State.IDLE)
```

---

## ⚙️ 配置管理

### config.yaml 新增配置

```yaml
# ========================================
# 对话生成配置 (LLM) - Phase 1.3
# ========================================
llm:
  enabled: true                          # 是否启用 LLM
  engine: "qwen"                         # LLM 引擎
  model: "qwen-turbo"                    # 模型选择

  # API 配置
  api_key: null                          # DashScope API Key

  # 生成参数
  temperature: 0.7                       # 温度参数 (0-1)
  max_tokens: 1500                       # 最大 token 数

  # 对话历史
  enable_history: true                   # 是否启用对话历史
  max_history: 10                        # 最大历史轮数

  # 系统提示词
  system_prompt: null                    # 系统提示词

# ========================================
# 语音合成配置 (TTS) - Phase 1.3
# ========================================
# 注意: 此配置与 feedback.tts 共享同一个引擎
tts:
  engine: "piper"
  model_path: "./models/piper/zh_CN-huayan-medium.onnx"
  length_scale: 1.0
```

### 配置参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `llm.enabled` | `true` | 是否启用 LLM 功能 |
| `llm.model` | `qwen-turbo` | 模型选择 (turbo/plus/max) |
| `llm.api_key` | `null` | DashScope API Key |
| `llm.temperature` | `0.7` | 温度参数，越高越随机 |
| `llm.max_tokens` | `1500` | 最大生成 token 数 |
| `llm.enable_history` | `true` | 是否启用对话历史 |
| `llm.max_history` | `10` | 最大对话历史轮数 |

### API Key 配置方式

**方式1: 环境变量 (推荐)**
```bash
export DASHSCOPE_API_KEY="your-api-key"
```

**方式2: 配置文件**
```yaml
llm:
  api_key: "your-api-key"
```

---

## 📊 性能指标

| 指标 | 目标 | 备注 |
|------|------|------|
| **LLM 响应延迟** | < 2s | 取决于网络和模型 |
| **Token 生成速度** | > 50 tokens/s | qwen-turbo |
| **对话历史支持** | 10 轮 | 可配置 |
| **API 调用成功率** | > 99% | 需要稳定网络 |

**API 定价参考** (2026-01):
- qwen-turbo: ¥0.008/1K tokens
- qwen-plus: ¥0.04/1K tokens
- qwen-max: ¥0.12/1K tokens

---

## 🧪 测试

### 单元测试

```bash
# 测试 LLM 模块
pytest tests/unit/test_llm.py -v
```

**测试覆盖**:
- LLM 引擎初始化
- API Key 配置
- 对话生成
- 对话历史管理
- 错误处理

### 集成测试

```bash
# 运行 Phase 1.3 集成测试
python tests/manual/test_phase13_llm.py
```

**测试选项**:
- `[1]` 测试 LLM 引擎初始化
- `[2]` 测试 LLM 对话生成
- `[3]` 测试对话历史
- `[4]` 测试 TTS 引擎
- `[5]` 测试完整流程 (LLM + TTS)
- `[a]` 运行所有测试

### 完整系统测试

```bash
# 启动主程序
python main.py
```

**测试流程**:
1. 说出唤醒词 "Alexa"
2. 听到 TTS 回复 "我在"
3. 说出问题（如"今天天气怎么样"）
4. 静音 1.5 秒
5. 听到 STT 识别结果（控制台输出）
6. 听到 LLM 生成回复（控制台输出）
7. 听到 TTS 语音播报

---

## 📝 API 参考

### QwenLLMEngine

```python
from src.llm import QwenLLMEngine

# 初始化
llm = QwenLLMEngine(
    api_key="your-api-key",
    model="qwen-turbo",
    temperature=0.7,
    max_tokens=1500,
    enable_history=True,
    max_history=10
)

# 生成回复
reply = llm.generate("你好")

# 对话接口（更多信息）
result = llm.chat("你好")
print(result["reply"])           # 回复文本
print(result["usage"])           # Token 使用
print(result["finish_reason"])   # 结束原因

# 对话历史
history = llm.get_conversation_history()
llm.reset_conversation()         # 重置历史

# 模型信息
info = llm.get_model_info()
print(info)
# {'name': 'qwen-turbo', 'provider': '阿里云 DashScope', ...}
```

---

## 🔗 后续阶段

### Phase 1.4 规划

- [ ] 添加多轮对话优化
- [ ] 添加意图识别
- [ ] 添加技能插件系统
- [ ] 优化响应速度

---

## ✅ 完成清单

### 代码实现
- [x] LLMEngine 抽象接口
- [x] QwenLLMEngine 实现
- [x] 状态机 SPEAKING 状态
- [x] PROCESSING 状态更新 (STT + LLM + TTS)
- [x] 配置文件更新
- [x] main.py 更新

### 测试
- [x] LLM 单元测试
- [x] 集成测试工具

### 文档
- [x] 开发文档
- [ ] API 参考
- [ ] 交付文档

---

## 📚 相关文档

- [Phase 1.1 开发文档](../development/phase1.1-piper-tts.md)
- [Phase 1.2 开发文档](../development/phase1.2-stt.md)
- [千问 API 文档](https://help.aliyun.com/zh/dashscope/)
- [DashScope SDK 文档](https://github.com/aliyun/dashscope)
