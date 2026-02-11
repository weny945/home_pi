# 豆包 TTS 集成指南（V3 HTTP 单向流式）

## 概述

豆包 TTS 是字节跳动火山引擎提供的语音合成服务，支持高质量中文语音合成。

## API 版本

- **V3 HTTP 单向流式 API**
- 文档: https://www.volcengine.com/docs/6561/1598757

## 获取 API 密钥

1. 访问 [火山引擎控制台](https://console.volcengine.com/speech/service)
2. 开通"语音合成"服务
3. 获取以下信息：
   - **APP ID**: 应用标识
   - **Access Token**: 访问令牌

## 配置说明

在 `config.yaml` 中添加以下配置：

```yaml
tts:
  engine: "doubao"  # 使用豆包 TTS

  doubao:
    # API 配置
    api_key: "${DOUBAO_ACCESS_KEY}"    # Access Token
    app_id: "${DOUBAO_APP_ID}"         # APP ID
    uid: "default_user"                # 用户标识

    # 资源 ID（模型版本）- 根据你的订阅选择
    resource_id: "seed-tts-2.0"        # 推荐：豆包语音合成模型 2.0

    # 模型版本（可选，仅模型 2.0 有效）
    model: "seed-tts-2.0-expressive"   # 表现力强，支持 QA/Cot

    # 发音人（模型 2.0）
    voice: "zh_female_qingxinmeili_moon_bigtts"  # 清新美丽-月（女声，推荐）

    # 音频参数
    format: "mp3"                      # 音频格式
    sample_rate: 24000                 # 采样率
    speed: 0                           # 语速（0=正常）
    volume: 0                          # 音量（0=正常）

    # 缓存
    cache:
      enabled: true                    # 启用缓存
      cache_dir: "./data/tts_cache"
```

> 💡 **提示**: 使用诊断工具找出你账户可用的 Resource ID：
> ```bash
> python tests/manual/diagnose_doubao_config.py
> ```

## 环境变量设置

推荐使用环境变量存储敏感信息：

```bash
# 方法 1: 临时设置
export DOUBAO_ACCESS_KEY="your_access_key_here"
export DOUBAO_APP_ID="your_app_id_here"

# 方法 2: 持久化设置（添加到 ~/.bashrc 或 .env.sh）
echo 'export DOUBAO_ACCESS_KEY="your_access_key_here"' >> ~/.bashrc
echo 'export DOUBAO_APP_ID="your_app_id_here"' >> ~/.bashrc
source ~/.bashrc
```

## 发音人列表

### 豆包语音合成模型 2.0 (resource_id: seed-tts-2.0) ✅ 推荐

| 发音人 ID | 描述 | 类型 |
|-----------|------|------|
| zh_female_qingxinmeili_moon_bigtts | 清新美丽-月 | 女声（推荐） |
| zh_female_wenrou_moon_bigtts | 温柔-月 | 女声 |
| zh_female_tianmei_moon_bigtts | 甜美-月 | 女声 |
| zh_male_wennuan_moon_bigtts | 温暖男声-月 | 男声（推荐） |
| zh_male_qingchen_moon_bigtts | 清朗-月 | 男声 |

### 豆包语音合成模型 1.0 (resource_id: seed-tts-1.0)

| 发音人 ID | 描述 | 类型 |
|-----------|------|------|
| zh_female_shuangkuaisisi_moon_bigtts | 双快思思-月 | 女声（推荐） |
| zh_female_qingxinmeili | 清新美丽女声 | 女声 |
| zh_female_wenrou | 温柔女声 | 女声 |
| zh_female_tianmei | 甜美女声 | 女声 |
| zh_female_huoli | 活力女声 | 女声 |
| zh_male_qingchen | 清朗男声 | 男声（推荐） |
| zh_male_chunhou | 醇厚男声 | 男声 |
| zh_male_wenhe | 温和男声 | 男声 |
| zh_male_huoli | 活力男声 | 男声 |

## 音频参数

### format（音频格式）
- `mp3`: 推荐格式，文件小，兼容性好
- `wav`: 无损格式，文件较大
- `pcm`: 原始 PCM 数据

### sample_rate（采样率）
- `8000`: 8kHz（电话质量）
- `16000`: 16kHz（标准语音）
- `24000`: 24kHz（推荐，高质量）
- `48000`: 48kHz（高保真）

### speed（语速）
- 范围: `[-50, 100]`
- `0`: 正常速度
- `-50`: 0.5 倍速
- `100`: 2.0 倍速

### volume（音量）
- 范围: `[-50, 100]`
- `0`: 正常音量
- `-50`: 0.5 倍音量
- `100`: 2.0 倍音量

## 测试

运行测试脚本验证配置：

```bash
# 设置环境变量
export DOUBAO_ACCESS_KEY="your_access_key"
export DOUBAO_APP_ID="your_app_id"

# 运行测试
python tests/manual/test_doubao_v3_tts.py
```

## 使用方式

### 1. 在反馈中使用（唤醒回复）

```yaml
feedback:
  mode: "tts"
  tts:
    engine: "doubao"
    # ... 豆包配置 ...
```

### 2. 在状态机中使用（LLM 回复）

```yaml
tts:
  engine: "doubao"
  # ... 豆包配置 ...
```

### 3. 代码中使用

```python
from src.tts import create_doubao_engine

config = {
    "doubao": {
        "api_key": "your_access_key",
        "app_id": "your_app_id",
        "voice": "zh_female_shuangkuaisisi_moon_bigtts",
    }
}

engine = create_doubao_engine(config)
audio_data = engine.synthesize("你好，我是胡桃")
```

## 计费

- 豆包 TTS 按字符数计费
- 新用户通常有免费额度
- 详情请查看火山引擎控制台的计费说明

## 故障排查

### 1. 认证失败
- 检查 APP ID 和 Access Token 是否正确
- 确认服务已开通

### 2. 发音人错误
- 检查发音人 ID 与 resource_id 是否匹配
- 模型 1.0 的发音人不适用于模型 2.0

### 3. 网络超时
- 检查网络连接
- 增加 `timeout` 参数

### 4. 音频无法播放
- 检查采样率与播放设备是否匹配
- 尝试不同的音频格式

## 参考资源

- [火山引擎控制台](https://console.volcengine.com/speech/service)
- [V3 HTTP 单向流式 API 文档](https://www.volcengine.com/docs/6561/1598757)
- [发音人列表](https://www.volcengine.com/docs/6561/1598757#_2-2%E8%AF%B7%E6%B1%82body)
