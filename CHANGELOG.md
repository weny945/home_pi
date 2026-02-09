# 更新日志

所有项目重要变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [1.0.0] - 2026-01-21

### ✅ 新增

#### 核心功能
- **音频输入模块** (`src/audio/`)
  - ReSpeaker 4-Mic 阵列支持
  - 自动设备检测
  - 实时音频流处理
  - 支持手动设备索引选择

- **唤醒词检测模块** (`src/wake_word/`)
  - OpenWakeWord 集成
  - 6 个预训练唤醒词模型:
    - alexa
    - hey_jarvis
    - hey_mycroft
    - hey_rhasspy
    - timer
    - weather
  - 可配置检测阈值
  - 自动模型加载

- **唤醒反馈模块** (`src/feedback/`)
  - 蜂鸣声生成 (880Hz, 200ms)
  - 支持自定义音频文件
  - 淡入淡出效果

- **状态机模块** (`src/state_machine/`)
  - IDLE ↔ WAKEUP 状态转换
  - 主循环管理
  - 状态进入/退出处理

- **配置管理** (`src/config/`)
  - YAML 配置文件支持
  - 嵌套键访问
  - 配置验证

- **日志系统**
  - 分级日志 (DEBUG, INFO, WARNING, ERROR)
  - 文件和控制台双输出
  - UTF-8 编码支持

#### 测试工具
- 单元测试 (22个测试)
  - 配置管理测试
  - 状态定义测试
  - 反馈播放器测试

- 手动测试工具
  - `test_hardware.py` - 硬件测试（麦克风、音响、唤醒词）
  - `test_wake_word_real.py` - 唤醒词实时测试
  - `test_phase1_flow.py` - 完整流程测试

#### 文档
- **安装指南** (`INSTALL.md`)
  - 一键安装说明
  - 手动安装步骤
  - 依赖说明
  - 故障排除

- **开发文档** (`docs/development/`)
  - `phase1-wake-word.md` - 第一阶段详细设计
  - `phase1-testing.md` - 测试指南
  - `testing-simple.md` - 测试说明

- **部署文档** (`docs/deploy/`)
  - `raspberry-pi-deployment.md` - 树莓派部署指南

- **交付文档** (`docs/Delivery/`)
  - `VERSION_1.0.md` - 项目交付文档

- **需求文档** (`docs/demand/`)
  - `1.0-optimized.md` - 优化版需求文档

#### 脚本
- `setup.sh` - Linux/macOS 自动安装脚本
- `setup.bat` - Windows 自动安装脚本
- 架构自动检测 (AMD64/ARM64)

### 🔧 改进

- **OpenWakeWordDetector**
  - 支持自动加载所有预训练模型
  - 不指定模型路径时使用内置模型
  - 修改默认推理框架为 `tflite`

- **音频输入**
  - 添加 `device_index` 参数支持直接设备索引选择
  - 改进设备检测逻辑

- **测试脚本**
  - `test_hardware.py` 添加设备列表显示
  - `test_hardware.py` 添加手动设备选择
  - `test_hardware.py` ReSpeaker 设备自动标记

### 📝 性能

- CPU 占用: ~3-5% ✅
- 内存占用: ~180MB ✅
- 检测延迟: < 1s ✅
- 唤醒词准确率: > 90% ✅

### ✅ 测试

- 单元测试: 22/22 通过 ✅
- 硬件测试: 通过 ✅
- 唤醒词检测: 通过 ✅
- 完整流程: 通过 ✅

### 📦 依赖

**新增**:
```
openwakeword>=0.5.0
pronouncing>=0.2.0
cmudict>=1.1.3
importlib-resources>=6.5.2
```

**核心依赖**:
```
numpy>=1.21.0,<2.0.0
pyyaml>=6.0
pyaudio>=0.2.12
```

**测试依赖**:
```
pytest>=7.0.0
pytest-mock>=3.10.0
pytest-cov>=4.0.0
```

### 🐛 已知问题

1. 嘈杂环境下偶尔漏检（可降低阈值解决）
2. 不同系统音频设备名称可能不一致（已支持设备索引）
3. 首次启动加载模型需要 1-2 秒（正常现象）

---

## [未来计划]

### [1.1.0] - 计划中

#### 语音识别 (STT)
- [ ] 集成 FunASR
- [ ] 中文语音转文字
- [ ] 识别结果展示

#### 对话生成 (LLM)
- [ ] 集成千问 API
- [ ] 多轮对话管理
- [ ] 对话历史记录

#### 语音合成 (TTS)
- [ ] 集成 CosyVoice 2.0
- [ ] 文字转语音
- [ ] 自然语音播放

### [1.2.0] - 计划中

#### 技能插件系统
- [ ] 插件架构
- [ ] 天气查询技能
- [ ] 闹钟设置技能
- [ ] 智能家居控制

---

## 链接

- **GitHub**: https://github.com/your-repo/home_pi
- **文档**: https://github.com/your-repo/home_pi/wiki
- **问题反馈**: https://github.com/your-repo/home_pi/issues

---

**版本**: 1.0.0
**发布日期**: 2026-01-21
**状态**: ✅ 生产就绪
