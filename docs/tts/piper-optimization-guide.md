# Piper TTS 语音优化配置指南

本文档详细说明了 `config.yaml` 中的 Piper TTS 配置选项，帮助你根据需求调整语音输出的音质、语速和表现力。

## 📋 目录

- [方案1：合成参数优化](#方案1合成参数优化)
- [方案2：文本增强功能](#方案2文本增强功能)
- [方案3：句间停顿控制](#方案3句间停顿控制)
- [配置示例](#配置示例)
- [常见问题](#常见问题)

---

## 方案1：合成参数优化

### 1.1 语速控制 (`length_scale`)

```yaml
length_scale: 1.0  # 语速缩放
```

**作用**：控制语音播放速度

**推荐值**：
| 值 | 效果 | 适用场景 |
|---|---|---|
| `0.7` | 更快 | 信息播报、新闻阅读 |
| `0.9` | 稍快 | 日常对话 |
| `1.0` | 正常（推荐） | 通用场景 |
| `1.2` | 较慢 | 讲故事、教学 |
| `1.5` | 很慢 | 强调重要信息 |

**注意事项**：
- 语速过快（< 0.7）可能导致发音不清晰
- 语速过慢（> 1.5）可能影响用户体验

---

### 1.2 音色随机性 (`noise_scale`)

```yaml
noise_scale: 0.667  # 音色随机性/情感波动
```

**作用**：控制语音生成的随机性，影响语音的"饱满度"和情感表现

**推荐值**：
| 值 | 效果 | 适用场景 |
|---|---|---|
| `0.5-0.6` | 机械、平淡 | 正式场合、新闻播报 |
| `0.667` | 默认值（平衡） | 通用场景（推荐） |
| `0.7-0.8` | 有情感、自然 | 日常对话、聊天 |
| `0.9-1.0` | 情感丰富、生动 | 讲故事、朗诵 |

**注意事项**：
- 值过小（< 0.5）：声音过于机械
- 值过大（> 1.0）：可能导致音质损耗

---

### 1.3 韵律变化 (`noise_w_scale`)

```yaml
noise_w_scale: 0.8  # 韵律噪声/语气变化
```

**作用**：控制语调变化的幅度，影响语音的"抑扬顿挫"

**推荐值**：
| 值 | 效果 | 适用场景 |
|---|---|---|
| `0.6-0.7` | 稳定、单调 | 新闻播报、正式场合 |
| `0.8` | 默认值（推荐） | 通用场景 |
| `0.9-1.0` | 语气变化大、生动 | 讲故事、聊天 |

**注意事项**：
- 建议与 `noise_scale` 配合调整
- 过高的值可能导致语调起伏过大

---

## 方案2：文本增强功能

### 2.1 自定义停顿标记

```yaml
text_enhancement:
  enabled: true  # 启用文本增强
  pause_marks_enabled: true  # 启用停顿标记解析
```

**功能**：支持在文本中插入自定义停顿标记

**使用方法**：
```python
# 在 LLM 回复或固定消息中使用停顿标记
text = "你好[PAUSE:0.3]，我是胡桃[PAUSE:0.5]，很高兴为你服务"
```

**转换规则**：
- `[PAUSE:0.3]` → 转换为逗号（短停顿）
- `[PAUSE:0.6]` → 转换为逗号+句号（中等停顿）
- `[PAUSE:1.0]` → 转换为多个标点（长停顿）

**参数配置**：
```yaml
text_enhancement:
  pause_to_punctuation:
    enabled: true
    commas_per_second: 2  # 每秒停顿对应2个逗号
```

---

### 2.2 文本清理规则

```yaml
text_enhancement:
  remove_wavy_tilde: true  # 移除波浪线（～~）
  fix_final_particles: true  # 修复句尾助词发音
```

**功能说明**：

1. **移除波浪线** (`remove_wavy_tilde`)
   - 问题：波浪线 "～~" 会导致 TTS 发音异常
   - 处理：自动移除所有波浪线

2. **修复句尾助词** (`fix_final_particles`)
   - 问题：句尾的"的"、"了"、"着"等助词发音不自然
   - 处理：自动在这些助词后添加逗号，增加停顿

---

## 方案3：句间停顿控制

### 3.1 配置说明

```yaml
sentence_silence: 0.2  # 句间停顿时长（秒）
```

**作用**：在音频末尾添加静音，增加语音的呼吸感和自然感

**推荐值**：
| 值 | 效果 | 适用场景 |
|---|---|---|
| `0.0` | 无停顿 | 连续播放、快速响应 |
| `0.2` | 自然呼吸感（推荐） | 日常对话 |
| `0.3-0.5` | 明显停顿 | 强调重要信息 |
| `0.5-1.0` | 长停顿 | 讲故事、教学 |

**注意事项**：
- 停顿时间会累积，影响整体播放时长
- 建议根据文本长度和场景灵活调整

---

## 配置示例

### 示例1：日常对话模式（推荐）

```yaml
tts:
  local:
    length_scale: 1.0      # 正常语速
    noise_scale: 0.7       # 略带情感
    noise_w_scale: 0.8     # 自然语调
    sentence_silence: 0.2  # 自然呼吸感

    text_enhancement:
      enabled: true
      pause_marks_enabled: true
      remove_wavy_tilde: true
      fix_final_particles: true
```

**特点**：平衡自然，适合大多数场景

---

### 示例2：新闻播报模式

```yaml
tts:
  local:
    length_scale: 0.95     # 稍快
    noise_scale: 0.6       # 机械、平稳
    noise_w_scale: 0.7     # 语调稳定
    sentence_silence: 0.1  # 短停顿

    text_enhancement:
      enabled: true
      pause_marks_enabled: false  # 禁用自定义停顿
      remove_wavy_tilde: true
      fix_final_particles: true
```

**特点**：快速、准确，适合信息播报

---

### 示例3：讲故事模式

```yaml
tts:
  local:
    length_scale: 1.2      # 较慢
    noise_scale: 0.8       # 情感丰富
    noise_w_scale: 0.9     # 语调生动
    sentence_silence: 0.5  # 明显停顿

    text_enhancement:
      enabled: true
      pause_marks_enabled: true
      pause_to_punctuation:
        commas_per_second: 1.5  # 更长的停顿
      remove_wavy_tilde: true
      fix_final_particles: true
```

**特点**：生动、有表现力，适合讲故事

---

### 示例4：极简模式（低资源）

```yaml
tts:
  local:
    length_scale: 1.0
    noise_scale: 0.667
    noise_w_scale: 0.8
    sentence_silence: 0.0   # 禁用停顿（减少计算）

    text_enhancement:
      enabled: false  # 禁用文本增强（提升速度）
```

**特点**：最快响应，适合低性能设备

---

## 常见问题

### Q1: 如何调整语音的情感表现力？

**A**: 主要通过 `noise_scale` 和 `noise_w_scale` 控制：

- **更平淡**：降低 `noise_scale` 到 0.5-0.6
- **更自然**：保持默认值（0.667 和 0.8）
- **更生动**：提高到 0.8-0.9

### Q2: 如何让语音听起来更像真人？

**A**: 推荐配置：

```yaml
noise_scale: 0.75          # 略高于默认
noise_w_scale: 0.85        # 增加语调变化
sentence_silence: 0.3      # 增加呼吸感
```

配合 LLM 的系统提示词，使用口语化表达。

### Q3: 语音播放速度太快/太慢怎么办？

**A**: 调整 `length_scale`：

- **太快**：增加到 1.2-1.5
- **太慢**：降低到 0.8-0.9

### Q4: 为什么文本中的 "～~" 会导致发音异常？

**A**: Piper TTS 会尝试将波浪线作为字符发音，导致异常。解决方案：

1. 启用 `remove_wavy_tilde: true`（自动移除）
2. 在 LLM 系统提示词中避免使用波浪线

### Q5: 如何在特定位置添加停顿？

**A**: 使用 `[PAUSE:X.X]` 标记：

```python
# 在 LLM 系统提示词或固定消息中
"你好[PAUSE:0.5]，请问有什么可以帮你的？"
```

### Q6: sentence_silence 和 [PAUSE] 标记有什么区别？

**A**:

| 特性 | `sentence_silence` | `[PAUSE:X.X]` |
|---|---|---|
| **作用位置** | 音频末尾 | 文本任意位置 |
| **实现方式** | 添加静音音频 | 添加标点符号 |
| **精度** | 固定时长 | 灵活控制 |
| **推荐场景** | 整体呼吸感 | 精细控制 |

建议两者配合使用，效果最佳。

### Q7: 如何验证配置是否生效？

**A**: 查看日志输出：

```
Piper TTS 配置: length_scale=1.0, noise_scale=0.7, noise_w_scale=0.8, sentence_silence=0.2s
```

如果未看到日志，检查配置文件路径和格式是否正确。

---

## 总结

### 推荐配置（日常使用）

```yaml
tts:
  local:
    length_scale: 1.0
    noise_scale: 0.7
    noise_w_scale: 0.8
    sentence_silence: 0.2

    text_enhancement:
      enabled: true
      pause_marks_enabled: true
      remove_wavy_tilde: true
      fix_final_particles: true
```

### 快速调整指南

| 需求 | 调整参数 |
|---|---|
| 语速更快/更慢 | `length_scale` ↓/↑ |
| 更平淡/更生动 | `noise_scale` ↓/↑ |
| 更单调/更抑扬顿挫 | `noise_w_scale` ↓/↑ |
| 增加呼吸感 | `sentence_silence` ↑ |
| 精细控制停顿 | 使用 `[PAUSE:X.X]` 标记 |

---

## 参考资源

- [Piper TTS GitHub](https://github.com/rhasspy/piper)
- [Piper 文档](https://rhasspy.github.io/piper/)
- [项目配置文件](../../config.yaml)
- [Piper 引擎实现](../../src/tts/piper_engine.py)
