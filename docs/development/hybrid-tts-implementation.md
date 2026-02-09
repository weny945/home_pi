# 混合 TTS 引擎使用说明

## 功能概述

混合 TTS 引擎实现了远程/本地自动切换功能：

1. **优先使用远程 TTS**（GPT-SoVITS API）- 音质更好
2. **远程失败时自动切换到本地 TTS**（Piper）- 保证可用性
3. **后台健康检查** - 每小时检测远程服务器是否恢复
4. **自动切回远程 TTS** - 当远程服务器恢复时自动切回

## 架构设计

```
┌─────────────────────────────────────────────────┐
│          Hybrid TTS Engine (混合引擎)           │
│  ┌───────────────────────────────────────────┐  │
│  │  策略: 优先远程 → 失败切换本地 → 自动恢复   │  │
│  └───────────────────────────────────────────┘  │
│                      │                          │
│        ┌─────────────┴─────────────┐           │
│        ↓                           ↓            │
│  ┌──────────────┐          ┌──────────────┐   │
│  │ Remote TTS   │          │  Local TTS   │   │
│  │ (GPT-SoVITS) │          │   (Piper)    │   │
│  │              │          │              │   │
│  │ HTTP API     │          │ ONNX Model   │   │
│  │ 高音质       │          │ 离线可用     │   │
│  └──────────────┘          └──────────────┘   │
│        ↓                           ↓            │
│  ┌──────────────────────────────────────────┐  │
│  │     后台健康检查线程 (每小时)             │  │
│  │  - 检测远程服务器状态                     │  │
│  │  - 自动切回远程 TTS                       │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

## 配置说明

### config.yaml 配置

```yaml
tts:
  # 引擎类型: "hybrid"(混合), "remote"(远程), "piper"(本地)
  engine: "hybrid"

  # 混合引擎配置
  hybrid:
    health_check_interval: 3600  # 健康检查间隔（秒），默认 1 小时
    auto_failback: true          # 是否自动切回远程 TTS

  # 远程 TTS 配置
  remote:
    enabled: true                # 是否启用远程 TTS
    server_ip: "192.168.1.100"   # ⚠️ 修改为你的电脑IP
    port: 9880                   # 端口号
    timeout: 60                  # 请求超时时间（秒）
    text_lang: "zh"              # 文本语言
    speed: 1.0                   # 语速 (0.6-1.65)

  # 本地 TTS 配置
  local:
    engine: "piper"
    model_path: "./models/piper/zh_CN-huayan-medium.onnx"
    length_scale: 1.0
```

### 引擎类型选择

1. **hybrid**（推荐）
   - 优先使用远程 TTS（高音质）
   - 失败自动切换本地 TTS（高可用）
   - 后台自动健康检查和恢复

2. **remote**
   - 仅使用远程 TTS
   - 服务器不可用时会失败

3. **piper**
   - 仅使用本地 TTS
   - 完全离线，不受网络影响

## 使用步骤

### 1. 启动远程 TTS 服务器

在 Windows 电脑上：
1. 双击运行 `start_api.bat`
2. 确认看到 "服务启动成功" 消息
3. 记下电脑的 IP 地址（运行 `ipconfig` 查看）

### 2. 配置树莓派

编辑 `config.yaml`：
```yaml
tts:
  engine: "hybrid"
  remote:
    server_ip: "192.168.1.100"  # ⚠️ 改成你的电脑IP
```

### 3. 测试连接

```bash
# 测试远程服务器连接
python tests/manual/test_remote_tts_connection.py -s 192.168.1.100

# 测试混合引擎
python tests/unit/test_hybrid_tts.py
```

### 4. 运行主程序

```bash
python main.py
```

## 工作流程

### 正常流程

```
用户说话 → STT识别 → LLM生成回复 → 混合TTS合成 → 播放音频
                                    ↓
                              检查远程TTS状态
                                    ↓
                         ┌──────────┴──────────┐
                         ↓                     ↓
                    远程可用                远程不可用
                         ↓                     ↓
                    使用远程TTS            使用本地TTS
                    (GPT-SoVITS)           (Piper)
```

### 故障切换流程

```
正在使用远程TTS
      ↓
远程请求失败（超时/连接错误/服务器错误）
      ↓
自动切换到本地TTS
      ↓
记录日志：⚠️ 远程TTS失败，切换到本地TTS
      ↓
继续使用本地TTS...
      ↓
[后台线程] 每小时检查远程服务器状态
      ↓
远程服务器恢复
      ↓
自动切回远程TTS
      ↓
记录日志：✅ 远程TTS已恢复，自动切换回远程
```

## 日志示例

### 启动日志

```
============================================================
混合 TTS 引擎初始化
============================================================
  远程引擎: RemoteTTSEngine
  本地引擎: PiperTTSEngine
  当前使用: 远程 TTS
  健康检查间隔: 3600 秒
  自动切回: 启用
============================================================
✅ 后台健康检查线程已启动
```

### 正常合成日志

```
DEBUG - 使用远程 TTS 合成
DEBUG - 请求远程 TTS: 今天天气真不错
DEBUG - ✅ 远程 TTS 合成成功: 238848 采样点
```

### 故障切换日志

```
WARNING - ⚠️  远程 TTS 合成失败: ConnectionError
INFO - 🔄 自动切换到本地 TTS
DEBUG - 使用本地 TTS 合成
DEBUG - ✅ 本地 TTS 合成成功: 238848 采样点
```

### 自动恢复日志

```
INFO - ✅ 远程 TTS 已恢复在线！
INFO -    自动切换回远程 TTS 引擎
```

## 健康检查机制

### 后台线程

混合引擎启动时会创建一个后台守护线程：
- **名称**: `TTS-HealthCheck`
- **类型**: Daemon（主程序退出时自动终止）
- **间隔**: 默认 1 小时（可配置）

### 检查逻辑

```python
while True:
    # 等待指定间隔
    time.sleep(health_check_interval)

    # 检查远程服务器状态
    is_available = remote_engine.check_health()

    # 如果从不可用恢复到可用
    if not was_available and is_available:
        # 自动切换回远程
        current_engine = "remote"
```

### 手动控制

```python
# 强制切换到远程TTS
hybrid_engine.force_remote()

# 强制切换到本地TTS
hybrid_engine.force_local()

# 获取状态
status = hybrid_engine.get_status()
```

## 故障排查

### 问题1: 远程TTS一直无法连接

**检查清单**：
- [ ] GPT-SoVITS API 服务是否已启动？
- [ ] 服务器 IP 地址是否正确？
- [ ] 防火墙是否放行 9880 端口？
- [ ] 树莓派和电脑是否在同一局域网？
- [ ] 网络连接是否正常？

**测试命令**：
```bash
# 测试网络连通性
ping 192.168.1.100

# 测试端口是否开放
telnet 192.168.1.100 9880

# 测试 API 响应
curl http://192.168.1.100:9880/status

# 使用测试脚本
python tests/manual/test_remote_tts_connection.py -s 192.168.1.100
```

### 问题2: 混合引擎一直使用本地TTS

**可能原因**：
1. 远程服务器未启动
2. `remote.enabled` 设置为 `false`
3. 远程引擎初始化失败

**解决方法**：
```bash
# 查看日志
tail -f logs/phase1.log | grep TTS

# 应该看到：
# ✅ 远程 TTS 引擎初始化成功
# 或
# ⚠️  远程 TTS 引擎初始化失败: ConnectionError
```

### 问题3: 自动切换不工作

**检查配置**：
```yaml
tts:
  hybrid:
    auto_failback: true  # 确保为 true
    health_check_interval: 3600  # 检查间隔是否合理
```

**手动触发健康检查**：
```python
from src.tts import HybridTTSEngine, RemoteTTSEngine, PiperTTSEngine

# 创建引擎
remote = RemoteTTSEngine("192.168.1.100")
local = PiperTTSEngine()
hybrid = HybridTTSEngine(remote, local, health_check_interval=30)

# 手动检查
hybrid._remote_engine.check_health()
```

## 性能对比

| 指标 | 远程 TTS (GPT-SoVITS) | 本地 TTS (Piper) |
|------|----------------------|------------------|
| 音质 | ⭐⭐⭐⭐⭐ 优秀 | ⭐⭐⭐ 一般 |
| 延迟 | ~2-5 秒（网络） | ~0.5-1 秒（本地） |
| 依赖 | 网络连接 | 无（完全离线） |
| CPU占用 | 服务器端 | 树莓派本地 |
| 可用性 | 中（依赖网络） | 高（本地运行） |

## 最佳实践

1. **开发/测试环境**：使用 `engine: "piper"`（本地TTS），避免网络依赖
2. **生产环境**：使用 `engine: "hybrid"`（混合引擎），兼顾音质和可用性
3. **网络不稳定**：增加 `timeout` 和 `health_check_interval`
4. **快速响应**：仅使用本地 TTS

## 相关文件

- **引擎实现**：
  - `src/tts/engine.py` - 抽象接口
  - `src/tts/remote_engine.py` - 远程TTS引擎
  - `src/tts/hybrid_engine.py` - 混合引擎
  - `src/tts/piper_engine.py` - 本地TTS引擎

- **配置**：
  - `config.yaml` - TTS 配置

- **测试**：
  - `tests/unit/test_hybrid_tts.py` - 混合引擎测试
  - `tests/manual/test_remote_tts_connection.py` - 连接测试

- **文档**：
  - `docs/tts-api/` - GPT-SoVITS API 文档
  - `docs/development/phase1.3-llm.md` - LLM/TTS 集成文档
